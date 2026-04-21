import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

#  Page config
st.set_page_config(
    page_title="Nitrate in Groundwater – Europe",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

h1, h2, h3 {
    font-family: 'DM Serif Display', serif;
}

.main { background-color: #f0f4f8; }

.metric-card {
    background: white;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.06);
    border-left: 4px solid #1a6b9a;
}

.metric-card.danger { border-left-color: #d94f3d; }
.metric-card.warning { border-left-color: #e8a838; }
.metric-card.good { border-left-color: #2e9e5b; }

.metric-label {
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #6b7280;
    margin-bottom: 4px;
}

.metric-value {
    font-size: 28px;
    font-weight: 600;
    color: #111827;
    line-height: 1.1;
}

.metric-sub {
    font-size: 13px;
    color: #9ca3af;
    margin-top: 4px;
}

.threshold-banner {
    background: linear-gradient(135deg, #fff7ed, #fef3c7);
    border: 1px solid #f59e0b;
    border-radius: 10px;
    padding: 12px 18px;
    margin-bottom: 20px;
    font-size: 14px;
    color: #92400e;
}

section[data-testid="stSidebar"] {
    background-color: #0f2942;
}
section[data-testid="stSidebar"] * {
    color: #e2eaf4 !important;
}
section[data-testid="stSidebar"] .stSelectbox label,
section[data-testid="stSidebar"] .stMultiSelect label,
section[data-testid="stSidebar"] .stSlider label {
    color: #94b8d4 !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
}
</style>
""", unsafe_allow_html=True)

# Load & clean data from Excel
@st.cache_data
def load_data():
    # Read raw Excel sheet
    raw = pd.read_excel("sdg_06_40_page_spreadsheet.xlsx", sheet_name="Data", header=None)

    # Row 8 has TIME + years, rows 9 onwards are countries
    years = [int(x) for x in raw.iloc[8, 1:].dropna().tolist()]

    records = []
    for _, row in raw.iloc[9:46, :].iterrows():
        country = row[0]
        if pd.isna(country) or country in ["Special value", "GEO (Labels)"]:
            continue
        for i, year in enumerate(years):
            val = row[i + 1]
            nitrate = None if (val == ":" or pd.isna(val)) else float(val)
            records.append({"country": country, "year": year, "nitrate_mg_per_l": nitrate})

    df = pd.DataFrame(records)

    # Separate EU aggregates from individual countries
    eu_agg = df[df["country"] == "European Union (aggregate changing according to the context)"].copy()
    eu_agg["country"] = "EU Average"
    df = df[~df["country"].str.contains("European Union", na=False)]
    df = pd.concat([df, eu_agg], ignore_index=True)

    df = df[df["nitrate_mg_per_l"].notna()]
    df["year"] = df["year"].astype(int)
    df["above_threshold"] = df["nitrate_mg_per_l"] > 50
    return df

df = load_data()
EU_THRESHOLD = 50  # mg/L — EU Nitrates Directive drinking water limit

all_countries = sorted([c for c in df["country"].unique() if c != "EU Average"])
all_years = sorted(df["year"].unique())

# Sidebar 
with st.sidebar:
    st.markdown("##  Nitrate Dashboard")
    st.markdown("---")

    st.markdown("#### Year Range")
    year_range = st.slider(
        "Select years",
        min_value=int(min(all_years)),
        max_value=int(max(all_years)),
        value=(2007, 2023),
        label_visibility="collapsed",
    )

    st.markdown("#### Countries")
    selected_countries = st.multiselect(
        "Select countries to analyse",
        options=all_countries,
        default=["Spain", "Germany", "France", "Italy", "Belgium", "Poland","Bulgaria"],
        label_visibility="collapsed",
    )

    st.markdown("#### Highlight Threshold")
    show_threshold = st.toggle("Show EU 50 mg/L limit", value=True)

    st.markdown("---")
    st.markdown(
        "<p style='font-size:11px; color:#5a7a96;'>Data: EEA Waterbase / Eurostat SDG 06.40<br>Updated: January 2026</p>",
        unsafe_allow_html=True,
    )

#Filter data 
df_filtered = df[
    (df["year"] >= year_range[0])
    & (df["year"] <= year_range[1])
    & (df["country"].isin(selected_countries + ["EU Average"]))
]

df_sel = df_filtered[df_filtered["country"] != "EU Average"]
df_eu = df_filtered[df_filtered["country"] == "EU Average"]

# latest year data for all countries
latest_year = df[df["country"] != "EU Average"]["year"].max()
df_latest = df[(df["year"] == latest_year) & (df["country"] != "EU Average")]

# Header
st.markdown("# Nitrate in European Groundwater")
st.markdown(
    "Monitoring nitrate (NO₃) concentrations across Europe. "
    "The **EU drinking water threshold is 50 mg/L** — exceedance poses health risks and signals agricultural pollution pressure."
)

if show_threshold:
    st.markdown(
        f"""<div class="threshold-banner">
        ⚠️ <strong>EU Nitrates Directive:</strong> Groundwater exceeding <strong>50 mg NO₃/L</strong>
        is classified as polluted and unsafe for drinking without treatment.
        </div>""",
        unsafe_allow_html=True,
    )

# KPI Cards
col1, col2, col3, col4 = st.columns(4)

if not df_sel.empty:
    avg_latest = df_sel[df_sel["year"] == df_sel["year"].max()]["nitrate_mg_per_l"].mean()
    max_country = df_latest.loc[df_latest["nitrate_mg_per_l"].idxmax()]
    min_country = df_latest.loc[df_latest["nitrate_mg_per_l"].idxmin()]
    countries_over = df_latest[df_latest["nitrate_mg_per_l"] > EU_THRESHOLD]["country"].count()

    card_class = "danger" if avg_latest > EU_THRESHOLD else ("warning" if avg_latest > 30 else "good")
    with col1:
        st.markdown(f"""<div class="metric-card {card_class}">
            <div class="metric-label">Avg (Selected, {df_sel['year'].max()})</div>
            <div class="metric-value">{avg_latest:.1f} mg/L</div>
            <div class="metric-sub">EU limit: 50 mg/L</div>
        </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""<div class="metric-card danger">
            <div class="metric-label">Highest ({latest_year})</div>
            <div class="metric-value">{max_country['nitrate_mg_per_l']:.1f} mg/L</div>
            <div class="metric-sub">{max_country['country']}</div>
        </div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""<div class="metric-card good">
            <div class="metric-label">Lowest ({latest_year})</div>
            <div class="metric-value">{min_country['nitrate_mg_per_l']:.1f} mg/L</div>
            <div class="metric-sub">{min_country['country']}</div>
        </div>""", unsafe_allow_html=True)

    with col4:
        st.markdown(f"""<div class="metric-card {'danger' if countries_over > 0 else 'good'}">
            <div class="metric-label">Above 50 mg/L ({latest_year})</div>
            <div class="metric-value">{countries_over} countries</div>
            <div class="metric-sub">out of {len(df_latest)} with data</div>
        </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Row 1: Line chart + Bar chart 
col_left, col_right = st.columns([3, 2])

with col_left:
    st.markdown("### Nitrate Trends Over Time")
    if df_sel.empty or not selected_countries:
        st.info("Select at least one country from the sidebar.")
    else:
        fig_line = go.Figure()

        colors = px.colors.qualitative.Bold
        for i, country in enumerate(selected_countries):
            cdf = df_sel[df_sel["country"] == country].sort_values("year")
            if cdf.empty:
                continue
            fig_line.add_trace(go.Scatter(
                x=cdf["year"], y=cdf["nitrate_mg_per_l"],
                name=country, mode="lines+markers",
                line=dict(width=2.5, color=colors[i % len(colors)]),
                marker=dict(size=5),
                hovertemplate=f"<b>{country}</b><br>Year: %{{x}}<br>Nitrate: %{{y:.2f}} mg/L<extra></extra>",
            ))

        # EU Average
        if not df_eu.empty:
            eu_sorted = df_eu.sort_values("year")
            fig_line.add_trace(go.Scatter(
                x=eu_sorted["year"], y=eu_sorted["nitrate_mg_per_l"],
                name="EU Average", mode="lines",
                line=dict(width=2, dash="dot", color="#9ca3af"),
                hovertemplate="<b>EU Average</b><br>Year: %{x}<br>Nitrate: %{y:.2f} mg/L<extra></extra>",
            ))

        if show_threshold:
            fig_line.add_hline(y=EU_THRESHOLD, line_dash="dash", line_color="#d94f3d",
                               annotation_text="EU Limit (50 mg/L)", annotation_position="top left",
                               annotation_font_color="#d94f3d")

        fig_line.update_layout(
            paper_bgcolor="white", plot_bgcolor="white",
            margin=dict(t=20, b=80, l=50, r=20),
            legend=dict(orientation="h", yanchor="top", y=-0.18, xanchor="left", x=0, font=dict(color="#111827"), bgcolor="rgba(0,0,0,0)"),
            xaxis=dict(showgrid=False, title="Year", title_font=dict(color="#374151"), tickfont=dict(color="#374151"), linecolor="#d1d5db"),
            yaxis=dict(showgrid=True, gridcolor="#f3f4f6", title="mg NO₃/L", title_font=dict(color="#374151"), tickfont=dict(color="#374151")),
            height=400,
            font=dict(family="DM Sans", color="#111827"),
        )
        st.plotly_chart(fig_line, use_container_width=True)

with col_right:
    st.markdown(f"### Country Ranking ({latest_year})")
    df_bar = df_latest.sort_values("nitrate_mg_per_l", ascending=True).tail(20)
    bar_colors = ["#d94f3d" if v > EU_THRESHOLD else "#1a6b9a" for v in df_bar["nitrate_mg_per_l"]]

    fig_bar = go.Figure(go.Bar(
        x=df_bar["nitrate_mg_per_l"],
        y=df_bar["country"],
        orientation="h",
        marker_color=bar_colors,
        hovertemplate="<b>%{y}</b><br>%{x:.2f} mg/L<extra></extra>",
    ))

    if show_threshold:
        fig_bar.add_vline(x=EU_THRESHOLD, line_dash="dash", line_color="#d94f3d",
                          annotation_text="50 mg/L", annotation_position="top")

    fig_bar.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=20, b=40, l=10, r=20),
        xaxis=dict(showgrid=True, gridcolor="#f3f4f6", title="mg NO₃/L", title_font=dict(color="#374151"), tickfont=dict(color="#374151")),
        yaxis=dict(showgrid=False, tickfont=dict(color="#374151")),
        height=380,
        font=dict(family="DM Sans", color="#111827"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

#Row 2: Map + Change analysis
col_map, col_change = st.columns([3, 2])

with col_map:
    st.markdown(f"### Geographic Distribution ({latest_year})")

    # Country code mapping for choropleth
    country_iso = {
        "Austria": "AUT", "Belgium": "BEL", "Bulgaria": "BGR", "Croatia": "HRV",
        "Cyprus": "CYP", "Czechia": "CZE", "Denmark": "DNK", "Estonia": "EST",
        "Finland": "FIN", "France": "FRA", "Germany": "DEU", "Greece": "GRC",
        "Hungary": "HUN", "Iceland": "ISL", "Ireland": "IRL", "Italy": "ITA",
        "Latvia": "LVA", "Lithuania": "LTU", "Luxembourg": "LUX", "Malta": "MLT",
        "Netherlands": "NLD", "Norway": "NOR", "Poland": "POL", "Portugal": "PRT",
        "Romania": "ROU", "Serbia": "SRB", "Slovakia": "SVK", "Slovenia": "SVN",
        "Spain": "ESP", "Sweden": "SWE", "Switzerland": "CHE", "United Kingdom": "GBR",
    }

    df_map = df_latest.copy()
    df_map["iso"] = df_map["country"].map(country_iso)
    df_map = df_map.dropna(subset=["iso"])

    fig_map = px.choropleth(
        df_map, locations="iso", color="nitrate_mg_per_l",
        hover_name="country",
        hover_data={"nitrate_mg_per_l": ":.2f", "iso": False},
        color_continuous_scale=["#d4f1c4", "#f7e78e", "#f0a830", "#d94f3d"],
        range_color=[0, 60],
        labels={"nitrate_mg_per_l": "mg NO₃/L"},
        scope="europe",
    )
    fig_map.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        paper_bgcolor="white",
        coloraxis_colorbar=dict(title="mg/L", thickness=14, len=0.7, tickfont=dict(color="#374151"), title_font=dict(color="#374151")),
        height=370,
        font=dict(family="DM Sans", color="#111827"),
        geo=dict(bgcolor="white", lakecolor="#cce5f5", landcolor="#f9fafb",
                 showlakes=True, showocean=True, oceancolor="#ddeeff"),
    )
    st.plotly_chart(fig_map, use_container_width=True)

with col_change:
    st.markdown("### Change from 2007 to 2023")
    df_2007 = df[(df["year"] == 2007) & (df["country"] != "EU Average")]
    df_2023 = df[(df["year"] == 2023) & (df["country"] != "EU Average")]
    df_change = df_2007.merge(df_2023, on="country", suffixes=("_2007", "_2023"))
    df_change["change"] = df_change["nitrate_mg_per_l_2023"] - df_change["nitrate_mg_per_l_2007"]
    df_change = df_change.sort_values("change")

    change_colors = ["#2e9e5b" if v < 0 else "#d94f3d" for v in df_change["change"]]
    fig_change = go.Figure(go.Bar(
        x=df_change["change"],
        y=df_change["country"],
        orientation="h",
        marker_color=change_colors,
        hovertemplate="<b>%{y}</b><br>Change: %{x:+.2f} mg/L<extra></extra>",
    ))
    fig_change.add_vline(x=0, line_color="#374151", line_width=1)
    fig_change.update_layout(
        paper_bgcolor="white", plot_bgcolor="white",
        margin=dict(t=20, b=40, l=10, r=20),
        xaxis=dict(showgrid=True, gridcolor="#f3f4f6", title="Change in mg NO₃/L", title_font=dict(color="#374151"), tickfont=dict(color="#374151")),
        yaxis=dict(showgrid=False, tickfont=dict(color="#374151", size=10)),
        height=370,
        font=dict(family="DM Sans", color="#111827"),
    )
    st.plotly_chart(fig_change, use_container_width=True)

#Row 3: Data table
with st.expander("📋 View Raw Data Table", expanded=False):
    df_pivot = df[df["country"] != "EU Average"].pivot_table(
        index="country", columns="year", values="nitrate_mg_per_l"
    ).reset_index()
    df_pivot.columns = [str(c) for c in df_pivot.columns]
    st.dataframe(df_pivot, use_container_width=True, height=400)
    st.download_button(
        "Download cleaned CSV",
        data=df.to_csv(index=False),
        file_name="nitrate_groundwater_clean.csv",
        mime="text/csv",
    )

#Footer
st.markdown("---")
st.markdown(
    "<p style='font-size:12px; color:#9ca3af;'>Data source: European Environment Agency (EEA) — "
    "Nitrate in Groundwater [sdg_06_40], updated January 2026. "
    "Unit: milligrams of nitrate per litre (mg NO₃/L). "
    "Threshold reference: EU Nitrates Directive (91/676/EEC).</p>",
    unsafe_allow_html=True,
)


