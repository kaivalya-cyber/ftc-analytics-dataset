import streamlit as st
import pandas as pd
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Team Explorer", page_icon="🔍", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🔍 Team Explorer", "Deep-dive into any team's performance history, OPR trends, and event results.")
team_list = sorted(teams["team_number"].unique())
team_number = st.selectbox("Search for a team by number", team_list, index=0, label_visibility="collapsed")

if team_number:
    team_info = teams[teams["team_number"] == team_number].iloc[0]
    st.markdown(f'<div class="section-card" style="margin-top:1rem;"><div style="display:flex;align-items:center;gap:1rem;"><div style="font-size:3rem;">🤖</div><div><div style="font-size:1.6rem;font-weight:700;">Team {team_number}</div><div style="color:var(--text-secondary);font-size:1rem;">{team_info["team_name"] if pd.notna(team_info["team_name"]) else "—"}</div></div></div><div style="display:flex;gap:2rem;margin-top:1.2rem;flex-wrap:wrap;"><div><span style="color:var(--text-secondary);">📍</span> {team_info["country"] if pd.notna(team_info["country"]) else "—"}, {team_info["state_province"] if pd.notna(team_info["state_province"]) else "—"}</div><div><span style="color:var(--text-secondary);">🎂</span> Rookie Year: {int(team_info["rookie_year"]) if pd.notna(team_info["rookie_year"]) else "—"}</div><div><span style="color:var(--text-secondary);">⚔️</span> Matches Played: {(matches[(matches["red_team_1"]==team_number)|(matches["red_team_2"]==team_number)|(matches["blue_team_1"]==team_number)|(matches["blue_team_2"]==team_number)]).shape[0]}</div></div></div>', unsafe_allow_html=True)

    te = team_events[team_events["team_number"] == team_number].sort_values("season")
    if len(te) > 0:
        st.markdown("### 📋 Event History")
        display = te[["season", "event_key", "wins", "losses", "ties", "opr", "ccwm", "ranking"]].copy()
        display["Win Rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
        st.dataframe(display.rename(columns={"event_key": "Event", "season": "Season", "wins": "W", "losses": "L", "ties": "T", "opr": "OPR", "ccwm": "CCWM", "ranking": "Rank"}), use_container_width=True, hide_index=True, column_config={"OPR": st.column_config.NumberColumn(format="%.1f"), "CCWM": st.column_config.NumberColumn(format="%.1f"), "Win Rate": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1)})
        if len(te) > 1:
            st.markdown("### 📈 OPR / CCWM Trend")
            st.line_chart(te.set_index("event_key")[["opr", "ccwm"]], use_container_width=True)
        if elo_df is not None:
            telo = elo_df[elo_df["team_number"] == team_number].sort_values(["season", "event_key", "match_number"])
            if len(telo) > 1:
                st.markdown("### 📈 ELO Rating Trend")
                telo_chart = telo.reset_index(drop=True)
                telo_chart["Match #"] = range(1, len(telo_chart) + 1)
                st.line_chart(telo_chart.set_index("Match #")[["elo_after"]], use_container_width=True)
                cte = current_elo[current_elo["team_number"] == team_number] if current_elo is not None else None
                if cte is not None and len(cte) > 0:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current ELO", f"{cte['current_elo'].iloc[0]:.0f}")
                    c2.metric("Peak ELO", f"{telo['elo_after'].max():.0f}")
                    c3.metric("Min ELO", f"{telo['elo_after'].min():.0f}")
        st.markdown("### 📊 Season Summary")
        te_tmp = te.copy()
        te_tmp["total_matches"] = te_tmp["wins"] + te_tmp["losses"] + te_tmp["ties"]
        seasons_played = te_tmp.groupby("season").agg(Matches=("total_matches", "sum"), Wins=("wins", "sum"), Losses=("losses", "sum"), Ties=("ties", "sum"), Best_OPR=("opr", "max"), Avg_OPR=("opr", "mean")).round(2)
        st.dataframe(seasons_played, use_container_width=True)
    else:
        st.info("No event data found for this team.")
