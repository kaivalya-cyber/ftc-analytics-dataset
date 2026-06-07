import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Penalty Analysis", page_icon="🚩", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🚩 Penalty Analysis", "Explore penalty contributions — which teams benefit or suffer most from penalties, and how penalties impact match outcomes.")

# --- Compute penalty contribution per team ---
# NP-OPR (Non-Penalty OPR) vs OPR: difference = penalty contribution
penalty_data = []
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    opr = row["opr"] if not pd.isna(row["opr"]) else 0
    np_opr = row["np_opr"] if not pd.isna(row["np_opr"]) else 0
    penalty_contrib = opr - np_opr
    penalty_data.append({
        "team_number": tn,
        "event_key": row["event_key"],
        "season": row["season"],
        "opr": opr,
        "np_opr": np_opr,
        "penalty_contrib": penalty_contrib,
    })

penalty_df = pd.DataFrame(penalty_data)

# Aggregate per team
team_penalty = penalty_df.groupby("team_number").agg(
    avg_opr=("opr", "mean"),
    avg_np_opr=("np_opr", "mean"),
    avg_penalty=("penalty_contrib", "mean"),
    total_penalty=("penalty_contrib", "sum"),
    events=("event_key", "count"),
).reset_index()

team_penalty["penalty_pct"] = team_penalty["avg_penalty"] / team_penalty["avg_opr"].replace(0, np.nan) * 100

# --- Summary cards ---
total_teams_with_penalty = len(team_penalty[team_penalty["avg_penalty"].abs() > 0.01])
net_positive = (team_penalty["avg_penalty"] > 0.01).sum()
net_negative = (team_penalty["avg_penalty"] < -0.01).sum()
median_penalty = team_penalty["avg_penalty"].median()

st.markdown("### 📊 Penalty Overview")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_card_html("🚩", str(total_teams_with_penalty), "Teams w/ Penalty Data", "accent-red"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card_html("📈", str(net_positive), "Net Positive (benefit)", "accent-blue"), unsafe_allow_html=True)
with c3:
    st.markdown(stat_card_html("📉", str(net_negative), "Net Negative (suffer)", "accent-orange"), unsafe_allow_html=True)
with c4:
    st.markdown(stat_card_html("🎯", f"{median_penalty:.2f}", "Median Penalty OPR", "accent-green"), unsafe_allow_html=True)

st.markdown("---")

# --- Top teams by penalty contribution ---
col_a, col_b = st.columns(2)

with col_a:
    st.markdown("### 🟢 Top 15 Teams — Most Penalty-Aided")
    top_positive = team_penalty.nlargest(15, "avg_penalty")
    pos_display = top_positive[["team_number", "avg_opr", "avg_np_opr", "avg_penalty", "penalty_pct", "events"]].copy()
    pos_display["avg_opr"] = pos_display["avg_opr"].round(1)
    pos_display["avg_np_opr"] = pos_display["avg_np_opr"].round(1)
    pos_display["avg_penalty"] = pos_display["avg_penalty"].round(2)
    pos_display["penalty_pct"] = pos_display["penalty_pct"].round(1)
    st.dataframe(
        pos_display.rename(columns={
            "team_number": "Team", "avg_opr": "OPR", "avg_np_opr": "NP-OPR",
            "avg_penalty": "Penalty OPR", "penalty_pct": "Penalty %", "events": "Events",
        }),
        use_container_width=True, hide_index=True,
        column_config={
            "Penalty %": st.column_config.NumberColumn(format="%.1f%%"),
            "OPR": st.column_config.NumberColumn(format="%.1f"),
            "NP-OPR": st.column_config.NumberColumn(format="%.1f"),
            "Penalty OPR": st.column_config.NumberColumn(format="%.2f"),
        },
    )

with col_b:
    st.markdown("### 🔴 Top 15 Teams — Most Penalty-Hurt")
    top_negative = team_penalty.nsmallest(15, "avg_penalty")
    neg_display = top_negative[["team_number", "avg_opr", "avg_np_opr", "avg_penalty", "penalty_pct", "events"]].copy()
    neg_display["avg_opr"] = neg_display["avg_opr"].round(1)
    neg_display["avg_np_opr"] = neg_display["avg_np_opr"].round(1)
    neg_display["avg_penalty"] = neg_display["avg_penalty"].round(2)
    neg_display["penalty_pct"] = neg_display["penalty_pct"].round(1)
    st.dataframe(
        neg_display.rename(columns={
            "team_number": "Team", "avg_opr": "OPR", "avg_np_opr": "NP-OPR",
            "avg_penalty": "Penalty OPR", "penalty_pct": "Penalty %", "events": "Events",
        }),
        use_container_width=True, hide_index=True,
        column_config={
            "Penalty %": st.column_config.NumberColumn(format="%.1f%%"),
            "OPR": st.column_config.NumberColumn(format="%.1f"),
            "NP-OPR": st.column_config.NumberColumn(format="%.1f"),
            "Penalty OPR": st.column_config.NumberColumn(format="%.2f"),
        },
    )

