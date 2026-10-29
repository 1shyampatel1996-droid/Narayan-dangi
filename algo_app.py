
import streamlit as st
import pandas as pd
import requests
import pyotp
import time
import threading
from datetime import datetime
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# ==================== पेज सेटअप और विशिष्ट आइकॉन ====================
st.set_page_config(
    page_title="एल्गो स्ट्राइक स्कैनर", 
    page_icon="🎯",  # अलग आइकॉन ताकि दूसरे ऐप्स से कंफ्यूजन न हो
    layout="wide"
)

# ==================== मोबाइल के लिए कॉम्पैक्ट CSS डिज़ाइन ====================
st.markdown("""
    <style>
    h1 { font-size: 20px !important; }
    h2 { font-size: 18px !important; }
    h3 { font-size: 16px !important; }
    p, label, .stNumberInput label { font-size: 12px !important; }
    .stNumberInput { width: 100% !important; margin-bottom: -10px; }
    table { font-size: 12px !important; }
    </style>
""", unsafe_allow_html=True)

# ==================== आपकी API डिटेल्स ====================
API_KEY = "GAuh625s"
CLIENT_CODE = "N417637"
PASSWORD = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

# ==================== ग्लोबल स्टेट ====================
if "live_ltp" not in st.session_state:
    st.session_state.live_ltp = {}

if "nifty_pinned" not in st.session_state:
    st.session_state.nifty_pinned = None

if "sensex_pinned" not in st.session_state:
    st.session_state.sensex_pinned = None

# ==================== डिजिटल रूट और 3-डिजिट कोड कैलकुलेशन ====================
def get_digital_root(number):
    num = int(abs(number))
    while num >= 10:
        num = sum(int(digit) for digit in str(num))
    return num

def calculate_custom_digit_code(price):
    price_str = str(price).replace(".", "")
    total_sum = sum(int(d) for d in price_str if d.isdigit())
    single_digit = get_digital_root(total_sum)
    code_3digit = f"{total_sum}{single_digit}"
    return total_sum, single_digit, code_3digit

# ==================== स्ट्राइक फाइंडर ====================
def find_digit_strikes(current_spot, step, target_digit):
    base_strike = round(current_spot / step) * step
    matched_strikes = []
    
    for i in range(-25, 26):
        s = base_strike + (i * step)
        if get_digital_root(s) == target_digit:
            matched_strikes.append(s)
            
    if not matched_strikes:
        return [base_strike, base_strike - step, base_strike + step]
        
    main_strike = min(matched_strikes, key=lambda x: abs(x - current_spot))
    idx = matched_strikes.index(main_strike)
    
    rev_strike = matched_strikes[idx - 1] if idx > 0 else main_strike - step
    next_strike = matched_strikes[idx + 1] if idx < len(matched_strikes) - 1 else main_strike + step
    
    return [main_strike, rev_strike, next_strike]

# ==================== STREAMLIT UI ====================
st.title("⚡ एल्गो स्ट्राइक स्कैनर (Buy & Sell/Short)")

tab_nifty, tab_sensex = st.tabs(["📊 Nifty", "📈 Sensex"])

