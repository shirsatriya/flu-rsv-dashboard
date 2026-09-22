"""
Flu & RSV Hospital Admissions Tracker
Weekly confirmed hospital admissions by US state, from CDC's National
Healthcare Safety Network (NHSN) via the Delphi Epidata API.

Run with:  python -m streamlit run app.py
"""

import datetime as dt

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import streamlit as st
from epiweeks import Week

st.set_page_config(page_title="Flu & RSV Tracker", page_icon="🦠", layout="wide")

API_URL = "https://api.delphi.cmu.edu/epidata/covidcast/"
SIGNALS = {
    "Flu": "confirmed_admissions_flu_ew",
    "RSV": "confirmed_admissions_rsv_ew",
}
BACKUP_FILE = "flu_rsv_backup.csv"

# Approximate 2024 US Census Bureau population estimates
STATE_POP = {
    "al": 5157699, "ak": 740133, "az": 7582384, "ar": 3088354, "ca": 39431263,
    "co": 5957493, "ct": 3675069, "de": 1051917, "dc": 702250, "fl": 23372215,
    "ga": 11180878, "hi": 1446146, "id": 2001619, "il": 12710158, "in": 6924275,
    "ia": 3241488, "ks": 2970606, "ky": 4588372, "la": 4597740, "me": 1405012,
    "md": 6263220, "ma": 7136171, "mi": 10140459, "mn": 5793151, "ms": 2943045,
    "mo": 6245466, "mt": 1137233, "ne": 2005465, "nv": 3267467, "nh": 1409032,
    "nj": 9500851, "nm": 2130256, "ny": 19867248, "nc": 11046024, "nd": 796568,
    "oh": 11883304, "ok": 4095393, "or": 4272371, "pa": 13078751, "ri": 1112308,
    "sc": 5478831, "sd": 924669, "tn": 7227750, "tx": 31290831, "ut": 3503613,
    "vt": 648493, "va": 8811195, "wa": 7958180, "wv": 1769979, "wi": 5960975,
    "wy": 587618, "pr": 3203295,
}

STATE_NAMES = {
    "al": "Alabama", "ak": "Alaska", "az": "Arizona", "ar": "Arkansas",
    "ca": "California", "co": "Colorado", "ct": "Connecticut", "de": "Delaware",
    "dc": "District of Columbia", "fl": "Florida", "ga": "Georgia", "hi": "Hawaii",
    "id": "Idaho", "il": "Illinois", "in": "Indiana", "ia": "Iowa", "ks": "Kansas",
    "ky": "Kentucky", "la": "Louisiana", "me": "Maine", "md": "Maryland",
    "ma": "Massachusetts", "mi": "Michigan", "mn": "Minnesota", "ms": "Mississippi",
    "mo": "Missouri", "mt": "Montana", "ne": "Nebraska", "nv": "Nevada",
    "nh": "New Hampshire", "nj": "New Jersey", "nm": "New Mexico", "ny": "New York",
    "nc": "North Carolina", "nd": "North Dakota", "oh": "Ohio", "ok": "Oklahoma",
    "or": "Oregon", "pa": "Pennsylvania", "ri": "Rhode Island",
    "sc": "South Carolina", "sd": "South Dakota", "tn": "Tennessee", "tx": "Texas",
    "ut": "Utah", "vt": "Vermont", "va": "Virginia", "wa": "Washington",
    "wv": "West Virginia", "wi": "Wisconsin", "wy": "Wyoming", "pr": "Puerto Rico",
}


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def fetch_signal(signal, disease):
    """Download one NHSN signal for every state, from fall 2024 onward."""
    end_year = dt.date.today().year + 1
    params = {
        "data_source": "nhsn",
        "signals": signal,
        "geo_type": "state",
        "geo_values": "*",
        "time_type": "week",
        "time_values": f"202440-{end_year}52",
    }
    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("result") != 1:
        raise RuntimeError(payload.get("message", "Unknown API error"))
    df = pd.DataFrame(payload["epidata"])[["geo_value", "time_value", "value"]]
    df["disease"] = disease
    return df


