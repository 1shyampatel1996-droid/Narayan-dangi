import math
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

IST = ZoneInfo("Asia/Kolkata")

MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)

SECRET_NAMES = (
    "ANGEL_API_KEY",
    "ANGEL_CLIENT_ID",
    "ANGEL_PIN",
    "ANGEL_TOTP_SECRET",
)

st.markdown(
    """
<style>
.block-container {
    padding: 1rem .4rem .5rem;
    max-width: 100%;
}
div[data-testid="stVerticalBlock"] {
    gap: .4rem;
}
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
.market-name {
    font-size: 10px;
}
.market-open {
    font-size: 12px;
    margin-top: 3px;
}
.market-code {
    font-size: 23px;
    font-weight: 800;
    color: #22c55e;
}
.market-time {
    font-size: 9px;
    opacity: .7;
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
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number) or number <= 0:
        return None

    return number


def open_code(value):
    number = positive(value)
    if number is None:
        return "—"

    total = sum(int(c) for c in f"{number:.2f}" if c.isdigit())
    return f"{total:02d}{digit(total)}"


def read_credentials():
    try:
        values = {
            name: str(st.secrets.get(name, "")).strip()
            for name in SECRET_NAMES
        }
    except Exception:
        values = {}

    if all(values.get(name) for name in SECRET_NAMES):
        return values

    st.info("Angel One की जानकारी भरें और Login दबाएँ।")

    with st.form("angel_login_form"):
        api_key = st.text_input("SmartAPI API key", type="password")
        client_id = st.text_input("Angel One Client ID")
        pin = st.text_input("Angel One PIN", type="password")
        secret = st.text_input(
            "TOTP setup secret — 6 अंक वाला OTP नहीं",
            type="password",
        )
        submitted = st.form_submit_button("Login")

    if not submitted:
        st.stop()

    values = {
        "ANGEL_API_KEY": api_key.strip(),
        "ANGEL_CLIENT_ID": client_id.strip(),
        "ANGEL_PIN": pin.strip(),
        "ANGEL_TOTP_SECRET": secret.strip(),
    }

    if not all(values.values()):
        st.error("चारों बॉक्स भरें।")
        st.stop()

    return values


def connect():
    today = datetime.now(IST).date().isoformat()

    if st.session_state.get("angel_login_day") != today:
        st.session_state.pop("angel_client", None)

    if "angel_client" in st.session_state:
        return st.session_state["angel_client"]

    values = read_credentials()

    try:
        client = SmartConnect(
            api_key=values["ANGEL_API_KEY"],
            timeout=12,
        )

        secret = values["ANGEL_TOTP_SECRET"].replace(" ", "")
        otp = pyotp.TOTP(secret).now()

        result = client.generateSession(
            values["ANGEL_CLIENT_ID"],
            values["ANGEL_PIN"],
            otp,
        )

        if not isinstance(result, dict) or not result.get("status"):
            raise RuntimeError("Login rejected")

    except Exception:
        st.error(
            "Login नहीं हुआ। API key, Client ID, PIN और "
            "TOTP setup secret जाँचकर फिर Login करें।"
        )
        st.stop()

    st.session_state["angel_client"] = client
    st.session_state["angel_login_day"] = today
    return client


@st.cache_data(ttl=3600, show_spinner=False)
def instrument_master(day):
    response = requests.get(MASTER_URL, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())

    required = {
        "token",
