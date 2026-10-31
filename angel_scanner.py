import math
import time
from datetime import datetime
from html import escape
from zoneinfo import ZoneInfo

import pandas as pd
import pyotp
import requests
import streamlit as st
from SmartApi import SmartConnect


st.set_page_config(
    page_title="Angel Digit Scanner",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

IST = ZoneInfo("Asia/Kolkata")

MASTER_URL = (
    "https://margincalculator.angelbroking.com/"
    "OpenAPI_File/files/OpenAPIScripMaster.json"
)

SECRET_NAMES = (
    "ANGEL_API_KEY",
    "ANGEL_CLIENT_ID",
    "ANGEL_PIN",
    "ANGEL_TOTP_SECRET",
)

st.markdown(
    """
<style>
.block-container {
    padding: 1rem .4rem .5rem;
    max-width: 100%;
}
div[data-testid="stVerticalBlock"] {
    gap: .4rem;
}
div[data-testid="stHorizontalBlock"] {
    flex-wrap: nowrap !important;
    gap: .35rem;
}
div[data-testid="stColumn"] {
    min-width: 0 !important;
}
.market-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    margin-bottom: 1rem;
}
.market-card {
    border: 1px solid #687184;
    border-radius: 8px;
    padding: 7px 2px;
    text-align: center;
    overflow-wrap: anywhere;
    min-height: 145px;
    box-sizing: border-box;
}
.market-name {
    font-size: 10px;
}
.market-open {
    font-size: 12px;
    margin-top: 3px;
}
.market-code {
    font-size: 23px;
    font-weight: 800;
    color: #22c55e;
}
.market-time {
    font-size: 9px;
    line-height: 1.4;
    margin-top: 6px;
    opacity: .7;
}
</style>
""",
    unsafe_allow_html=True,
)


def digit(value):
    total = sum(int(c) for c in str(abs(int(value))))
    while total > 9:
        total = sum(int(c) for c in str(total))
    return total


def positive(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number) or number <= 0:
        return None

    return number


def open_code(value):
    number = positive(value)
    if number is None:
        return "—"

    total = sum(int(c) for c in f"{number:.2f}" if c.isdigit())
    return f"{total:02d}{digit(total)}"


def saved_credentials(secrets):
    aliases = {
        "ANGEL_API_KEY": ("ANGEL_API_KEY", "API_KEY", "APIKEY"),
        "ANGEL_CLIENT_ID": ("ANGEL_CLIENT_ID", "CLIENT_ID", "CLIENT_CODE", "CLIENTCODE"),
        "ANGEL_PIN": ("ANGEL_PIN", "PIN", "MPIN", "PASSWORD"),
        "ANGEL_TOTP_SECRET": ("ANGEL_TOTP_SECRET", "TOTP_SECRET", "TOTP_KEY", "TOTP"),
    }
    def normalized(key):
        return "".join(c for c in str(key).upper() if c.isalnum())

    sources = [secrets]
    for section in ("angel", "angel_one", "angelone", "smartapi", "ANGEL", "ANGEL_ONE", "SMARTAPI"):
        nested = secrets.get(section)
        if hasattr(nested, "items"):
            sources.append(nested)
    values = {}
    for target, names in aliases.items():
        values[target] = ""
        for source in sources:
            entries = {normalized(k): v for k, v in source.items()
                       if not hasattr(v, "items")}
            for name in names:
                value = entries.get(normalized(name))
                if value is not None and str(value).strip():
                    values[target] = str(value).strip()
                    break
            if values[target]:
                break
    return values


def read_credentials():
    try:
        values = saved_credentials(st.secrets)
    except Exception:
        values = {}

    if not values.get("ANGEL_API_KEY") or not values.get("ANGEL_CLIENT_ID"):
        st.info(
            "एक बार सेटअप बाकी है। Manage app → Settings → Secrets में "
            "ANGEL_API_KEY और ANGEL_CLIENT_ID सेव करें। "
            "केवल OTP से Login के लिए ANGEL_PIN भी सेव करें; "
            "केवल PIN से Login के लिए ANGEL_TOTP_SECRET सेव करें।"
        )
        st.stop()

    has_totp = bool(values.get("ANGEL_TOTP_SECRET"))
    has_pin = bool(values.get("ANGEL_PIN"))
    if not has_totp and not has_pin:
        st.info(
            "एक बॉक्स वाला Login चालू करने के लिए Secrets में "
            "ANGEL_PIN या ANGEL_TOTP_SECRET सेव करें।"
        )
        st.stop()

    # Always ask for a fresh factor before opening a broker session.
    pin_mode = has_totp and not has_pin
    field_key = "angel_login_factor"
    with st.form("angel_login_form", clear_on_submit=True):
        factor = st.text_input(
            "Angel One PIN" if pin_mode else "Authenticator का 6 अंक वाला code",
            type="password",
            key=field_key,
            max_chars=16 if pin_mode else 6,
        )
        submitted = st.form_submit_button("Login", use_container_width=True)

    if not submitted:
        st.stop()
    factor = factor.strip()
    if pin_mode:
        if not factor or not factor.isascii() or not factor.isdigit():
            st.error("अपना Angel One PIN डालें।")
            st.stop()
        values["ANGEL_PIN"] = factor
    else:
        if len(factor) != 6 or not factor.isascii() or not factor.isdigit():
            st.error("Authenticator का छह अंकों वाला नया code डालें।")
            st.stop()
        values["ANGEL_OTP"] = factor
    return values


def connect():
    today = datetime.now(IST).date().isoformat()

    if st.session_state.get("angel_login_day") != today:
        st.session_state.pop("angel_client", None)

    if "angel_client" in st.session_state:
        return st.session_state["angel_client"]

    values = read_credentials()

    try:
        client = SmartConnect(
            api_key=values["ANGEL_API_KEY"],
            timeout=12,
        )

        otp = values.get("ANGEL_OTP")
        if not otp:
            secret = values["ANGEL_TOTP_SECRET"].replace(" ", "")
            otp = pyotp.TOTP(secret).now()

        result = client.generateSession(
            values["ANGEL_CLIENT_ID"],
            values["ANGEL_PIN"],
            otp,
        )

        if not isinstance(result, dict) or not result.get("status"):
            raise RuntimeError("Login rejected")

    except Exception:
        st.error(
            "Login नहीं हुआ। PIN या नया authenticator code जाँचें। "
            "समस्या बनी रहे तो Secrets में सेव जानकारी जाँचें।"
        )
        st.stop()

    st.session_state["angel_client"] = client
    st.session_state["angel_login_day"] = today
    st.rerun()
    return client


@st.cache_data(ttl=3600, show_spinner=False)
def instrument_master(day):
    response = requests.get(MASTER_URL, timeout=30)
    response.raise_for_status()
    frame = pd.DataFrame(response.json())

    required = {
        "token",
        "symbol",
        "name",
        "exch_seg",
        "instrumenttype",
        "expiry",
        "strike",
    }

    if not required.issubset(frame.columns):
        raise ValueError("Instrument list incomplete")

    text_columns = (
        "token",
        "symbol",
        "name",
        "exch_seg",
        "instrumenttype",
    )

    for column in text_columns:
        frame[column] = (
            frame[column].fillna("").astype(str).str.strip()
        )

    frame["expiry_date"] = pd.to_datetime(
        frame["expiry"].astype(str).str.upper(),
        format="%d%b%Y",
        errors="coerce",
    )

    frame["strike_price"] = (
        pd.to_numeric(frame["strike"], errors="coerce") / 100
    )

    return frame


def find_spot(frame, exchange, aliases):
    exchange_match = frame["exch_seg"].eq(exchange)
    name_match = frame["name"].str.upper().isin(aliases)
    symbol_match = frame["symbol"].str.upper().isin(aliases)

    mask = exchange_match & (name_match | symbol_match)
    matches = frame.loc[mask]

    if matches.empty:
        return None

    return matches.iloc[0]


def find_future(frame, name, exchange, today):
    name_match = frame["name"].str.upper().eq(name)
    exchange_match = frame["exch_seg"].eq(exchange)
    type_match = frame["instrumenttype"].eq("FUTIDX")
    expiry_match = frame["expiry_date"].ge(pd.Timestamp(today))

    mask = name_match & exchange_match & type_match & expiry_match
    matches = frame.loc[mask].sort_values("expiry_date")

    if matches.empty:
        return None

    return matches.iloc[0]


def quotes(client, instruments):
    exchange_tokens = {}

    for item in instruments:
        if item is None:
            continue

        exchange = str(item["exch_seg"])
        token = str(item["token"])

        exchange_tokens.setdefault(exchange, [])

        if token not in exchange_tokens[exchange]:
            exchange_tokens[exchange].append(token)

    if not exchange_tokens:
        return {}

    last_request = st.session_state.get("last_quote", 0.0)
    remaining = 1.1 - (time.monotonic() - last_request)

    if remaining > 0:
        time.sleep(remaining)

    st.session_state["last_quote"] = time.monotonic()

    try:
        result = client.getMarketData("FULL", exchange_tokens)

        if not isinstance(result, dict) or not result.get("status"):
            raise RuntimeError("Quotes rejected")

        data = result.get("data") or {}
        fetched = data.get("fetched") or []

        return {
            (
                str(item.get("exchange")),
                str(item.get("symbolToken")),
            ): item
            for item in fetched
        }

    except Exception:
        raise RuntimeError(
            "Angel One से भाव नहीं मिले। Refresh करें; "
            "समस्या बनी रहे तो दोबारा Login करें।"
        ) from None


def get_quote(data, instrument):
    if instrument is None:
        return {}

    key = (
        str(instrument["exch_seg"]),
        str(instrument["token"]),
    )
    return data.get(key, {})


def nearby_strikes(available, selector, spot):
    matching = sorted(
        strike for strike in available
        if digit(strike) == selector
    )

    if not matching:
        return []

    index = min(
        range(len(matching)),
        key=lambda i: (abs(matching[i] - spot), matching[i]),
    )

    return matching[max(0, index - 1):index + 2]


def match_text(price, targets):
    if price is None:
        return "भाव नहीं मिला"

    matches = []

    for index, target in enumerate(targets, start=1):
        if target > 0 and target * 0.9 <= price <= target * 1.1:
            matches.append(f"P{index}: {target:.2f}")

    return " | ".join(matches) if matches else "—"


def highlight(row):
    matched = row["Match ±10%"] not in ("—", "भाव नहीं मिला")
    style = (
        "background-color: #14532d; color: white;"
        if matched else ""
    )
    return [style] * len(row)


st.markdown("#### 📊 Angel Digit Scanner")

if st.button("दोबारा Login"):
    st.session_state.pop("angel_client", None)
    st.session_state.pop("angel_login_day", None)
    st.rerun()

client = connect()


@st.fragment(run_every="10s")
def dashboard():
    today = datetime.now(IST).date()

    if st.session_state.get("angel_login_day") != today.isoformat():
        st.rerun()

    try:
        master = instrument_master(today.isoformat())
    except Exception:
        st.error(
            "Angel One की instrument list नहीं मिली। "
            "कुछ देर बाद Refresh करें।"
        )
        return

    nifty = find_spot(
        master,
        "NSE",
        ["NIFTY", "NIFTY 50", "NIFTY50"],
    )
    sensex = find_spot(
        master,
        "BSE",
        ["SENSEX", "BSE SENSEX"],
    )
    nifty_future = find_future(master, "NIFTY", "NFO", today)
    sensex_future = find_future(master, "SENSEX", "BFO", today)

    markets = [
        ("NIFTY", nifty),
        ("NIFTY FUT", nifty_future),
        ("SENSEX", sensex),
        ("SENSEX FUT", sensex_future),
    ]

    try:
        market_quotes = quotes(
            client,
            [item for _, item in markets if item is not None],
        )
    except RuntimeError as error:
        st.error(str(error))
        return

    cards = []
    missing_markets = []

    for label, item in markets:
        if item is None:
            missing_markets.append(label)

        quote = get_quote(market_quotes, item)
        opening = positive(quote.get("open"))
        opening_text = (
            f"{opening:,.2f}" if opening is not None else "—"
        )
        feed_time = str(quote.get("exchFeedTime") or "समय नहीं मिला")

        cards.append(
            '<div class="market-card">'
            f'<div class="market-name">{escape(label)}</div>'
            f'<div class="market-open">{opening_text}</div>'
            f'<div class="market-code">{open_code(opening)}</div>'
            f'<div class="market-time">{escape(feed_time)}</div>'
            "</div>"
        )

    st.markdown(
        '<div class="market-grid">' + "".join(cards) + "</div>",
        unsafe_allow_html=True,
    )

    if missing_markets:
        st.caption(
            "Instrument list में नहीं मिले: "
            + ", ".join(missing_markets)
        )

    st.caption(
        "OPEN और quote का समय broker से हैं। "
        "बाज़ार बंद होने पर पिछला उपलब्ध session दिख सकता है।"
    )

    columns = st.columns(2)

    first = columns[0].number_input(
        "Strike digit 1",
        min_value=1,
        max_value=9,
        value=6,
        step=1,
        key="selector_one",
    )

    second = columns[1].number_input(
        "Strike digit 2",
        min_value=1,
        max_value=9,
        value=9,
        step=1,
        key="selector_two",
    )

    columns = st.columns(3)
    targets = []

    for index in range(3):
        target = columns[index].number_input(
            f"भाव {index + 1}",
            min_value=0.0,
            value=0.0,
            step=0.05,
            format="%.2f",
            key=f"target_{index}",
        )
        targets.append(target)

    spot = positive(get_quote(market_quotes, nifty).get("ltp"))

    if spot is None:
        st.warning(
            "Nifty का मौजूदा भाव नहीं मिला; strike scan रुका है।"
        )
        return

    mask = (
        master["name"].str.upper().eq("NIFTY")
        & master["exch_seg"].eq("NFO")
        & master["instrumenttype"].eq("OPTIDX")
        & master["expiry_date"].ge(pd.Timestamp(today))
        & master["symbol"].str.endswith(("CE", "PE"))
        & master["strike_price"].gt(0)
    )

    options = master.loc[mask].copy()

    if options.empty:
        st.warning("Nifty option contracts नहीं मिले।")
        return

    expiries = sorted(
        options["expiry_date"].dropna().unique().tolist()
    )

    expiry = st.selectbox(
        "NIFTY expiry",
        options=expiries,
        format_func=lambda value: pd.Timestamp(value).strftime(
            "%d-%m-%Y"
        ),
        key=f"expiry_{today.isoformat()}",
    )

    options = options.loc[
        options["expiry_date"].eq(pd.Timestamp(expiry))
    ].copy()

    options["side"] = options["symbol"].str[-2:]

    sides = options.groupby("strike_price")["side"].nunique()
    available = sides.loc[sides.eq(2)].index.tolist()

    contracts = []
    labels = []

    for group, selector in enumerate((first, second), start=1):
        selected = nearby_strikes(available, selector, spot)

        if len(selected) < 3:
            st.caption(
                f"Box {group}: digit {selector} के तीन पड़ोसी "
                "strikes इस expiry में पूरे उपलब्ध नहीं हैं।"
            )

        for strike in selected:
            for side in ("CE", "PE"):
                contract_mask = (
                    options["strike_price"].eq(strike)
                    & options["side"].eq(side)
                )

                item = options.loc[contract_mask].iloc[0]
                contracts.append(item)
                labels.append(
                    (group, selector, int(strike), side)
                )

    if not contracts:
        st.info("इन digits के contracts नहीं मिले।")
        return

    try:
        option_quotes = quotes(client, contracts)
    except RuntimeError as error:
        st.error(str(error))
        return

    rows = []

    for item, label in zip(contracts, labels):
        group, selector, strike, side = label
        quote = get_quote(option_quotes, item)
        price = positive(quote.get("ltp"))

        rows.append(
            {
                "Box": group,
                "Digit": selector,
                "Strike": strike,
                "Type": "CALL" if side == "CE" else "PUT",
                "भाव": price,
                "Match ±10%": match_text(price, targets),
                "Quote समय": str(
                    quote.get("exchFeedTime") or "—"
                ),
            }
        )

    frame = pd.DataFrame(rows)

    styled = frame.style.apply(
        highlight,
        axis=1,
    ).format(
        {"भाव": "{:.2f}"},
        na_rep="—",
    )

    st.dataframe(
        styled,
        hide_index=True,
        use_container_width=True,
        height=min(465, 38 + 35 * len(frame)),
    )

    st.button("अभी Refresh करें", key="refresh_quotes")

    st.caption(
        f"NIFTY {spot:,.2f} · "
        f"जाँच {datetime.now(IST).strftime('%H:%M:%S')} IST · "
        "हर 10 सेकंड refresh · भाव 0 = target बंद"
    )

    st.caption(
        "हरा रंग = मौजूदा premium का target से ±10% match। "
        "यह buy/sell signal या पुराने chart candles का scan नहीं है।"
    )


dashboard()
