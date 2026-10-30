import streamlit as st
import pandas as pd

# =========================================================
# PAGE
# =========================================================

st.set_page_config(
    page_title="Trading Scanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =========================================================
# MOBILE COMPACT CSS
# =========================================================

st.markdown("""
<style>

/* Main page spacing */
.block-container {
    padding-top: 0.4rem !important;
    padding-bottom: 0.5rem !important;
    padding-left: 0.45rem !important;
    padding-right: 0.45rem !important;
    max-width: 100% !important;
}

/* Hide Streamlit unnecessary space */
header[data-testid="stHeader"] {
    height: 0px;
}

/* Compact headings */
h1, h2, h3 {
    margin-top: 0.2rem !important;
    margin-bottom: 0.2rem !important;
}

/* Compact inputs */
div[data-testid="stNumberInput"] {
    margin-bottom: 0px !important;
}

div[data-testid="stNumberInput"] input {
    min-height: 38px !important;
    height: 38px !important;
    font-size: 16px !important;
    padding: 4px 7px !important;
}

div[data-testid="stNumberInput"] label {
    font-size: 11px !important;
    margin-bottom: 1px !important;
}

/* Reduce vertical gaps */
div[data-testid="stVerticalBlock"] {
    gap: 0.35rem !important;
}

/* Compact columns */
div[data-testid="column"] {
    padding: 0px 2px !important;
}

/* Compact dataframe */
div[data-testid="stDataFrame"] {
    font-size: 12px !important;
}

/* Top market cards */
.market-card {
    border: 1px solid #3a3d47;
    border-radius: 8px;
    padding: 5px 3px;
    text-align: center;
    min-height: 62px;
}

.market-name {
    font-size: 10px;
    color: #aeb4bf;
    line-height: 1.1;
}

.market-open {
    font-size: 11px;
    margin-top: 3px;
}

.market-code {
    font-size: 20px;
    font-weight: 800;
    line-height: 1.1;
}

/* Section labels */
.small-title {
    font-size: 12px;
    font-weight: 700;
    margin-top: 4px;
    margin-bottom: 2px;
    color: #c9ced8;
}

/* Buy / Sell colors */
.buy-text {
    color: #16a34a;
    font-weight: 800;
}

.sell-text {
    color: #ef4444;
    font-weight: 800;
}

/* Mobile */
@media (max-width: 600px) {

    .block-container {
        padding-left: 5px !important;
        padding-right: 5px !important;
    }

    div[data-testid="stHorizontalBlock"] {
        gap: 4px !important;
    }

    div[data-testid="column"] {
        min-width: 0 !important;
    }

    .market-name {
        font-size: 8px;
    }

    .market-open {
        font-size: 9px;
    }

    .market-code {
        font-size: 17px;
    }
}

</style>
""", unsafe_allow_html=True)


# =========================================================
# DIGIT FUNCTIONS
# =========================================================

def open_digit_code(price):

    if price <= 0:
        return "-", 0, 0

    # 22964.50 -> "2296450"
    text = f"{price:.2f}"

    digits = [
        int(x)
        for x in text
        if x.isdigit()
    ]

    first_sum = sum(digits)

    single = first_sum

    while single > 9:
        single = sum(
            int(x)
            for x in str(single)
        )

    code = f"{first_sum}{single}"

    return code, first_sum, single


def strike_digit(strike):

    strike = int(strike)

    total = sum(
        int(x)
        for x in str(abs(strike))
    )

    while total > 9:

        total = sum(
            int(x)
            for x in str(total)
        )

    return total


# =========================================================
# DEMO OPTION DATA
# Later Angel One live feed will replace this function
# =========================================================

def make_demo_data():

    rows = []

    spot = 23250

    for strike in range(
        21000,
        25501,
        50
    ):

        distance = strike - spot

        # Demo premiums only
        ce = max(
            5,
            150 - (distance * 0.025)
        )

        pe = max(
            5,
            150 + (distance * 0.025)
        )

        ce = round(
            ce + ((strike // 50) % 7),
            2
        )

        pe = round(
            pe + ((strike // 50) % 5),
            2
        )

        rows.append({
            "strike": strike,
            "digit": strike_digit(strike),
            "ce": ce,
            "pe": pe
        })

    return pd.DataFrame(rows)


# =========================================================
# HEADER
# =========================================================

st.markdown(
    "<div style='font-size:16px;font-weight:800;'>"
    "📊 TRADING SCANNER"
    "</div>",
    unsafe_allow_html=True
)


# =========================================================
# OPEN PRICE INPUTS
# =========================================================

st.markdown(
    '<div class="small-title">DAY OPEN / DIGIT CODE</div>',
    unsafe_allow_html=True
)

open_cols = st.columns(4)

with open_cols[0]:

    nifty_open = st.number_input(
        "NIFTY",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="nifty_open"
    )

with open_cols[1]:

    nifty_future_open = st.number_input(
        "NIFTY FUT",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="nifty_future_open"
    )

with open_cols[2]:

    sensex_open = st.number_input(
        "SENSEX",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="sensex_open"
    )

with open_cols[3]:

    sensex_future_open = st.number_input(
        "SENSEX FUT",
        min_value=0.0,
        value=0.0,
        step=0.05,
        format="%.2f",
        key="sensex_future_open"
    )


# =========================================================
# DIGIT CODE CARDS
# =========================================================

nifty_code, _, _ = open_digit_code(
    nifty_open
)

nifty_fut_code, _, _ = open_digit_code(
    nifty_future_open
)

sensex_code, _, _ = open_digit_code(
    sensex_open
)

sensex_fut_code, _, _ = open_digit_code(
