import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Upset Analysis", page_icon="⚡", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
_, opr_lookup, _, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("⚡ Upset Analysis", "Discover when underdogs win — tracking matches where the predicted favorite (by OPR or ELO) loses.")

upset_rows = []
for _, row in matches.iterrows():
    r1, r2 = int(row["red_team_1"]), int(row["red_team_2"])
    b1, b2 = int(row["blue_team_1"]), int(row["blue_team_2"])
    winner = row["winner"]
    if winner not in ["red", "blue"]: continue
    red_opr = opr_lookup.get(r1, 0) + opr_lookup.get(r2, 0)
    blue_opr = opr_lookup.get(b1, 0) + opr_lookup.get(b2, 0)
    opr_fav = "red" if red_opr > blue_opr else "blue" if blue_opr > red_opr else "tie"
    opr_upset = (opr_fav != "tie" and opr_fav != winner)
    red_elo = np.mean([elo_lookup.get(r1, 1500), elo_lookup.get(r2, 1500)])
    blue_elo = np.mean([elo_lookup.get(b1, 1500), elo_lookup.get(b2, 1500)])
    elo_fav = "red" if red_elo > blue_elo else "blue" if blue_elo > red_elo else "tie"
    elo_upset = (elo_fav != "tie" and elo_fav != winner)
    upset_rows.append({"season": row["season"], "is_playoff": row["is_playoff"], "opr_upset": opr_upset, "elo_upset": elo_upset, "opr_diff": abs(red_opr - blue_opr), "red_score": row["red_score"], "blue_score": row["blue_score"], "winner": winner, "opr_fav": opr_fav, "red_team_1": r1, "red_team_2": r2, "blue_team_1": b1, "blue_team_2": b2, "event_key": row["event_key"], "match_number": row["match_number"]})

upset_df = pd.DataFrame(upset_rows)
total = len(upset_df)
opr_upsets = upset_df["opr_upset"].sum()
elo_upsets = upset_df["elo_upset"].sum()

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(stat_card_html("⚡", f"{opr_upsets/total*100:.1f}%", "OPR Upset Rate", "accent-red"), unsafe_allow_html=True)
with c2: st.markdown(stat_card_html("📊", f"{elo_upsets/total*100:.1f}%", "ELO Upset Rate", "accent-blue"), unsafe_allow_html=True)
with c3: st.markdown(stat_card_html("🎯", f"{total:,}", "Matches Analyzed", "accent-orange"), unsafe_allow_html=True)
with c4: st.markdown(stat_card_html("🤖", f"{opr_upsets}", "Total OPR Upsets", "accent-green"), unsafe_allow_html=True)

st.markdown("---"); st.markdown("### 📊 Upset Rate by Season")
season_upset_stats = upset_df.groupby("season").agg(Matches=("opr_upset", "count"), OPR_Upset_Rate=("opr_upset", "mean"), ELO_Upset_Rate=("elo_upset", "mean"))
season_upset_stats["OPR_Upset_Rate"] *= 100
season_upset_stats["ELO_Upset_Rate"] *= 100
season_upset_stats["Matches"] = season_upset_stats["Matches"].astype(int)
st.bar_chart(season_upset_stats[["OPR_Upset_Rate", "ELO_Upset_Rate"]], use_container_width=True)
st.dataframe(season_upset_stats.rename(columns={"OPR_Upset_Rate": "OPR Upset %", "ELO_Upset_Rate": "ELO Upset %"}), use_container_width=True, column_config={"OPR Upset %": st.column_config.NumberColumn(format="%.1f%%"), "ELO Upset %": st.column_config.NumberColumn(format="%.1f%%")})

st.markdown("### 🏁 Qualification vs Playoff Upsets")
qual_u = upset_df[~upset_df["is_playoff"]]
playoff_u = upset_df[upset_df["is_playoff"]]
c1, c2 = st.columns(2)
with c1:
    st.metric("Qual OPR Upset Rate", f"{qual_u['opr_upset'].mean()*100:.1f}%")
    st.metric("Qual ELO Upset Rate", f"{qual_u['elo_upset'].mean()*100:.1f}%")
    st.caption(f"{len(qual_u)} qualification matches")
with c2:
    st.metric("Playoff OPR Upset Rate", f"{playoff_u['opr_upset'].mean()*100:.1f}%")
    st.metric("Playoff ELO Upset Rate", f"{playoff_u['elo_upset'].mean()*100:.1f}%")
    st.caption(f"{len(playoff_u)} playoff matches")

st.markdown("---"); st.markdown("### 🔥 Biggest OPR Upsets")
biggest = upset_df[upset_df["opr_upset"]].nlargest(15, "opr_diff")
biggest_display = biggest[["season", "event_key", "match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "opr_diff", "winner"]].copy()
biggest_display["Score"] = biggest_display.apply(lambda r: f"{int(r['red_score'])}–{int(r['blue_score'])}", axis=1)
biggest_display["opr_diff"] = biggest_display["opr_diff"].round(0).astype(int)
st.dataframe(biggest_display[["season", "event_key", "match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "Score", "opr_diff", "winner"]].rename(columns={"season": "Season", "event_key": "Event", "match_number": "Match #", "red_team_1": "R1", "red_team_2": "R2", "blue_team_1": "B1", "blue_team_2": "B2", "opr_diff": "OPR Diff", "winner": "Winner"}), use_container_width=True, hide_index=True, column_config={"OPR Diff": st.column_config.NumberColumn(format="%d")})
