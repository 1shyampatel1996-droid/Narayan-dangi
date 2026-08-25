import streamlit as st

# पेज सेटअप
st.set_page_config(page_title="Manual ITM Signal Dashboard", layout="wide")
st.title("📊 Manual ITM Signal & Price Dashboard")

st.sidebar.title("🛠️ Manual Price Inputs")
st.sidebar.info("यहाँ जो नंबर एक बार डाल देंगे, वह रिफ्रेश करने पर भी सुरक्षित रहेगा।")

# --- Session State Initialization ---
if 'nifty_spot_val' not in st.session_state:
    st.session_state.nifty_spot_val = 22000.0
if 'nifty_fut_val' not in st.session_state:
    st.session_state.nifty_fut_val = 22050.0
if 'sensex_spot_val' not in st.session_state:
    st.session_state.sensex_spot_val = 73000.0
if 'sensex_fut_val' not in st.session_state:
    st.session_state.sensex_fut_val = 73100.0

# --- 1. मैनुअल इनपुट फील्ड्स ---
st.sidebar.markdown("### Nifty Group (Gap: 50)")
manual_nifty_spot = st.sidebar.number_input("Nifty 50 Open", key="nifty_spot_val", step=50.0)
manual_nifty_fut = st.sidebar.number_input("Nifty Future Open", key="nifty_fut_val", step=50.0)

st.sidebar.markdown("### Sensex Group (Gap: 100)")
manual_sensex_spot = st.sidebar.number_input("Sensex Open", key="sensex_spot_val", step=100.0)
manual_sensex_fut = st.sidebar.number_input("Sensex Future Open", key="sensex_fut_val", step=100.0)

# --- सहायक फंक्शन: 3-अंकों का डिजिट कैलकुलेशन ---
def calculate_digits(open_price):
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
    return final_digit, third_digit

# --- स्ट्राइक प्राइस और टाइप (CE/PE) निकालने का फंक्शन ---
def get_strike_and_type(price, compare_val1, compare_val2, is_nifty=True):
    step = 50 if is_nifty else 100
    base_strike = round(price / step) * step
    
    if compare_val1 >= compare_val2:
        itm_strike = base_strike - step if price < base_strike else base_strike
        return int(itm_strike), "CE"
    else:
        itm_strike = base_strike + step if price > base_strike else base_strike
        return int(itm_strike), "PE"

# --- डेटा प्रोसेस करें ---
n_spot_final_dig, n_spot_third = calculate_digits(manual_nifty_spot)
n_fut_final_dig, n_fut_third = calculate_digits(manual_nifty_fut)

s_spot_final_dig, s_spot_third = calculate_digits(manual_sensex_spot)
s_fut_final_dig, s_fut_third = calculate_digits(manual_sensex_fut)

# Nifty के लिए स्ट्राइक और टाइप्स
n_spot_p_strike, n_spot_p_type = get_strike_and_type(manual_nifty_spot, manual_nifty_fut, manual_nifty_spot, True)
n_spot_d_strike, n_spot_d_type = get_strike_and_type(manual_nifty_spot, n_fut_final_dig, n_spot_final_dig, True)

n_fut_p_strike, n_fut_p_type = get_strike_and_type(manual_nifty_fut, manual_nifty_spot, manual_nifty_fut, True)
n_fut_d_strike, n_fut_d_type = get_strike_and_type(manual_nifty_fut, n_spot_final_dig, n_fut_final_dig, True)

# Sensex के लिए स्ट्राइक और टाइप्स
s_spot_p_strike, s_spot_p_type = get_strike_and_type(manual_sensex_spot, manual_sensex_fut, manual_sensex_spot, False)
s_spot_d_strike, s_spot_d_type = get_strike_and_type(manual_sensex_spot, s_fut_final_dig, s_spot_final_dig, False)

s_fut_p_strike, s_fut_p_type = get_strike_and_type(manual_sensex_fut, manual_sensex_spot, manual_sensex_fut, False)
s_fut_d_strike, s_fut_d_type = get_strike_and_type(manual_sensex_fut, s_spot_final_dig, s_fut_final_dig, False)

