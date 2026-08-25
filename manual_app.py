import streamlit as st

# पेज सेटअप
st.set_page_config(page_title="Manual ITM Signal Dashboard", layout="wide")
st.title("📊 Manual ITM Signal & Price Dashboard")

st.sidebar.title("🛠️ Manual Price Inputs")
st.sidebar.info("यहाँ जो नंबर एक बार डाल देंगे, वह रिफ्रेश करने पर भी सुरक्षित रहेगा।")

# --- Session State Initialization ---
if 'nifty_spot' not in st.session_state:
    st.session_state.nifty_spot = 22000.0
if 'nifty_fut' not in st.session_state:
    st.session_state.nifty_fut = 22050.0
if 'sensex_spot' not in st.session_state:
    st.session_state.sensex_spot = 73000.0
if 'sensex_fut' not in st.session_state:
    st.session_state.sensex_fut = 73100.0

# --- 1. मैनुअल इनपुट फील्ड्स ---
st.sidebar.markdown("### Nifty Group (Gap: 50)")
st.session_state.nifty_spot = st.sidebar.number_input("Nifty 50 Open", value=st.session_state.nifty_spot, step=50.0)
st.session_state.nifty_fut = st.sidebar.number_input("Nifty Future Open", value=st.session_state.nifty_fut, step=50.0)

st.sidebar.markdown("### Sensex Group (Gap: 100)")
st.session_state.sensex_spot = st.sidebar.number_input("Sensex Open", value=st.session_state.sensex_spot, step=100.0)
st.session_state.sensex_fut = st.sidebar.number_input("Sensex Future Open", value=st.session_state.sensex_fut, step=100.0)

manual_nifty_spot = st.session_state.nifty_spot
manual_nifty_fut = st.session_state.nifty_fut
manual_sensex_spot = st.session_state.sensex_spot
manual_sensex_fut = st.session_state.sensex_fut

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

# --- डिस्प्ले फॉर्मेटिंग और डॉट लॉजिक ---
def format_itm_display(price, compare_val1, compare_val2, digit_val1, digit_val2, is_nifty=True):
    # प्राइस बेस्ड स्ट्राइक और टाइप
    p_strike, p_type = get_strike_and_type(price, compare_val1, compare_val2, is_nifty)
    # डिजिट बेस्ड स्ट्राइक और टाइप
    d_strike, d_type = get_strike_and_type(price, digit_val1, digit_val2, is_nifty)
    
    p_color = "#28a745" if p_type == "CE" else "#dc3545"
    d_color = "#28a745" if d_type == "CE" else "#dc3545"
    
    # नियम: अगर दोनों का स्ट्राइक सेम है और टाइप भी सेम है, तभी डॉट दिखाएं, अन्यथा खाली रखें
    match_dot = ""
    if p_strike == d_strike and p_type == d_type:
        dot_icon = "🟢" if p_type == "CE" else "🔴"
        match_dot = f" &nbsp; <span style='font-size: 15px;'>{dot_icon}</span>"
        
    res_str = f"<span style='color: {p_color}; font-weight: bold; font-size: 12px;'>{p_strike}</span>"
    res_str += f" | <span style='color: {d_color}; font-weight: bold; font-size: 12px;'>{d_strike}</span>"
    res_str += match_dot
    
    return res_str

# --- डेटा प्रोसेस करें ---
n_spot_final_dig, n_spot_third = calculate_digits(manual_nifty_spot)
n_fut_final_dig, n_fut_third = calculate_digits(manual_nifty_fut)

s_spot_final_dig, s_spot_third = calculate_digits(manual_sensex_spot)
s_fut_final_dig, s_fut_third = calculate_digits(manual_sensex_fut)

# कलर्स
n_price_spot_col = "#dc3545" if manual_nifty_fut >= manual_nifty_spot else "#28a745"
n_price_fut_col = "#28a745" if manual_nifty_fut >= manual_nifty_spot else "#dc3545"
n_digit_spot_col = "#dc3545" if n_fut_third >= n_spot_third else "#28a745"
n_digit_fut_col = "#28a745" if n_fut_third >= n_spot_third else "#dc3545"

s_price_spot_col = "#dc3545" if manual_sensex_fut >= manual_sensex_spot else "#28a745"
s_price_fut_col = "#28a745" if manual_sensex_fut >= manual_sensex_spot else "#dc3545"
s_digit_spot_col = "#dc3545" if s_fut_third >= s_spot_third else "#28a745"
s_digit_fut_col = "#28a745" if s_fut_third >= s_spot_third else "#dc3545"

# --- ITM वैल्यूज ---
n_spot_itm_final = format_itm_display(manual_nifty_spot, manual_nifty_fut, manual_nifty_spot, n_fut_final_dig, n_spot_final_dig, True)
n_fut_itm_final = format_itm_display(manual_nifty_fut, manual_nifty_spot, manual_nifty_fut, n_spot_final_dig, n_fut_final_dig, True)

s_spot_itm_final = format_itm_display(manual_sensex_spot, manual_sensex_fut, manual_sensex_spot, s_fut_final_dig, s_spot_final_dig, False)
s_fut_itm_final = format_itm_display(manual_sensex_fut, manual_sensex_spot, manual_sensex_fut, s_spot_final_dig, s_fut_final_dig, False)


# --- UI डिस्प्ले ---
st.markdown("### 1. Nifty Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 15px; font-size: 14px;">
    <!-- Nifty 50 Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 8px;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Nifty 50</div>
        <div style="width: 32%; text-align: right; color: {n_price_spot_col}; font-weight: bold;">{manual_nifty_spot:,.2f}<br>{n_spot_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {n_digit_spot_col}; font-weight: bold;">{n_spot_final_dig}</div>
    </div>
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 32%; text-align: right; color: {n_price_fut_col}; font-weight: bold;">{manual_nifty_fut:,.2f}<br>{n_fut_itm_final}</div>
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
        <div style="width: 32%; text-align: right; color: {s_price_spot_col}; font-weight: bold;">{manual_sensex_spot:,.2f}<br>{s_spot_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {s_digit_spot_col}; font-weight: bold;">{s_spot_final_dig}</div>
    </div>
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 32%; text-align: right; color: {s_price_fut_col}; font-weight: bold;">{manual_sensex_fut:,.2f}<br>{s_fut_itm_final}</div>
        <div style="width: 20%; text-align: right; color: {s_digit_fut_col}; font-weight: bold;">{s_fut_final_dig}</div>
    </div>
</div>
""", unsafe_allow_html=True)
