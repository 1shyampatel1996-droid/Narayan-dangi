import streamlit as st

# सेटअप
st.set_page_config(page_title="Market Live App", layout="wide")
st.title("Market Live Data Dashboard")

def get_color(val1, val2):
    try:
        d1 = int(str(val1)[-1])
        d2 = int(str(val2)[-1])
        return ("green", "red") if d1 > d2 else ("red", "green")
    except:
        return ("black", "black")

# डेटा सोर्स
nifty_idx_open, nifty_idx_fin = "24361.9", "257"
nifty_fut_open, nifty_fut_fin = "24452.0", "178"
sensex_idx_open, sensex_idx_fin = "77903.43", "336"
sensex_fut_open, sensex_fut_fin = "78278.0", "325"

n_col1, n_col2 = get_color(nifty_idx_open, nifty_idx_fin)
s_col1, s_col2 = get_color(sensex_idx_open, sensex_idx_fin)

# फंक्शन: एक सीधी लाइन में डेटा दिखाने के लिए
def show_row(name, price, fin_val, color):
    col1, col2, col3 = st.columns([2.5, 2, 1.5])
    with col1:
        st.markdown(f"**{name}**")
    with col2:
        st.markdown(f"{price}")
    with col3:
        st.markdown(f"<span style='color:{color}'>{fin_val}</span>", unsafe_allow_html=True)

# 1. Nifty Group
st.markdown("### 1. Nifty Group")
show_row("Nifty 50", nifty_idx_open, nifty_idx_fin, n_col2)
show_row("Future", nifty_fut_open, nifty_fut_fin, n_col1)

st.markdown("---")

# 2. Sensex Group
st.markdown("### 2. Sensex Group")
show_row("Sensex", sensex_idx_open, sensex_idx_fin, s_col2)
show_row("Future", sensex_fut_open, sensex_fut_fin, s_col1)
