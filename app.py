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

# HTML टेबल फॉर्मेट ताकि मोबाइल पर भी एक ही लाइन में रहे
html_code = f"""
<div style="font-size: 16px; line-height: 2.2;">
    <b>1. Nifty Group</b><br>
    <div style="display: flex; justify-content: space-between; padding: 2px 0;">
        <span style="width: 40%;"><b>Nifty 50</b></span>
        <span style="width: 35%; text-align: right;">{nifty_idx_open}</span>
        <span style="width: 20%; text-align: right; color: {n_col2}; font-weight: bold;">{nifty_idx_fin}</span>
    </div>
    <div style="display: flex; justify-content: space-between; padding: 2px 0;">
        <span style="width: 40%;"><b>Future</b></span>
        <span style="width: 35%; text-align: right;">{nifty_fut_open}</span>
        <span style="width: 20%; text-align: right; color: {n_col1}; font-weight: bold;">{nifty_fut_fin}</span>
    </div>
    
    <hr style="margin: 10px 0;">
    
    <b>2. Sensex Group</b><br>
    <div style="display: flex; justify-content: space-between; padding: 2px 0;">
        <span style="width: 40%;"><b>Sensex</b></span>
        <span style="width: 35%; text-align: right;">{sensex_idx_open}</span>
        <span style="width: 20%; text-align: right; color: {s_col2}; font-weight: bold;">{sensex_idx_fin}</span>
    </div>
    <div style="display: flex; justify-content: space-between; padding: 2px 0;">
        <span style="width: 40%;"><b>Future</b></span>
        <span style="width: 35%; text-align: right;">{sensex_fut_open}</span>
        <span style="width: 20%; text-align: right; color: {s_col1}; font-weight: bold;">{sensex_fut_fin}</span>
    </div>
</div>
"""

st.markdown(html_code, unsafe_allow_html=True)
