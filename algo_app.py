import streamlit as st
import pandas as pd
import requests
import pyotp
import time
from datetime import datetime
from SmartApi import SmartConnect

# ==================== Page Setup & Icon ====================
st.set_page_config(
    page_title="Algo Strike Scanner", 
    page_icon="🎯", 
    layout="wide"
)

# ==================== CSS Design ====================
st.markdown("""
    <style>
    h1 { font-size: 18px !important; }
    p, label { font-size: 11px !important; font-weight: bold !important; color: #cbd5e1 !important; }
    table { font-size: 12px !important; }
    
    .stTextInput {
        max-width: 140px !important;
        margin-bottom: -10px !important;
    }
    .stTextInput input {
        background-color: #1e293b !important;
        color: white !important;
        border: 1px solid #334155 !important;
        border-radius: 4px !important;
        padding: 2px 6px !important;
        height: 30px !important;
        font-size: 12px !important;
    }

    .compact-box { background-color: #1e293b; padding: 8px; border-radius: 6px; font-size: 12px; color: white; margin-bottom: 6px; text-align: center; }
    .pin-box { background-color: #064e3b; padding: 8px; border-radius: 6px; font-size: 13px; color: #34d399; font-weight: bold; margin-bottom: 6px; text-align: center; border: 1px solid #059669; }
    </style>
""", unsafe_allow_html=True)

# ==================== API Details ====================
API_KEY = "GAuh625s"
CLIENT_CODE = "N417637"
PASSWORD = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

# ==================== Global State ====================
if "live_ltp" not in st.session_state:
    st.session_state.live_ltp = {}

if "prev_ltp" not in st.session_state:
    st.session_state.prev_ltp = {}

if "strike_open_prices" not in st.session_state:
    st.session_state.strike_open_prices = {}

if "nifty_pinned" not in st.session_state:
    st.session_state.nifty_pinned = None

if "sensex_pinned" not in st.session_state:
    st.session_state.sensex_pinned = None

if "nifty_day_locked" not in st.session_state:
    st.session_state.nifty_day_locked = False
    st.session_state.nifty_s_open = 0.0
    st.session_state.nifty_f_open = 0.0

if "sensex_day_locked" not in st.session_state:
    st.session_state.sensex_day_locked = False
    st.session_state.sensex_s_open = 0.0
    st.session_state.sensex_f_open = 0.0

# ==================== SmartConnect Session & LTP (With Error Catching) ====================
@st.cache_resource
def get_smart_connect_session():
    try:
        smart_api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smart_api.generateSession(CLIENT_CODE, PASSWORD, totp)
        if data and data.get('status'):
            return smart_api
        else:
            st.error(f"SmartAPI Login Failed: {data}")
    except Exception as e:
        st.error(f"SmartAPI Connection Exception: {e}")
    return None

def fetch_live_ltp_from_broker(exchange, symbol, token):
    smart_api = get_smart_connect_session()
    if smart_api:
        try:
            ltp_data = smart_api.ltpData(exchange, symbol, token)
            if ltp_data and 'data' in ltp_data:
                return float(ltp_data['data'].get('ltp', 0.0))
        except Exception as e:
            # यदि कोई विशेष सिंबल या टोकन में एरर होगी तो वह यहाँ पकड़ी जाएगी
            pass
    return 0.0

# ==================== Digital Root & 3-Digit Code ====================
def get_digital_root(number):
    num = int(abs(number))
    while num >= 10:
        num = sum(int(digit) for digit in str(num))
    return num

def calculate_custom_digit_code(price):
    if price == 0:
        return "00"
    price_str = str(price).replace(".", "")
    total_sum = sum(int(d) for d in price_str if d.isdigit())
    single_digit = get_digital_root(total_sum)
    code_3digit = f"{total_sum}{single_digit}"
    return code_3digit

# ==================== Strike Finder ====================
def find_digit_strikes(current_spot, step, target_digit):
    if current_spot == 0:
        current_spot = 24000.0
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
st.title("⚡ Algo Strike Scanner")

