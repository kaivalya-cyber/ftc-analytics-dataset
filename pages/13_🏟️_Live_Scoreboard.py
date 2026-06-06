import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
from shared import inject_css, load_data, build_lookups, hero_header, render_sidebar

st.set_page_config(page_title="Live Scoreboard", page_icon="🏟️", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🏟️ Live Scoreboard", "Real-time match results and team rankings for the current season.")

# Auto-refresh note
st.caption(f"⏱️ Last loaded: {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")

# Attempt to fetch live data from TOA public API
current_season = "2324"  # Latest season in dataset
live_data = None
try:
    resp = requests.get(f"https://theorangealliance.org/api/event?season_key={current_season}", timeout=5,
                        headers={"Accept": "application/json"})
    if resp.status_code == 200:
        live_data = resp.json()
        st.success(f"📡 Live TOA API connected — {len(live_data) if isinstance(live_data, list) else '?'} events found for {season_labels.get(current_season, current_season)}")
    else:
        st.info("📡 TOA API unavailable. Showing latest data from processed dataset.")
except Exception:
    st.info("📡 TOA API unavailable. Showing latest data from processed dataset.")

st.markdown("---")

# Show recent matches from processed data
st.markdown("### 🏟️ Most Recent Matches")
season_matches = matches[matches["season"] == current_season].sort_values(["event_key", "match_number"], ascending=[False, False])
recent = season_matches.head(20)

if len(recent) > 0:
    # Scoreboard-style display
    for _, row in recent.iterrows():
        r1, r2 = int(row["red_team_1"]), int(row["red_team_2"])
        b1, b2 = int(row["blue_team_1"]), int(row["blue_team_2"])
        rs, bs = int(row["red_score"]), int(row["blue_score"])
        winner = row["winner"]
        event = row["event_key"]
        is_playoff = row["is_playoff"]

        # Determine highlight
        red_highlight = "border-left: 3px solid #E74C3C;" if winner == "red" else ""
        blue_highlight = "border-left: 3px solid #3498DB;" if winner == "blue" else ""
        tie_style = "opacity: 0.7;" if winner == "tie" else ""

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:1rem;padding:0.6rem 1rem;margin-bottom:0.4rem;background:var(--bg-card);border-radius:8px;border:1px solid var(--border-subtle);{tie_style}">
            <div style="font-size:0.7rem;color:var(--text-secondary);min-width:90px;">{event}<br><small>{'🏆' if is_playoff else '⚔️'} {'Playoff' if is_playoff else 'Qual'}</small></div>
            <div style="flex:1;text-align:right;{red_highlight}padding-right:1rem;">
                <span style="font-weight:700;">Team {r1}</span> & <span style="font-weight:700;">Team {r2}</span>
            </div>
            <div style="font-size:1.6rem;font-weight:800;min-width:80px;text-align:center;">
                <span style="color:{'#E74C3C' if winner=='red' else '#a0a0b5'}">{rs}</span>
                <span style="color:var(--text-secondary);margin:0 0.3rem;">—</span>
                <span style="color:{'#3498DB' if winner=='blue' else '#a0a0b5'}">{bs}</span>
            </div>
            <div style="flex:1;text-align:left;{blue_highlight}padding-left:1rem;">
                <span style="font-weight:700;">Team {b1}</span> & <span style="font-weight:700;">Team {b2}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.info("No recent matches found.")

# Live rankings table
st.markdown("---")
st.markdown("### 📊 Current Season Rankings (by Win Rate)")

season_te = team_events[team_events["season"] == current_season].copy()
if len(season_te) > 0:
    season_te["win_rate"] = season_te["wins"] / (season_te["wins"] + season_te["losses"] + season_te["ties"])
    rankings = season_te.nlargest(20, "win_rate")[["team_number", "wins", "losses", "ties", "opr", "win_rate"]].copy()
    rankings["win_rate"] = (rankings["win_rate"] * 100).round(1)
    rankings["opr"] = rankings["opr"].round(1)
    rankings["record"] = rankings.apply(lambda r: f"{int(r['wins'])}-{int(r['losses'])}-{int(r['ties'])}", axis=1)
    rankings["Rank"] = range(1, len(rankings) + 1)

    st.dataframe(
        rankings[["Rank", "team_number", "record", "opr", "win_rate"]].rename(
            columns={"team_number": "Team", "record": "Record", "opr": "OPR", "win_rate": "Win %"}
        ),
        use_container_width=True, hide_index=True,
        column_config={
            "Rank": st.column_config.NumberColumn(width="small"),
            "OPR": st.column_config.NumberColumn(format="%.1f"),
            "Win %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

# Refresh button
st.markdown("---")
c1, c2, c3 = st.columns([1, 1, 1])
with c2:
    if st.button("🔄 Refresh Now", use_container_width=True):
        st.rerun()
