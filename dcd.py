import itertools
import re

import pandas as pd
import streamlit as st
import sympy as sp

from sympy import Symbol
from sympy.logic.boolalg import (
    And, Or, Not, Xor, simplify_logic
)

# --------------------------------------------------
# 1. DASHBOARD CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="Boolean Expression Simplifier",
    page_icon="🔌",
    layout="wide"
)

st.title("🔌 Boolean Expression Simplifier")
st.subheader("Digital Electronics Minor Project")
st.write(
    "Enter a Boolean expression to generate its simplified "
    "form, truth table, Karnaugh map and logic representation."
)

# --------------------------------------------------
# 2. EXPRESSION NORMALIZATION
# --------------------------------------------------

def normalize_expression(raw):

    expr = raw.strip()

    if not expr:
        raise ValueError("Please enter a Boolean expression.")

    expr = expr.replace("¬", "~")
    expr = expr.replace("!", "~")
    expr = expr.replace("·", "&")
    expr = expr.replace("*", "&")
    expr = expr.replace(".", "&")
    expr = expr.replace("+", "|")

    # Convert postfix complement: A' -> ~A
    expr = re.sub(
        r"([A-Za-z][A-Za-z0-9_]*)'",
        r"~\1",
        expr
    )

    # Convert parenthesized complement: (A+B)' -> ~(A+B)
    expr = re.sub(
        r"(\([^()]*\))'",
        r"~\1",
        expr
    )

    return expr


# --------------------------------------------------
# 3. BOOLEAN EXPRESSION PARSING
# --------------------------------------------------

def parse_boolean_expression(raw):

    normalized = normalize_expression(raw)

    names = sorted(
        set(re.findall(
            r"\b[A-Za-z][A-Za-z0-9_]*\b",
            normalized
        ))
    )

    if not names:
        raise ValueError("No Boolean variables found.")

    if len(names) > 6:
        raise ValueError("Maximum 6 variables are supported.")

    symbols = {
        name: Symbol(name)
        for name in names
    }

    try:
        expr = sp.sympify(
            normalized,
            locals=symbols,
            evaluate=False
        )
    except Exception:
        raise ValueError(
            "Invalid expression. Check operators and brackets."
        )

    # Validate expression nodes
    allowed = (Symbol, And, Or, Not, Xor)

    def validate(node):
        if isinstance(node, Symbol):
            return
        if node in (sp.true, sp.false):
            return
        if not isinstance(node, allowed):
            raise ValueError("Only Boolean operators are allowed.")
        for arg in node.args:
            validate(arg)

    validate(expr)

    return expr, [symbols[n] for n in names], names


# --------------------------------------------------
# 4. EVALUATE BOOLEAN EXPRESSION
# --------------------------------------------------

def evaluate_expr(expr, symbols, values):

    substitutions = {
        symbol: bool(value)
        for symbol, value in zip(symbols, values)
    }

    result = expr.subs(substitutions)

    return int(bool(result))


# --------------------------------------------------
# 5. GENERATE TRUTH TABLE
# --------------------------------------------------

def make_truth_table(expr, symbols, names):

    rows = []

    combinations = itertools.product(
        [0, 1],
        repeat=len(symbols)
    )

    for values in combinations:

        output = evaluate_expr(
            expr,
            symbols,
            values
        )

        rows.append(list(values) + [output])

    return pd.DataFrame(
        rows,
        columns=names + ["Output"]
    )


# --------------------------------------------------
# 6. GRAY CODE GENERATION
# --------------------------------------------------

def gray_code(n):

    return [
        i ^ (i >> 1)
        for i in range(2 ** n)
    ]


# --------------------------------------------------
# 7. GENERATE KARNAUGH MAP
# --------------------------------------------------

def make_kmap(df, names):

    n = len(names)

    if n < 2 or n > 4:
        return None

    if n == 2:
        row_vars = names[:1]
        col_vars = names[1:]

    elif n == 3:
        row_vars = names[:1]
        col_vars = names[1:]

    else:
        row_vars = names[:2]
        col_vars = names[2:]

    row_codes = gray_code(len(row_vars))
    col_codes = gray_code(len(col_vars))

    grid = []

    for r in row_codes:

        row = []

        for c in col_codes:

            assignment = {}

            for i, name in enumerate(row_vars):
                assignment[name] = (
                    r >> (len(row_vars) - 1 - i)
                ) & 1

            for i, name in enumerate(col_vars):
                assignment[name] = (
                    c >> (len(col_vars) - 1 - i)
                ) & 1

            match = df

            for name, bit in assignment.items():
                match = match[match[name] == bit]

            row.append(
                int(match.iloc[0]["Output"])
            )

        grid.append(row)

    row_labels = [
        format(x, f"0{len(row_vars)}b")
        for x in row_codes
    ]

    col_labels = [
        format(x, f"0{len(col_vars)}b")
        for x in col_codes
    ]

    return (
        pd.DataFrame(
            grid,
            index=row_labels,
            columns=col_labels
        ),
        row_vars,
        col_vars
    )


# --------------------------------------------------
# 8. LOGIC EXPRESSION TREE
# --------------------------------------------------

