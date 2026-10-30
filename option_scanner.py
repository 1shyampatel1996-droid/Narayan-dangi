import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NIFTY SENSEX Option Scanner",
    page_icon="📈",
    layout="wide"
)


# ---------------- DIGIT CALCULATION ----------------

def digit_sum(value):
    digits = [int(x) for x in str(value) if x.isdigit()]
    total = sum(digits)

    reduced = total
    while reduced > 9:
        reduced = sum(int(x) for x in str(reduced))

    code = f"{total:02d}{reduced}"
    return total, reduced, code


def strike_digit(strike):
    digits = [int(x) for x in str(int(float(strike)))]
    total = sum(digits)

    while total > 9:
        total = sum(int(x) for x in str(total))

    return total


def price_matches(ltp, target, pct):
    if target <= 0:
        return False

    lower = target * (1 - pct / 100)
    upper = target * (1 + pct / 100)

    return lower <= ltp <= upper


# ---------------- DEMO DATA ----------------

def demo_data():

    rows = []

    markets = [
        ("NIFTY", range(22900, 23601, 50), 23250),
        ("SENSEX", range(73700, 74801, 100), 74200)
    ]

    for underlying, strikes, reference in markets:

        for strike in strikes:

            digit = strike_digit(strike)
            distance = abs(strike - reference)

            ce = max(8, 155 - distance * 0.20)
            pe = max(8, 155 - distance * 0.20)

            ce += (strike % 7) * 1.7
            pe += (strike % 9) * 1.3

            rows.append({
                "underlying": underlying,
                "expiry": "DEMO",
                "strike": strike,
                "option_type": "CE",
                "ltp": round(ce, 2),
                "strike_digit": digit
            })

            rows.append({
                "underlying": underlying,
                "expiry": "DEMO",
                "strike": strike,
                "option_type": "PE",
                "ltp": round(pe, 2),
                "strike_digit": digit
            })

    return pd.DataFrame(rows)


# ---------------- CSV DATA ----------------

def normalize_chain(df):

    required = {
        "underlying",
        "strike",
        "option_type",
        "ltp"
    }

    missing = required - set(df.columns)

    if missing:
        raise ValueError(
            "CSV में जरूरी columns missing हैं: "
            + ", ".join(missing)
        )

    out = df.copy()

    out["underlying"] = (
        out["underlying"].astype(str).str.upper().str.strip()
    )

    out["option_type"] = (
        out["option_type"].astype(str).str.upper().str.strip()
    )

    out["strike"] = pd.to_numeric(
        out["strike"], errors="coerce"
    )

    out["ltp"] = pd.to_numeric(
        out["ltp"], errors="coerce"
    )

    out = out.dropna(subset=["strike", "ltp"])

    out = out[out["option_type"].isin(["CE", "PE"])]

    out["strike_digit"] = out["strike"].apply(strike_digit)

    if "expiry" not in out.columns:
        out["expiry"] = "—"

    return out


# ---------------- BUY SELL INPUTS ----------------

def make_targets():

    buy = []
    sell = []

    for i in range(1, 4):

        value = st.session_state.get(f"buy_{i}", 0)

        if value and value > 0:
            buy.append((f"BUY {i}", float(value)))

    for i in range(1, 3):

        value = st.session_state.get(f"sell_{i}", 0)

        if value and value > 0:
            sell.append((f"SELL {i}", float(value)))

    return buy, sell


# ---------------- DASHBOARD ----------------

st.title("📈 NIFTY / SENSEX OPTION SCANNER")

st.caption(
    "Digit Scanner | CE / PE | Buy Sell Price Matching"
)

st.divider()


# ---------------- DAY OPEN PRICE ----------------

st.subheader("1. DAY OPEN PRICE")

open_cols = st.columns(4)

open_fields = [
    ("NIFTY 50 INDEX", "open_nifty"),
    ("NIFTY CURRENT FUTURE", "open_nifty_fut"),
    ("SENSEX INDEX", "open_sensex"),
    ("SENSEX CURRENT FUTURE", "open_sensex_fut")
]

for col, (label, key) in zip(open_cols, open_fields):

    with col:

        st.number_input(
            label,
            min_value=0.0,
            value=0.0,
            step=0.05,
            key=key
        )


