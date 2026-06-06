import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Team Comparison", page_icon="📊", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("📊 Team Comparison", "Compare up to 4 teams side-by-side with radar charts on OPR, ELO, Win Rate, and Composite Score.")

# Compute composite scores (z-score within full dataset)
team_stats = {}
for tn in sorted(teams["team_number"].unique()):
    opr = opr_lookup.get(tn, 0)
    wr = wr_lookup.get(tn, 0.5)
    elo = elo_lookup.get(tn, 1500) if elo_lookup else 1500
    team_stats[tn] = {"opr": opr, "elo": elo, "win_rate": wr}

stats_df = pd.DataFrame(team_stats).T
# Normalize to 0-1 for radar
for col in ["opr", "elo", "win_rate"]:
    mn, mx = stats_df[col].min(), stats_df[col].max()
    rng = max(mx - mn, 1e-6)
    stats_df[f"{col}_norm"] = (stats_df[col] - mn) / rng
# Composite = average of normalized metrics
stats_df["composite_norm"] = (stats_df["opr_norm"] + stats_df["elo_norm"] + stats_df["win_rate_norm"]) / 3
stats_df["composite"] = stats_df["composite_norm"] * 100  # scale to 0-100 for display

# Team selection
team_list = sorted(teams["team_number"].unique())
n_teams = st.slider("Number of teams to compare", 2, 4, 2)
if n_teams >= 4:
    st.warning("Maximum 4 teams for a readable radar chart.", icon="⚠️")
    n_teams = 4

selected_teams = []
cols = st.columns(n_teams)
for i, col in enumerate(cols):
    with col:
        idx = i if i < len(team_list) else 0
        tn = st.selectbox(f"Team {i+1}", team_list, key=f"tc_{i}", index=idx)
        if tn not in selected_teams:
            selected_teams.append(tn)

selected_teams = [t for t in selected_teams if t in team_list]

if len(selected_teams) >= 2:
    # Remove duplicates while preserving order
    seen = set()
    selected_teams = [t for t in selected_teams if not (t in seen or seen.add(t))]
    
    # Radar chart
    categories = ["OPR", "ELO", "Win Rate", "Composite"]
    team_colors = ["#E74C3C", "#3498DB", "#F39C12", "#27AE60"]
    
    fig = go.Figure()
    rgb_map = [(231, 76, 60), (52, 152, 219), (243, 156, 18), (39, 174, 96)]
    for i, tn in enumerate(selected_teams):
        row = stats_df.loc[tn]
        vals = [row["opr_norm"], row["elo_norm"], row["win_rate_norm"], row["composite_norm"]]
        vals.append(vals[0])  # close the polygon
        cats = categories + [categories[0]]
        name = teams[teams["team_number"] == tn]["team_name"].iloc[0] if len(teams[teams["team_number"] == tn]) > 0 else f"Team {tn}"
        r, g, b = rgb_map[i % len(rgb_map)]
        fig.add_trace(go.Scatterpolar(
            r=vals, theta=cats,
            name=f"{tn} — {name}",
            fill="toself",
            fillcolor=f"rgba({r},{g},{b},0.25)",
            line=dict(color=team_colors[i % len(team_colors)], width=2),
            opacity=0.7,
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(range=[0, 1.05], gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color="#a0a0b5")),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.1)", tickfont=dict(color="#f0f0f5", size=13)),
            bgcolor="rgba(0,0,0,0)",
        ),
        template="plotly_dark",
        height=550,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5, font=dict(color="#f0f0f5")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Side-by-side stat cards
    st.markdown("---")
    st.markdown("### 📋 Stat Comparison")
    st_cols = st.columns(len(selected_teams))
    for i, tn in enumerate(selected_teams):
        with st_cols[i]:
            row = stats_df.loc[tn]
            name = teams[teams["team_number"] == tn]["team_name"].iloc[0] if len(teams[teams["team_number"] == tn]) > 0 else f"Team {tn}"
            st.markdown(stat_card_html(f"🤖", f"Team {tn}", name, ["accent-red","accent-blue","accent-orange","accent-green"][i]), unsafe_allow_html=True)
            st.metric("OPR", f"{row['opr']:.1f}")
            st.metric("ELO", f"{row['elo']:.0f}")
            st.metric("Win Rate", f"{row['win_rate']*100:.1f}%")
            st.metric("Composite", f"{row['composite']:.1f}")
    
    # Bar chart comparison for raw metrics
    st.markdown("---")
    st.markdown("### 📊 Raw Metric Comparison")
    metric_tabs = st.tabs(["OPR", "ELO", "Win Rate", "Composite"])
    for tab, metric, fmt in zip(metric_tabs, ["opr", "elo", "win_rate", "composite"], [".1f", ".0f", ".0%", ".1f"]):
        with tab:
            fig2 = go.Figure(data=[go.Bar(
                x=[f"Team {tn}" for tn in selected_teams],
                y=[stats_df.loc[tn, metric] for tn in selected_teams],
                marker_color=team_colors[:len(selected_teams)],
                text=[f"{stats_df.loc[tn, metric]:{fmt}}" for tn in selected_teams],
                textposition="outside",
                textfont=dict(color="#f0f0f5"),
            )])
            fig2.update_layout(
                template="plotly_dark", height=350,
                showlegend=False,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#f0f0f5"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            )
            st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("Select at least 2 teams to compare them side-by-side.")
