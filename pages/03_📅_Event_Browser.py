import streamlit as st
import pandas as pd
from shared import inject_css, load_data, build_lookups, hero_header, render_sidebar

st.set_page_config(page_title="Event Browser", page_icon="📅", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, _, _, _, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("📅 Event Browser", "Explore match results, rankings, and statistics for any event in the dataset.")
col_s, col_e = st.columns(2)
with col_s:
    season = st.selectbox("Season", sorted(matches["season"].unique()), format_func=lambda x: f"{x} — {season_labels.get(x, x)}")
with col_e:
    season_matches = matches[matches["season"] == season]
    event_list = sorted(season_matches["event_key"].unique())
    event = st.selectbox("Event", event_list)

if event:
    em = season_matches[season_matches["event_key"] == event].sort_values("match_number")
    quals = em[~em["is_playoff"]]
    playoffs = em[em["is_playoff"]]
    scores_e = pd.concat([em["red_score"], em["blue_score"]])
    st.markdown(f'<div class="section-card"><div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:1rem;"><div><div style="font-size:1.4rem;font-weight:700;">{em["event_name"].iloc[0]}</div><div style="color:var(--text-secondary);">{event} · Region: {em["region"].iloc[0]}</div></div><div style="display:flex;gap:2rem;"><div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(em)}</div><div style="font-size:0.75rem;color:var(--text-secondary);">MATCHES</div></div><div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(quals)}</div><div style="font-size:0.75rem;color:var(--text-secondary);">QUALS</div></div><div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{len(playoffs)}</div><div style="font-size:0.75rem;color:var(--text-secondary);">PLAYOFF</div></div><div style="text-align:center;"><div style="font-size:1.5rem;font-weight:700;">{scores_e.mean():.0f}</div><div style="font-size:0.75rem;color:var(--text-secondary);">AVG SCORE</div></div></div></div></div>', unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["🏁 Qualification Matches", "🏆 Playoff Matches"])
    with tab1:
        if len(quals) > 0:
            st.dataframe(quals[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]], use_container_width=True, hide_index=True, column_config={"match_number": "Match #", "red_team_1": "Red 1", "red_team_2": "Red 2", "blue_team_1": "Blue 1", "blue_team_2": "Blue 2", "red_score": st.column_config.NumberColumn("Red", format="%d"), "blue_score": st.column_config.NumberColumn("Blue", format="%d"), "winner": st.column_config.TextColumn("Winner", width="small")})
        else:
            st.info("No qualification matches found.")
    with tab2:
        if len(playoffs) > 0:
            st.dataframe(playoffs[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]], use_container_width=True, hide_index=True, column_config={"match_number": "Match #", "red_team_1": "Red 1", "red_team_2": "Red 2", "blue_team_1": "Blue 1", "blue_team_2": "Blue 2", "red_score": st.column_config.NumberColumn("Red", format="%d"), "blue_score": st.column_config.NumberColumn("Blue", format="%d"), "winner": st.column_config.TextColumn("Winner", width="small")})
        else:
            st.info("No playoff matches found.")

    event_te = team_events[team_events["event_key"] == event].sort_values("ranking")
    if len(event_te) > 0:
        st.markdown("### 🏅 Event Rankings")
        rd = event_te[["ranking", "team_number", "wins", "losses", "ties", "opr", "ccwm"]].copy()
        rd["win_rate"] = (rd["wins"] / (rd["wins"] + rd["losses"] + rd["ties"])).round(2)
        st.dataframe(rd.rename(columns={"ranking": "Rank", "team_number": "Team", "wins": "W", "losses": "L", "ties": "T", "opr": "OPR", "ccwm": "CCWM", "win_rate": "Win %"}), use_container_width=True, hide_index=True, column_config={"OPR": st.column_config.NumberColumn(format="%.1f"), "CCWM": st.column_config.NumberColumn(format="%.1f"), "Win %": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1)})
