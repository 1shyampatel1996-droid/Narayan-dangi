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

# --- सहायक फंक्शन: डिजिट और थर्ड डिजिट कैलकुलेशन ---
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

# --- स्ट्राइक प्राइस (ITM) निकालने का लॉजिक ---
def get_itm_recommendation(price, color_status, is_nifty=True):
    step = 50 if is_nifty else 100
    base_strike = round(price / step) * step
    
    if color_status == "green":
        itm_strike = base_strike - step if price < base_strike else base_strike
        return f"🟢 {int(itm_strike)} CE"
    else:
        itm_strike = base_strike + step if price > base_strike else base_strike
        return f"🔴 {int(itm_strike)} PE"

# --- डेटा प्रोसेस करें ---
_, n_spot_third = calculate_digits(manual_nifty_spot)
_, n_fut_third = calculate_digits(manual_nifty_fut)

_, s_spot_third = calculate_digits(manual_sensex_spot)
_, s_fut_third = calculate_digits(manual_sensex_fut)

# डिजिट कलर
n_digit_spot_col = "red" if n_fut_third >= n_spot_third else "green"
n_digit_fut_col = "green" if n_fut_third >= n_spot_third else "red"

s_digit_spot_col = "red" if s_fut_third >= s_spot_third else "green"
s_digit_fut_col = "green" if s_fut_third >= s_spot_third else "red"

# प्राइस कलर
n_price_spot_col = "red" if manual_nifty_fut >= manual_nifty_spot else "green"
n_price_fut_col = "green" if manual_nifty_fut >= manual_nifty_spot else "red"

s_price_spot_col = "red" if manual_sensex_fut >= manual_sensex_spot else "green"
s_price_fut_col = "green" if manual_sensex_fut >= manual_sensex_spot else "red"

# ITM रिकमेंडेशन
n_spot_itm = get_itm_recommendation(manual_nifty_spot, n_price_spot_col, is_nifty=True)
n_fut_itm = get_itm_recommendation(manual_nifty_fut, n_price_fut_col, is_nifty=True)

s_spot_itm = get_itm_recommendation(manual_sensex_spot, s_price_spot_col, is_nifty=False)
s_fut_itm = get_itm_recommendation(manual_sensex_fut, s_price_fut_col, is_nifty=False)

# --- UI डिस्प्ले (मोबाइल फ्रेंडली कॉम्पैक्ट रो डिज़ाइन) ---
st.markdown("### 1. Nifty Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 15px;">
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #333;">
        <span style="font-weight: bold; color: #fff;">Nifty 50</span>
        <span style="color: {n_price_spot_col}; font-weight: bold;">{manual_nifty_spot:,.2f}</span>
        <span style="color: {n_digit_spot_col};">Dig: {n_spot_third}</span>
        <span style="font-weight: bold; color: #fff;">{n_spot_itm}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; margin-top: 4px;">
        <span style="font-weight: bold; color: #fff;">Future</span>
        <span style="color: {n_price_fut_col}; font-weight: bold;">{manual_nifty_fut:,.2f}</span>
        <span style="color: {n_digit_fut_col};">Dig: {n_fut_third}</span>
        <span style="font-weight: bold; color: #fff;">{n_fut_itm}</span>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 2. Sensex Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 10px; border-radius: 8px; margin-bottom: 10px; font-size: 15px;">
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px solid #333;">
        <span style="font-weight: bold; color: #fff;">Sensex</span>
        <span style="color: {s_price_spot_col}; font-weight: bold;">{manual_sensex_spot:,.2f}</span>
        <span style="color: {s_digit_spot_col};">Dig: {s_spot_third}</span>
        <span style="font-weight: bold; color: #fff;">{s_spot_itm}</span>
    </div>
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; margin-top: 4px;">
        <span style="font-weight: bold; color: #fff;">Future</span>
        <span style="color: {s_price_fut_col}; font-weight: bold;">{manual_sensex_fut:,.2f}</span>
        <span style="color: {s_digit_fut_col};">Dig: {s_fut_third}</span>
        <span style="font-weight: bold; color: #fff;">{s_fut_itm}</span>
    </div>
</div>
""", unsafe_allow_html=True)
