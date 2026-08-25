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
def get_itm_text_and_color(price, compare_val1, compare_val2, is_nifty=True):
    step = 50 if is_nifty else 100
    base_strike = round(price / step) * step
    
    if compare_val1 >= compare_val2:
        itm_strike = base_strike - step if price < base_strike else base_strike
        return f"🟢 {int(itm_strike)}"
    else:
        itm_strike = base_strike + step if price > base_strike else base_strike
        return f"🔴 {int(itm_strike)}"

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
n_spot_price_itm = get_itm_text_and_color(manual_nifty_spot, manual_nifty_fut, manual_nifty_spot, True)
n_spot_digit_itm = get_itm_text_and_color(manual_nifty_spot, n_fut_final_dig, n_spot_final_dig, True)

n_fut_price_itm = get_itm_text_and_color(manual_nifty_fut, manual_nifty_spot, manual_nifty_fut, True)
n_fut_digit_itm = get_itm_text_and_color(manual_nifty_fut, n_spot_final_dig, n_fut_final_dig, True)

s_spot_price_itm = get_itm_text_and_color(manual_sensex_spot, manual_sensex_fut, manual_sensex_spot, False)
s_spot_digit_itm = get_itm_text_and_color(manual_sensex_spot, s_fut_final_dig, s_spot_final_dig, False)

s_fut_price_itm = get_itm_text_and_color(manual_sensex_fut, manual_sensex_spot, manual_sensex_fut, False)
s_fut_digit_itm = get_itm_text_and_color(manual_sensex_fut, s_spot_final_dig, s_fut_final_dig, False)


# --- UI डिस्प्ले (Streamlit Native Columns का उपयोग) ---
st.markdown("### 1. Nifty Group")
with st.container():
    st.markdown("---")
    # Row 1: Nifty 50
    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])
    with col1:
        st.markdown("**Nifty 50**")
    with col2:
        st.markdown(f"<span style='color:{n_price_spot_col}; font-weight:bold;'>{manual_nifty_spot:,.2f}</span><br><span style='font-size:13px;'>{n_spot_price_itm}</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span style='color:{n_digit_spot_col}; font-weight:bold;'>{n_spot_final_dig}</span><br><span style='font-size:13px;'>{n_spot_digit_itm}</span>", unsafe_allow_html=True)
    
    st.write("")
    # Row 2: Future
    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])
    with col1:
        st.markdown("**Future**")
    with col2:
        st.markdown(f"<span style='color:{n_price_fut_col}; font-weight:bold;'>{manual_nifty_fut:,.2f}</span><br><span style='font-size:13px;'>{n_fut_price_itm}</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span style='color:{n_digit_fut_col}; font-weight:bold;'>{n_fut_final_dig}</span><br><span style='font-size:13px;'>{n_fut_digit_itm}</span>", unsafe_allow_html=True)

st.markdown("### 2. Sensex Group")
with st.container():
    st.markdown("---")
    # Row 1: Sensex
    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])
    with col1:
        st.markdown("**Sensex**")
    with col2:
        st.markdown(f"<span style='color:{s_price_spot_col}; font-weight:bold;'>{manual_sensex_spot:,.2f}</span><br><span style='font-size:13px;'>{s_spot_price_itm}</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span style='color:{s_digit_spot_col}; font-weight:bold;'>{s_spot_final_dig}</span><br><span style='font-size:13px;'>{s_spot_digit_itm}</span>", unsafe_allow_html=True)
    
    st.write("")
    # Row 2: Future
    col1, col2, col3 = st.columns([1.5, 1.5, 1.5])
    with col1:
        st.markdown("**Future**")
    with col2:
        st.markdown(f"<span style='color:{s_price_fut_col}; font-weight:bold;'>{manual_sensex_fut:,.2f}</span><br><span style='font-size:13px;'>{s_fut_price_itm}</span>", unsafe_allow_html=True)
    with col3:
        st.markdown(f"<span style='color:{s_digit_fut_col}; font-weight:bold;'>{s_fut_final_dig}</span><br><span style='font-size:13px;'>{s_fut_digit_itm}</span>", unsafe_allow_html=True)
