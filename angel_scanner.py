import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

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

# नई credentials बनने पर इन चार values को बदलें.
API_KEY = "GAuh625s"
CLIENT_ID = "N417637"
PIN = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

IST = ZoneInfo("Asia/Kolkata")
MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)

st.markdown(
    """
    <style>
    .block-container {
        padding: .7rem .4rem;
        max-width: 100%;
    }
    div[data-testid="stVerticalBlock"] {gap: .4rem;}
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: .35rem;
    }
    div[data-testid="stColumn"] {
        min-width: 0 !important;
    }
    .market-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 4px;
    }
    .market-card {
        border: 1px solid #687184;
        border-radius: 8px;
        padding: 7px 2px;
        text-align: center;
        overflow-wrap: anywhere;
    }
    .market-name {font-size: 10px;}
    .market-open {font-size: 12px;}
    .market-code {
        font-size: 24px;
        font-weight: 800;
        color: #22c55e;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def digit(value):
    total = sum(int(c) for c in str(abs(int(value))))
    while total > 9:
        total = sum(int(c) for c in str(total))
    return total


def positive(value):
    try:
        number = float(value)
        if pd.notna(number) and number > 0:
            return number
    except (TypeError, ValueError):
        pass
    return None


def open_code(value):
    if value is None:
        return "—"
    total = sum(int(c) for c in f"{value:.2f}" if c.isdigit())
    return f"{total:02d}{digit(total)}"


def connect():
    today = datetime.now(IST).date().isoformat()

    if st.session_state.get("login_day") != today:
        st.session_state.pop("angel_client", None)

    if "angel_client" not in st.session_state:
        try:
            api = SmartConnect(api_key=API_KEY, timeout=12)
            otp = pyotp.TOTP(TOTP_SECRET.strip()).now()
            result = api.generateSession(CLIENT_ID, PIN, otp)

            if not isinstance(result, dict) or not result.get("status"):
                raise ValueError("Login rejected")

        except Exception:
            st.error(
                "Angel One login नहीं हुआ। API key, Client ID, "
                "PIN और TOTP setup secret जाँचें।"
            )
            st.stop()

        st.session_state.angel_client = api
        st.session_state.login_day = today

    return st.session_state.angel_client


@st.cache_data(ttl=3600, show_spinner=False)
def instrument_master(day):
    response = requests.get(MASTER_URL, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())

    required = {
        "token",
        "symbol",
        "name",
        "exch_seg",
        "instrumenttype",
        "expiry",
        "strike",
    }

    if not required.issubset(frame.columns):
        raise ValueError("Instrument list incomplete")

    columns = (
        "token", "symbol", "name", "exch_seg", "instrumenttype"
    )
    for column in columns:
        frame[column] = (
            frame[column].fillna("").astype(str).str.strip()
        )

    frame["expiry_date"] = pd.to_datetime(
        frame["expiry"],
        format="%d%b%Y",
        errors="coerce",
    )
    frame["strike_price"] = (
        pd.to_numeric(frame["strike"], errors="coerce") / 100
    )
    return frame


def find_spot(frame, exchange, aliases):
    exchange_match = frame["exch_seg"].eq(exchange)
    name_match = frame["name"].str.upper().isin(aliases)
    symbol_match = frame["symbol"].str.upper().isin(aliases)

    mask = exchange_match & (name_match | symbol_match)
    matches = frame.loc[mask]

    if matches.empty:
        raise ValueError("Index token missing")

    return matches.iloc[0]


def find_future(frame, name, exchange, today):
    name_match = frame["name"].str.upper().eq(name)
    exchange_match = frame["exch_seg"].eq(exchange)
    type_match = frame["instrumenttype"].eq("FUTIDX")
    expiry_match = frame["expiry_date"].ge(pd.Timestamp(today))

    mask = name_match & exchange_match & type_match & expiry_match
    matches = frame.loc[mask].sort_values("expiry_date")

    if matches.empty:
        return None

    return matches.iloc[0]


def quotes(api, instruments):
    tokens = {}

    for item in instruments:
        exchange = str(item["exch_seg"])
        token = str(item["token"])
        tokens.setdefault(exchange, [])

        if token not in tokens[exchange]:
            tokens[exchange].append(token)

    if not tokens:
        return {}

    elapsed = time.monotonic() - st.session_state.get(
        "last_quote_request", 0
    )
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    st.session_state.last_quote_request = time.monotonic()
    result = api.getMarketData("FULL", tokens)

    if not isinstance(result, dict) or not result.get("status"):
        raise RuntimeError("Quotes unavailable")

    fetched = (result.get("data") or {}).get("fetched") or []

    return {
        (str(q.get("exchange")), str(q.get("symbolToken"))): q
        for q in fetched
    }


def get_quote(data, item):
    if item is None:
        return {}

    key = (str(item["exch_seg"]), str(item["token"]))
    return data.get(key, {})


def nearby_strikes(available, selector, spot):
    matching = sorted(
        strike for strike in available if digit(strike) == selector
    )

    if not matching:
        return []

    index = min(
        range(len(matching)),
        key=lambda i: (abs(matching[i] - spot), matching[i]),
    )

    return matching[max(0, index - 1):index + 2]


def match_text(price, targets):
    if price is None:
        return "भाव नहीं मिला"

    matches = []
    for index, target in enumerate(targets, start=1):
        if target > 0 and target * 0.9 <= price <= target * 1.1:
            matches.append(f"P{index}: {target:.2f}")

    return " | ".join(matches) if matches else "—"


def highlight(row):
    matched = row["Match ±10%"] not in ("—", "भाव नहीं मिला")
    color = (
        "background-color: #14532d; color: white;"
        if matched else ""
    )
    return [color] * len(row)


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

        nifty = find_spot(
            master, "NSE", ["NIFTY", "NIFTY 50", "NIFTY50"]
        )
        sensex = find_spot(
            master, "BSE", ["SENSEX", "BSE SENSEX"]
        )
        nifty_future = find_future(
            master, "NIFTY", "NFO", today
        )
        sensex_future = find_future(
            master, "SENSEX", "BFO", today
        )

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
            "Instruments या market data नहीं मिला। "
            "अगला refresh होने दें या दोबारा Login दबाएँ।"
        )
        return

    cards = []
    feed_dates = set()
    unknown_date = False

    for label, item in markets:
        quote = get_quote(market_quotes, item)
        opening = positive(quote.get("open"))
        opening_text = (
            f"{opening:,.2f}" if opening is not None else "—"
        )

        feed_time = str(quote.get("exchFeedTime") or "")
        parsed = pd.to_datetime(
            feed_time,
            format="%d-%b-%Y %H:%M:%S",
            errors="coerce",
        )

        if pd.isna(parsed):
            unknown_date = True
        else:
            feed_dates.add(parsed.date())

        cards.append(
            '<div class="market-card">'
            f'<div class="market-name">{escape(label)}</div>'
            f'<div class="market-open">{opening_text}</div>'
            f'<div class="market-code">{open_code(opening)}</div>'
            "</div>"
        )

    st.markdown(
        '<div class="market-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )

    old_dates = sorted(
        day.isoformat() for day in feed_dates if day != today
    )

    if old_dates:
        st.caption(
            "पुराने session का डेटा: " + ", ".join(old_dates)
        )
    if unknown_date:
        st.caption("कुछ market quotes की तारीख की पुष्टि नहीं हुई।")

    columns = st.columns(2)

    first = columns[0].