st.subheader("OPEN PRICE DIGIT CODE")

calc_cols = st.columns(4)

for col, (label, key) in zip(calc_cols, open_fields):

    value = st.session_state[key]

    with col:

        if value > 0:

            total, reduced, code = digit_sum(value)

            st.metric(
                label,
                code
            )

            st.caption(
                f"Digit Sum: {total} | Single Digit: {reduced}"
            )

        else:

            st.metric(label, "—")


st.divider()


# ---------------- SCANNER SETTINGS ----------------

st.subheader("2. OPTION CHAIN SETTINGS")

left, right = st.columns(2)

with left:

    selected_underlying = st.selectbox(
        "SELECT MARKET",
        ["NIFTY", "SENSEX"]
    )

    expiry_choice = st.text_input(
        "EXPIRY FILTER (OPTIONAL)",
        value=""
    )

    default_spot = (
        23250.0 if selected_underlying == "NIFTY"
        else 74200.0
    )

    spot = st.number_input(
        "CURRENT SPOT / FUTURE PRICE",
        min_value=0.0,
        value=default_spot,
        step=1.0
    )


with right:

    digit_col1, digit_col2 = st.columns(2)

    with digit_col1:

        strike_digit_a = st.number_input(
            "STRIKE DIGIT COLUMN 1",
            min_value=0,
            max_value=9,
            value=6,
            step=1
        )

    with digit_col2:

        strike_digit_b = st.number_input(
            "STRIKE DIGIT COLUMN 2",
            min_value=0,
            max_value=9,
            value=3,
            step=1
        )

    pct = st.number_input(
        "PRICE MATCHING RANGE (%)",
        min_value=0.1,
        max_value=50.0,
        value=10.0,
        step=0.5
    )


st.info(
    "दोनों Strike Digit Boxes में अलग-अलग digit डाल सकते हैं। "
    "दोनों की scanning अलग-अलग होगी।"
)


# ---------------- BUY SELL PRICES ----------------

st.divider()

st.subheader("3. BUY AND SELL PRICE INPUTS")

buy_cols = st.columns(3)

for i, col in enumerate(buy_cols, start=1):

    with col:

        st.number_input(
            f"BUY PRICE {i} (₹)",
            min_value=0.0,
            value=0.0,
            step=0.05,
            key=f"buy_{i}"
        )


sell_cols = st.columns(2)

for i, col in enumerate(sell_cols, start=1):

    with col:

        st.number_input(
            f"SELL PRICE {i} (₹)",
            min_value=0.0,
            value=0.0,
            step=0.05,
            key=f"sell_{i}"
        )


# ---------------- MARKET DATA ----------------

st.divider()

st.subheader("4. MARKET DATA")

source = st.radio(
    "SELECT DATA SOURCE",
    ["Demo Sample Data", "CSV Upload"],
    horizontal=True
)


if source == "CSV Upload":

    uploaded = st.file_uploader(
        "UPLOAD OPTION CHAIN CSV",
        type=["csv"]
    )

    if uploaded is not None:

        try:

            chain = normalize_chain(
                pd.read_csv(uploaded)
            )

            st.success(
                f"CSV Loaded: {len(chain)} rows"
            )

        except Exception as exc:

            st.error(str(exc))
            chain = demo_data()

    else:

        st.info("CSV upload होने तक Demo Data दिखेगा।")
        chain = demo_data()

else:

    chain = demo_data()

    st.warning(
        "यह Demo Data है। Live Market Price नहीं है।"
    )


# ---------------- FILTER DATA ----------------

if expiry_choice.strip():

    chain = chain[
        chain["expiry"].astype(str).str.contains(
            expiry_choice.strip(),
            case=False,
            na=False
        )
    ]


chain = chain[
    chain["underlying"] == selected_underlying
].copy()


# ---------------- STRIKE SCANNER ----------------

st.divider()

st.subheader(
    "5. PREVIOUS / CURRENT / NEXT STRIKE SCANNER"
)

