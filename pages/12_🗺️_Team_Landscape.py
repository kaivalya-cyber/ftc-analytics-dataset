import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from shared import inject_css, load_data, build_lookups, hero_header, render_sidebar

st.set_page_config(page_title="Team Landscape", page_icon="🗺️", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🗺️ Team Landscape", "Explore the competitive landscape: every team plotted by OPR vs ELO, sized by win rate, colored by season.")

# Build scatter data
scatter_rows = []
for tn in opr_lookup:
    opr = opr_lookup.get(tn, 0)
    wr = wr_lookup.get(tn, 0.5)
    elo = elo_lookup.get(tn, 1500) if elo_lookup else 1500
    # Find the team's primary season (most matches)
    tm = matches[(matches["red_team_1"] == tn) | (matches["red_team_2"] == tn) | (matches["blue_team_1"] == tn) | (matches["blue_team_2"] == tn)]
    primary_season = tm["season"].mode().iloc[0] if len(tm) > 0 else "unknown"
    name = teams[teams["team_number"] == tn]["team_name"].iloc[0] if len(teams[teams["team_number"] == tn]) > 0 else f"Team {tn}"
    scatter_rows.append({"team_number": tn, "name": name, "opr": opr, "elo": elo, "win_rate": wr, "season": primary_season, "matches": len(tm)})

df = pd.DataFrame(scatter_rows)
df = df[df["opr"] > 0].copy()  # filter out zero-OPR teams

# Season filter
all_seasons = sorted(df["season"].unique())
selected_seasons = st.multiselect("Filter by season", all_seasons, default=all_seasons, key="landscape_season")
filtered = df[df["season"].isin(selected_seasons)]

if len(filtered) > 0:
    # Color map for seasons
    season_colors = {
        "1819": "#E74C3C", "1920": "#3498DB", "2021": "#F39C12",
        "2122": "#27AE60", "2223": "#9B59B6", "2324": "#E67E22",
    }
    color_map = {s: season_colors.get(s, "#888") for s in all_seasons}

    fig = go.Figure()

    for season in selected_seasons:
        season_data = filtered[filtered["season"] == season]
        if len(season_data) == 0:
            continue
        fig.add_trace(go.Scatter(
            x=season_data["opr"],
            y=season_data["elo"],
            mode="markers",
            name=f"{season_labels.get(season, season)}",
            marker=dict(
                size=np.clip(season_data["win_rate"] * 40 + 6, 6, 35),
                color=color_map[season],
                opacity=0.75,
                line=dict(width=0.5, color="rgba(255,255,255,0.2)"),
            ),
            text=[f"Team {row['team_number']}: {row['name']}<br>OPR: {row['opr']:.1f}<br>ELO: {row['elo']:.0f}<br>Win Rate: {row['win_rate']*100:.1f}%<br>Matches: {row['matches']}" for _, row in season_data.iterrows()],
            hoverinfo="text",
        ))

    fig.update_layout(
        xaxis_title="OPR (Offensive Power Rating)",
        yaxis_title="ELO Rating",
        template="plotly_dark",
        height=650,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(color="#f0f0f5")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.15)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.15)"),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Top-right quadrant teams (elite)
    st.markdown("---")
    st.markdown("### 🏆 Elite Quadrant (High OPR + High ELO)")
    opr_median = filtered["opr"].median()
    elo_median = filtered["elo"].median()
    elite = filtered[(filtered["opr"] >= opr_median) & (filtered["elo"] >= elo_median)].nlargest(15, "win_rate")
    elite_display = elite[["team_number", "name", "opr", "elo", "win_rate", "season"]].copy()
    elite_display["opr"] = elite_display["opr"].round(1)
    elite_display["elo"] = elite_display["elo"].round(0).astype(int)
    elite_display["win_rate"] = (elite_display["win_rate"] * 100).round(1)
    st.dataframe(
        elite_display.rename(columns={"team_number": "Team", "name": "Name", "opr": "OPR", "elo": "ELO", "win_rate": "Win %", "season": "Season"}),
        use_container_width=True, hide_index=True,
        column_config={
            "OPR": st.column_config.NumberColumn(format="%.1f"),
            "ELO": st.column_config.NumberColumn(format="%d"),
            "Win %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    # Stats summary
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Teams Shown", len(filtered))
    c2.metric("Median OPR", f"{opr_median:.1f}")
    c3.metric("Median ELO", f"{elo_median:.0f}")
    c4.metric("Elite Teams", len(elite))
else:
    st.info("Select at least one season to display the team landscape.")