# --- Penalty distribution chart ---
st.markdown("---")
st.markdown("### 📊 Penalty Contribution Distribution")
st.caption("Positive = team's OPR is higher with penalties included (benefits from penalties). Negative = team's OPR drops without penalties (hurt by penalties).")

fig1 = go.Figure()
fig1.add_trace(go.Histogram(
    x=team_penalty["avg_penalty"],
    nbinsx=50,
    marker_color="#E74C3C",
    opacity=0.75,
    hovertemplate="Penalty OPR: %{x:.2f}<br>Teams: %{y}<extra></extra>",
    name="All Teams",
))
fig1.add_vline(x=0, line_dash="dash", line_color="#F39C12", line_width=2)
fig1.update_layout(
    template="plotly_dark", height=350,
    title="Penalty Contribution (OPR − NP-OPR) per Team",
    xaxis_title="Penalty OPR Contribution",
    yaxis_title="Number of Teams",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    bargap=0.05,
)
st.plotly_chart(fig1, use_container_width=True)

# --- Penalty by season ---
st.markdown("### 📅 Penalty Trends by Season")
season_penalty = penalty_df.groupby("season").agg(
    mean_penalty=("penalty_contrib", "mean"),
    median_penalty=("penalty_contrib", "median"),
    teams=("team_number", "nunique"),
).reset_index().sort_values("season")

fig2 = go.Figure()
fig2.add_trace(go.Bar(
    x=[season_labels.get(s, s) for s in season_penalty["season"]],
    y=season_penalty["mean_penalty"],
    marker_color="#3498DB",
    name="Mean Penalty OPR",
    hovertemplate="%{x}<br>Mean Penalty: %{y:.3f}<extra></extra>",
))
fig2.add_trace(go.Scatter(
    x=[season_labels.get(s, s) for s in season_penalty["season"]],
    y=season_penalty["median_penalty"],
    mode="lines+markers",
    marker=dict(color="#F39C12", size=8),
    line=dict(width=2, color="#F39C12"),
    name="Median Penalty OPR",
    hovertemplate="%{x}<br>Median Penalty: %{y:.3f}<extra></extra>",
))
fig2.update_layout(
    template="plotly_dark", height=350,
    title="Average Penalty Contribution by Season",
    xaxis_title="Season",
    yaxis_title="Penalty OPR Contribution",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig2, use_container_width=True)

# --- Penalty impact on win rate ---
st.markdown("### 🎯 Penalty Impact on Performance")
st.caption("Teams are grouped by penalty contribution percentiles. Higher penalty contribution often correlates with better performance.")

team_penalty["penalty_tier"] = pd.qcut(team_penalty["avg_penalty"], q=5, labels=["Very Low", "Low", "Medium", "High", "Very High"])
tier_wr = []
for tier in ["Very Low", "Low", "Medium", "High", "Very High"]:
    tier_teams = team_penalty[team_penalty["penalty_tier"] == tier]["team_number"]
    tier_wrs = [wr_lookup.get(t, 0.5) for t in tier_teams]
    tier_wr.append({
        "Penalty Tier": tier,
        "Teams": len(tier_teams),
        "Avg Win Rate": np.mean(tier_wrs) * 100,
        "Avg OPR": team_penalty[team_penalty["penalty_tier"] == tier]["avg_opr"].mean(),
        "Avg Penalty OPR": team_penalty[team_penalty["penalty_tier"] == tier]["avg_penalty"].mean(),
    })

tier_df = pd.DataFrame(tier_wr)

fig3 = go.Figure()
fig3.add_trace(go.Bar(
    x=tier_df["Penalty Tier"],
    y=tier_df["Avg Win Rate"],
    marker=dict(
        color=tier_df["Avg Penalty OPR"],
        colorscale="RdBu",
        showscale=True,
        colorbar=dict(title="Avg Penalty OPR"),
    ),
    text=[f"{w:.1f}%" for w in tier_df["Avg Win Rate"]],
    textposition="outside",
    textfont=dict(color="#f0f0f5"),
    hovertemplate="<b>%{x}</b><br>Win Rate: %{y:.1f}%<br>Teams: %{customdata[0]}<br>Avg OPR: %{customdata[1]:.1f}<extra></extra>",
    customdata=list(zip(tier_df["Teams"], tier_df["Avg OPR"])),
))
fig3.update_layout(
    template="plotly_dark", height=350,
    title="Win Rate by Penalty Contribution Tier",
    xaxis_title="Penalty Contribution Tier",
    yaxis_title="Avg Win Rate (%)",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    showlegend=False,
)
st.plotly_chart(fig3, use_container_width=True)