if not chain.empty:

    buy_targets, sell_targets = make_targets()

    digit_settings = [
        ("STRIKE DIGIT COLUMN 1", int(strike_digit_a)),
        ("STRIKE DIGIT COLUMN 2", int(strike_digit_b))
    ]

    for column_name, selected_digit in digit_settings:

        st.markdown(
            f"### {column_name}: {selected_digit}"
        )

        strikes = sorted(
            chain.loc[
                chain["strike_digit"] == selected_digit,
                "strike"
            ].dropna().unique()
        )

        if not strikes:

            st.warning(
                f"Digit {selected_digit} की कोई matching strike नहीं मिली।"
            )

            continue


        # CURRENT STRIKE = nearest matching strike
        # at or below the entered spot price.

        below = [
            strike for strike in strikes
            if strike <= spot
        ]

        if below:

            current = below[-1]

        else:

            current = min(
                strikes,
                key=lambda x: abs(x - spot)
            )


        index = strikes.index(current)

        chosen = []

        if index > 0:

            chosen.append(
                ("PREVIOUS", strikes[index - 1])
            )

        chosen.append(
            ("CURRENT", current)
        )

        if index + 1 < len(strikes):

            chosen.append(
                ("NEXT", strikes[index + 1])
            )


        records = []

        for position, strike in chosen:

            for option_type in ["CE", "PE"]:

                subset = chain[
                    (chain["strike"] == strike)
                    &
                    (chain["option_type"] == option_type)
                ]

                for _, row in subset.iterrows():

                    ltp = float(row["ltp"])

                    buy_hits = [
                        name
                        for name, target in buy_targets
                        if price_matches(ltp, target, pct)
                    ]

                    sell_hits = [
                        name
                        for name, target in sell_targets
                        if price_matches(ltp, target, pct)
                    ]

                    records.append({

                        "POSITION": position,

                        "EXPIRY": row.get(
                            "expiry", "—"
                        ),

                        "STRIKE PRICE": int(strike),

                        "STRIKE DIGIT": selected_digit,

                        "OPTION": option_type,

                        "LTP (₹)": ltp,

                        "BUY MATCH": (
                            ", ".join(buy_hits)
                            if buy_hits else "—"
                        ),

                        "SELL MATCH": (
                            ", ".join(sell_hits)
                            if sell_hits else "—"
                        )

                    })


        if records:

            result = pd.DataFrame(records)

            def highlight_matches(row):

                styles = []

                for column in result.columns:

                    if (
                        column == "BUY MATCH"
                        and row["BUY MATCH"] != "—"
                    ):

                        styles.append(
                            "background-color: #d9fbe5; "
                            "color: #14532d; font-weight: bold"
                        )

                    elif (
                        column == "SELL MATCH"
                        and row["SELL MATCH"] != "—"
                    ):

                        styles.append(
                            "background-color: #ffe0e0; "
                            "color: #7f1d1d; font-weight: bold"
                        )

                    else:

                        styles.append("")

                return styles


            styled = result.style.apply(
                highlight_matches,
                axis=1
            )

            st.dataframe(
                styled,
                use_container_width=True,
                hide_index=True
            )

        else:

            st.warning(
                "इन strikes के CE/PE contracts नहीं मिले।"
            )


    st.caption(
        f"Green = Buy Match | Red = Sell Match | "
        f"Price Range = ±{pct}%"
    )


else:

    st.warning(
        "Selected market का data उपलब्ध नहीं है।"
    )


# ---------------- CSV FORMAT ----------------

with st.expander("CSV FORMAT"):

    st.code(
        """underlying,expiry,strike,option_type,ltp
NIFTY,DEMO,23000,CE,101.50
NIFTY,DEMO,23000,PE,98.25
SENSEX,DEMO,74000,CE,120.00
SENSEX,DEMO,74000,PE,115.00""",
        language="csv"
    )


# ---------------- IMPORTANT ----------------

st.divider()

st.warning(
    """
IMPORTANT:

1. अभी यह app Demo Data और CSV पर चलता है।
2. Angel One Live WebSocket अभी connect नहीं है।
3. यह app अपने आप BUY या SELL order नहीं भेजता।
4. Green और Red केवल price match बताते हैं,
   executed order की पुष्टि नहीं करते।
5. Live trading से पहले Paper Trading और testing करें।
6. अपना Angel One password, PIN, TOTP या API Secret
   किसी के साथ share न करें।
"""
)
