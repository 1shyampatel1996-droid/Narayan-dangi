import time
from datetime import datetime
from zoneinfo import ZoneInfo
from html import escape

import pandas as pd
import pyotp
import requests
import streamlit as st
from SmartApi import SmartConnect

st.set_page_config(
    page_title="Angel Digit Scanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

IST = ZoneInfo("Asia/Kolkata")
MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)

st.markdown("""
<style>
.block-container {
    max-width: 100%;
    padding: 1rem .45rem .5rem;
}
div[data-testid="stVerticalBlock"] {gap: .4rem;}
div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: .4rem;
}
div[data-testid="stColumn"] {
    min-width: 0 !important;
}
.market-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    position: sticky;
    top: 0;
    z-index: 20;
    background: var(--background-color, #10141c);
}
.market-card {
    padding: 7px 3px;
    border: 1px solid #687184;
    border-radius: 8px;
    text-align: center;
    overflow-wrap: anywhere;
}
.market-name {font-size: 10px;}
.market-open {font-size: 12px; margin-top: 3px;}
.market-code {font-size: 23px; font-weight: 800; color: #22c55e;}
.market-time {font-size: 9px; opacity: .7;}
</style>
""", unsafe_allow_html=True)


def digit(value):
    total = sum(int(c) for c in str(abs(int(value))))
    while total > 9:
        total = sum(int(c) for c in str(total))
    return total


def open_code(value):
    if value is None or value <= 0:
        return "—"
    total = sum(int(c) for c in f"{value:.2f}" if c.isdigit())
    return f"{total:02d}{digit(total)}"


def positive(value):
    try:
        value = float(value)
        return value if pd.notna(value) and value > 0 else None
    except (TypeError, ValueError):
        return None


def credentials():
    names = [
        "ANGEL_API_KEY", "ANGEL_CLIENT_ID",
        "ANGEL_PIN", "ANGEL_TOTP_SECRET",
    ]
    try:
        values = {
            name: str(st.secrets.get(name, "")).strip()
            for name in names
        }
    except FileNotFoundError:
        values = {}

    if not all(values.get(name) for name in names):
        st.info(
            "Streamlit Settings → Secrets में चारों "
            "ANGEL values जोड़कर Save करें।"
        )
        st.stop()
    return values


def connect():
    today = datetime.now(IST).date().isoformat()
    if st.session_state.get("angel_login_day") != today:
        st.session_state.pop("angel_client", None)

    if "angel_client" not in st.session_state:
        values = credentials()
        try:
            client = SmartConnect(
                api_key=values["ANGEL_API_KEY"], timeout=12
            )
            otp = pyotp.TOTP(values["ANGEL_TOTP_SECRET"]).now()
            result = client.generateSession(
                values["ANGEL_CLIENT_ID"],
                values["ANGEL_PIN"],
                otp,
            )
            if not isinstance(result, dict) or not result.get("status"):
                raise ValueError("Login rejected")
        except Exception:
            st.error(
                "Angel One login नहीं हुआ। API key, Client ID, "
                "PIN और TOTP secret जाँचें।"
            )
            st.stop()

        st.session_state.angel_client = client
        st.session_state.angel_login_day = today
    return st.session_state.angel_client


@st.cache_data(ttl=3600, show_spinner=False)
def instrument_master(day):
    response = requests.get(MASTER_URL, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())
    required = {
        "token", "symbol", "name", "exch_seg",
        "instrumenttype", "expiry", "strike",
    }
    if not required.issubset(frame.columns):
        raise ValueError("Invalid instrument master")

    for col in ["token", "symbol", "name", "exch_seg", "instrumenttype"]:
        frame[col] = frame[col].fillna("").astype(str).str.strip()

    frame["expiry_date"] = pd.to_datetime(
        frame["expiry"], format="%d%b%Y", errors="coerce"
    )
    frame["strike_price"] = (
        pd.to_numeric(frame["strike"], errors="coerce") / 100
    )
    return frame


def spot_instrument(frame, exchange, aliases):
    names = frame["name"].str.upper()
    symbols = frame["symbol"].str.upper()
    matches = frame[
        frame["exch_seg"].eq(exchange)
        & (names.isin(aliases) | symbols.isin(aliases))
    ]
    if matches.empty:
        raise ValueError("Spot index token not found")
    return matches.iloc[0]


