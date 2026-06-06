import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Player of the Season", page_icon="🥇", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)
render_sidebar(matches, teams)

hero_header("🥇 Player of the Season", "Composite power rankings combining OPR, ELO, and Win Rate into a single score for each season.")

# Build season-end ELO lookup from historical elo_df (per-season accuracy)
season_elo_lookup = {}
if elo_df is not None:
    elo_df_sorted = elo_df.sort_values(["season", "team_number", "match_number"])
    last_elo = elo_df_sorted.groupby(["season", "team_number"])["elo_after"].last().reset_index()
    for _, row in last_elo.iterrows():
        season_elo_lookup[(row["season"], int(row["team_number"]))] = row["elo_after"]

# Build composite scores per season
rows = []
for season in sorted(matches["season"].unique()):
    season_te = team_events[team_events["season"] == season].copy()
    if len(season_te) == 0:
        continue
    # Get per-team stats for this season
    for _, row in season_te.iterrows():
        tn = int(row["team_number"])
        opr = row["opr"] if not pd.isna(row["opr"]) else 0
        wr = row["wins"] / max(row["wins"] + row["losses"] + row["ties"], 1)
        elo = season_elo_lookup.get((season, tn), 1500)
        rows.append({"season": season, "team_number": tn, "opr": opr, "elo": elo, "win_rate": wr})

ps_df = pd.DataFrame(rows)

# Normalize each metric within its season (z-score)
for metric in ["opr", "elo", "win_rate"]:
    ps_df[f"{metric}_z"] = ps_df.groupby("season")[metric].transform(lambda x: (x - x.mean()) / max(x.std(), 1e-6))

# Composite score = equally weighted z-scores
ps_df["composite"] = (ps_df["opr_z"] + ps_df["elo_z"] + ps_df["win_rate_z"]) / 3

# Rank within each season
ps_df["rank"] = ps_df.groupby("season")["composite"].rank(ascending=False, method="min").astype(int)

# Season selector
st.markdown("### 🏆 Select Season")
selected_season = st.selectbox("Season", sorted(matches["season"].unique()), format_func=lambda x: f"{x} — {season_labels[x]}", label_visibility="collapsed")

season_data = ps_df[ps_df["season"] == selected_season].sort_values("rank")

# Top 3 stat cards
top3 = season_data.head(3)
c1, c2, c3 = st.columns(3)
medals = ["🥇", "🥈", "🥉"]
accent_colors = ["accent-red", "accent-blue", "accent-orange"]
for i, (_, t) in enumerate(top3.iterrows()):
    with [c1, c2, c3][i]:
        tn = int(t["team_number"])
        team_name = teams[teams["team_number"] == tn]["team_name"].iloc[0] if len(teams[teams["team_number"] == tn]) > 0 else f"Team {tn}"
        st.markdown(stat_card_html(medals[i], f"Team {tn}", team_name, accent_colors[i]), unsafe_allow_html=True)
        st.caption(f"Composite: {t['composite']:.2f}  ·  OPR: {t['opr']:.1f}  ·  ELO: {t['elo']:.0f}")

st.markdown("---")

# Full leaderboard
st.markdown(f"### 📊 {season_labels[selected_season]} Leaderboard")
top_n = st.slider("Show top N", 5, 50, 15)
display = season_data.head(top_n)[["rank", "team_number", "composite", "opr", "elo", "win_rate"]].copy()
display["composite"] = display["composite"].round(2)
display["opr"] = display["opr"].round(1)
display["elo"] = display["elo"].round(0).astype(int)
display["win_rate"] = (display["win_rate"] * 100).round(1)

# Merge team names
display = display.merge(teams[["team_number", "team_name"]], on="team_number", how="left")
display["Team"] = display.apply(lambda r: f"{int(r['team_number'])} — {r['team_name']}" if pd.notna(r['team_name']) else str(int(r['team_number'])), axis=1)

st.dataframe(
    display[["rank", "Team", "composite", "opr", "elo", "win_rate"]].rename(
        columns={"rank": "Rank", "composite": "Composite", "opr": "OPR", "elo": "ELO", "win_rate": "Win %"}
    ),
    use_container_width=True, hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(width="small"),
        "Composite": st.column_config.NumberColumn(format="%.2f"),
        "OPR": st.column_config.NumberColumn(format="%.1f"),
        "ELO": st.column_config.NumberColumn(format="%d"),
        "Win %": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

# Distribution chart
st.markdown("---")
st.markdown("### 📊 Composite Score Distribution")
hist = pd.cut(season_data["composite"], bins=20).value_counts().sort_index()
st.bar_chart(pd.DataFrame({"Score Range": [str(i) for i in hist.index], "Count": hist.values}).set_index("Score Range"), use_container_width=True)

# Cross-season top performers
st.markdown("---")
st.markdown("### 🏅 All-Time Best Composite Scores")
all_best = ps_df.nlargest(15, "composite")[["season", "team_number", "composite", "opr", "elo", "win_rate"]].copy()
all_best["composite"] = all_best["composite"].round(2)
all_best["opr"] = all_best["opr"].round(1)
all_best["elo"] = all_best["elo"].round(0).astype(int)
all_best["win_rate"] = (all_best["win_rate"] * 100).round(1)
all_best["Rank"] = range(1, len(all_best) + 1)
all_best = all_best.merge(teams[["team_number", "team_name"]], on="team_number", how="left")
all_best["Team"] = all_best.apply(lambda r: f"{int(r['team_number'])} — {r['team_name']}" if pd.notna(r['team_name']) else str(int(r['team_number'])), axis=1)

st.dataframe(
    all_best[["Rank", "Team", "season", "composite", "opr", "elo", "win_rate"]].rename(
        columns={"season": "Season", "composite": "Composite", "opr": "OPR", "elo": "ELO", "win_rate": "Win %"}
    ),
    use_container_width=True, hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn(width="small"),
        "Composite": st.column_config.NumberColumn(format="%.2f"),
        "OPR": st.column_config.NumberColumn(format="%.1f"),
        "ELO": st.column_config.NumberColumn(format="%d"),
        "Win %": st.column_config.NumberColumn(format="%.1f%%"),
    },
)