@st.cache_data(ttl=3600, show_spinner="Fetching the latest CDC data...")
def load_data():
    """Fetch live data (falling back to the saved CSV) and add derived columns."""
    source = "live"
    try:
        raw = pd.concat(
            [fetch_signal(sig, name) for name, sig in SIGNALS.items()],
            ignore_index=True,
        )
    except Exception:
        raw = pd.read_csv(BACKUP_FILE)[["geo_value", "time_value", "value", "disease"]]
        source = "backup"

    raw = raw[raw["geo_value"].isin(STATE_POP)].copy()

    # Convert CDC epiweeks (e.g. 202606) to the Saturday each week ends on
    raw["date"] = pd.to_datetime(
        raw["time_value"].apply(lambda w: Week(int(w) // 100, int(w) % 100).enddate())
    )

    raw["population"] = raw["geo_value"].map(STATE_POP)
    raw["per_100k"] = raw["value"] / raw["population"] * 100000
    raw["state_name"] = raw["geo_value"].map(STATE_NAMES)

    # Respiratory seasons run from August through July, e.g. "2025–26"
    start_year = raw["date"].dt.year.where(raw["date"].dt.month >= 8,
                                           raw["date"].dt.year - 1)
    raw["season"] = start_year.astype(str) + "–" + (start_year + 1).astype(str).str[-2:]
    season_start = pd.to_datetime(start_year.astype(str) + "-08-01")
    raw["season_week"] = (raw["date"] - season_start).dt.days // 7 + 1

    return raw, source


try:
    data, source = load_data()
except Exception:
    st.error(
        "Couldn't reach the Delphi Epidata API, and no backup file was found. "
        f"Check your internet connection, or put {BACKUP_FILE} in the same folder as app.py."
    )
    st.stop()


# ---------------------------------------------------------------------------
# Header and controls
# ---------------------------------------------------------------------------

st.title("🦠 Flu & RSV hospital admissions tracker")
st.caption(
    "Weekly confirmed hospital admissions for every US state, from CDC's National "
    "Healthcare Safety Network. New data arrives each week and loads automatically."
)
if source == "backup":
    st.warning("Live data is unavailable right now, so this page is showing the saved backup.")

with st.sidebar:
    st.header("Controls")
    disease = st.radio("Disease", ["Flu", "RSV"])
    measure = st.radio("Measure", ["Per 100k residents", "Total admissions"])
    state_options = sorted(STATE_NAMES.values())
    state_name = st.selectbox("State for trend charts", state_options,
                              index=state_options.index("California"))

col = "per_100k" if measure == "Per 100k residents" else "value"
unit_label = "Admissions per 100k" if col == "per_100k" else "Admissions"

d = data[data["disease"] == disease]
dates = sorted(pd.Timestamp(x) for x in d.dropna(subset=["value"])["date"].unique())
latest, prev = dates[-1], dates[-2]


# ---------------------------------------------------------------------------
# Headline numbers
# ---------------------------------------------------------------------------

national = d.groupby("date")["value"].sum()
this_week, last_week = national[latest], national[prev]
change = (this_week - last_week) / last_week * 100 if last_week else 0.0

current = d[d["date"] == latest].set_index("geo_value")
previous = d[d["date"] == prev].set_index("geo_value")
trend = pd.DataFrame({
    "State": current["state_name"],
    "This week": current["value"],
    "Last week": previous["value"],
}).dropna()
trend["Change (%)"] = (
    (trend["This week"] - trend["Last week"])
    / trend["Last week"].replace(0, np.nan) * 100
)
eligible = trend[trend["Last week"] >= 5]
rising = eligible[eligible["Change (%)"] > 10]

current_season = d.loc[d["date"] == latest, "season"].iloc[0]
season_dates = d.loc[d["season"] == current_season, "date"].unique()
season_totals = national[national.index.isin(season_dates)]
peak_date, peak_value = season_totals.idxmax(), season_totals.max()

c1, c2, c3 = st.columns(3)
c1.metric(
    f"US {disease} admissions, week ending {latest:%b %d, %Y}",
    f"{this_week:,.0f}",
    f"{change:+.1f}% vs prior week",
    delta_color="inverse",
)
c2.metric("States rising more than 10%", len(rising))
c3.metric(
    f"{current_season} season peak so far (week ending {peak_date:%b %d})",
    f"{peak_value:,.0f}",
)
st.caption("The latest week is often revised upward as late hospital reports arrive.")


# ---------------------------------------------------------------------------
# Map
# ---------------------------------------------------------------------------

st.subheader(f"{disease} admissions by state")
map_date = st.select_slider(
    "Week ending",
    options=dates,
    value=latest,
    format_func=lambda x: x.strftime("%b %d, %Y"),
)
week = d[d["date"] == map_date].copy()
week["state"] = week["geo_value"].str.upper()

fig_map = px.choropleth(
    week,
    locations="state",
    locationmode="USA-states",
    color=col,
    scope="usa",
    color_continuous_scale="Reds",
    hover_name="state_name",
    hover_data={"state": False, "value": ":,.0f", "per_100k": ":.1f"},
    labels={"value": "Admissions", "per_100k": "Per 100k"},
)
fig_map.update_layout(margin=dict(l=0, r=0, t=10, b=0),
                      coloraxis_colorbar_title=unit_label,
                      paper_bgcolor="rgba(0,0,0,0)")
fig_map.update_geos(bgcolor="rgba(0,0,0,0)", showlakes=False)
st.plotly_chart(fig_map)


# ---------------------------------------------------------------------------
# State trends
# ---------------------------------------------------------------------------

state_data = data[data["state_name"] == state_name]
left, right = st.columns(2)

with left:
    st.subheader(f"Flu vs RSV in {state_name}")
    fig_compare = px.line(
        state_data, x="date", y=col, color="disease",
        labels={col: unit_label, "date": "", "disease": "Disease"},
        color_discrete_map={"Flu": "#E4572E", "RSV": "#4C9BE8"},
    )
    st.plotly_chart(fig_compare)

with right:
    st.subheader(f"{disease} season by season in {state_name}")
    # Past seasons in muted colors, the current season in bright red on top
    seasons = sorted(state_data["season"].unique())
    muted = ["#8C8C8C", "#4C9BE8", "#9B7ED9", "#3CB4A0"]
    season_colors = {s: muted[i % len(muted)] for i, s in enumerate(seasons)}
    season_colors[current_season] = "#E4572E"
    fig_seasons = px.line(
        state_data[state_data["disease"] == disease],
        x="season_week", y=col, color="season",
        labels={col: unit_label, "season_week": "Weeks since August 1",
                "season": "Season"},
        color_discrete_map=season_colors,
    )
    for trace in fig_seasons.data:
        trace.line.width = 4 if trace.name == current_season else 2
    st.plotly_chart(fig_seasons)


# ---------------------------------------------------------------------------
# Rising states
# ---------------------------------------------------------------------------

st.subheader("Fastest-rising states this week")
st.caption("Only states with at least 5 admissions last week, so tiny numbers don't dominate.")
top = eligible.sort_values("Change (%)", ascending=False).head(10)
if top.empty:
    st.info("No state had enough admissions last week to compare.")
else:
    st.dataframe(
        top.style.format({
            "This week": "{:,.0f}",
            "Last week": "{:,.0f}",
            "Change (%)": "{:+.1f}%",
        }),
        hide_index=True,
    )

st.divider()
st.caption(
    "Data: CDC National Healthcare Safety Network (NHSN), accessed through the "
    "Delphi Epidata API at Carnegie Mellon University. Population: US Census Bureau "
    "2024 estimates. Admissions before November 2024 were reported voluntarily, and "
    "RSV counts from that period are much less complete."
)