def current_future(frame, name, exchange, today):
    matches = frame[
        frame["name"].str.upper().eq(name)
        & frame["exch_seg"].eq(exchange)
        & frame["instrumenttype"].eq("FUTIDX")
        & frame["expiry_date"].ge(pd.Timestamp(today))
    ].sort_values("expiry_date")
    return None if matches.empty else matches.iloc[0]


def quotes(client, instruments):
    tokens = {}
    for item in instruments:
        exchange = str(item["exch_seg"])
        token = str(item["token"])
        tokens.setdefault(exchange, [])
        if token not in tokens[exchange]:
            tokens[exchange].append(token)

    if not tokens:
        return {}

    # Space consecutive market-data requests.
    last = st.session_state.get("last_market_request", 0)
    remaining = 1.1 - (time.monotonic() - last)
    if remaining > 0:
        time.sleep(remaining)

    st.session_state.last_market_request = time.monotonic()
    try:
        result = client.getMarketData("FULL", tokens)
        if not isinstance(result, dict) or not result.get("status"):
            raise ValueError("Market data rejected")
        fetched = (result.get("data") or {}).get("fetched") or []
    except Exception:
        raise RuntimeError(
            "Angel One से भाव नहीं मिले। थोड़ी देर बाद Refresh करें। "
            "समस्या बनी रहे तो दोबारा Login करें।"
        ) from None

    return {
        (str(q.get("exchange")), str(q.get("symbolToken"))): q
        for q in fetched
    }


def get_quote(data, instrument):
    if instrument is None:
        return {}
    key = (str(instrument["exch_seg"]), str(instrument["token"]))
    return data.get(key, {})


def nearby_strikes(available, selector, spot):
    matching = sorted(s for s in available if digit(s) == selector)
    if not matching:
        return []
    index = min(
        range(len(matching)),
        key=lambda i: (abs(matching[i] - spot), matching[i]),
    )
    # One previous, nearest matching strike, one next.
    return matching[max(0, index - 1):index + 2]


def match_text(price, targets):
    if price is None:
        return "भाव नहीं मिला"
    matches = [
        f"P{i + 1}: {target:.2f}"
        for i, target in enumerate(targets)
        if target > 0 and target * .9 <= price <= target * 1.1
    ]
    return " | ".join(matches) if matches else "—"


st.markdown("#### 📊 Angel Digit Scanner")

if st.button("दोबारा Login"):
    st.session_state.pop("angel_client", None)
    st.rerun()

client = connect()