# ----------- NIFTY TAB -----------
with tab_nifty:
    st.markdown("**Nifty 50 सेटिंग्स (Buy & Sell)**")
    
    # इनपुट कॉलम्स (बाइंग और सेल शॉर्ट के लिए)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_d1 = st.number_input("डिट 1", 0, 9, 3, key="nd1")
    with col2:
        n_d2 = st.number_input("डिट 2", 0, 9, 7, key="nd2")
    with col3:
        n_buy = st.number_input("बाइंग भाव", 1.0, 2000.0, 150.0, key="n_buy")
    with col4:
        n_sell = st.number_input("सेल शॉर्ट भाव", 1.0, 2000.0, 250.0, key="n_sell")

    nifty_spot_open = 24000.50
    nifty_fut_open = 24025.75

    ns_sum, ns_single, ns_code = calculate_custom_digit_code(nifty_spot_open)
    nf_sum, nf_single, nf_code = calculate_custom_digit_code(nifty_fut_open)

    st.markdown("---")
    st.markdown("🕒 **9:12:10 AM ओपन सेटलमेंट कोड (Nifty)**")
    nc1, nc2 = st.columns(2)
    with nc1:
        st.info(f"**Spot Open:** {nifty_spot_open}\n\n🔢 **योग:** {ns_sum} | 🎯 **सिंगल:** {ns_single} | ✨ **कोड:** **{ns_code}**")
    with nc2:
        st.info(f"**Future Open:** {nifty_fut_open}\n\n🔢 **योग:** {nf_sum} | 🎯 **सिंगल:** {nf_single} | ✨ **कोड:** **{nf_code}**")

    strikes_d1 = find_digit_strikes(nifty_spot_open, 50, n_d1)
    strikes_d2 = find_digit_strikes(nifty_spot_open, 50, n_d2)

    st.markdown("📌 **Nifty पिन बोर्ड**")
    if st.session_state.nifty_pinned:
        st.success(f"🎯 {st.session_state.nifty_pinned}")
    else:
        st.info("ट्रिगर प्रतीक्षारत...")

    st.markdown("📋 **स्ट्राइक्स (CE & PE) - Buy & Sell Tracking**")
    contracts = []
    for s in strikes_d1 + strikes_d2:
        ltp_val = st.session_state.live_ltp.get(str(s), 0.0)
        contracts.append({
            "Strike": f"{s} CE", 
            "LTP": ltp_val, 
            "Buy Target": n_buy, 
            "Sell Target": n_sell
        })
        contracts.append({
            "Strike": f"{s} PE", 
            "LTP": ltp_val, 
            "Buy Target": n_buy, 
            "Sell Target": n_sell
        })
    
    st.table(pd.DataFrame(contracts))

# ----------- SENSEX TAB -----------
with tab_sensex:
    st.markdown("**Sensex सेटिंग्स (Buy & Sell)**")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        s_d1 = st.number_input("डिट 1 ", 0, 9, 5, key="sd1")
    with col2:
        s_d2 = st.number_input("डिट 2 ", 0, 9, 8, key="sd2")
    with col3:
        s_buy = st.number_input("बाइंग भाव ", 1.0, 3000.0, 300.0, key="s_buy")
    with col4:
        s_sell = st.number_input("सेल शॉर्ट भाव ", 1.0, 3000.0, 450.0, key="s_sell")

    sensex_spot_open = 73250.25
    sensex_fut_open = 73300.50

    ss_sum, ss_single, ss_code = calculate_custom_digit_code(sensex_spot_open)
    sf_sum, sf_single, sf_code = calculate_custom_digit_code(sensex_fut_open)

    st.markdown("---")
    st.markdown("🕒 **9:12:10 AM ओपन सेटलमेंट कोड (Sensex)**")
    sc1, sc2 = st.columns(2)
    with sc1:
        st.info(f"**Spot Open:** {sensex_spot_open}\n\n🔢 **योग:** {ss_sum} | 🎯 **सिंगल:** {ss_single} | ✨ **कोड:** **{ss_code}**")
    with sc2:
        st.info(f"**Future Open:** {sensex_fut_open}\n\n🔢 **योग:** {sf_sum} | 🎯 **सिंगल:** {sf_single} | ✨ **कोड:** **{sf_code}**")

    s_strikes_d1 = find_digit_strikes(sensex_spot_open, 100, s_d1)
    s_strikes_d2 = find_digit_strikes(sensex_spot_open, 100, s_d2)

    st.markdown("📌 **Sensex पिन बोर्ड**")
    if st.session_state.sensex_pinned:
        st.success(f"🎯 {st.session_state.sensex_pinned}")
    else:
        st.info("ट्रिगर प्रतीक्षारत...")

    st.markdown("📋 **स्ट्राइक्स (CE & PE) - Buy & Sell Tracking**")
    s_contracts = []
    for s in s_strikes_d1 + s_strikes_d2:
        ltp_val = st.session_state.live_ltp.get(str(s), 0.0)
        s_contracts.append({
            "Strike": f"{s} CE", 
            "LTP": ltp_val, 
            "Buy Target": s_buy, 
            "Sell Target": s_sell
        })
        s_contracts.append({
            "Strike": f"{s} PE", 
            "LTP": ltp_val, 
            "Buy Target": s_buy, 
            "Sell Target": s_sell
        })
    
    st.table(pd.DataFrame(s_contracts))