# --- नया डॉट नियम: यदि दोनों का टाइप (CE/PE) एक जैसा है, तो डॉट दिखाएं ---
def get_type_match_dot(p_type, d_type):
    if p_type == d_type:
        return " 🟢" if p_type == "CE" else " 🔴"
    return ""

n_spot_dot = get_type_match_dot(n_spot_p_type, n_spot_d_type)
n_fut_dot = get_type_match_dot(n_fut_p_type, n_fut_d_type)
s_spot_dot = get_type_match_dot(s_spot_p_type, s_spot_d_type)
s_fut_dot = get_type_match_dot(s_fut_p_type, s_fut_d_type)

# कलर्स
n_price_spot_col = "#dc3545" if manual_nifty_fut >= manual_nifty_spot else "#28a745"
n_price_fut_col = "#28a745" if manual_nifty_fut >= manual_nifty_spot else "#dc3545"
n_digit_spot_col = "#dc3545" if n_fut_third >= n_spot_third else "#28a745"
n_digit_fut_col = "#28a745" if n_fut_third >= n_spot_third else "#28a745"

s_price_spot_col = "#dc3545" if manual_sensex_fut >= manual_sensex_spot else "#28a745"
s_price_fut_col = "#28a745" if manual_sensex_fut >= manual_sensex_spot else "#28a745"
s_digit_spot_col = "#dc3545" if s_fut_third >= s_spot_third else "#28a745"
s_digit_fut_col = "#28a745" if s_fut_third >= s_spot_third else "#28a745"

# --- डिस्प्ले फॉर्मेट ---
def make_display(p_strike, p_type, d_strike, d_type, dot):
    p_col = "#28a745" if p_type == "CE" else "#dc3545"
    d_col = "#28a745" if d_type == "CE" else "#dc3545"
    return f"<span style='color: {p_col}; font-weight: bold; font-size: 12px;'>{p_strike}</span> | <span style='color: {d_col}; font-weight: bold; font-size: 12px;'>{d_strike}</span>{dot}"

n_spot_itm_final = make_display(n_spot_p_strike, n_spot_p_type, n_spot_d_strike, n_spot_d_type, n_spot_dot)
n_fut_itm_final = make_display(n_fut_p_strike, n_fut_p_type, n_fut_d_strike, n_fut_d_type, n_fut_dot)

s_spot_itm_final = make_display(s_spot_p_strike, s_spot_p_type, s_spot_d_strike, s_spot_d_type, s_spot_dot)
s_fut_itm_final = make_display(s_fut_p_strike, s_fut_p_type, s_fut_d_strike, s_fut_d_type, s_fut_dot)

# --- UI डिस्प्ले ---
st.markdown("### 1. Nifty Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px;">
    <!-- Nifty 50 Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 8px;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Nifty 50</div>
        <div style="width: 42%; text-align: right; color: {n_price_spot_col}; font-weight: bold;">{manual_nifty_spot:,.2f}<br>{n_spot_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {n_digit_spot_col}; font-weight: bold;">{n_spot_final_dig}</div>
    </div>
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 42%; text-align: right; color: {n_price_fut_col}; font-weight: bold;">{manual_nifty_fut:,.2f}<br>{n_fut_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {n_digit_fut_col}; font-weight: bold;">{n_fut_final_dig}</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 2. Sensex Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px;">
    <!-- Sensex Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 8px;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Sensex</div>
        <div style="width: 42%; text-align: right; color: {s_price_spot_col}; font-weight: bold;">{manual_sensex_spot:,.2f}<br>{s_spot_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {s_digit_spot_col}; font-weight: bold;">{s_spot_final_dig}</div>
    </div>
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 42%; text-align: right; color: {s_price_fut_col}; font-weight: bold;">{manual_sensex_fut:,.2f}<br>{s_fut_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {s_digit_fut_col}; font-weight: bold;">{s_fut_final_dig}</div>
    </div>
</div>
""", unsafe_allow_html=True)
