import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Season Trends", page_icon="📈", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("📈 Season Trends", "Year-over-year macro trends — scoring, competitiveness, and regional growth across 6 FTC seasons.")

# --- Compute season-level metrics ---
season_metrics = []
for season in sorted(matches["season"].unique()):
    sm = matches[matches["season"] == season]
    all_scores = pd.concat([sm["red_score"], sm["blue_score"]])
    close_rate = (sm["score_diff"].abs() <= 15).mean() * 100

    # OPR upset rate
    opr_upsets = 0
    for _, row in sm[sm["winner"] != "tie"].iterrows():
        red_opr = opr_lookup.get(row["red_team_1"], 0) + opr_lookup.get(row["red_team_2"], 0)
        blue_opr = opr_lookup.get(row["blue_team_1"], 0) + opr_lookup.get(row["blue_team_2"], 0)
        if red_opr > blue_opr and row["winner"] == "blue":
            opr_upsets += 1
        elif blue_opr > red_opr and row["winner"] == "red":
            opr_upsets += 1
    non_ties = len(sm[sm["winner"] != "tie"])
    upset_rate = (opr_upsets / non_ties * 100) if non_ties > 0 else 0

    # Teams
    season_teams = set()
    for col in ["red_team_1", "red_team_2", "blue_team_1", "blue_team_2"]:
        season_teams.update(sm[col].dropna().astype(int).unique())

    # New teams (rookie year -> FTC season mapping)
    rookie_to_season = {str(y): f"{str(y)[2:]}{str(y+1)[2:]}" for y in range(2018, 2025)}
    rookie_teams_all = set()
    if "rookie_year" in teams.columns:
        for _, trow in teams.iterrows():
            ry = str(int(trow["rookie_year"])) if not pd.isna(trow["rookie_year"]) else None
            mapped = rookie_to_season.get(ry)
            if mapped == season:
                rookie_teams_all.add(int(trow["team_number"]))
    new_teams = len(season_teams & rookie_teams_all)

    season_metrics.append({
        "season": season,
        "matches": len(sm),
        "events": sm["event_key"].nunique(),
        "teams": len(season_teams),
        "new_teams": new_teams,
        "regions": sm["region"].nunique(),
        "mean_score": all_scores.mean(),
        "median_score": all_scores.median(),
        "std_score": all_scores.std(),
        "max_score": all_scores.max(),
        "close_rate": close_rate,
        "upset_rate": upset_rate,
        "playoff_pct": sm["is_playoff"].mean() * 100,
    })

metrics_df = pd.DataFrame(season_metrics).sort_values("season")

# --- Summary cards ---
st.markdown("### 📊 6-Season Overview")
c1, c2, c3, c4 = st.columns(4)
with c1:
    growth = metrics_df["matches"].iloc[-1] / metrics_df["matches"].iloc[0] * 100 - 100
    st.markdown(stat_card_html("📈", f"+{growth:.0f}%", "Match Growth", "accent-red"), unsafe_allow_html=True)
with c2:
    first_score, last_score = metrics_df["mean_score"].iloc[0], metrics_df["mean_score"].iloc[-1]
    st.markdown(stat_card_html("🎯", f"{first_score:.0f} → {last_score:.0f}", "Mean Score Trend", "accent-blue"), unsafe_allow_html=True)
with c3:
    first_close, last_close = metrics_df["close_rate"].iloc[0], metrics_df["close_rate"].iloc[-1]
    st.markdown(stat_card_html("⚡", f"{first_close:.0f}% → {last_close:.0f}%", "Close Rate Trend", "accent-orange"), unsafe_allow_html=True)
with c4:
    st.markdown(stat_card_html("🌎", str(metrics_df["regions"].iloc[-1]), "Regions (Latest)", "accent-green"), unsafe_allow_html=True)

st.markdown("---")

# --- Scoring trends ---
st.markdown("### 🎯 Scoring Trends Over Time")
fig1 = go.Figure()
fig1.add_trace(go.Scatter(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["mean_score"],
    mode="lines+markers",
    name="Mean Score",
    line=dict(width=3, color="#E74C3C"),
    marker=dict(size=10, color="#E74C3C"),
    hovertemplate="%{x}<br>Mean Score: %{y:.1f}<extra></extra>",
))
fig1.add_trace(go.Scatter(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["median_score"],
    mode="lines+markers",
    name="Median Score",
    line=dict(width=2, color="#3498DB", dash="dash"),
    marker=dict(size=8, color="#3498DB"),
    hovertemplate="%{x}<br>Median Score: %{y:.1f}<extra></extra>",
))
fig1.add_trace(go.Scatter(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["max_score"],
    mode="lines+markers",
    name="Max Score",
    line=dict(width=2, color="#F39C12", dash="dot"),
    marker=dict(size=8, color="#F39C12"),
    hovertemplate="%{x}<br>Max Score: %{y:.0f}<extra></extra>",
))
fig1.update_layout(
    template="plotly_dark", height=400,
    title="Score Progression Across Seasons",
    xaxis_title="Season", yaxis_title="Score",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig1, use_container_width=True)

# --- Match volume and competitiveness ---
col_l, col_r = st.columns(2)