def to_dot(expr):

    lines = [
        "digraph BooleanCircuit {",
        'rankdir="TB";',
        'node [shape=box, style="rounded,filled", fillcolor="#EAF2F8"];'
    ]

    counter = [0]

    def walk(node):

        counter[0] += 1
        current = f"n{counter[0]}"

        if node in (sp.true, sp.false):

            label = "1" if node == sp.true else "0"

            lines.append(
                f'{current} [label="{label}", shape=ellipse];'
            )

            return current

        if isinstance(node, Symbol):

            lines.append(
                f'{current} [label="{node}", shape=ellipse];'
            )

            return current

        if isinstance(node, Not):
            label = "NOT"

        elif isinstance(node, And):
            label = "AND"

        elif isinstance(node, Or):
            label = "OR"

        elif isinstance(node, Xor):
            label = "XOR"

        else:
            label = str(node)

        lines.append(
            f'{current} [label="{label}"];'
        )

        for arg in node.args:

            child = walk(arg)

            lines.append(
                f"{child} -> {current};"
            )

        return current

    walk(expr)

    lines.append("}")

    return "\n".join(lines)


# --------------------------------------------------
# 9. USER INPUT
# --------------------------------------------------

st.divider()

expression = st.text_input(
    "Enter Boolean Expression",
    value="(A & B) | (A & ~B)"
)

form = st.selectbox(
    "Select Simplification Type",
    [
        "SOP (Sum of Products)",
        "POS (Product of Sums)",
        "Both"
    ]
)

simplify_button = st.button(
    "SIMPLIFY EXPRESSION",
    type="primary",
    use_container_width=True
)


# --------------------------------------------------
# 10. MAIN PROCESSING
# --------------------------------------------------

if simplify_button:

    try:

        expr, symbols, names = parse_boolean_expression(
            expression
        )

        # Generate SOP and POS
        sop = simplify_logic(
            expr,
            form="dnf",
            force=True
        )

        pos = simplify_logic(
            expr,
            form="cnf",
            force=True
        )

        # Generate truth table
        df = make_truth_table(
            expr,
            symbols,
            names
        )

        # Dashboard metrics
        total_rows = 2 ** len(names)

        total_minterms = int(
            df["Output"].sum()
        )

        st.success("Expression simplified successfully!")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Variables",
            len(names)
        )

        col2.metric(
            "Truth Table Rows",
            total_rows
        )

        col3.metric(
            "Minterms",
            total_minterms
        )

        # ------------------------------------------
        # SIMPLIFIED EXPRESSION
        # ------------------------------------------

        st.header("1. Simplified Expression")
        if form == "SOP (Sum of Products)":

            st.code(f"SOP = {sop}")

        elif form == "POS (Product of Sums)":

            st.code(f"POS = {pos}")

        else:

            st.code(
                f"SOP = {sop}\nPOS = {pos}"
            )

        # ------------------------------------------
        # TRUTH TABLE
        # ------------------------------------------

        st.header("2. Truth Table")

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True
        )

        # ------------------------------------------
        # MINTERMS AND MAXTERMS
        # ------------------------------------------

        st.header("3. Minterms and Maxterms")

        minterms = [
            i for i, value in enumerate(df["Output"])
            if value == 1
        ]

        maxterms = [
            i for i, value in enumerate(df["Output"])
            if value == 0
        ]

        st.write("Minterms:", minterms)
        st.write("Maxterms:", maxterms)

        # ------------------------------------------
        # K-MAP
        # ------------------------------------------

        st.header("4. Karnaugh Map")

        km = make_kmap(df, names)

        if km is not None:

            km_df, row_vars, col_vars = km

            st.write(
                f"Rows: {row_vars} | Columns: {col_vars}"
            )

            st.dataframe(
                km_df,
                use_container_width=True
            )

        else:

            st.info(
                "K-map is available for 2, 3 and 4 variables."
            )

        # ------------------------------------------
        # LOGIC TREE
        # ------------------------------------------

        st.header("5. Logic Expression Tree")

        st.graphviz_chart(
            to_dot(sop),
            use_container_width=True
        )

        # ------------------------------------------
        # VERIFICATION
        # ------------------------------------------

        st.header("6. Equivalence Verification")

        selected = (
            pos if form == "POS (Product of Sums)"
            else sop
        )

        equivalence = sp.simplify_logic(
            sp.Equivalent(expr, selected),
            force=True
        )

        if equivalence == sp.true:

            st.success(
                "Original and simplified expressions are equivalent."
            )

        else:

            st.error(
                "Expressions are not equivalent."
            )

        # ------------------------------------------
        # DOWNLOAD TRUTH TABLE
        # ------------------------------------------

        st.header("7. Download Results")

        csv = df.to_csv(
            index=False
        ).encode("utf-8")

        st.download_button(
            label="Download Truth Table CSV",
            data=csv,
            file_name="truth_table.csv",
            mime="text/csv"
        )

    except Exception as e:

        st.error(str(e))


# --------------------------------------------------
# 11. FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "Boolean Expression Simplification System | "
    "Python Minor Project | Digital Electronics"
)