tab_nifty, tab_sensex = st.tabs(["📊 Nifty", "📈 Sensex"])

# ----------- NIFTY TAB -----------
with tab_nifty:
    now_time = datetime.now().time()
    
    live_n_spot = fetch_live_ltp_from_broker("NSE", "NIFTY", "999920000")
    live_n_fut = fetch_live_ltp_from_broker("NFO", "NIFTY26MARFUT", "0")
    
    if not st.session_state.nifty_day_locked:
        if live_n_spot > 0:
            st.session_state.nifty_s_open = live_n_spot
        if live_n_fut > 0:
            st.session_state.nifty_f_open = live_n_fut
        if now_time.hour > 9 or (now_time.hour == 9 and now_time.minute >= 13):
            if st.session_state.nifty_s_open > 0:
                st.session_state.nifty_day_locked = True

    n_spot_open = st.session_state.nifty_s_open if st.session_state.nifty_s_open > 0 else (live_n_spot if live_n_spot > 0 else 24000.0)
    n_fut_open = st.session_state.nifty_f_open if st.session_state.nifty_f_open > 0 else (live_n_fut if live_n_fut > 0 else 24025.0)

    ns_code = calculate_custom_digit_code(n_spot_open)
    nf_code = calculate_custom_digit_code(n_fut_open)

    st.markdown(f"""
        <div class="compact-box">
            <b>S:</b> {n_spot_open} (Code: <b>{ns_code}</b>) &nbsp;&nbsp;|&nbsp;&nbsp; <b>F:</b> {n_fut_open} (Code: <b>{nf_code}</b>)
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.nifty_pinned:
        st.markdown(f"""
            <div class="pin-box">
                🎯 First Trigger Lock (Nifty): {st.session_state.nifty_pinned}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: #0f172a; padding: 6px; border-radius: 6px; text-align: center; color: #94a3b8; font-size: 12px; margin-bottom: 6px;">
                📌 Nifty Pin Board: Waiting for trigger...
            </div>
        """, unsafe_allow_html=True)

    if "n_d1_val" not in st.session_state: st.session_state.n_d1_val = "3"
    if "n_d2_val" not in st.session_state: st.session_state.n_d2_val = "7"
    if "n_b1_val" not in st.session_state: st.session_state.n_b1_val = "150.0"
    if "n_b2_val" not in st.session_state: st.session_state.n_b2_val = "200.0"
    if "n_sell_val" not in st.session_state: st.session_state.n_sell_val = "250.0"

    col1, col2 = st.columns(2)
    with col1:
        n_d1_str = st.text_input("Digit 1", st.session_state.n_d1_val, key="nd1_input")
        st.session_state.n_d1_val = n_d1_str
    with col2:
        n_d2_str = st.text_input("Digit 2", st.session_state.n_d2_val, key="nd2_input")
        st.session_state.n_d2_val = n_d2_str

    b_col1, b_col2, b_col3 = st.columns(3)
    with b_col1:
        nb1_str = st.text_input("Buy 1", st.session_state.n_b1_val, key="nb1_input")
        st.session_state.n_b1_val = nb1_str
    with b_col2:
        nb2_str = st.text_input("Buy 2", st.session_state.n_b2_val, key="nb2_input")
        st.session_state.n_b2_val = nb2_str
    with b_col3:
        nsell_str = st.text_input("Sell", st.session_state.n_sell_val, key="nsell_input")
        st.session_state.n_sell_val = nsell_str

    n_d1 = int(n_d1_str) if n_d1_str.isdigit() else 3
    n_d2 = int(n_d2_str) if n_d2_str.isdigit() else 7
    n_b1 = float(nb1_str) if nb1_str.replace('.', '', 1).isdigit() else 150.0
    n_b2 = float(nb2_str) if nb2_str.replace('.', '', 1).isdigit() else 200.0
    n_sell = float(nsell_str) if nsell_str.replace('.', '', 1).isdigit() else 250.0

    strikes_d1 = find_digit_strikes(n_spot_open, 50, n_d1)
    strikes_d2 = find_digit_strikes(n_spot_open, 50, n_d2)

    contracts = []
    for s in strikes_d1 + strikes_d2:
        for opt_type in ["CE", "PE"]:
            strike_name = f"{s} {opt_type}"
            ltp_val = fetch_live_ltp_from_broker("NFO", strike_name, "0")
            if ltp_val == 0.0:
                ltp_val = st.session_state.live_ltp.get(strike_name, 0.0)
            else:
                st.session_state.live_ltp[strike_name] = ltp_val

            if strike_name not in st.session_state.strike_open_prices and ltp_val > 0:
                st.session_state.strike_open_prices[strike_name] = ltp_val
            strike_open = st.session_state.strike_open_prices.get(strike_name, ltp_val)

            old_ltp = st.session_state.prev_ltp.get(strike_name, ltp_val)
            st.session_state.prev_ltp[strike_name] = ltp_val

            if ltp_val > 0 and st.session_state.nifty_pinned is None:
                if strike_open >= n_b1 and old_ltp >= n_b1 and ltp_val <= n_b1 and abs(ltp_val - n_b1) <= 2.0:
                    st.session_state.nifty_pinned = f"{strike_name} @ ₹{ltp_val} (Buy 1)"
                elif strike_open >= n_b2 and old_ltp >= n_b2 and ltp_val <= n_b2 and abs(ltp_val - n_b2) <= 2.0:
                    st.session_state.nifty_pinned = f"{strike_name} @ ₹{ltp_val} (Buy 2)"
                elif strike_open <= n_sell and old_ltp <= n_sell and ltp_val >= n_sell and abs(ltp_val - n_sell) <= 2.0:
                    st.session_state.nifty_pinned = f"{strike_name} @ ₹{ltp_val} (Sell)"

            contracts.append({
                "Strike": strike_name, "LTP": ltp_val, 
                "Buy 1": n_b1, "Buy 2": n_b2, "Sell": n_sell
            })
    
    st.table(pd.DataFrame(contracts))

# ----------- SENSEX TAB -----------
with tab_sensex:
    live_s_spot = fetch_live_ltp_from_broker("BSE", "SENSEX", "999919000")
    live_s_fut = fetch_live_ltp_from_broker("BFO", "SENSEXFUT", "0")

    if not st.session_state.sensex_day_locked:
        if live_s_spot > 0:
            st.session_state.sensex_s_open = live_s_spot
        if live_s_fut > 0:
            st.session_state.sensex_f_open = live_s_fut
        if now_time.hour > 9 or (now_time.hour == 9 and now_time.minute >= 13):
            if st.session_state.sensex_s_open > 0:
                st.session_state.sensex_day_locked = True

    s_spot_open = st.session_state.sensex_s_open if st.session_state.sensex_s_open > 0 else (live_s_spot if live_s_spot > 0 else 73250.0)
    s_fut_open = st.session_state.sensex_f_open if st.session_state.sensex_f_open > 0 else (live_s_fut if live_s_fut > 0 else 73300.0)

    ss_code = calculate_custom_digit_code(s_spot_open)
    sf_code = calculate_custom_digit_code(s_fut_open)

    st.markdown(f"""
        <div class="compact-box">
            <b>S:</b> {s_spot_open} (Code: <b>{ss_code}</b>) &nbsp;&nbsp;|&nbsp;&nbsp; <b>F:</b> {s_fut_open} (Code: <b>{sf_code}</b>)
        </div>
    """, unsafe_allow_html=True)

    if st.session_state.sensex_pinned:
        st.markdown(f"""
            <div class="pin-box">
                🎯 First Trigger Lock (Sensex): {st.session_state.sensex_pinned}
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background-color: #0f172a; padding: 6px; border-radius: 6px; text-align: center; color: #94a3b8; font-size: 12px; margin-bottom: 6px;">
                📌 Sensex Pin Board: Waiting for trigger...
            </div>
        """, unsafe_allow_html=True)

    if "s_d1_val" not in st.session_state: st.session_state.s_d1_val = "5"
    if "s_d2_val" not in st.session_state: st.session_state.s_d2_val = "8"
    if "s_b1_val" not in st.session_state: st.session_state.s_b1_val = "300.0"
    if "s_b2_val" not in st.session_state: st.session_state.s_b2_val = "350.0"
    if "s_sell_val" not in st.session_state: st.session_state.s_sell_val = "450.0"

    sd_col1, sd_col2 = st.columns(2)
    with sd_col1:
        sd1_str = st.text_input("Digit 1", st.session_state.s_d1_val, key="sd1_input")
        st.session_state.s_d1_val = sd1_str
    with sd_col2:
        sd2_str = st.text_input("Digit 2", st.session_state.s_d2_val, key="sd2_input")
        st.session_state.s_d2_val = sd2_str

    sb_col1, sb_col2, sb_col3 = st.columns(3)
    with sb_col1:
        sb1_str = st.text_input("Buy 1", st.session_state.s_b1_val, key="sb1_input")
        st.session_state.s_b1_val = sb1_str
    with sb_col2:
        sb2_str = st.text_input("Buy 2", st.session_state.s_b2_val, key="sb2_input")
        st.session_state.s_b2_val = sb2_str
    with sb_col3:
        ssell_str = st.text_input("Sell", st.session_state.s_sell_val, key="ssell_input")
        st.session_state.s_sell_val = ssell_str

    s_d1 = int(sd1_str) if sd1_str.isdigit() else 5
    s_d2 = int(sd2_str) if sd2_str.isdigit() else 8
    s_b1 = float(sb1_str) if sb1_str.replace('.', '', 1).isdigit() else 300.0
    s_b2 = float(sb2_str) if sb2_str.replace('.', '', 1).isdigit() else 350.0
    s_sell = float(ssell_str) if ssell_str.replace('.', '', 1).isdigit() else 450.0

    s_strikes_d1 = find_digit_strikes(s_spot_open, 100, s_d1)
    s_strikes_d2 = find_digit_strikes(s_spot_open, 100, s_d2)

    s_contracts = []
    for s in s_strikes_d1 + s_strikes_d2:
        for opt_type in ["CE", "PE"]:
            strike_name = f"{s} {opt_type}"
            ltp_val = fetch_live_ltp_from_broker("BFO", strike_name, "0")
            if ltp_val == 0.0:
                ltp_val = st.session_state.live_ltp.get(strike_name, 0.0)
            else:
                st.session_state.live_ltp[strike_name] = ltp_val

            if strike_name not in st.session_state.strike_open_prices and ltp_val > 0:
                st.session_state.strike_open_prices[strike_name] = ltp_val
            strike_open = st.session_state.strike_open_prices.get(strike_name, ltp_val)

            old_ltp = st.session_state.prev_ltp.get(strike_name, ltp_val)
            st.session_state.prev_ltp[strike_name] = ltp_val

            if ltp_val > 0 and st.session_state.sensex_pinned is None:
                if strike_open >= s_b1 and old_ltp >= s_b1 and ltp_val <= s_b1 and abs(ltp_val - s_b1) <= 2.0:
                    st.session_state.sensex_pinned = f"{strike_name} @ ₹{ltp_val} (Buy 1)"
                elif strike_open >= s_b2 and old_ltp >= s_b2 and ltp_val <= s_b2 and abs(ltp_val - s_b2) <= 2.0:
                    st.session_state.sensex_pinned = f"{strike_name} @ ₹{ltp_val} (Buy 2)"
                elif strike_open <= s_sell and old_ltp <= s_sell and ltp_val >= s_sell and abs(ltp_val - s_sell) <= 2.0:
                    st.session_state.sensex_pinned = f"{strike_name} @ ₹{ltp_val} (Sell)"

            s_contracts.append({
                "Strike": strike_name, "LTP": ltp_val, 
                "Buy 1": s_b1, "Buy 2": s_b2, "Sell": s_sell
            })
    
    st.table(pd.DataFrame(s_contracts))
