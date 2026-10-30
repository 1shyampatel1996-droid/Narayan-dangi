import os
import time
import json
import requests
import pandas as pd
from datetime import datetime, date, timedelta
from SmartApi import SmartConnect

# ==================== Page Setup & Icon ====================
st = __import__('streamlit')
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

today_str = str(date.today())
if "day_open_date" not in st.session_state or st.session_state.day_open_date != today_str:
    st.session_state.day_open_date = today_str
    st.session_state.official_nifty_open = None
    st.session_state.official_sensex_open = None

# ==================== STREAMLIT UI & MANUAL OTP LOGIN ====================
st.title("⚡ Algo Strike Scanner")

st.markdown("### 🔐 Broker Authentication (OTP Login)")
manual_otp = st.text_input("Google Authenticator OTP (6 Digits)", type="password", key="manual_otp_input")

@st.cache_resource(ttl=600)
def get_smart_connect_session_with_otp(otp_code):
    if not otp_code or len(otp_code) != 6:
        return None
    try:
        smart_api = SmartConnect(api_key=API_KEY)
        data = smart_api.generateSession(CLIENT_CODE, PASSWORD, otp_code)
        if data and data.get('status'):
            return smart_api
        else:
            st.error(f"Login Failed: {data}")
    except Exception as e:
        st.error(f"Connection Exception: {e}")
    return None

smart_api_instance = None
if manual_otp and len(manual_otp) == 6:
    smart_api_instance = get_smart_connect_session_with_otp(manual_otp)
    if smart_api_instance:
        st.success("✅ Connected to Broker Successfully!")

# ==================== Scrip Master & Live Token Mapping ====================
@st.cache_resource(ttl=3600)
def load_angel_scrip_master():
    url = "https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json"
    local_file = "OpenAPIScripMaster.json"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200:
            data = response.json()
            with open(local_file, "w") as f:
                json.dump(data, f)
            return pd.DataFrame(data)
    except Exception as e:
        pass
    
    if os.path.exists(local_file):
        with open(local_file, "r") as f:
            return pd.DataFrame(json.load(f))
    return pd.DataFrame()

scrip_df = load_angel_scrip_master()

def get_symbol_token(exchange, tradingsymbol):
    if scrip_df.empty:
        return ""
    try:
        # Exact symbol matching from master json
        for col_exch, col_sym in [('exch_seg', 'symbol'), ('exchange', 'tradingsymbol')]:
            if col_exch in scrip_df.columns and col_sym in scrip_df.columns:
                matched = scrip_df[(scrip_df[col_exch].astype(str).str.upper() == exchange.upper()) & 
                                   (scrip_df[col_sym].astype(str).str.upper() == tradingsymbol.upper())]
                if not matched.empty:
                    return str(matched.iloc[0]['token'])
                
        # Fallback partial/contains search for options
        for col in scrip_df.columns:
            sub = scrip_df[scrip_df[col].astype(str).str.upper() == tradingsymbol.upper()]
            if not sub.empty:
                for _, row in sub.iterrows():
                    if 'token' in scrip_df.columns:
                        return str(row['token'])
    except Exception as e:
        pass
    return ""

def fetch_live_ltp_safely(exchange, tradingsymbol):
    if smart_api_instance:
        token = get_symbol_token(exchange, tradingsymbol)
        if not token:
            return 0.0
        try:
            ltp_data = smart_api_instance.ltpData(exchange, tradingsymbol, token)
            if ltp_data and 'data' in ltp_data:
                return float(ltp_data['data'].get('ltp', 0.0))
        except Exception as e:
            pass
    return 0.0

def fetch_official_broker_open(exchange, tradingsymbol):
    if smart_api_instance:
        try:
            token_id = get_symbol_token(exchange, tradingsymbol)
            if not token_id:
                return 0.0
                
            from_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d 09:00")
            to_date = datetime.now().strftime("%Y-%m-%d 15:30")
            params = {
                "exchange": exchange,
                "symboltoken": token_id,
                "interval": "ONE_DAY",
                "fromdate": from_date,
                "todate": to_date
            }
            candledata = smart_api_instance.getCandleData(params)
            if candledata and 'data' in candledata and candledata['data']:
                latest_candle = candledata['data'][-1]
                val = float(latest_candle[1])
                if val > 0:
                    return val
        except Exception as e:
            pass
            
    live_val = fetch_live_ltp_safely(exchange, tradingsymbol)
    if live_val > 0:
        return live_val
        
    return 0.0

# ==================== Digital Root & Calculations ====================
def get_digital_root(number):
    try:
        num = int(abs(float(number)))
    except:
        return 0
    while num >= 10:
        num = sum(int(digit) for digit in str(num))
    return num

def calculate_custom_digit_code(price):
    if not price or price == 0:
        return "00"
    price_str = str(price).replace(".", "")
    total_sum = sum(int(d) for d in price_str if d.isdigit())
    single_digit = get_digital_root(total_sum)
    return f"{total_sum}{single_digit}"

def find_digit_strikes(current_spot, step, target_digit):
    if not current_spot or current_spot == 0:
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

# Updated based on your screenshot format: e.g., NIFTY 03NOV26 23500 CE
def get_current_expiry_symbol(index_name, strike, opt_type):
    now = datetime.now()
    days_to_thu = (3 - now.weekday()) % 7
    if days_to_thu == 0 and now.hour >= 15:
        days_to_thu = 7
    expiry_date = now + timedelta(days=days_to_thu)
    exp_str = expiry_date.strftime("%d%b%y").upper() # Format like 03NOV26
    
    return f"{index_name}{exp_str}{int(strike)}{opt_type}"