@st.fragment(run_every="10s")
def dashboard():
    today = datetime.now(IST).date()

    try:
        master = instrument_master(today.isoformat())
        nifty = spot_instrument(
            master, "NSE", ["NIFTY", "NIFTY 50", "NIFTY50"]
        )
        sensex = spot_instrument(
            master, "BSE", ["SENSEX", "BSE SENSEX"]
        )
        nifty_future = current_future(master, "NIFTY", "NFO", today)
        sensex_future = current_future(master, "SENSEX", "BFO", today)

        markets = [
            ("NIFTY", nifty),
            ("NIFTY FUT", nifty_future),
            ("SENSEX", sensex),
            ("SENSEX FUT", sensex_future),
        ]
        instruments = [
            item for _, item in markets if item is not None
        ]
        market_quotes = quotes(client, instruments)
    except Exception:
        st.error(
            "Market instruments या quotes नहीं मिले। "
            "Refresh होने दें; जरूरत हो तो दोबारा Login करें।"
        )
        return

    cards = []
    old_dates = set()
    unknown_date = False

    for label, item in markets:
        quote = get_quote(market_quotes, item)
        opening = positive(quote.get("open"))
        opening_text = f"{opening:,.2f}" if opening is not None else "—"
        feed_time = str(quote.get("exchFeedTime") or "")
        feed_date = pd.to_datetime(
            feed_time, format="%d-%b-%Y %H:%M:%S", errors="coerce"
        )
        if pd.isna(feed_date):
            unknown_date = True
        elif feed_date.date() != today:
            old_dates.add(feed_date.date().isoformat())

        cards.append(
            '<div class="market-card">'
            f'<div class="market-name">{escape(label)}</div>'
            f'<div class="market-open">{opening_text}</div>'
            f'<div class="market-code">{open_code(opening)}</div>'
            f'<div class="market-time">{escape(feed_time or "तारीख नहीं मिली")}</div>'
            '</div>'
        )

    st.markdown(
        '<div class="market-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )

    if old_dates:
        st.caption(
            "पुराने session का डेटा भी मिला: "
            + ", ".join(sorted(old_dates))
        )
    if unknown_date:
        st.caption("कुछ quotes की तारीख की पुष्टि नहीं हुई।")

    st.caption(
        "OPEN और समय broker quote से हैं। "
        "बाज़ार बंद होने पर पिछला उपलब्ध भाव दिख सकता है।"
    )

    cols = st.columns(2)
    first = cols[0].number_input(
        "Strike digit 1", min_value=1, max_value=9,
        value=6, step=1, key="selector_one",
    )
    second = cols[1].number_input(
        "Strike digit 2", min_value=1, max_value=9,
        value=9, step=1, key="selector_two",
    )

    cols = st.columns(3)
    targets = [
        cols[i].number_input(
            f"भाव {i + 1}", min_value=0.0, value=0.0,
            step=0.05, format="%.2f", key=f"target_{i}",
        )
        for i in range(3)
    ]

    spot = positive(get_quote(market_quotes, nifty).get("ltp"))
    if spot is None:
        st.warning("Nifty का मौजूदा भाव नहीं मिला; strike scan रुका है।")
        return

    options = master[
        master["name"].str.upper().eq("NIFTY")
        & master["exch_seg"].eq("NFO")
        & master["instrumenttype"].eq("OPTIDX")
        & master["expiry_date"].ge(pd.Timestamp(today))
        & master["symbol"].str.endswith(("CE", "PE"))
    ].copy()

    if options.empty:
        st.warning("Nifty option contracts नहीं मिले।")
        return

    expiries = sorted(options["expiry_date"].dropna().unique())
    expiry = st.selectbox(
        "NIFTY expiry", expiries,
        format_func=lambda value: pd.Timestamp(value).strftime("%d-%m-%Y"),
        key=f"expiry_{today.isoformat()}",
    )
    options = options[options["expiry_date"].eq(expiry)].copy()
    options["side"] = options["symbol"].str[-2:]

    # Only scan strikes having both CALL and PUT.
    sides = options.groupby("strike_price")["side"].nunique()
    available = sorted(sides[sides.eq(2)].index.tolist())

    contracts = []
    labels = []
    for group, selector in enumerate([first, second], start=1):
        selected = nearby_strikes(available, selector, spot)
        if len(selected) < 3:
            st.warning(
                f"Digit {selector}: इस expiry में तीन पड़ोसी strikes "
                "पूरे उपलब्ध नहीं हैं।"
            )
        for strike in selected:
            for side in ["CE", "PE"]:
                item = options[
                    options["strike_price"].eq(strike)
                    & options["side"].eq(side)
                ].iloc[0]
                contracts.append(item)
                labels.append((group, selector, int(strike), side))

    if not contracts:
        st.info("चुने हुए digit के contracts नहीं मिले।")
        return

    try:
        option_quotes = quotes(client, contracts)
    except RuntimeError as error:
        st.error(str(error))
        return

    rows = []
    missing = False
    for item, label in zip(contracts, labels):
        quote = get_quote(option_quotes, item)
        price = positive(quote.get("ltp"))
        missing = missing or price is None
        group, selector, strike, side = label
        rows.append({
            "Box": group,
            "Digit": selector,
            "Strike": strike,
            "Type": "CALL" if side == "CE" else "PUT",
            "भाव": price,
            "Match ±10%": match_text(price, targets),
            "Quote समय": str(quote.get("exchFeedTime") or "—"),
        })

    frame = pd.DataFrame(rows)

    def highlight(row):
        matched = row["Match ±10%"] not in ["—", "भाव नहीं मिला"]
        color = "background-color: #14532d; color: #ffffff;" if matched else ""
        return [color] * len(row)

    st.dataframe(
        frame.style.apply(highlight, axis=1).format(
            {"भाव": "{:.2f}"}, na_rep="—"
        ),
        hide_index=True,
        use_container_width=True,
        height=min(470, 38 + 35 * len(frame)),
    )

    if missing:
        st.caption("कुछ contracts के भाव नहीं मिले; उन्हें match नहीं माना गया।")
    st.caption(
        f"NIFTY {spot:,.2f} · जाँच "
        f"{datetime.now(IST).strftime('%H:%M:%S')} IST · "
        "हर 10 सेकंड refresh · भाव 0 रखने पर वह target बंद"
    )


dashboard()
