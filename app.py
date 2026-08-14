import streamlit as st

# यह एक उदाहरण है, आप अपना डेटा सोर्स यहाँ वैसे ही रखें जैसे अभी है
# यहाँ हम सिर्फ डिस्प्ले फॉर्मेट बदल रहे हैं

st.title("Market Live Data Dashboard")

# 1. Nifty Group
st.subheader("1. Nifty Group")
# फॉर्मेट: [नाम] [ओपन प्राइस] [नंबर]
st.write(f"Nifty 50 Index | 24361.9 | 257")
st.write(f"Nifty Current Future | 24452.0 | 178")

# 2. Sensex Group
st.subheader("2. Sensex Group")
# फॉर्मेट: [नाम] [ओपन प्राइस] [नंबर]
st.write(f"Sensex Index | 77903.43 | 336")
st.write(f"Sensex Current Future | 78278.0 | 325")
