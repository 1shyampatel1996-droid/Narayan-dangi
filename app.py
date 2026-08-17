import streamlit as st
import yfinance as yf
import requests
import pandas as pd
from SmartApi import SmartConnect
import pyotp
from datetime import datetime, timedelta

# पेज सेटअप
st.set_page_config(page_title="Market Live App", layout="wide")
st.title("Market Live Data Dashboard")

# --- Angel One क्रेडेंशियल्स ---
API_KEY = "GAuh625s"
CLIENT_ID = "N417637"
PIN = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

# साइडबार में रिफ्रेश बटन
st.sidebar.title("Controls")
if st.sidebar.button("🔄 Refresh Market Data"):
    st.rerun()

# --- सिंगल सेशन कनेक्शन (रेट-लिमिट से बचने के लिए) ---
@st.cache_resource(ttl=600)
def get_angel_session():
    try:
        obj = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = obj.generateSession(CLIENT_ID, PIN, totp)
        if data and data.get('status'):
            return obj
    except Exception:
        pass
    return None

# --- फ्यूचर टोकन ऑटो-सर्च ---
@st.cache_data(ttl=1800)
def get_current_future_token(symbol_name, exchange_segment):
    try:
        url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            df = pd.DataFrame(response.json())
            filtered = df[(df['name'] == symbol_name) & (df['exch_seg'] == exchange_segment) & (df['symbol'].str.endswith("FUT"))]
            if not filtered.empty:
                if 'expiry' in filtered.columns:
                    filtered['expiry_date'] = pd.to_datetime(filtered['expiry'], format='%d%b%Y', errors='coerce')
                    filtered = filtered.sort_values(by='expiry_date')
                return str(filtered.iloc[0]['token'])
    except Exception:
        pass
    return None

# --- Angel One डेटा फेचिंग (फ्यूचर्स के लिए) ---
def get_angel_one_data(obj, symbol_token, exchange="NFO"):
    open_price = 0.0
    if not obj or not symbol_token:
        return 0.0, 0, 0
    try:
        historic_param = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": "ONE_DAY",
            "fromdate": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d %H:%M"),
            "todate": datetime.now().strftime("%Y-%m-%d %H:%M")
        }
        candles = obj.getCandleData(historic_param)
        if candles and isinstance(candles, dict) and 'data' in candles and candles['data']:
            open_price = float(candles['data'][-1][1])
    except Exception:
        pass
    
    # डिजिट कैलकुलेशन लॉजिक
    price_str = f"{open_price:.2f}".replace(".", "").replace(",", "")
    digit_sum = sum(int(char) for char in price_str if char.isdigit())
    temp_sum = digit_sum
    while temp_sum >= 10:
        temp_sum = sum(int(c) for c in str(temp_sum))
    if digit_sum < 10:
        final_digit = digit_sum * 100 + digit_sum * 10 + temp_sum
    else:
        final_digit = (digit_sum * 10) + temp_sum
    third_digit = final_digit % 10
    return open_price, final_digit, third_digit

# --- Yahoo Finance (स्पॉट इंडेक्स के लिए: Nifty 50 और Sensex) ---
def get_spot_index_yf(ticker):
    try:
        df = yf.Ticker(ticker).history(period="2d", interval="1d")
        if df.empty or 'Open' not in df.columns:
            return 0.0, 0, 0
        open_price = float(df['Open'].iloc[-1])
        if pd.isna(open_price) or open_price <= 0:
            open_price = float(df['Open'].iloc[-2])
            
        price_str = f"{open_price:.2f}".replace(".", "").replace(",", "")
        digit_sum = sum(int(char) for char in price_str if char.isdigit())
        temp_sum = digit_sum
        while temp_sum >= 10:
            temp_sum = sum(int(c) for c in str(temp_sum))
        if digit_sum < 10:
            final_digit = digit_sum * 100 + digit_sum * 10 + temp_sum
        else:
            final_digit = (digit_sum * 10) + temp_sum
        third_digit = final_digit % 10
        return open_price, final_digit, third_digit
    except Exception:
        return 0.0, 0, 0

# सेशन और टोकन इनिशियलाइज़ेशन
angel_obj = get_angel_session()

# स्पॉट डेटा Yahoo Finance से (^NSEI और ^BSESN)
nifty_open, nifty_dig, nifty_third = get_spot_index_yf("^NSEI")
sensex_open, sensex_dig, sensex_third = get_spot_index_yf("^BSESN")

# फ्यूचर डेटा Angel One से
nifty_fut_token = get_current_future_token("NIFTY", "NFO")
sensex_fut_token = get_current_future_token("SENSEX", "BFO")

nifty_fut_open, nifty_fut_dig, nifty_fut_third = get_angel_one_data(angel_obj, nifty_fut_token, "NFO")
sensex_fut_open, sensex_fut_dig, sensex_fut_third = get_angel_one_data(angel_obj, sensex_fut_token, "BFO")

# कलर कंपेरिजन
n_col1 = "green" if nifty_third >= nifty_fut_third else "red"
n_col2 = "green" if nifty_fut_third >= nifty_third else "red"

s_col1 = "green" if sensex_third >= sensex_fut_third else "red"
s_col2 = "green" if sensex_fut_third >= sensex_third else "red"

