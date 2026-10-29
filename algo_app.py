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
    page_icon="🎯", 
    layout="wide"
)

# ==================== मोबाइल के लिए कॉम्पैक्ट और छोटी CSS डिज़ाइन ====================
st.markdown("""
    <style>
    h1 { font-size: 18px !important; }
    h2 { font-size: 16px !important; }
    h3 { font-size: 14px !important; }
    p, label, .stNumberInput label { font-size: 11px !important; }
    .stNumberInput { margin-bottom: -15px; }
    table { font-size: 11px !important; }
    .compact-box { background-color: #1e293b; padding: 8px 10px; border-radius: 6px; font-size: 11px; color: white; margin-bottom: 8px; text-align: center; }
    .pin-box { background-color: #064e3b; padding: 10px; border-radius: 6px; font-size: 13px; color: #34d399; font-weight: bold; margin-bottom: 10px; text-align: center; border: 1px solid #059669; }
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
    return code_3digit

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
st.title("⚡ एल्गो स्ट्राइक स्कैनर")

tab_nifty, tab_sensex = st.tabs(["📊 Nifty", "📈 Sensex"])

# ----------- NIFTY TAB -----------
with tab_nifty:
    nifty_spot_open = 24000.50
    nifty_fut_open = 24025.75

    ns_code = calculate_custom_digit_code(nifty_spot_open)
    nf_code = calculate_custom_digit_code(nifty_fut_open)

    # 1. 9:12:10 ओपन प्राइस और कोड बॉक्स
    st.markdown(f"""
        <div class="compact-box">
            🕒 <b>9:12:10 Nifty Open</b><br>
            <b>S:</b> {nifty_spot_open} (कोड: <b>{ns_code}</b>) | <b>F:</b> {nifty_fut_open} (कोड: <b>{nf_code}</b>)
        </div>
    """, unsafe_allow_html=True)

    # 2. सबसे पहले ट्रिगर होने वाली स्ट्राइक का पिन बोर्ड (सबसे ऊपर)
    if st.session_state.nifty_pinned:
        st.markdown(f"""
            <div class="pin-box">
                🎯 प्रथम ट्रिगर लॉक (Nifty): {st.session_state.nifty_pinned}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: #0f172a; padding: 6px; border-radius: 6px; text-align: center; color: #94a3b8; font-size: 11px; margin-bottom: 8px;">
                📌 Nifty पिन बोर्ड: ट्रिगर प्रतीक्षारत...
            </div>
        """, unsafe_allow_html=True)

    # 3. स्ट्राइक डिजिट के 2 बॉक्स एक लाइन में
    col1, col2 = st.columns(2)
    with col1:
        n_d1 = st.number_input("डिट 1", 0, 9, 3, key="nd1")
    with col2:
        n_d2 = st.number_input("डिट 2", 0, 9, 7, key="nd2")

    # 4. तीनों भाव (बाइंग 1, बाइंग 2, सेल शॉर्ट) के 3 बॉक्स एक लाइन में
    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        n_b1 = st.number_input("बाइंग 1", 1.0, 2000.0, 150.0, key="n_b1")
    with b_col2:
        n_b2 = st.number_input("बाइंग 2", 1.0, 2000.0, 200.0, key="n_b2")
    with b_col3:
        n_sell = st.number_input("सेल शॉर्ट", 1.0, 2000.0, 250.0, key="n_sell")

    strikes_d1 = find_digit_strikes(nifty_spot_open, 50, n_d1)
    strikes_d2 = find_digit_strikes(nifty_spot_open, 50, n_d2)

    contracts = []
    for s in strikes_d1 + strikes_d2:
        for opt_type in ["CE", "PE"]:
            strike_name = f"{s} {opt_type}"
            ltp_val = st.session_state.live_ltp.get(str(s), 0.0)
            
            # ट्रिगर चेक लॉजिक (यदि LTP बाइंग या सेल भाव के पास match हो)
            if ltp_val > 0 and st.session_state.nifty_pinned is None:
                if abs(ltp_val - n_b1) <= 2.0 or abs(ltp_val - n_b2) <= 2.0 or abs(ltp_val - n_sell) <= 2.0:
                    st.session_state.nifty_pinned = f"{strike_name} @ ₹{ltp_val}"

            contracts.append({
                "Strike": strike_name, "LTP": ltp_val, 
                "Buy 1": n_b1, "Buy 2": n_b2, "Sell": n_sell
            })
    
    st.table(pd.DataFrame(contracts))

# ----------- SENSEX TAB -----------
with tab_sensex:
    sensex_spot_open = 73250.25
    sensex_fut_open = 73300.50

    ss_code = calculate_custom_digit_code(sensex_spot_open)
    sf_code = calculate_custom_digit_code(sensex_fut_open)

    st.markdown(f"""
        <div class="compact-box">
            🕒 <b>9:12:10 Sensex Open</b><br>
            <b>S:</b> {sensex_spot_open} (कोड: <b>{ss_code}</b>) | <b>F:</b> {sensex_fut_open} (कोड: <b>{sf_code}</b>)
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.sensex_pinned:
        st.markdown(f"""
            <div class="pin-box">
                🎯 प्रथम ट्रिगर लॉक (Sensex): {st.session_state.sensex_pinned}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: #0f172a; padding: 6px; border-radius: 6px; text-align: center; color: #94a3b8; font-size: 11px; margin-bottom: 8px;">
                📌 Sensex पिन बोर्ड: ट्रिगर प्रतीक्षारत...
            </div>
        """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        s_d1 = st.number_input("डिट 1 ", 0, 9, 5, key="sd1")
    with col2:
        s_d2 = st.number_input("डिट 2 ", 0, 9, 8, key="sd2")

    s_b_col1, s_b_col2, s_b_col3 = st.columns(3)
    with s_b_col1:
        s_b1 = st.number_input("बाइंग 1 ", 1.0, 3000.0, 300.0, key="s_b1")
    with s_b_col2:
        s_b2 = st.number_input("बाइंग 2 ", 1.0, 3000.0, 350.0, key="s_b2")
    with s_b_col3:
        s_sell = st.number_input("सेल शॉर्ट ", 1.0, 3000.0, 450.0, key="s_sell")

    s_strikes_d1 = find_digit_strikes(sensex_spot_open, 100, s_d1)
    s_strikes_d2 = find_digit_strikes(sensex_spot_open, 100, s_d2)

    s_contracts = []
    for s in s_strikes_d1 + s_strikes_d2:
        for opt_type in ["CE", "PE"]:
            strike_name = f"{s} {opt_type}"
            ltp_val = st.session_state.live_ltp.get(str(s), 0.0)
            
            if ltp_val > 0 and st.session_state.sensex_pinned is None:
                if abs(ltp_val - s_b1) <= 2.0 or abs(ltp_val - s_b2) <= 2.0 or abs(ltp_val - s_sell) <= 2.0:
                    st.session_state.sensex_pinned = f"{strike_name} @ ₹{ltp_val}"

            s_contracts.append({
                "Strike": strike_name, "LTP": ltp_val, 
                "Buy 1": s_b1, "Buy 2": s_b2, "Sell": s_sell
            })
    
    st.table(pd.DataFrame(s_contracts))
