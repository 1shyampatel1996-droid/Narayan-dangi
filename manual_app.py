import streamlit as st

# पेज सेटअप
st.set_page_config(page_title="Manual ITM Signal Dashboard", layout="wide")
st.title("📊 Manual ITM Signal & Price Dashboard")

st.sidebar.title("🛠️ Manual Price Inputs")
st.sidebar.info("यहाँ आप अपनी मर्जी से ओपन प्राइस दर्ज कर सकते हैं।")

# --- 1. मैनुअल इनपुट फील्ड्स (साइडबार में) ---
st.sidebar.markdown("### Nifty Group (Gap: 50)")
manual_nifty_spot = st.sidebar.number_input("Nifty 50 Open", value=22000.0, step=50.0)
manual_nifty_fut = st.sidebar.number_input("Nifty Future Open", value=22050.0, step=50.0)

st.sidebar.markdown("### Sensex Group (Gap: 100)")
manual_sensex_spot = st.sidebar.number_input("Sensex Open", value=73000.0, step=100.0)
manual_sensex_fut = st.sidebar.number_input("Sensex Future Open", value=73100.0, step=100.0)

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

# --- ITM स्ट्राइक प्राइस निकालने का लॉजिक ---
def get_itm_badge(price, compare_val1, compare_val2, is_nifty=True):
    step = 50 if is_nifty else 100
    base_strike = round(price / step) * step
    
    # अगर तुलनात्मक वैल्यू बड़ी या बराबर है तो Green (Call), अन्यथा Red (Put)
    if compare_val1 >= compare_val2:
        itm_strike = base_strike - step if price < base_strike else base_strike
        return f"<span style='color: #28a745; font-weight: bold;'>🟢 {int(itm_strike)}</span>"
    else:
        itm_strike = base_strike + step if price > base_strike else base_strike
        return f"<span style='color: #dc3545; font-weight: bold;'>🔴 {int(itm_strike)}</span>"

# --- डेटा प्रोसेस करें ---
n_spot_final_dig, n_spot_third = calculate_digits(manual_nifty_spot)
n_fut_final_dig, n_fut_third = calculate_digits(manual_nifty_fut)

s_spot_final_dig, s_spot_third = calculate_digits(manual_sensex_spot)
s_fut_final_dig, s_fut_third = calculate_digits(manual_sensex_fut)

# कलर्स
n_price_spot_col = "red" if manual_nifty_fut >= manual_nifty_spot else "green"
n_price_fut_col = "green" if manual_nifty_fut >= manual_nifty_spot else "red"
n_digit_spot_col = "red" if n_fut_third >= n_spot_third else "green"
n_digit_fut_col = "green" if n_fut_third >= n_spot_third else "red"

s_price_spot_col = "red" if manual_sensex_fut >= manual_sensex_spot else "green"
s_price_fut_col = "green" if manual_sensex_fut >= manual_sensex_spot else "red"
s_digit_spot_col = "red" if s_fut_third >= s_spot_third else "green"
s_digit_fut_col = "green" if s_fut_third >= s_spot_third else "red"

# --- ITM वैल्यूज ---
# Nifty Price ITM
n_spot_price_itm = get_itm_badge(manual_nifty_spot, manual_nifty_fut, manual_nifty_spot, True)
n_fut_price_itm = get_itm_badge(manual_nifty_fut, manual_nifty_spot, manual_nifty_fut, True)
# Nifty Digit ITM
n_spot_digit_itm = get_itm_badge(manual_nifty_spot, n_fut_final_dig, n_spot_final_dig, True)
n_fut_digit_itm = get_itm_badge(manual_nifty_fut, n_spot_final_dig, n_fut_final_dig, True)

# Sensex Price ITM
s_spot_price_itm = get_itm_badge(manual_sensex_spot, manual_sensex_fut, manual_sensex_spot, False)
s_fut_price_itm = get_itm_badge(manual_sensex_fut, manual_sensex_spot, manual_sensex_fut, False)
# Sensex Digit ITM
s_spot_digit_itm = get_itm_badge(manual_sensex_spot, s_fut_final_dig, s_spot_final_dig, False)
s_fut_digit_itm = get_itm_badge(manual_sensex_fut, s_spot_final_dig, s_fut_final_dig, False)


# --- UI डिस्प्ले ---
st.markdown("### 1. Nifty Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
    <!-- Nifty Spot Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 8px;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Nifty 50</div>
        <div style="width: 25%; text-align: right; color: {n_price_spot_col}; font-weight: bold;">{manual_nifty_spot:,.2f}<br><span style="font-size: 13px;">{n_spot_price_itm}</span></div>
        <div style="width: 20%; text-align: right; color: {n_digit_spot_col}; font-weight: bold;">{n_spot_final_dig}<br><span style="font-size: 13px;">{n_spot_digit_itm}</span></div>
    </div>
    
    <!-- Nifty Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 25%; text-align: right; color: {n_price_fut_col}; font-weight: bold;">{manual_nifty_fut:,.2f}<br><span style="font-size: 13px;">{n_fut_price_itm}</span></div>
        <div style="width: 20%; text-align: right; color: {n_digit_fut_col}; font-weight: bold;">{n_fut_final_dig}<br><span style="font-size: 13px;">{n_fut_digit_itm}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 2. Sensex Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 15px;">
    <!-- Sensex Spot Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #333; padding-bottom: 8px; margin-bottom: 8px;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Sensex</div>
        <div style="width: 25%; text-align: right; color: {s_price_spot_col}; font-weight: bold;">{manual_sensex_spot:,.2f}<br><span style="font-size: 13px;">{s_spot_price_itm}</span></div>
        <div style="width: 20%; text-align: right; color: {s_digit_spot_col}; font-weight: bold;">{s_spot_final_dig}<br><span style="font-size: 13px;">{s_spot_digit_itm}</span></div>
    </div>
    
    <!-- Sensex Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center;">
        <div style="width: 25%; font-weight: bold; color: #fff;">Future</div>
        <div style="width: 25%; text-align: right; color: {s_price_fut_col}; font-weight: bold;">{manual_sensex_fut:,.2f}<br><span style="font-size: 13px;">{s_fut_price_itm}</span></div>
        <div style="width: 20%; text-align: right; color: {s_digit_fut_col}; font-weight: bold;">{s_fut_final_dig}<br><span style="font-size: 13px;">{s_fut_digit_itm}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)
