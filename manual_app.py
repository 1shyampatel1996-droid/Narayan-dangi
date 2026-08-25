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

# --- ITM स्ट्राइक प्राइस निकालने का लॉजिक (प्राइस या डिजिट दोनों के लिए) ---
def get_itm_strike_and_color(price, reference_value, compare_value, is_nifty=True):
    step = 50 if is_nifty else 100
    base_strike = round(price / step) * step
    
    # यदि तुलनात्मक वैल्यू बड़ी या बराबर है तो Green (Call), अन्यथा Red (Put)
    if compare_value >= reference_value:
        itm_strike = base_strike - step if price < base_strike else base_strike
        # हरा रंग (Call)
        return f"<span style='color: #28a745; font-weight: bold;'>🟢 {int(itm_strike)} CE</span>"
    else:
        itm_strike = base_strike + step if price > base_strike else base_strike
        # लाल रंग (Put)
        return f"<span style='color: #dc3545; font-weight: bold;'>🔴 {int(itm_strike)} PE</span>"

# --- डेटा प्रोसेस करें ---
n_spot_final_dig, n_spot_third = calculate_digits(manual_nifty_spot)
n_fut_final_dig, n_fut_third = calculate_digits(manual_nifty_fut)

s_spot_final_dig, s_spot_third = calculate_digits(manual_sensex_spot)
s_fut_final_dig, s_fut_third = calculate_digits(manual_sensex_fut)

# --- 1. प्राइस के आधार पर ITM (फ्यूचर बनाम स्पॉट प्राइस) ---
n_spot_price_itm = get_itm_strike_and_color(manual_nifty_spot, manual_nifty_spot, manual_nifty_fut, is_nifty=True)
n_fut_price_itm = get_itm_strike_and_color(manual_nifty_fut, manual_nifty_fut, manual_nifty_spot, is_nifty=True)

s_spot_price_itm = get_itm_strike_and_color(manual_sensex_spot, manual_sensex_spot, manual_sensex_fut, is_nifty=False)
s_fut_price_itm = get_itm_strike_and_color(manual_sensex_fut, manual_sensex_fut, manual_sensex_spot, is_nifty=False)

# --- 2. डिजिट के आधार पर ITM (फ्यूचर डिजिट बनाम स्पॉट डिजिट) ---
n_spot_digit_itm = get_itm_strike_and_color(manual_nifty_spot, n_spot_final_dig, n_fut_final_dig, is_nifty=True)
n_fut_digit_itm = get_itm_strike_and_color(manual_nifty_fut, n_fut_final_dig, n_spot_final_dig, is_nifty=True)

s_spot_digit_itm = get_itm_strike_and_color(manual_sensex_spot, s_spot_final_dig, s_fut_final_dig, is_nifty=False)
s_fut_digit_itm = get_itm_strike_and_color(manual_sensex_fut, s_fut_final_dig, s_spot_final_dig, is_nifty=False)

# डिस्प्ले कलर्स (प्राइस और डिजिट के लिए)
n_price_spot_col = "red" if manual_nifty_fut >= manual_nifty_spot else "green"
n_price_fut_col = "green" if manual_nifty_fut >= manual_nifty_spot else "red"
n_digit_spot_col = "red" if n_fut_third >= n_spot_third else "green"
n_digit_fut_col = "green" if n_fut_third >= n_spot_third else "red"

s_price_spot_col = "red" if manual_sensex_fut >= manual_sensex_spot else "green"
s_price_fut_col = "green" if manual_sensex_fut >= manual_sensex_spot else "red"
s_digit_spot_col = "red" if s_fut_third >= s_spot_third else "green"
s_digit_fut_col = "green" if s_fut_third >= s_spot_third else "red"


# --- UI डिस्प्ले (प्राइस ITM और डिजिट ITM दोनों एक ही लाइन में नीचे शो होंगे) ---
st.markdown("### 1. Nifty Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 15px;">
    <!-- Nifty 50 Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #333;">
        <span style="font-weight: bold; color: #fff; width: 25%;">Nifty 50</span>
        <span style="color: {n_price_spot_col}; font-weight: bold; width: 25%; text-align: right;">{manual_nifty_spot:,.2f}</span>
        <span style="color: {n_digit_spot_col}; font-weight: bold; width: 20%; text-align: right;">{n_spot_final_dig}</span>
        <span style="width: 30%; text-align: right;">Price: {n_spot_price_itm}</span>
    </div>
    <div style="padding-left: 5px; font-size: 13px; color: #ccc; margin-bottom: 6px;">
        Digit ITM: {n_spot_digit_itm}
    </div>
    
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-top: 1px solid #333; margin-top: 4px;">
        <span style="font-weight: bold; color: #fff; width: 25%;">Future</span>
        <span style="color: {n_price_fut_col}; font-weight: bold; width: 25%; text-align: right;">{manual_nifty_fut:,.2f}</span>
        <span style="color: {n_digit_fut_col}; font-weight: bold; width: 20%; text-align: right;">{n_fut_final_dig}</span>
        <span style="width: 30%; text-align: right;">Price: {n_fut_price_itm}</span>
    </div>
    <div style="padding-left: 5px; font-size: 13px; color: #ccc;">
        Digit ITM: {n_fut_digit_itm}
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### 2. Sensex Group")
st.markdown(f"""
<div style="background-color: #1e1e1e; padding: 12px; border-radius: 8px; margin-bottom: 12px; font-size: 15px;">
    <!-- Sensex Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-bottom: 1px solid #333;">
        <span style="font-weight: bold; color: #fff; width: 25%;">Sensex</span>
        <span style="color: {s_price_spot_col}; font-weight: bold; width: 25%; text-align: right;">{manual_sensex_spot:,.2f}</span>
        <span style="color: {s_digit_spot_col}; font-weight: bold; width: 20%; text-align: right;">{s_spot_final_dig}</span>
        <span style="width: 30%; text-align: right;">Price: {s_spot_price_itm}</span>
    </div>
    <div style="padding-left: 5px; font-size: 13px; color: #ccc; margin-bottom: 6px;">
        Digit ITM: {s_spot_digit_itm}
    </div>
    
    <!-- Future Row -->
    <div style="display: flex; justify-content: space-between; align-items: center; padding: 6px 0; border-top: 1px solid #333; margin-top: 4px;">
        <span style="font-weight: bold; color: #fff; width: 25%;">Future</span>
        <span style="color: {s_price_fut_col}; font-weight: bold; width: 25%; text-align: right;">{manual_sensex_fut:,.2f}</span>
        <span style="color: {s_digit_fut_col}; font-weight: bold; width: 20%; text-align: right;">{s_fut_final_dig}</span>
        <span style="width: 30%; text-align: right;">Price: {s_fut_price_itm}</span>
    </div>
    <div style="padding-left: 5px; font-size: 13px; color: #ccc;">
        Digit ITM: {s_fut_digit_itm}
    </div>
</div>
""", unsafe_allow_html=True)