# --- 1. Nifty Group UI ---
st.markdown("### 1. Nifty Group")
st.markdown(
    f"""
<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 16px;">
    <span style="width: 40%;"><b>Nifty 50</b></span>
    <span style="width: 35%; text-align: right;">{nifty_open:,.2f}</span>
    <span style="width: 20%; text-align: right; color: {n_col2}; font-weight: bold;">{nifty_dig}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 16px;">
    <span style="width: 40%;"><b>Future</b></span>
    <span style="width: 35%; text-align: right;">{nifty_fut_open:,.2f}</span>
    <span style="width: 20%; text-align: right; color: {n_col1}; font-weight: bold;">{nifty_fut_dig}</span>
</div>
""",
    unsafe_allow_html=True,
)

st.markdown("---")

# --- 2. Sensex Group UI ---
st.markdown("### 2. Sensex Group")
st.markdown(
    f"""
<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 16px;">
    <span style="width: 40%;"><b>Sensex</b></span>
    <span style="width: 35%; text-align: right;">{sensex_open:,.2f}</span>
    <span style="width: 20%; text-align: right; color: {s_col2}; font-weight: bold;">{sensex_dig}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 4px 0; font-size: 16px;">
    <span style="width: 40%;"><b>Future</b></span>
    <span style="width: 35%; text-align: right;">{sensex_fut_open:,.2f}</span>
    <span style="width: 20%; text-align: right; color: {s_col1}; font-weight: bold;">{sensex_fut_dig}</span>
</div>
""",
    unsafe_allow_html=True,
)

# --- 3 & 4. Crypto (Bitcoin & Ethereum) - सुरक्षित एवं अपरिवर्तित ---
def get_coinbase_daily_open(product_id):
    try:
        url = f"https://api.exchange.coinbase.com/products/{product_id}/candles?granularity=86400"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code == 200:
            candles = response.json()
            if candles and len(candles) > 0:
                open_price = float(candles[0][3])
                if open_price <= 0 and len(candles) > 1:
                    open_price = float(candles[1][3])
                
                price_str = f"{open_price:.2f}".replace(".", "").replace(",", "")
                digit_sum = sum(int(char) for char in price_str if char.isdigit())
                temp_sum = digit_sum
                while temp_sum >= 10:
                    temp_sum = sum(int(c) for c in str(temp_sum))
                if digit_sum < 10:
                    final_digit = digit_sum * 100 + digit_sum * 10 + temp_sum
                else:
                    final_digit = (digit_sum * 10) + temp_sum
                third_digit = final_digit % 10
                return open_price, final_digit, third_digit
    except Exception:
        pass
    return 0.0, 0, 0

def get_cme_future_data(ticker_symbol):
    try:
        df = yf.Ticker(ticker_symbol).history(period="2d", interval="1d")
        if df.empty or 'Open' not in df.columns:
            return 0.0, 0, 0
        open_price = float(df['Open'].iloc[-1])
        if pd.isna(open_price) or open_price <= 0:
            open_price = float(df['Open'].iloc[-2])
        price_str = f"{open_price:.2f}".replace(".", "").replace(",", "")
        digit_sum = sum(int(char) for char in price_str if char.isdigit())
        temp_sum = digit_sum
        while temp_sum >= 10:
            temp_sum = sum(int(c) for c in str(temp_sum))
        if digit_sum < 10:
            final_digit = digit_sum * 100 + digit_sum * 10 + temp_sum
        else:
            final_digit = (digit_sum * 10) + temp_sum
        third_digit = final_digit % 10
        return open_price, final_digit, third_digit
    except Exception:
        return 0.0, 0, 0

btc_cb_open, btc_cb_dig, btc_cb_third = get_coinbase_daily_open("BTC-USD")
btc_cme_open, btc_cme_dig, btc_cme_third = get_cme_future_data("BTC=F")

eth_cb_open, eth_cb_dig, eth_cb_third = get_coinbase_daily_open("ETH-USD")
eth_cme_open, eth_cme_dig, eth_cme_third = get_cme_future_data("ETH=F")

btc_cb_col = "green" if btc_cb_third >= btc_cme_third else "red"
btc_cme_col = "green" if btc_cme_third >= btc_cb_third else "red"

eth_cb_col = "green" if eth_cb_third >= eth_cme_third else "red"
eth_cme_col = "green" if eth_cme_third >= eth_cb_third else "red"

# --- 3. Bitcoin Group UI ---
st.markdown("---")
st.markdown("### 3. Bitcoin Group")
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
    <span style='width: 40%; font-weight: 500;'>Bitcoin</span>
    <span style='width: 35%; text-align: right;'>{btc_cb_open:,.2f}</span>
    <span style='width: 20%; text-align: right; color: {btc_cb_col}; font-weight: bold;'>{btc_cb_dig}</span>
</div>
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
    <span style='width: 40%; font-weight: 500;'>Future</span>
    <span style='width: 35%; text-align: right;'>{btc_cme_open:,.2f}</span>
    <span style='width: 20%; text-align: right; color: {btc_cme_col}; font-weight: bold;'>{btc_cme_dig}</span>
</div>
""", unsafe_allow_html=True)

# --- 4. Ethereum Group UI ---
st.markdown("---")
st.markdown("### 4. Ethereum Group")
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
    <span style='width: 40%; font-weight: 500;'>Ethereum</span>
    <span style='width: 35%; text-align: right;'>{eth_cb_open:,.2f}</span>
    <span style='width: 20%; text-align: right; color: {eth_cb_col}; font-weight: bold;'>{eth_cb_dig}</span>
</div>
<div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;'>
    <span style='width: 40%; font-weight: 500;'>Future</span>
    <span style='width: 35%; text-align: right;'>{eth_cme_open:,.2f}</span>
    <span style='width: 20%; text-align: right; color: {eth_cme_col}; font-weight: bold;'>{eth_cme_dig}</span>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