with col_l:
    st.markdown("### 📊 Match Volume by Season")
    fig2 = go.Figure(data=[go.Bar(
        x=[season_labels.get(s, s) for s in metrics_df["season"]],
        y=metrics_df["matches"],
        marker_color="#3498DB",
        text=metrics_df["matches"],
        textposition="outside",
        textfont=dict(color="#f0f0f5"),
        hovertemplate="%{x}<br>Matches: %{y}<br>Events: %{customdata}<extra></extra>",
        customdata=metrics_df["events"],
    )])
    fig2.update_layout(
        template="plotly_dark", height=350,
        xaxis_title="Season", yaxis_title="Matches",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_r:
    st.markdown("### ⚡ Competitiveness Trends")
    fig3 = go.Figure()
    fig3.add_trace(go.Bar(
        x=[season_labels.get(s, s) for s in metrics_df["season"]],
        y=metrics_df["close_rate"],
        name="Close Match %",
        marker_color="#27AE60",
        hovertemplate="%{x}<br>Close Rate: %{y:.1f}%<extra></extra>",
    ))
    fig3.add_trace(go.Scatter(
        x=[season_labels.get(s, s) for s in metrics_df["season"]],
        y=metrics_df["upset_rate"],
        mode="lines+markers",
        name="Upset Rate %",
        yaxis="y2",
        marker=dict(color="#E74C3C", size=8),
        line=dict(width=2, color="#E74C3C"),
        hovertemplate="%{x}<br>Upset Rate: %{y:.1f}%<extra></extra>",
    ))
    fig3.update_layout(
        template="plotly_dark", height=350,
        xaxis_title="Season",
        yaxis=dict(title="Close Match %", side="left", gridcolor="rgba(255,255,255,0.08)"),
        yaxis2=dict(title="Upset Rate %", side="right", overlaying="y", gridcolor="rgba(255,255,255,0)"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    st.plotly_chart(fig3, use_container_width=True)

# --- Regional growth ---
st.markdown("### 🌎 Regional Growth")

region_by_season = matches.groupby(["season", "region"]).size().reset_index(name="matches")
region_pivot = region_by_season.pivot(index="season", columns="region", values="matches").fillna(0)

fig4 = go.Figure()
colors = ["#E74C3C", "#3498DB", "#F39C12", "#27AE60", "#9B59B6", "#1ABC9C", "#E67E22", "#2ECC71", "#E91E63", "#00BCD4"]
for i, region in enumerate(region_pivot.columns):
    fig4.add_trace(go.Bar(
        x=[season_labels.get(s, s) for s in region_pivot.index],
        y=region_pivot[region],
        name=region,
        marker_color=colors[i % len(colors)],
        hovertemplate=f"{region}<br>%{{x}}: %{{y}} matches<extra></extra>",
    ))

fig4.update_layout(
    template="plotly_dark", height=400,
    barmode="stack",
    title="Matches per Region by Season",
    xaxis_title="Season", yaxis_title="Matches",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig4, use_container_width=True)

# --- Team Growth ---
st.markdown("### 🤖 Team Growth")
fig5 = go.Figure()
fig5.add_trace(go.Bar(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["teams"],
    name="Total Teams",
    marker_color="#3498DB",
    hovertemplate="%{x}<br>Teams: %{y}<extra></extra>",
))
fig5.add_trace(go.Scatter(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["new_teams"],
    mode="lines+markers",
    name="New Teams (Rookies)",
    marker=dict(color="#27AE60", size=10),
    line=dict(width=2, color="#27AE60"),
    hovertemplate="%{x}<br>Rookies: %{y}<extra></extra>",
))
fig5.update_layout(
    template="plotly_dark", height=350,
    title="Team Participation by Season",
    xaxis_title="Season", yaxis_title="Number of Teams",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig5, use_container_width=True)

# --- Score volatility ---
st.markdown("### 📊 Score Volatility by Season")
fig6 = go.Figure()
fig6.add_trace(go.Bar(
    x=[season_labels.get(s, s) for s in metrics_df["season"]],
    y=metrics_df["std_score"],
    marker=dict(
        color=metrics_df["std_score"],
        colorscale="Reds",
        showscale=False,
    ),
    text=[f"{s:.1f}" for s in metrics_df["std_score"]],
    textposition="outside",
    textfont=dict(color="#f0f0f5"),
    hovertemplate="%{x}<br>Std Dev: %{y:.1f}<extra></extra>",
))
fig6.update_layout(
    template="plotly_dark", height=350,
    title="Score Standard Deviation by Season (higher = more variable outcomes)",
    xaxis_title="Season", yaxis_title="Score Std Dev",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    showlegend=False,
)
st.plotly_chart(fig6, use_container_width=True)

# --- Detail table ---
st.markdown("---")
st.markdown("### 📋 Season Metrics Table")
display_metrics = metrics_df.copy()
for col in ["mean_score", "median_score", "std_score", "close_rate", "upset_rate"]:
    display_metrics[col] = display_metrics[col].round(1)

st.dataframe(
    display_metrics.rename(columns={
        "season": "Season", "matches": "Matches", "events": "Events",
        "teams": "Teams", "new_teams": "Rookies", "regions": "Regions",
        "mean_score": "Mean Score", "median_score": "Median", "std_score": "Std Dev",
        "max_score": "Max", "close_rate": "Close %", "upset_rate": "Upset %",
        "playoff_pct": "Playoff %",
    }),
    use_container_width=True, hide_index=True,
    column_config={
        "Close %": st.column_config.NumberColumn(format="%.1f%%"),
        "Upset %": st.column_config.NumberColumn(format="%.1f%%"),
        "Mean Score": st.column_config.NumberColumn(format="%.1f"),
        "Median": st.column_config.NumberColumn(format="%.1f"),
        "Std Dev": st.column_config.NumberColumn(format="%.1f"),
    },
)
