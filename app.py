import streamlit as st
import yfinance as yf
import requests
import pandas as pd

# पेज सेटअप
st.set_page_config(page_title="Market Live App", layout="wide")
st.title("Market Live Data Dashboard")

# --- फंक्शन: केवल रियल ओपन प्राइस फेच करने के लिए (बिना किसी फेरबदल के) ---
def get_real_market_data(ticker_symbol):
    try:
        df = yf.Ticker(ticker_symbol).history(period="2d", interval="1d")
        if df.empty or 'Open' not in df.columns:
            return 0.0, 0, 0
        
        open_price = float(df['Open'].iloc[-1])
        if pd.isna(open_price) or open_price <= 0:
            open_price = float(df['Open'].iloc[-2])
            
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
    except Exception:
        return 0.0, 0, 0

# वास्तविक डेटा फेच करना (रियल टिकर्स के साथ)
nifty_open, nifty_dig, nifty_third = get_real_market_data("^NSEI")
nifty_fut_open, nifty_fut_dig, nifty_fut_third = get_real_market_data("NIFTY=F")

sensex_open, sensex_dig, sensex_third = get_real_market_data("^BSESN")
sensex_fut_open, sensex_fut_dig, sensex_fut_third = get_real_market_data("BSESN=F") # यदि टिकर उपलब्ध हो

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

# --- 3 & 4. Crypto (Bitcoin & Ethereum) - सुरक्षित और यथावत ---
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
