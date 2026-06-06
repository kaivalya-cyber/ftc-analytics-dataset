#!/usr/bin/env python3
"""
shared.py — Common utilities for the FTC Analytics Dashboard
Loaded by all pages in pages/ and dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent / "data" / "processed"

# ---------------------------------------------------------------------------
# Injected CSS (call once per app)
# ---------------------------------------------------------------------------
def inject_css():
    st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    :root {
        --ftc-red: #E74C3C; --ftc-blue: #3498DB; --ftc-orange: #F39C12; --ftc-green: #27AE60;
        --bg-dark: #0f0f13; --bg-card: #1a1a24; --text-primary: #f0f0f5; --text-secondary: #a0a0b5;
        --border-subtle: rgba(255,255,255,0.06); --gradient-hero: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        --gradient-red: linear-gradient(135deg, #E74C3C, #C0392B); --gradient-blue: linear-gradient(135deg, #3498DB, #2980B9);
        --shadow-card: 0 4px 24px rgba(0,0,0,0.3); --radius-lg: 16px; --radius-md: 10px; --radius-sm: 8px;
    }
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu, footer, header { visibility: hidden; }
    .stApp { background: var(--bg-dark); }
    section[data-testid="stSidebar"] { background: linear-gradient(180deg, #12121c 0%, #0d0d17 100%); border-right: 1px solid var(--border-subtle); }
    section[data-testid="stSidebar"] .stRadio label { padding: 0.7rem 1rem !important; border-radius: var(--radius-sm) !important; transition: all 0.2s ease; font-weight: 500; font-size: 0.95rem; }
    section[data-testid="stSidebar"] .stRadio label:hover { background: rgba(255,255,255,0.05) !important; }
    .hero-header { background: var(--gradient-hero); border-radius: var(--radius-lg); padding: 2.5rem 2rem; margin-bottom: 1.5rem; border: 1px solid var(--border-subtle); position: relative; overflow: hidden; }
    .hero-header::before { content: ""; position: absolute; top: -50%; right: -20%; width: 400px; height: 400px; background: radial-gradient(circle, rgba(231,76,60,0.08) 0%, transparent 70%); border-radius: 50%; }
    .hero-header::after { content: ""; position: absolute; bottom: -40%; left: -10%; width: 350px; height: 350px; background: radial-gradient(circle, rgba(52,152,219,0.06) 0%, transparent 70%); border-radius: 50%; }
    .hero-title { font-size: 2.4rem; font-weight: 800; background: linear-gradient(135deg, #E74C3C 0%, #F39C12 50%, #3498DB 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; margin-bottom: 0.3rem; position: relative; z-index: 1; }
    .hero-subtitle { font-size: 1.05rem; color: var(--text-secondary); font-weight: 400; position: relative; z-index: 1; }
    .stat-card { background: var(--bg-card); border-radius: var(--radius-md); padding: 1.25rem 1.5rem; border: 1px solid var(--border-subtle); transition: all 0.25s ease; position: relative; overflow: hidden; }
    .stat-card:hover { border-color: rgba(255,255,255,0.12); transform: translateY(-2px); box-shadow: var(--shadow-card); }
    .stat-card-icon { font-size: 1.8rem; margin-bottom: 0.4rem; }
    .stat-card-value { font-size: 2rem; font-weight: 700; color: var(--text-primary); line-height: 1.1; }
    .stat-card-label { font-size: 0.82rem; color: var(--text-secondary); font-weight: 500; text-transform: uppercase; letter-spacing: 0.05em; margin-top: 0.2rem; }
    .stat-card-accent { position: absolute; top: 0; left: 0; width: 100%; height: 3px; }
    .accent-red { background: var(--gradient-red); } .accent-blue { background: var(--gradient-blue); }
    .accent-orange { background: linear-gradient(135deg, #F39C12, #E67E22); } .accent-green { background: linear-gradient(135deg, #27AE60, #1E8449); }
    .section-card { background: var(--bg-card); border-radius: var(--radius-lg); padding: 1.5rem; border: 1px solid var(--border-subtle); margin-bottom: 1rem; }
    .prediction-bar { height: 12px; border-radius: 6px; background: var(--bg-dark); overflow: hidden; margin: 0.5rem 0; border: 1px solid var(--border-subtle); }
    .prediction-fill-red { height: 100%; background: var(--gradient-red); border-radius: 6px; transition: width 0.6s ease; }
    .prediction-fill-blue { height: 100%; background: var(--gradient-blue); border-radius: 6px; transition: width 0.6s ease; }
    .chip { display: inline-block; padding: 0.25rem 0.75rem; border-radius: 20px; font-size: 0.78rem; font-weight: 600; }
    .chip-red { background: rgba(231,76,60,0.15); color: #E74C3C; border: 1px solid rgba(231,76,60,0.3); }
    .chip-blue { background: rgba(52,152,219,0.15); color: #3498DB; border: 1px solid rgba(52,152,219,0.3); }
    .chip-green { background: rgba(39,174,96,0.15); color: #27AE60; border: 1px solid rgba(39,174,96,0.3); }
    [data-testid="stDataFrame"] { border-radius: var(--radius-md) !important; overflow: hidden; border: 1px solid var(--border-subtle) !important; }
    .stButton > button { border-radius: var(--radius-sm) !important; font-weight: 600 !important; }
    .stButton > button[kind="primary"] { background: var(--gradient-red) !important; border: none !important; }
    .stButton > button[kind="primary"]:hover { transform: translateY(-1px); }
    [data-testid="stMetricValue"] { font-weight: 700 !important; }
    h1, h2, h3 { font-weight: 700 !important; letter-spacing: -0.02em; }
    hr { border-color: var(--border-subtle) !important; margin: 1.5rem 0 !important; }
    [data-testid="stAlert"] { border-radius: var(--radius-md) !important; border: none !important; }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Cached data loader
# ---------------------------------------------------------------------------
@st.cache_data
def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    teams = pd.read_csv(DATA_DIR / "teams.csv")
    team_events = pd.read_csv(DATA_DIR / "team_events.csv")
    elo_df = None
    current_elo = None
    elo_path = DATA_DIR / "team_elo.csv"
    current_elo_path = DATA_DIR / "current_elo.csv"
    if elo_path.exists():
        elo_df = pd.read_csv(elo_path)
    if current_elo_path.exists():
        current_elo = pd.read_csv(current_elo_path)
    return matches, teams, team_events, elo_df, current_elo


# ---------------------------------------------------------------------------
# Lookup builders
# ---------------------------------------------------------------------------
def build_lookups(matches, teams, team_events, current_elo):
    season_labels = {
        "1819": "Rover Ruckus 🤖", "1920": "Skystone 🪨", "2021": "Ultimate Goal 🎯",
        "2122": "Freight Frenzy 📦", "2223": "Power Play ⚡", "2324": "Centerstage 🎭",
    }
    opr_lookup, opr_counts = {}, {}
    for _, row in team_events.iterrows():
        tn = int(row["team_number"])
        opr = row["opr"] if not pd.isna(row["opr"]) else 0
        opr_lookup[tn] = opr_lookup.get(tn, 0.0) + opr
        opr_counts[tn] = opr_counts.get(tn, 0) + 1
    for tn in opr_lookup:
        opr_lookup[tn] /= opr_counts[tn]

    wr_lookup, wr_counts = {}, {}
    for _, row in team_events.iterrows():
        tn = int(row["team_number"])
        w, l, t = row["wins"], row["losses"], row["ties"]
        wr = w / (w + l + t) if (w + l + t) > 0 else 0.5
        wr_lookup[tn] = wr_lookup.get(tn, 0.0) + wr
        wr_counts[tn] = wr_counts.get(tn, 0) + 1
    for tn in wr_lookup:
        wr_lookup[tn] /= wr_counts[tn]

    elo_lookup = {}
    if current_elo is not None:
        for _, row in current_elo.iterrows():
            elo_lookup[int(row["team_number"])] = row["current_elo"]

    all_diffs = []
    for _, row in matches.iterrows():
        r1_o = opr_lookup.get(row["red_team_1"], 0)
        r2_o = opr_lookup.get(row["red_team_2"], 0)
        b1_o = opr_lookup.get(row["blue_team_1"], 0)
        b2_o = opr_lookup.get(row["blue_team_2"], 0)
        all_diffs.append((r1_o + r2_o) - (b1_o + b2_o))
    opr_scale = max(np.std(all_diffs), 1.0)

    return season_labels, opr_lookup, wr_lookup, elo_lookup, opr_scale


def stat_card_html(icon, value, label, accent_class):
    return f"""<div class="stat-card">
        <div class="stat-card-accent {accent_class}"></div>
        <div class="stat-card-icon">{icon}</div>
        <div class="stat-card-value">{value}</div>
        <div class="stat-card-label">{label}</div></div>"""


def hero_header(title, subtitle):
    st.markdown(f"""<div class="hero-header">
        <div class="hero-title" style="font-size:1.8rem;">{title}</div>
        <div class="hero-subtitle">{subtitle}</div></div>""", unsafe_allow_html=True)


def render_sidebar(matches, teams):
    """Render the shared sidebar on all pages."""
    with st.sidebar:
        st.markdown("""
        <div style="text-align:center; padding:0.5rem 0 1.5rem 0;">
            <div style="font-size:2.8rem;margin-bottom:0.3rem;">🤖</div>
            <div style="font-size:1.2rem;font-weight:800;letter-spacing:-0.02em;background:linear-gradient(135deg,#E74C3C,#3498DB);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">FTC ANALYTICS</div>
            <div style="font-size:0.75rem;color:#606080;font-weight:500;margin-top:0.15rem;">BY KAIVALYA SINGH</div>
        </div>
        """, unsafe_allow_html=True)
        st.caption(f"📊 {len(matches):,} matches\n\n🤖 {len(teams):,} teams\n\n📅 {matches['event_key'].nunique()} events\n\n🌎 {matches['region'].nunique()} regions")
        st.markdown("---")
        st.markdown("[📖 GitHub](https://github.com/kaivalya-cyber/ftc-analytics-dataset)  |  [📄 Paper](dataset_description.md)\n\nBuilt with ❤️ using Streamlit")
