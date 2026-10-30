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

# आपकी दी हुई details. नई credentials बनने पर यहीं बदलें.
API_KEY = "GAuh625s"
CLIENT_ID = "N417637"
PIN = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

IST = ZoneInfo("Asia/Kolkata")
MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)

st.markdown("""
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
div[data-testid="stColumn"] {min-width: 0 !important;}
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
""", unsafe_allow_html=True)


def digit(value):
    total = sum(int(c) for c in str(abs(int(value))))
    while total > 9:
        total = sum(int(c) for c in str(total))
    return total


def positive(value):
    try:
        number = float(value)
        return number if pd.notna(number) and number > 0 else None
    except (TypeError, ValueError):
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
            client = SmartConnect(api_key=API_KEY, timeout=12)
            otp = pyotp.TOTP(TOTP_SECRET.strip()).now()
            result = client.generateSession(CLIENT_ID, PIN, otp)
            if not isinstance(result, dict) or not result.get("status"):
                raise ValueError("Login rejected")
        except Exception:
            st.error(
                "Angel One login नहीं हुआ। API key, Client ID, "
                "PIN और TOTP setup secret जाँचें।"
            )
            st.stop()

        st.session_state.angel_client = client
        st.session_state.login_day = today

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
        raise ValueError("Instrument list incomplete")

    for column in [
        "token", "symbol", "name", "exch_seg", "instrumenttype"
    ]:
        frame[column] = (
            frame[column].fillna("").astype(str).str.strip()
        )

    frame["expiry_date"] = pd.to_datetime(
        frame["expiry"], format="%d%b%Y", errors="coerce"
    )
    frame["strike_price"] = (
        pd.to_numeric(frame["strike"], errors="coerce") / 100
    )
    return frame


def find_spot(frame, exchange, aliases):
    matches = frame[
        frame["exch_seg"].eq(exchange)
        & (
            frame["name"].str.upper().isin(aliases)
            | frame["symbol"].str.upper().isin(aliases)
        )
    ]
    if matches.empty:
        raise ValueError("Index token missing")
    return matches.iloc[0]


def find_future(frame, name, exchange, today):
    matches = frame[
        frame["name"].str.upper().eq(name)
        & frame["exch_seg"].eq(exchange)
        & frame["instrumenttype"].
