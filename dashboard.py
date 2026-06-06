#!/usr/bin/env python3
"""
FTC Analytics Dashboard
-----------------------
Premium interactive Streamlit dashboard for the FTC Open Analytics Dataset.
Multi-page app with pages in pages/ directory.

Run: streamlit run dashboard.py
"""

import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html

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

inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
season_labels, opr_lookup, wr_lookup, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

# ---- Sidebar ----
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

# ---- Hero ----
st.markdown('<div class="hero-header"><div class="hero-title">FTC Open Analytics</div><div class="hero-subtitle">A clean, structured dataset of FIRST Tech Challenge match results spanning 6 seasons — from Rover Ruckus to Centerstage — with computed OPR metrics and machine learning benchmarks.</div></div>', unsafe_allow_html=True)

# ---- Stat cards ----
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(stat_card_html("📊", f"{len(matches):,}", "Total Matches", "accent-red"), unsafe_allow_html=True)
with c2: st.markdown(stat_card_html("🤖", f"{len(teams):,}", "Unique Teams", "accent-blue"), unsafe_allow_html=True)
with c3: st.markdown(stat_card_html("📅", str(matches["event_key"].nunique()), "Events", "accent-orange"), unsafe_allow_html=True)
with c4: st.markdown(stat_card_html("🌎", str(matches["region"].nunique()), "Regions", "accent-green"), unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ---- Season breakdown ----
st.markdown("### 📊 Season Overview")
season_tab = st.selectbox("Select Season", list(season_labels.keys()), format_func=lambda x: f"{x} — {season_labels[x]}", label_visibility="collapsed")
sm = matches[matches["season"] == season_tab]
quals = sm[~sm["is_playoff"]]
playoffs = sm[sm["is_playoff"]]

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Matches", len(sm)); c2.metric("Qualification", len(quals))
c3.metric("Playoff", len(playoffs)); c4.metric("Events", sm["event_key"].nunique())

scores = pd.concat([sm["red_score"], sm["blue_score"]])
c1, c2, c3, c4 = st.columns(4)
c1.metric("Mean Score", f"{scores.mean():.1f}"); c2.metric("Median Score", f"{scores.median():.1f}")
c3.metric("Max Score", f"{scores.max():.0f}"); c4.metric("Std Dev", f"{scores.std():.1f}")

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**📈 Score Distribution**")
    sv = pd.concat([sm["red_score"], sm["blue_score"]])
    hist = pd.cut(sv, bins=25).value_counts().sort_index()
    st.bar_chart(pd.DataFrame({"Score Range": [str(i) for i in hist.index], "Count": hist.values}).set_index("Score Range"), use_container_width=True)
with col_b:
    st.markdown("**🏁 Win Distribution**")
    st.bar_chart(sm["winner"].value_counts(), use_container_width=True)

st.markdown("---")
st.markdown('<div style="display:flex;gap:1rem;flex-wrap:wrap;justify-content:center;"><span class="chip chip-green">✅ 1,762 matches</span><span class="chip chip-blue">✅ 902 teams</span><span class="chip chip-red">✅ 53 events</span><span class="chip chip-orange" style="background:rgba(243,156,18,0.15);color:#F39C12;border:1px solid rgba(243,156,18,0.3);">✅ 10 regions</span><span class="chip chip-blue">✅ 88.7% accuracy</span></div>', unsafe_allow_html=True)
