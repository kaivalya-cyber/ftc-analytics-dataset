import streamlit as st
import pandas as pd
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="OPR Leaderboard", page_icon="🏆", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, _, _, _, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🏆 OPR Leaderboard", "Top teams ranked by Offensive Power Rating — raw and per-season views.")
col1, col2 = st.columns([1, 1])
with col1:
    show_season = st.selectbox("Filter by Season", ["All Seasons"] + sorted(matches["season"].unique()), format_func=lambda x: f"{x} — {season_labels[x]}" if x in season_labels else x)
with col2:
    top_n = st.slider("Show top N teams", 5, 100, 20)

df = team_events.copy() if show_season == "All Seasons" else team_events[team_events["season"] == show_season].copy()
df = df.dropna(subset=["opr"]).sort_values("opr", ascending=False)

if len(df) > 0:
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(stat_card_html("🏅", f"{df['opr'].iloc[0]:.1f}", "Highest OPR", "accent-red"), unsafe_allow_html=True)
    with c2: st.markdown(stat_card_html("📊", f"{df['opr'].mean():.1f}", "Mean OPR", "accent-blue"), unsafe_allow_html=True)
    with c3: st.markdown(stat_card_html("🎯", f"{len(df):,}", "Teams Ranked", "accent-green"), unsafe_allow_html=True)

st.markdown(f"### 🔥 Top {top_n} Teams")
display = df.head(top_n)[["team_number", "event_key", "season", "opr", "ccwm", "wins", "losses", "ties", "ranking"]].copy()
display["Win Rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
display["opr"], display["ccwm"] = display["opr"].round(2), display["ccwm"].round(2)
st.dataframe(display.rename(columns={"team_number":"Team","event_key":"Event","season":"Season","opr":"OPR","ccwm":"CCWM","wins":"W","losses":"L","ties":"T","ranking":"Rank"}), use_container_width=True, hide_index=True, column_config={"OPR":st.column_config.NumberColumn(format="%.1f"),"CCWM":st.column_config.NumberColumn(format="%.1f"),"Win Rate":st.column_config.ProgressColumn(format="%.0f%%",min_value=0,max_value=1)})

st.markdown("---"); st.markdown("### 📊 OPR Distribution")
valid_oprs = df["opr"].dropna()
hist_data = pd.cut(valid_oprs, bins=30).value_counts().sort_index()
st.bar_chart(pd.DataFrame({"OPR Range":[str(i) for i in hist_data.index],"Count":hist_data.values}).set_index("OPR Range"), use_container_width=True)
c1,c2,c3,c4=st.columns(4)
c1.metric("Mean OPR",f"{valid_oprs.mean():.2f}"); c2.metric("Median OPR",f"{valid_oprs.median():.2f}")
c3.metric("Max OPR",f"{valid_oprs.max():.2f}"); c4.metric("Std Dev",f"{valid_oprs.std():.2f}")
q25,q75=valid_oprs.quantile(0.25),valid_oprs.quantile(0.75)
st.caption(f"IQR: {q25:.1f} – {q75:.1f} · Skewness: {valid_oprs.skew():.2f}")
