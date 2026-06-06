#!/usr/bin/env python3
"""
FTC Analytics Dashboard
-----------------------
Premium interactive Streamlit dashboard for exploring the FTC Open Analytics Dataset.
Features: Home, Team Explorer, Event Browser, OPR Leaderboard, Match Predictor.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ============================================================================
# Page config
# ============================================================================
st.set_page_config(
    page_title="FTC Analytics",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": "https://github.com/kaivalya-cyber/ftc-analytics-dataset",
        "Report a bug": "https://github.com/kaivalya-cyber/ftc-analytics-dataset/issues",
        "About": "FTC Open Analytics Dataset — 1,762 matches, 902 teams, 6 seasons.",
    },
)

# ============================================================================
# Custom CSS — premium FTC theme
# ============================================================================
st.markdown("""
<style>
    /* ── Google Font import ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Root variables ── */
    :root {
        --ftc-red: #E74C3C;
        --ftc-blue: #3498DB;
        --ftc-orange: #F39C12;
        --ftc-green: #27AE60;
        --ftc-purple: #8E44AD;
        --bg-dark: #0f0f13;
        --bg-card: #1a1a24;
        --bg-card-hover: #22222f;
        --text-primary: #f0f0f5;
        --text-secondary: #a0a0b5;
        --border-subtle: rgba(255,255,255,0.06);
        --border-glow-red: rgba(231,76,60,0.4);
        --border-glow-blue: rgba(52,152,219,0.4);
        --gradient-hero: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        --gradient-red: linear-gradient(135deg, #E74C3C, #C0392B);
        --gradient-blue: linear-gradient(135deg, #3498DB, #2980B9);
        --shadow-card: 0 4px 24px rgba(0,0,0,0.3);
        --shadow-glow-red: 0 0 30px rgba(231,76,60,0.15);
        --shadow-glow-blue: 0 0 30px rgba(52,152,219,0.15);
        --radius-lg: 16px;
        --radius-md: 10px;
        --radius-sm: 8px;
    }

    /* ── Global font ── */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* ── Hide Streamlit chrome ── */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* ── Main background ── */
    .stApp {
        background: var(--bg-dark);
    }

    /* ── Sidebar styling ── */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #12121c 0%, #0d0d17 100%);
        border-right: 1px solid var(--border-subtle);
    }
    section[data-testid="stSidebar"] .stRadio > div {
        gap: 0.35rem;
    }
    section[data-testid="stSidebar"] .stRadio label {
        padding: 0.7rem 1rem !important;
        border-radius: var(--radius-sm) !important;
        transition: all 0.2s ease;
        font-weight: 500;
        font-size: 0.95rem;
    }
    section[data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.05) !important;
    }
    section[data-testid="stSidebar"] .stRadio [role="radiogroup"] label[data-checked="true"] {
        background: linear-gradient(135deg, rgba(231,76,60,0.15), rgba(52,152,219,0.15)) !important;
        border-left: 3px solid var(--ftc-red) !important;
    }

    /* ── Hero gradient header ── */
    .hero-header {
        background: var(--gradient-hero);
        border-radius: var(--radius-lg);
        padding: 2.5rem 2rem;
        margin-bottom: 1.5rem;
        border: 1px solid var(--border-subtle);
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: "";
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(231,76,60,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-header::after {
        content: "";
        position: absolute;
        bottom: -40%;
        left: -10%;
        width: 350px;
        height: 350px;
        background: radial-gradient(circle, rgba(52,152,219,0.06) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-title {
        font-size: 2.4rem;
        font-weight: 800;
        background: linear-gradient(135deg, #E74C3C 0%, #F39C12 50%, #3498DB 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 0.3rem;
        position: relative;
        z-index: 1;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: var(--text-secondary);
        font-weight: 400;
        position: relative;
        z-index: 1;
    }

    /* ── Stat cards ── */
    .stat-card {
        background: var(--bg-card);
        border-radius: var(--radius-md);
        padding: 1.25rem 1.5rem;
        border: 1px solid var(--border-subtle);
        transition: all 0.25s ease;
        position: relative;
        overflow: hidden;
    }
    .stat-card:hover {
        border-color: rgba(255,255,255,0.12);
        transform: translateY(-2px);
        box-shadow: var(--shadow-card);
    }
    .stat-card-icon {
        font-size: 1.8rem;
        margin-bottom: 0.4rem;
    }
    .stat-card-value {
        font-size: 2rem;
        font-weight: 700;
        color: var(--text-primary);
        line-height: 1.1;
    }
    .stat-card-label {
        font-size: 0.82rem;
        color: var(--text-secondary);
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-top: 0.2rem;
    }
    .stat-card-accent {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
    }
    .accent-red { background: var(--gradient-red); }
    .accent-blue { background: var(--gradient-blue); }
    .accent-orange { background: linear-gradient(135deg, #F39C12, #E67E22); }
    .accent-green { background: linear-gradient(135deg, #27AE60, #1E8449); }

    /* ── Section cards ── */
    .section-card {
        background: var(--bg-card);
        border-radius: var(--radius-lg);
        padding: 1.5rem;
        border: 1px solid var(--border-subtle);
        margin-bottom: 1rem;
    }

    /* ── Prediction bar ── */
    .prediction-bar {
        height: 12px;
        border-radius: 6px;
        background: var(--bg-dark);
        overflow: hidden;
        margin: 0.5rem 0;
        border: 1px solid var(--border-subtle);
    }
    .prediction-fill-red {
        height: 100%;
        background: var(--gradient-red);
        border-radius: 6px;
        transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
        box-shadow: var(--shadow-glow-red);
    }
    .prediction-fill-blue {
        height: 100%;
        background: var(--gradient-blue);
        border-radius: 6px;
        transition: width 0.6s cubic-bezier(0.4,0,0.2,1);
        box-shadow: var(--shadow-glow-blue);
    }

    /* ── Chip badges ── */
    .chip {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.78rem;
        font-weight: 600;
        letter-spacing: 0.02em;
    }
    .chip-red {
        background: rgba(231,76,60,0.15);
        color: #E74C3C;
        border: 1px solid rgba(231,76,60,0.3);
    }
    .chip-blue {
        background: rgba(52,152,219,0.15);
        color: #3498DB;
        border: 1px solid rgba(52,152,219,0.3);
    }
    .chip-green {
        background: rgba(39,174,96,0.15);
        color: #27AE60;
        border: 1px solid rgba(39,174,96,0.3);
    }

    /* ── DataFrames ── */
    [data-testid="stDataFrame"] {
        border-radius: var(--radius-md) !important;
        overflow: hidden;
        border: 1px solid var(--border-subtle) !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        border-radius: var(--radius-sm) !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"] {
        background: var(--gradient-red) !important;
        border: none !important;
        box-shadow: 0 4px 15px rgba(231,76,60,0.3) !important;
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(231,76,60,0.4) !important;
    }

    /* ── Select boxes ── */
    .stSelectbox > div > div {
        border-radius: var(--radius-sm) !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600 !important;
        border-radius: var(--radius-sm) var(--radius-sm) 0 0 !important;
    }

    /* ── Metrics ── */
    [data-testid="stMetricValue"] {
        font-weight: 700 !important;
    }

    /* ── Markdown headings ── */
    h1, h2, h3 {
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }

    /* ── Divider ── */
    hr {
        border-color: var(--border-subtle) !important;
        margin: 1.5rem 0 !important;
    }

    /* ── Info/Success/Warning boxes ── */
    [data-testid="stAlert"] {
        border-radius: var(--radius-md) !important;
        border: none !important;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# Load data
# ============================================================================
DATA_DIR = Path(__file__).parent / "data" / "processed"
RESULTS_DIR = Path(__file__).parent / "results"


@st.cache_data
def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    teams = pd.read_csv(DATA_DIR / "teams.csv")
    team_events = pd.read_csv(DATA_DIR / "team_events.csv")
    
    # Load ELO data if available
    elo_df = None
    current_elo = None
    elo_path = DATA_DIR / "team_elo.csv"
    current_elo_path = DATA_DIR / "current_elo.csv"
    if elo_path.exists():
        elo_df = pd.read_csv(elo_path)
    if current_elo_path.exists():
        current_elo = pd.read_csv(current_elo_path)
    
    return matches, teams, team_events, elo_df, current_elo


matches, teams, team_events, elo_df, current_elo = load_data()

# ============================================================================
# Pre-computed values
# ============================================================================
season_labels = {
    "1819": "Rover Ruckus 🤖",
    "1920": "Skystone 🪨",
    "2021": "Ultimate Goal 🎯",
    "2122": "Freight Frenzy 📦",
    "2223": "Power Play ⚡",
    "2324": "Centerstage 🎭",
}

# Build OPR lookup: (team_number) -> average OPR across all events
opr_lookup = {}
opr_counts = {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    opr = row["opr"] if not pd.isna(row["opr"]) else 0
    if tn not in opr_lookup:
        opr_lookup[tn] = 0.0
        opr_counts[tn] = 0
    opr_lookup[tn] += opr
    opr_counts[tn] += 1
for tn in opr_lookup:
    opr_lookup[tn] = opr_lookup[tn] / opr_counts[tn]

# Build win rate lookup: (team_number) -> average win rate
wr_lookup = {}
wr_counts = {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    w, l, t = row["wins"], row["losses"], row["ties"]
    wr = w / (w + l + t) if (w + l + t) > 0 else 0.5
    if tn not in wr_lookup:
        wr_lookup[tn] = 0.0
        wr_counts[tn] = 0
    wr_lookup[tn] += wr
    wr_counts[tn] += 1
for tn in wr_lookup:
    wr_lookup[tn] = wr_lookup[tn] / wr_counts[tn]

# Pre-compute OPR diff std for sigmoid scaling
all_diffs = []
for _, row in matches.iterrows():
    r1_o = opr_lookup.get(row["red_team_1"], 0)
    r2_o = opr_lookup.get(row["red_team_2"], 0)
    b1_o = opr_lookup.get(row["blue_team_1"], 0)
    b2_o = opr_lookup.get(row["blue_team_2"], 0)
    all_diffs.append((r1_o + r2_o) - (b1_o + b2_o))
OPR_SCALE = max(np.std(all_diffs), 1.0)


def stat_card_html(icon, value, label, accent_class):
    """Render a premium stat card with custom HTML."""
    return f"""
    <div class="stat-card">
        <div class="stat-card-accent {accent_class}"></div>
        <div class="stat-card-icon">{icon}</div>
        <div class="stat-card-value">{value}</div>
        <div class="stat-card-label">{label}</div>
    </div>
    """


# ============================================================================
# Sidebar
# ============================================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 0.5rem 0 1.5rem 0;">
        <div style="font-size:2.8rem; margin-bottom:0.3rem;">🤖</div>
        <div style="font-size:1.2rem; font-weight:800; letter-spacing:-0.02em; 
                    background: linear-gradient(135deg, #E74C3C, #3498DB); 
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                    background-clip: text;">
            FTC ANALYTICS
        </div>
        <div style="font-size:0.75rem; color: #606080; font-weight:500; margin-top:0.15rem;">
            BY KAIVALYA SINGH
        </div>
    </div>
    """, unsafe_allow_html=True)

    page = st.radio(
        "NAVIGATE",
        ["🏠 Home", "🔍 Team Explorer", "📅 Event Browser", "🏆 OPR Leaderboard", "📈 ELO Ratings", "🎯 Match Predictor"],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.caption(
        f"📊 {len(matches):,} matches\n\n"
        f"🤖 {len(teams):,} teams\n\n"
        f"📅 {matches['event_key'].nunique()} events\n\n"
        f"🌎 {matches['region'].nunique()} regions"
    )
    st.markdown("---")
    st.markdown(
        "[📖 GitHub](https://github.com/kaivalya-cyber/ftc-analytics-dataset)  |  "
        "[📄 Paper](dataset_description.md)\n\n"
        "Built with ❤️ using Streamlit"
    )

# ============================================================================
# HOME
# ============================================================================
if page == "🏠 Home":
    # Hero header
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title">FTC Open Analytics</div>
        <div class="hero-subtitle">
            A clean, structured dataset of FIRST Tech Challenge match results spanning 6 seasons — 
            from Rover Ruckus to Centerstage — with computed OPR metrics and machine learning benchmarks.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Top-level stat cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(stat_card_html("📊", f"{len(matches):,}", "Total Matches", "accent-red"), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_card_html("🤖", f"{len(teams):,}", "Unique Teams", "accent-blue"), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_card_html("📅", str(matches["event_key"].nunique()), "Events", "accent-orange"), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_card_html("🌎", str(matches["region"].nunique()), "Regions", "accent-green"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Season breakdown
    st.markdown("### 📊 Season Overview")

    season_tab = st.selectbox(
        "Select Season",
        list(season_labels.keys()),
        format_func=lambda x: f"{x} — {season_labels[x]}",
        label_visibility="collapsed",
    )
    sm = matches[matches["season"] == season_tab]
    quals = sm[~sm["is_playoff"]]
    playoffs = sm[sm["is_playoff"]]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Matches", len(sm))
    c2.metric("Qualification", len(quals))
    c3.metric("Playoff", len(playoffs))
    c4.metric("Events", sm["event_key"].nunique())

    scores = pd.concat([sm["red_score"], sm["blue_score"]])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean Score", f"{scores.mean():.1f}")
    c2.metric("Median Score", f"{scores.median():.1f}")
    c3.metric("Max Score", f"{scores.max():.0f}")
    c4.metric("Std Dev", f"{scores.std():.1f}")

    # Charts
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**📈 Score Distribution**")
        score_vals = pd.concat([sm["red_score"], sm["blue_score"]])
        hist = pd.cut(score_vals, bins=25).value_counts().sort_index()
        hist_df = pd.DataFrame({"Score Range": [str(i) for i in hist.index], "Count": hist.values}).set_index("Score Range")
        st.bar_chart(hist_df, use_container_width=True)
    with col_b:
        st.markdown("**🏁 Win Distribution**")
        winner_counts = sm["winner"].value_counts()
        st.bar_chart(winner_counts, use_container_width=True)

    # Quick stats footer
    st.markdown("---")
    st.markdown("""
    <div style="display:flex; gap:1rem; flex-wrap:wrap; justify-content:center;">
        <span class="chip chip-green">✅ 1,762 matches</span>
        <span class="chip chip-blue">✅ 902 teams</span>
        <span class="chip chip-red">✅ 53 events</span>
        <span class="chip chip-orange" style="background:rgba(243,156,18,0.15); color:#F39C12; border:1px solid rgba(243,156,18,0.3);">✅ 10 regions</span>
        <span class="chip chip-blue">✅ 88.7% accuracy</span>
    </div>
    """, unsafe_allow_html=True)

# ============================================================================
# TEAM EXPLORER
# ============================================================================
elif page == "🔍 Team Explorer":
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">🔍 Team Explorer</div>
        <div class="hero-subtitle">Deep-dive into any team's performance history, OPR trends, and event results.</div>
    </div>
    """, unsafe_allow_html=True)

    team_list = sorted(teams["team_number"].unique())

    col_s, col_i = st.columns([2, 1])
    with col_s:
        team_number = st.selectbox("Search for a team by number", team_list, index=0, label_visibility="collapsed")

    if team_number:
        team_info = teams[teams["team_number"] == team_number].iloc[0]

        st.markdown(f"""
        <div class="section-card" style="margin-top:1rem;">
            <div style="display:flex; align-items:center; gap:1rem;">
                <div style="font-size:3rem;">🤖</div>
                <div>
                    <div style="font-size:1.6rem; font-weight:700;">Team {team_number}</div>
                    <div style="color:var(--text-secondary); font-size:1rem;">{team_info['team_name'] if pd.notna(team_info['team_name']) else '—'}</div>
                </div>
            </div>
            <div style="display:flex; gap:2rem; margin-top:1.2rem; flex-wrap:wrap;">
                <div><span style="color:var(--text-secondary);">📍</span> {team_info['country'] if pd.notna(team_info['country']) else '—'}, {team_info['state_province'] if pd.notna(team_info['state_province']) else '—'}</div>
                <div><span style="color:var(--text-secondary);">🎂</span> Rookie Year: {int(team_info['rookie_year']) if pd.notna(team_info['rookie_year']) else '—'}</div>
                <div><span style="color:var(--text-secondary);">⚔️</span> Matches Played: {(matches[(matches['red_team_1'] == team_number) | (matches['red_team_2'] == team_number) | (matches['blue_team_1'] == team_number) | (matches['blue_team_2'] == team_number)]).shape[0]}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Event history
        te = team_events[team_events["team_number"] == team_number].sort_values("season")
        if len(te) > 0:
            st.markdown("### 📋 Event History")
            display = te[["season", "event_key", "wins", "losses", "ties", "opr", "ccwm", "ranking"]].copy()
            display["Win Rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
            st.dataframe(
                display.rename(columns={
                    "event_key": "Event", "season": "Season", "wins": "W", "losses": "L",
                    "ties": "T", "opr": "OPR", "ccwm": "CCWM", "ranking": "Rank",
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "OPR": st.column_config.NumberColumn(format="%.1f"),
                    "CCWM": st.column_config.NumberColumn(format="%.1f"),
                    "Win Rate": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
                    "Season": st.column_config.TextColumn(width="small"),
                    "W": st.column_config.NumberColumn(width="small"),
                    "L": st.column_config.NumberColumn(width="small"),
                    "T": st.column_config.NumberColumn(width="small"),
                    "Rank": st.column_config.NumberColumn(width="small"),
                },
            )

            # OPR trend chart
            if len(te) > 1:
                st.markdown("### 📈 OPR / CCWM Trend")
                chart_data = te.set_index("event_key")[["opr", "ccwm"]]
                st.line_chart(chart_data, use_container_width=True)

            # ELO history chart
            if elo_df is not None:
                team_elo_history = elo_df[elo_df["team_number"] == team_number].sort_values(["season", "event_key", "match_number"])
                if len(team_elo_history) > 1:
                    st.markdown("### 📈 ELO Rating Trend")
                    st.caption("Each point shows ELO after a match. Teams start at 1500.")
                    elo_chart = team_elo_history.reset_index(drop=True).copy()
                    elo_chart["Match #"] = range(1, len(elo_chart) + 1)
                    st.line_chart(elo_chart.set_index("Match #")[["elo_after"]], use_container_width=True)
                    
                    current_team_elo = current_elo[current_elo["team_number"] == team_number] if current_elo is not None else None
                    if current_team_elo is not None and len(current_team_elo) > 0:
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Current ELO", f"{current_team_elo['current_elo'].iloc[0]:.0f}")
                        c2.metric("Peak ELO", f"{team_elo_history['elo_after'].max():.0f}")
                        c3.metric("Min ELO", f"{team_elo_history['elo_after'].min():.0f}")

            # Season summary stats
            st.markdown("### 📊 Season Summary")
            te_tmp = te.copy()
            te_tmp["total_matches"] = te_tmp["wins"] + te_tmp["losses"] + te_tmp["ties"]
            seasons_played = te_tmp.groupby("season").agg(
                Matches=("total_matches", "sum"),
                Wins=("wins", "sum"),
                Losses=("losses", "sum"),
                Ties=("ties", "sum"),
                Win_Rate=("wins", lambda x: x.sum() / max(x.sum() + te_tmp.loc[x.index, "losses"].sum() + te_tmp.loc[x.index, "ties"].sum(), 1)),
                Best_OPR=("opr", "max"),
                Avg_OPR=("opr", "mean"),
            ).round(2)
            st.dataframe(seasons_played, use_container_width=True)
        else:
            st.info("No event data found for this team.")

# ============================================================================
# EVENT BROWSER
# ============================================================================
elif page == "📅 Event Browser":
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">📅 Event Browser</div>
        <div class="hero-subtitle">Explore match results, rankings, and statistics for any event in the dataset.</div>
    </div>
    """, unsafe_allow_html=True)

    col_s, col_e = st.columns(2)
    with col_s:
        season = st.selectbox(
            "Season",
            sorted(matches["season"].unique()),
            format_func=lambda x: f"{x} — {season_labels.get(x, x)}",
        )
    with col_e:
        season_matches = matches[matches["season"] == season]
        event_list = sorted(season_matches["event_key"].unique())
        event = st.selectbox("Event", event_list)

    if event:
        event_matches = season_matches[season_matches["event_key"] == event].sort_values("match_number")
        quals = event_matches[~event_matches["is_playoff"]]
        playoffs = event_matches[event_matches["is_playoff"]]

        # Event header
        scores_e = pd.concat([event_matches["red_score"], event_matches["blue_score"]])
        st.markdown(f"""
        <div class="section-card">
            <div style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:1rem;">
                <div>
                    <div style="font-size:1.4rem; font-weight:700;">{event_matches['event_name'].iloc[0]}</div>
                    <div style="color:var(--text-secondary);">{event} &nbsp;·&nbsp; Region: {event_matches['region'].iloc[0]}</div>
                </div>
                <div style="display:flex; gap:2rem;">
                    <div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700;">{len(event_matches)}</div><div style="font-size:0.75rem; color:var(--text-secondary);">MATCHES</div></div>
                    <div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700;">{len(quals)}</div><div style="font-size:0.75rem; color:var(--text-secondary);">QUALS</div></div>
                    <div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700;">{len(playoffs)}</div><div style="font-size:0.75rem; color:var(--text-secondary);">PLAYOFF</div></div>
                    <div style="text-align:center;"><div style="font-size:1.5rem; font-weight:700;">{scores_e.mean():.0f}</div><div style="font-size:0.75rem; color:var(--text-secondary);">AVG SCORE</div></div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["🏁 Qualification Matches", "🏆 Playoff Matches"])

        with tab1:
            if len(quals) > 0:
                quals_display = quals[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]].copy()
                st.dataframe(
                    quals_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "match_number": "Match #",
                        "red_team_1": "Red 1",
                        "red_team_2": "Red 2",
                        "blue_team_1": "Blue 1",
                        "blue_team_2": "Blue 2",
                        "red_score": st.column_config.NumberColumn("Red", format="%d"),
                        "blue_score": st.column_config.NumberColumn("Blue", format="%d"),
                        "winner": st.column_config.TextColumn("Winner", width="small"),
                    },
                )
            else:
                st.info("No qualification matches found.")

        with tab2:
            if len(playoffs) > 0:
                playoffs_display = playoffs[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]].copy()
                st.dataframe(
                    playoffs_display,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "match_number": "Match #",
                        "red_team_1": "Red 1",
                        "red_team_2": "Red 2",
                        "blue_team_1": "Blue 1",
                        "blue_team_2": "Blue 2",
                        "red_score": st.column_config.NumberColumn("Red", format="%d"),
                        "blue_score": st.column_config.NumberColumn("Blue", format="%d"),
                        "winner": st.column_config.TextColumn("Winner", width="small"),
                    },
                )
            else:
                st.info("No playoff matches found.")

        # Event rankings
        event_te = team_events[team_events["event_key"] == event].sort_values("ranking")
        if len(event_te) > 0:
            st.markdown("### 🏅 Event Rankings")
            rankings_display = event_te[["ranking", "team_number", "wins", "losses", "ties", "opr", "ccwm"]].copy()
            rankings_display["win_rate"] = (rankings_display["wins"] / (rankings_display["wins"] + rankings_display["losses"] + rankings_display["ties"])).round(2)
            st.dataframe(
                rankings_display.rename(columns={
                    "ranking": "Rank", "team_number": "Team", "wins": "W", "losses": "L",
                    "ties": "T", "opr": "OPR", "ccwm": "CCWM", "win_rate": "Win %",
                }),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "OPR": st.column_config.NumberColumn(format="%.1f"),
                    "CCWM": st.column_config.NumberColumn(format="%.1f"),
                    "Win %": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
                },
            )

# ============================================================================
# OPR LEADERBOARD
# ============================================================================
elif page == "🏆 OPR Leaderboard":
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">🏆 OPR Leaderboard</div>
        <div class="hero-subtitle">Top teams ranked by Offensive Power Rating — raw and per-season views.</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        show_season = st.selectbox(
            "Filter by Season",
            ["All Seasons"] + sorted(matches["season"].unique()),
            format_func=lambda x: f"{x} — {season_labels[x]}" if x in season_labels else x,
        )
    with col2:
        top_n = st.slider("Show top N teams", 5, 100, 20)

    if show_season == "All Seasons":
        df = team_events.copy()
    else:
        df = team_events[team_events["season"] == show_season].copy()

    df = df.dropna(subset=["opr"]).sort_values("opr", ascending=False)

    # Top stat cards
    if len(df) > 0:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(stat_card_html("🏅", f"{df['opr'].iloc[0]:.1f}", "Highest OPR", "accent-red"), unsafe_allow_html=True)
        with c2:
            st.markdown(stat_card_html("📊", f"{df['opr'].mean():.1f}", "Mean OPR", "accent-blue"), unsafe_allow_html=True)
        with c3:
            st.markdown(stat_card_html("🎯", f"{len(df):,}", "Teams Ranked", "accent-green"), unsafe_allow_html=True)

    # Leaderboard table
    st.markdown(f"### 🔥 Top {top_n} Teams")
    display = df.head(top_n)[["team_number", "event_key", "season", "opr", "ccwm", "wins", "losses", "ties", "ranking"]].copy()
    display["Win Rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
    display["opr"] = display["opr"].round(2)
    display["ccwm"] = display["ccwm"].round(2)

    st.dataframe(
        display.rename(columns={
            "team_number": "Team", "event_key": "Event", "season": "Season",
            "opr": "OPR", "ccwm": "CCWM", "wins": "W", "losses": "L",
            "ties": "T", "ranking": "Rank",
        }),
        use_container_width=True,
        hide_index=True,
        column_config={
            "OPR": st.column_config.NumberColumn(format="%.1f"),
            "CCWM": st.column_config.NumberColumn(format="%.1f"),
            "Win Rate": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
        },
    )

    # OPR distribution
    st.markdown("---")
    st.markdown("### 📊 OPR Distribution")
    valid_oprs = df["opr"].dropna()
    hist_data = pd.cut(valid_oprs, bins=30).value_counts().sort_index()
    hist_df = pd.DataFrame({"OPR Range": [str(i) for i in hist_data.index], "Count": hist_data.values}).set_index("OPR Range")
    st.bar_chart(hist_df, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean OPR", f"{valid_oprs.mean():.2f}")
    c2.metric("Median OPR", f"{valid_oprs.median():.2f}")
    c3.metric("Max OPR", f"{valid_oprs.max():.2f}")
    c4.metric("Std Dev", f"{valid_oprs.std():.2f}")

    # Distribution stats
    q25, q75 = valid_oprs.quantile(0.25), valid_oprs.quantile(0.75)
    st.caption(f"Interquartile range: {q25:.1f} – {q75:.1f} · Skewness: {valid_oprs.skew():.2f}")

# ============================================================================
# ELO RATINGS
# ============================================================================
elif page == "📈 ELO Ratings":
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">📈 ELO Ratings</div>
        <div class="hero-subtitle">
            Rolling ELO ratings computed across all 1,762 matches. Teams start at 1500 and gain/lose points
            based on match outcomes using the standard ELO formula (K=32).
        </div>
    </div>
    """, unsafe_allow_html=True)

    if elo_df is None or current_elo is None:
        st.warning("⚠️ ELO data not found. Run `python scripts/compute_elo.py` first.")
    else:
        tab1, tab2 = st.tabs(["🏆 ELO Leaderboard", "🔍 ELO History"])

        with tab1:
            # Top stat cards
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(stat_card_html("🏅", f"{current_elo['current_elo'].max():.0f}", "Highest ELO", "accent-red"), unsafe_allow_html=True)
            with c2:
                st.markdown(stat_card_html("📊", f"{current_elo['current_elo'].mean():.0f}", "Mean ELO", "accent-blue"), unsafe_allow_html=True)
            with c3:
                st.markdown(stat_card_html("🤖", f"{len(current_elo):,}", "Teams Rated", "accent-orange"), unsafe_allow_html=True)
            with c4:
                st.markdown(stat_card_html("📐", f"{current_elo['current_elo'].std():.0f}", "Std Dev", "accent-green"), unsafe_allow_html=True)

            # Leaderboard
            top_n = st.slider("Show top N teams by ELO", 5, 100, 20, key="elo_top_n")
            top_elo = current_elo.sort_values("current_elo", ascending=False).head(top_n)
            
            # Merge with team names
            top_elo_display = top_elo.merge(teams[["team_number", "team_name"]], on="team_number", how="left")
            top_elo_display["Rank"] = range(1, len(top_elo_display) + 1)
            top_elo_display["current_elo"] = top_elo_display["current_elo"].round(0).astype(int)
            
            st.markdown(f"### 🔥 Top {top_n} Teams by Current ELO")
            st.dataframe(
                top_elo_display[["Rank", "team_number", "team_name", "current_elo"]].rename(
                    columns={"team_number": "Team #", "team_name": "Name", "current_elo": "ELO"}
                ),
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Rank": st.column_config.NumberColumn(width="small"),
                    "ELO": st.column_config.NumberColumn(format="%d"),
                },
            )

            # ELO distribution
            st.markdown("---")
            st.markdown("### 📊 ELO Distribution")
            valid_elos = current_elo["current_elo"].dropna()
            hist_data = pd.cut(valid_elos, bins=30).value_counts().sort_index()
            hist_df = pd.DataFrame({"ELO Range": [str(i) for i in hist_data.index], "Count": hist_data.values}).set_index("ELO Range")
            st.bar_chart(hist_df, use_container_width=True)

            c1, c2, c3 = st.columns(3)
            c1.metric("Range", f"{valid_elos.min():.0f} – {valid_elos.max():.0f}")
            c2.metric("Median", f"{valid_elos.median():.0f}")
            c3.metric("Teams > 1700", f"{(valid_elos > 1700).sum():,}")

        with tab2:
            st.markdown("### 🔍 Track a Team's ELO Over Time")
            
            elo_team_list = sorted(elo_df["team_number"].unique())
            elo_team = st.selectbox("Select Team", elo_team_list, key="elo_team_select")
            
            if elo_team:
                team_elo = elo_df[elo_df["team_number"] == elo_team].sort_values(["season", "event_key", "match_number"]).reset_index(drop=True)
                
                if len(team_elo) > 0:
                    # ELO line chart
                    team_elo["Match #"] = range(1, len(team_elo) + 1)
                    st.line_chart(team_elo.set_index("Match #")[["elo_after"]], use_container_width=True)
                    
                    # ELO stats
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Current ELO", f"{team_elo['elo_after'].iloc[-1]:.0f}")
                    c2.metric("Peak ELO", f"{team_elo['elo_after'].max():.0f}")
                    c3.metric("Total Change", f"{team_elo['elo_after'].iloc[-1] - 1500:+.0f}")
                    c4.metric("Matches", len(team_elo))
                    
                    # Show table of recent ELO changes
                    st.markdown("### 📋 Match-by-Match ELO History")
                    elo_display = team_elo[["season", "event_key", "match_number", "elo_before", "elo_after", "elo_change"]].tail(20).sort_values("match_number", ascending=False)
                    st.dataframe(
                        elo_display.rename(columns={
                            "season": "Season", "event_key": "Event", "match_number": "Match #",
                            "elo_before": "Before", "elo_after": "After", "elo_change": "Δ"
                        }),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Before": st.column_config.NumberColumn(format="%.0f"),
                            "After": st.column_config.NumberColumn(format="%.0f"),
                            "Δ": st.column_config.NumberColumn(format="%+.1f"),
                        },
                    )

# ============================================================================
# MATCH PREDICTOR
# ============================================================================
elif page == "🎯 Match Predictor":
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">🎯 Match Predictor</div>
        <div class="hero-subtitle">
            Predict the winner of a theoretical match based on each team's average OPR and historical win rate.
        </div>
    </div>
    """, unsafe_allow_html=True)

    team_list = sorted(teams["team_number"].unique())

    # Alliance selection
    st.markdown("### ⚔️ Select Alliances")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background:linear-gradient(135deg, rgba(231,76,60,0.08), rgba(231,76,60,0.02)); 
                    border:1px solid rgba(231,76,60,0.2); border-radius:12px; padding:1.2rem 1.2rem 0.8rem 1.2rem;">
            <div style="font-size:1.1rem; font-weight:700; color:#E74C3C; margin-bottom:0.6rem;">🔴 RED ALLIANCE</div>
        """, unsafe_allow_html=True)
        r1 = st.selectbox("Red Team 1", team_list, key="r1", index=0, label_visibility="collapsed")
        r2 = st.selectbox("Red Team 2", team_list, key="r2", index=min(1, len(team_list) - 1), label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div style="background:linear-gradient(135deg, rgba(52,152,219,0.08), rgba(52,152,219,0.02)); 
                    border:1px solid rgba(52,152,219,0.2); border-radius:12px; padding:1.2rem 1.2rem 0.8rem 1.2rem;">
            <div style="font-size:1.1rem; font-weight:700; color:#3498DB; margin-bottom:0.6rem;">🔵 BLUE ALLIANCE</div>
        """, unsafe_allow_html=True)
        b1 = st.selectbox("Blue Team 1", team_list, key="b1", index=min(2, len(team_list) - 1), label_visibility="collapsed")
        b2 = st.selectbox("Blue Team 2", team_list, key="b2", index=min(3, len(team_list) - 1), label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("🔮 PREDICT WINNER", type="primary", use_container_width=True):
        red_teams = [r1, r2]
        blue_teams = [b1, b2]

        def get_team_stats(tn):
            opr = opr_lookup.get(tn)
            wr = wr_lookup.get(tn)
            if opr is None:
                st.warning(f"⚠️ Team {tn} has no OPR data — using 0.0")
                opr = 0.0
            if wr is None:
                wr = 0.5
            return opr, wr

        red_oprs = [get_team_stats(t)[0] for t in red_teams]
        blue_oprs = [get_team_stats(t)[0] for t in blue_teams]
        red_wrs = [get_team_stats(t)[1] for t in red_teams]
        blue_wrs = [get_team_stats(t)[1] for t in blue_teams]

        red_opr_sum = sum(red_oprs)
        blue_opr_sum = sum(blue_oprs)
        opr_diff = red_opr_sum - blue_opr_sum

        # Logistic probability
        prob_red = 1 / (1 + np.exp(-opr_diff / OPR_SCALE))
        prob_blue = 1 - prob_red

        # OPR comparison chart
        st.markdown("### 📊 OPR Comparison")
        st.markdown(f"""
        <div style="display:flex; align-items:center; gap:1rem; margin:0.5rem 0 1.5rem 0;">
            <div style="flex:{prob_red}; min-width:60px;">
                <div style="font-weight:700; font-size:1.1rem; color:#E74C3C;">🔴 {red_opr_sum:.1f}</div>
                <div class="prediction-bar">
                    <div class="prediction-fill-red" style="width:100%;"></div>
                </div>
                <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.2rem;">
                    Team {r1}: {red_oprs[0]:.1f} OPR<br>
                    Team {r2}: {red_oprs[1]:.1f} OPR
                </div>
            </div>
            <div style="font-weight:600; color:var(--text-secondary); font-size:0.85rem; text-align:center;">
                vs
            </div>
            <div style="flex:{prob_blue}; min-width:60px;">
                <div style="font-weight:700; font-size:1.1rem; color:#3498DB;">🔵 {blue_opr_sum:.1f}</div>
                <div class="prediction-bar">
                    <div class="prediction-fill-blue" style="width:100%;"></div>
                </div>
                <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.2rem;">
                    Team {b1}: {blue_oprs[0]:.1f} OPR<br>
                    Team {b2}: {blue_oprs[1]:.1f} OPR
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Prediction result
        winner_emoji = "🔴" if prob_red > 0.5 else "🔵"
        winner_color = "RED" if prob_red > 0.5 else "BLUE"

        st.markdown(f"""
        <div class="section-card" style="text-align:center;">
            <div style="font-size:1.3rem; font-weight:700; margin-bottom:0.5rem;">
                {winner_emoji} {winner_color} WINS
            </div>
            <div style="font-size:2.5rem; font-weight:800; 
                        background: linear-gradient(135deg, {'#E74C3C' if prob_red > 0.5 else '#3498DB'}, 
                                                   {'#F39C12' if prob_red > 0.5 else '#2980B9'});
                        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
                        background-clip: text;">
                {max(prob_red, prob_blue):.1%}
            </div>
            <div style="color:var(--text-secondary); margin-top:0.3rem;">
                confidence · expected margin: ~{abs(opr_diff):.0f} points
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Win rate bars
        st.markdown("### 🎯 Win Probability Breakdown")
        pct_red = int(prob_red * 100)
        pct_blue = int(prob_blue * 100)
        st.markdown(f"""
        <div style="display:flex; gap:1rem; margin-top:0.5rem;">
            <div style="flex:1; text-align:center;">
                <div style="font-weight:700; color:#E74C3C; margin-bottom:0.3rem;">🔴 RED</div>
                <div class="prediction-bar">
                    <div class="prediction-fill-red" style="width:{prob_red*100:.0f}%;"></div>
                </div>
                <div style="font-weight:600; margin-top:0.3rem; font-size:1.1rem;">{prob_red:.1%}</div>
            </div>
            <div style="flex:1; text-align:center;">
                <div style="font-weight:700; color:#3498DB; margin-bottom:0.3rem;">🔵 BLUE</div>
                <div class="prediction-bar">
                    <div class="prediction-fill-blue" style="width:{prob_blue*100:.0f}%;"></div>
                </div>
                <div style="font-weight:600; margin-top:0.3rem; font-size:1.1rem;">{prob_blue:.1%}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Detailed stats
        st.markdown("### 📋 Team Details")
        detail_cols = st.columns(4)
        for i, (t, opr, wr) in enumerate([(r1, red_oprs[0], red_wrs[0]), (r2, red_oprs[1], red_wrs[1]),
                                           (b1, blue_oprs[0], blue_wrs[0]), (b2, blue_oprs[1], blue_wrs[1])]):
            alliance = "🔴" if i < 2 else "🔵"
            with detail_cols[i]:
                st.markdown(f"""
                <div class="stat-card" style="padding:0.8rem 1rem;">
                    <div style="font-weight:600;">{alliance} Team {t}</div>
                    <div style="font-size:1.3rem; font-weight:700; margin-top:0.3rem;">OPR {opr:.1f}</div>
                    <div style="color:var(--text-secondary); font-size:0.8rem;">Win Rate {wr:.0%}</div>
                </div>
                """, unsafe_allow_html=True)
