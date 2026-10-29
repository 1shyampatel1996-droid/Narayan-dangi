import streamlit as st
import pandas as pd
import requests
import pyotp
import time
import threading
from SmartApi import SmartConnect
from SmartApi.smartWebSocketV2 import SmartWebSocketV2

# ==================== आपकी भरी हुई डिटेल्स ====================
API_KEY = "GAuh625s"
CLIENT_CODE = "N417637"
PASSWORD = "1003"
TOTP_SECRET = "2YRKKEYE2HZD562KPXZTK7PXJY"

# ==================== ग्लोबल स्टेट और लाइव डेटा होल्डर ====================
if "live_ltp" not in st.session_state:
    st.session_state.live_ltp = {}

if "nifty_pinned" not in st.session_state:
    st.session_state.nifty_pinned = None

if "sensex_pinned" not in st.session_state:
    st.session_state.sensex_pinned = None

# ==================== डिजिटल रूट (सिंगल डिजिट) कैलकुलेशन ====================
def get_digital_root(number):
    num = int(abs(number))
    while num >= 10:
        num = sum(int(digit) for digit in str(num))
    return num

# ==================== सिंगल डिजिट आधारित स्ट्राइक फाइंडर ====================
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

# ==================== ANGEL ONE WEBSOCKET CONNECTION ====================
def init_angel_websocket():
    try:
        smart_api = SmartConnect(api_key=API_KEY)
        totp = pyotp.TOTP(TOTP_SECRET).now()
        data = smart_api.generateSession(CLIENT_CODE, PASSWORD, totp)
        
        if not data['status']:
            st.error(f"Angel One लॉगिन विफल: {data['message']}")
            return None
            
        feed_token = smart_api.getfeedToken()
        jwt_token = data['data']['jwtToken']
        
        sws = SmartWebSocketV2(
            auth_token=jwt_token,
            api_key=API_KEY,
            client_code=CLIENT_CODE,
            feed_token=feed_token
        )
        
        def on_data(wsapp, message):
            import json
            try:
                msg = json.loads(message)
                token = msg.get("token")
                ltp = msg.get("last_traded_price", 0) / 100.0
                if token and ltp > 0:
                    st.session_state.live_ltp[token] = ltp
            except Exception as e:
                pass

        def on_open(wsapp):
            token_list = [{
                "action": 1,
                "mode": 1,
                "exchangeType": 2, 
                "tokens": ["55432"] 
            }]
            sws.subscribe("algo_stream", 1, token_list)

        sws.on_open = on_open
        sws.on_data = on_data
        
        ws_thread = threading.Thread(target=sws.connect, daemon=True)
        ws_thread.start()
        return sws
    except Exception as e:
        st.warning(f"WebSocket कनेक्शन शुरू नहीं हो सका: {e}")
        return None

# ==================== STREAMLIT UI LAYOUT ====================
st.set_page_config(page_title="लाइव एल्गो ट्रेडिंग डैशबोर्ड", layout="wide")

st.title("⚡ लाइव एल्गो स्ट्राइक स्कैनर (Angel One WebSocket)")
st.caption("Nifty 50 एवं Sensex - लाइव टिक बाय टिक ऑटो मैचिंग")

tab_nifty, tab_sensex = st.tabs(["📊 Nifty 50 डैशबोर्ड", "📈 Sensex डैशबोर्ड"])

# ----------- NIFTY TAB -----------
with tab_nifty:
    st.subheader("Nifty 50 सेटिंग्स")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        n_d1 = st.number_input("निफ्टी स्ट्राइक डिजिट 1", 0, 9, 3, key="nd1")
    with col2:
        n_d2 = st.number_input("निफ्टी स्ट्राइक डिजिट 2", 0, 9, 7, key="nd2")
    with col3:
        n_p1 = st.number_input("निफ्टी बाइंग भाव 1", 1.0, 1000.0, 150.0, key="np1")
    with col4:
        n_p2 = st.number_input("निफ्टी बाइंग भाव 2", 1.0, 1000.0, 250.0, key="np2")

    nifty_spot = 24000.0  
    strikes_d1 = find_digit_strikes(nifty_spot, 50, n_d1)
    strikes_d2 = find_digit_strikes(nifty_spot, 50, n_d2)

    st.markdown("---")
    st.markdown("### 📌 Nifty फर्स्ट ट्रिगर पिन बोर्ड (दिनभर के लिए लॉक)")
    if st.session_state.nifty_pinned:
        st.success(f"🎯 **सबसे पहले ट्रिगर हुई स्ट्राइक:** {st.session_state.nifty_pinned}")
    else:
        st.info("अभी तक कोई स्ट्राइक ±3% एग्जैक्ट ट्रिगर ज़ोन में नहीं आई है...")

    st.subheader("📋 मॉनिटर हो रही स्ट्राइक्स (CE & PE)")
    contracts = []
    for s in strikes_d1 + strikes_d2:
        contracts.append({"Strike": f"{s} CE", "LTP": st.session_state.live_ltp.get(str(s), 0.0)})
        contracts.append({"Strike": f"{s} PE", "LTP": st.session_state.live_ltp.get(str(s), 0.0)})
    
    st.table(pd.DataFrame(contracts))

# ----------- SENSEX TAB -----------
with tab_sensex:
    st.subheader("Sensex सेटिंग्स")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        s_d1 = st.number_input("सेंसेक्स स्ट्राइक डिजिट 1", 0, 9, 5, key="sd1")
    with col2:
        s_d2 = st.number_input("सेंसेक्स स्ट्राइक डिजिट 2", 0, 9, 8, key="sd2")
    with col3:
        s_p1 = st.number_input("सेंसेक्स बाइंग भाव 1", 1.0, 2000.0, 300.0, key="sp1")
    with col4:
        s_p2 = st.number_input("सेंसेक्स बाइंग भाव 2", 1.0, 2000.0, 450.0, key="sp2")

    sensex_spot = 73000.0  
    s_strikes_d1 = find_digit_strikes(sensex_spot, 100, s_d1)
    s_strikes_d2 = find_digit_strikes(sensex_spot, 100, s_d2)

    st.markdown("---")
    st.markdown("### 📌 Sensex फर्स्ट ट्रिगर पिन बोर्ड (दिनभर के लिए लॉक)")
    if st.session_state.sensex_pinned:
        st.success(f"🎯 **सबसे पहले ट्रिगर हुई स्ट्राइक:** {st.session_state.sensex_pinned}")
    else:
        st.info("अभी तक कोई स्ट्राइक ±3% एग्जैक्ट ट्रिगर ज़ोन में नहीं आई है...")

    st.subheader("📋 मॉनिटर हो रही स्ट्राइक्स (CE & PE)")
    s_contracts = []
    for s in s_strikes_d1 + s_strikes_d2:
        s_contracts.append({"Strike": f"{s} CE", "LTP": st.session_state.live_ltp.get(str(s), 0.0)})
        s_contracts.append({"Strike": f"{s} PE", "LTP": st.session_state.live_ltp.get(str(s), 0.0)})
    
    st.table(pd.DataFrame(s_contracts))
