import streamlit as st

# पेज सेटअप
st.set_page_config(page_title="Market Live App", layout="wide")
st.title("Market Live Data Dashboard")

def get_color(val1, val2):
    try:
        d1 = int(str(val1)[-1])
        d2 = int(str(val2)[-1])
        return ("green", "red") if d1 > d2 else ("red", "green")
    except:
        return ("black", "black")

# उदाहरण डेटा (बाद में इसमें Angel One API जोड़ेंगे)
nifty_idx_open, nifty_idx_fin = "24361.9", "257"
nifty_fut_open, nifty_fut_fin = "24452.0", "178"
sensex_idx_open, sensex_idx_fin = "77903.43", "336"
sensex_fut_open, sensex_fut_fin = "78278.0", "325"

n_col1, n_col2 = get_color(nifty_idx_fin, nifty_fut_fin)
s_col1, s_col2 = get_color(sensex_idx_fin, sensex_fut_fin)

# बॉक्स 1: निफ्टी ग्रुप
st.markdown("### 1. Nifty Group")
st.write(f"**Nifty 50 Index** | ओपन: {nifty_idx_open}  &nbsp;&nbsp; नंबर: :{n_col1}[{nifty_idx_fin}]")
st.write(f"**Nifty Current Future** | ओपन: {nifty_fut_open}  &nbsp;&nbsp; नंबर: :{n_col2}[{nifty_fut_fin}]")

st.divider()

# बॉक्स 2: सेंसेक्स ग्रुप
st.markdown("### 2. Sensex Group")
st.write(f"**Sensex Index** | ओपन: {sensex_idx_open}  &nbsp;&nbsp; नंबर: :{s_col1}[{sensex_idx_fin}]")
st.write(f"**Sensex Current Future** | ओपन: {sensex_fut_open}  &nbsp;&nbsp; नंबर: :{s_col2}[{sensex_fut_fin}]")