tab_nifty, tab_sensex = st.tabs(["📊 Nifty", "📈 Sensex"])

# ----------- NIFTY TAB -----------
with tab_nifty:
    if st.session_state.official_nifty_open is None and smart_api_instance is not None:
        exact_open = fetch_official_broker_open("NSE", "NIFTY")
        if exact_open and exact_open > 0:
            st.session_state.official_nifty_open = exact_open

    n_spot_open = st.session_state.official_nifty_open if st.session_state.official_nifty_open else 0.0
    ns_code = calculate_custom_digit_code(n_spot_open)

    st.markdown(f"""
        <div class="compact-box">
            <b>Nifty Official Day Open:</b> {n_spot_open} &nbsp;|&nbsp; Code: <b>{ns_code}</b>
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
            trading_symbol = get_current_expiry_symbol("NIFTY", s, opt_type)
            ltp_val = fetch_live_ltp_safely("NFO", trading_symbol)
            if ltp_val == 0.0:
                ltp_val = st.session_state.live_ltp.get(trading_symbol, 0.0)
            else:
                st.session_state.live_ltp[trading_symbol] = ltp_val

            if trading_symbol not in st.session_state.strike_open_prices and ltp_val > 0:
                st.session_state.strike_open_prices[trading_symbol] = ltp_val
            strike_open = st.session_state.strike_open_prices.get(trading_symbol, ltp_val)

            old_ltp = st.session_state.prev_ltp.get(trading_symbol, ltp_val)
            st.session_state.prev_ltp[trading_symbol] = ltp_val

            if ltp_val > 0 and st.session_state.nifty_pinned is None:
                if strike_open >= n_b1 and old_ltp >= n_b1 and ltp_val <= n_b1 and abs(ltp_val - n_b1) <= 2.0:
                    st.session_state.nifty_pinned = f"{trading_symbol} @ ₹{ltp_val} (Buy 1)"
                elif strike_open >= n_b2 and old_ltp >= n_b2 and ltp_val <= n_b2 and abs(ltp_val - n_b2) <= 2.0:
                    st.session_state.nifty_pinned = f"{trading_symbol} @ ₹{ltp_val} (Buy 2)"
                elif strike_open <= n_sell and old_ltp <= n_sell and ltp_val >= n_sell and abs(ltp_val - n_sell) <= 2.0:
                    st.session_state.nifty_pinned = f"{trading_symbol} @ ₹{ltp_val} (Sell)"

            contracts.append({
                "Strike": f"{s} {opt_type}", "LTP": ltp_val, 
                "Buy 1": n_b1, "Buy 2": n_b2, "Sell": n_sell
            })
    
    st.table(pd.DataFrame(contracts))

# ----------- SENSEX TAB -----------
with tab_sensex:
    if st.session_state.official_sensex_open is None and smart_api_instance is not None:
        s_exact_open = fetch_official_broker_open("BSE", "SENSEX")
        if s_exact_open and s_exact_open > 0:
            st.session_state.official_sensex_open = s_exact_open

    s_spot_open = st.session_state.official_sensex_open if st.session_state.official_sensex_open else 0.0
    ss_code = calculate_custom_digit_code(s_spot_open)

    st.markdown(f"""
        <div class="compact-box">
            <b>Sensex Official Day Open:</b> {s_spot_open} &nbsp;|&nbsp; Code: <b>{ss_code}</b>
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
            trading_symbol = get_current_expiry_symbol("SENSEX", s, opt_type)
            ltp_val = fetch_live_ltp_safely("BFO", trading_symbol)
            if ltp_val == 0.0:
                ltp_val = st.session_state.live_ltp.get(trading_symbol, 0.0)
            else:
                st.session_state.live_ltp[trading_symbol] = ltp_val

            if trading_symbol not in st.session_state.strike_open_prices and ltp_val > 0:
                st.session_state.strike_open_prices[trading_symbol] = ltp_val
            strike_open = st.session_state.strike_open_prices.get(trading_symbol, ltp_val)

            old_ltp = st.session_state.prev_ltp.get(trading_symbol, ltp_val)
            st.session_state.prev_ltp[trading_symbol] = ltp_val

            if ltp_val > 0 and st.session_state.sensex_pinned is None:
                if strike_open >= s_b1 and old_ltp >= s_b1 and ltp_val <= s_b1 and abs(ltp_val - s_b1) <= 2.0:
                    st.session_state.sensex_pinned = f"{trading_symbol} @ ₹{ltp_val} (Buy 1)"
                elif strike_open >= s_b2 and old_ltp >= s_b2 and ltp_val <= s_b2 and abs(ltp_val - s_b2) <= 2.0:
                    st.session_state.sensex_pinned = f"{trading_symbol} @ ₹{ltp_val} (Buy 2)"
                elif strike_open <= s_sell and old_ltp <= s_sell and ltp_val >= s_sell and abs(ltp_val - s_sell) <= 2.0:
                    st.session_state.sensex_pinned = f"{trading_symbol} @ ₹{ltp_val} (Sell)"

            s_contracts.append({
                "Strike": f"{s} {opt_type}", "LTP": ltp_val, 
                "Buy 1": s_b1, "Buy 2": s_b2, "Sell": s_sell
            })
    
    st.table(pd.DataFrame(s_contracts))

# ==================== High-Speed Live Refresh Loop ====================
time.sleep(2)
st.rerun()
