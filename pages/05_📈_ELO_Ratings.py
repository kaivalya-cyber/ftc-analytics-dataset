import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="ELO Ratings", page_icon="📈", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
_, _, _, _, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("📈 ELO Ratings", "Rolling ELO ratings computed across all 1,762 matches. Teams start at 1500 and gain/lose points based on match outcomes (K=32).")

if elo_df is None or current_elo is None:
    st.warning("⚠️ ELO data not found. Run `python scripts/compute_elo.py` first.")
else:
    tab1, tab2 = st.tabs(["🏆 ELO Leaderboard", "🔍 ELO History"])
    with tab1:
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(stat_card_html("🏅", f"{current_elo['current_elo'].max():.0f}", "Highest ELO", "accent-red"), unsafe_allow_html=True)
        with c2: st.markdown(stat_card_html("📊", f"{current_elo['current_elo'].mean():.0f}", "Mean ELO", "accent-blue"), unsafe_allow_html=True)
        with c3: st.markdown(stat_card_html("🤖", f"{len(current_elo):,}", "Teams Rated", "accent-orange"), unsafe_allow_html=True)
        with c4: st.markdown(stat_card_html("📐", f"{current_elo['current_elo'].std():.0f}", "Std Dev", "accent-green"), unsafe_allow_html=True)
        top_n = st.slider("Show top N teams by ELO", 5, 100, 20, key="elo_top_n")
        top_elo = current_elo.sort_values("current_elo", ascending=False).head(top_n)
        top_elo_display = top_elo.merge(teams[["team_number", "team_name"]], on="team_number", how="left")
        top_elo_display["Rank"] = range(1, len(top_elo_display)+1)
        top_elo_display["current_elo"] = top_elo_display["current_elo"].round(0).astype(int)
        st.markdown(f"### 🔥 Top {top_n} Teams by Current ELO")
        st.dataframe(top_elo_display[["Rank","team_number","team_name","current_elo"]].rename(columns={"team_number":"Team #","team_name":"Name","current_elo":"ELO"}), use_container_width=True, hide_index=True, column_config={"Rank":st.column_config.NumberColumn(width="small"),"ELO":st.column_config.NumberColumn(format="%d")})
        st.markdown("---"); st.markdown("### 📊 ELO Distribution")
        valid_elos = current_elo["current_elo"].dropna()
        hist_data = pd.cut(valid_elos, bins=30).value_counts().sort_index()
        st.bar_chart(pd.DataFrame({"ELO Range":[str(i) for i in hist_data.index],"Count":hist_data.values}).set_index("ELO Range"), use_container_width=True)
        c1,c2,c3=st.columns(3)
        c1.metric("Range",f"{valid_elos.min():.0f} – {valid_elos.max():.0f}")
        c2.metric("Median",f"{valid_elos.median():.0f}")
        c3.metric("Teams > 1700",f"{(valid_elos>1700).sum():,}")
    with tab2:
        st.markdown("### 🔍 Track a Team's ELO Over Time")
        elo_team = st.selectbox("Select Team", sorted(elo_df["team_number"].unique()), key="elo_team_select")
        if elo_team:
            team_elo = elo_df[elo_df["team_number"]==elo_team].sort_values(["season","event_key","match_number"]).reset_index(drop=True)
            if len(team_elo)>0:
                team_elo["Match #"]=range(1,len(team_elo)+1)
                st.line_chart(team_elo.set_index("Match #")[["elo_after"]], use_container_width=True)
                c1,c2,c3,c4=st.columns(4)
                c1.metric("Current ELO",f"{team_elo['elo_after'].iloc[-1]:.0f}")
                c2.metric("Peak ELO",f"{team_elo['elo_after'].max():.0f}")
                c3.metric("Total Change",f"{team_elo['elo_after'].iloc[-1]-1500:+.0f}")
                c4.metric("Matches",len(team_elo))
                elo_display=team_elo[["season","event_key","match_number","elo_before","elo_after","elo_change"]].tail(20).sort_values("match_number",ascending=False)
                st.markdown("### 📋 Match-by-Match ELO History")
                st.dataframe(elo_display.rename(columns={"season":"Season","event_key":"Event","match_number":"Match #","elo_before":"Before","elo_after":"After","elo_change":"Δ"}), use_container_width=True, hide_index=True, column_config={"Before":st.column_config.NumberColumn(format="%.0f"),"After":st.column_config.NumberColumn(format="%.0f"),"Δ":st.column_config.NumberColumn(format="%+.1f")})
