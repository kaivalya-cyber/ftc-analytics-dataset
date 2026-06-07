import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Regional Analysis", page_icon="🌎", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🌎 Regional Analysis", "Compare FTC regions — match volume, team density, scoring, and competitive balance by region.")

# --- Region metrics ---
region_data = []
for region in sorted(matches["region"].unique()):
    rm = matches[matches["region"] == region]
    n_matches = len(rm)
    n_events = rm["event_key"].nunique()
    avg_score = rm[["red_score", "blue_score"]].values.mean()
    median_score = np.median(rm[["red_score", "blue_score"]].values.flatten())
    avg_margin = rm["score_diff"].abs().mean()
    close_rate = (rm["score_diff"].abs() <= 15).mean() * 100

    # Team counts
    region_teams = set()
    for col in ["red_team_1", "red_team_2", "blue_team_1", "blue_team_2"]:
        region_teams.update(rm[col].dropna().astype(int).unique())
    n_teams = len(region_teams)

    # Avg OPR of teams in region
    region_oprs = [opr_lookup.get(t, 0) for t in region_teams]
    avg_opr = np.mean(region_oprs) if region_oprs else 0
    top_opr = max(region_oprs) if region_oprs else 0

    # Avg ELO
    region_elos = [elo_lookup.get(t, 1500) if elo_lookup else 1500 for t in region_teams]
    avg_elo = np.mean(region_elos) if region_elos else 1500

    # Seasons covered
    seasons = sorted(rm["season"].unique())
    region_data.append({
        "region": region, "matches": n_matches, "events": n_events, "teams": n_teams,
        "avg_score": avg_score, "median_score": median_score, "avg_margin": avg_margin,
        "close_rate": close_rate, "avg_opr": avg_opr, "top_opr": top_opr,
        "avg_elo": avg_elo,
    })

region_df = pd.DataFrame(region_data).sort_values("matches", ascending=False)

# --- Summary cards ---
st.markdown("### 📊 Regional Overview")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_card_html("🌎", str(len(region_df)), "Regions", "accent-red"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card_html("📍", str(region_df["events"].sum()), "Total Events", "accent-blue"), unsafe_allow_html=True)
with c3:
    top_region = region_df.iloc[0]
    st.markdown(stat_card_html("🏆", top_region["region"], "Most Matches", "accent-orange"), unsafe_allow_html=True)
with c4:
    st.markdown(stat_card_html("🤖", str(region_df["teams"].sum()), "Unique Teams", "accent-green"), unsafe_allow_html=True)

st.markdown("---")

# --- Bar chart: Matches by Region ---
st.markdown("### 📊 Matches by Region")
fig1 = go.Figure(data=[go.Bar(
    x=region_df["region"],
    y=region_df["matches"],
    marker_color=["#E74C3C", "#3498DB", "#F39C12", "#27AE60", "#9B59B6", "#1ABC9C", "#E67E22", "#2ECC71", "#E74C3C", "#3498DB"][:len(region_df)],
    text=region_df["matches"],
    textposition="outside",
    textfont=dict(color="#f0f0f5"),
    hovertemplate="<b>%{x}</b><br>Matches: %{y}<br>Events: %{customdata[0]}<br>Teams: %{customdata[1]}<extra></extra>",
    customdata=list(zip(region_df["events"], region_df["teams"])),
)])
fig1.update_layout(
    template="plotly_dark", height=400,
    xaxis_title="Region", yaxis_title="Number of Matches",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    showlegend=False,
)
st.plotly_chart(fig1, use_container_width=True)

# --- Scoring & Competitiveness ---
st.markdown("### 🎯 Regional Scoring Profile")
col_l, col_r = st.columns(2)
with col_l:
    # Avg Score by Region
    fig2 = go.Figure(data=[go.Bar(
        x=region_df["region"],
        y=region_df["avg_score"],
        marker=dict(
            color=region_df["avg_score"],
            colorscale="RdBu",
            showscale=False,
        ),
        text=[f"{s:.0f}" for s in region_df["avg_score"]],
        textposition="outside",
        textfont=dict(color="#f0f0f5"),
        hovertemplate="<b>%{x}</b><br>Avg Score: %{y:.1f}<extra></extra>",
    )])
    fig2.update_layout(
        template="plotly_dark", height=350,
        title="Average Match Score by Region",
        xaxis_title="Region", yaxis_title="Avg Score",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)
with col_r:
    # Close Match Rate
    fig3 = go.Figure(data=[go.Bar(
        x=region_df["region"],
        y=region_df["close_rate"],
        marker=dict(
            color=region_df["close_rate"],
            colorscale="Greens",
            showscale=False,
        ),
        text=[f"{c:.0f}%" for c in region_df["close_rate"]],
        textposition="outside",
        textfont=dict(color="#f0f0f5"),
        hovertemplate="<b>%{x}</b><br>Close Matches: %{y:.1f}%<extra></extra>",
    )])
    fig3.update_layout(
        template="plotly_dark", height=350,
        title="Close Match Rate (margin ≤ 15 pts)",
        xaxis_title="Region", yaxis_title="Close Match %",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig3, use_container_width=True)

# --- Team Performance by Region ---
st.markdown("### 🤖 Team Performance by Region")
col_a, col_b = st.columns(2)
with col_a:
    fig4 = go.Figure(data=[go.Bar(
        x=region_df["region"],
        y=region_df["avg_opr"],
        marker=dict(
            color=region_df["avg_opr"],
            colorscale="Blues",
            showscale=False,
        ),
        text=[f"{o:.1f}" for o in region_df["avg_opr"]],
        textposition="outside",
        textfont=dict(color="#f0f0f5"),
        hovertemplate="<b>%{x}</b><br>Avg OPR: %{y:.1f}<extra></extra>",
    )])
    fig4.update_layout(
        template="plotly_dark", height=350,
        title="Average OPR by Region",
        xaxis_title="Region", yaxis_title="Avg OPR",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig4, use_container_width=True)
with col_b:
    fig5 = go.Figure(data=[go.Bar(
        x=region_df["region"],
        y=region_df["avg_elo"],
        marker=dict(
            color=region_df["avg_elo"],
            colorscale="Purples",
            showscale=False,
        ),
        text=[f"{e:.0f}" for e in region_df["avg_elo"]],
        textposition="outside",
        textfont=dict(color="#f0f0f5"),
        hovertemplate="<b>%{x}</b><br>Avg ELO: %{y:.0f}<extra></extra>",
    )])
    fig5.update_layout(
        template="plotly_dark", height=350,
        title="Average ELO by Region",
        xaxis_title="Region", yaxis_title="Avg ELO",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        showlegend=False,
    )
    st.plotly_chart(fig5, use_container_width=True)

# --- Region Detail Table ---
st.markdown("### 📋 Region Detail Table")
display_df = region_df.copy()
display_df["avg_score"] = display_df["avg_score"].round(1)
display_df["avg_margin"] = display_df["avg_margin"].round(1)
display_df["close_rate"] = display_df["close_rate"].round(1)
display_df["avg_opr"] = display_df["avg_opr"].round(1)
display_df["avg_elo"] = display_df["avg_elo"].round(0).astype(int)

st.dataframe(
    display_df[["region", "matches", "events", "teams", "avg_score", "avg_margin", "close_rate", "avg_opr", "avg_elo"]].rename(
        columns={
            "region": "Region", "matches": "Matches", "events": "Events", "teams": "Teams",
            "avg_score": "Avg Score", "avg_margin": "Avg Margin",
            "close_rate": "Close %", "avg_opr": "Avg OPR", "avg_elo": "Avg ELO",
        }
    ),
    use_container_width=True, hide_index=True,
    column_config={
        "Close %": st.column_config.NumberColumn(format="%.1f%%"),
        "Avg Score": st.column_config.NumberColumn(format="%.1f"),
        "Avg Margin": st.column_config.NumberColumn(format="%.1f"),
        "Avg OPR": st.column_config.NumberColumn(format="%.1f"),
    },
)

# --- Season filter for drill-down ---
st.markdown("---")
st.markdown("### 🔍 Drill Down by Season")
selected_region = st.selectbox("Select Region", sorted(matches["region"].unique()))
season_filter = st.selectbox("Season", ["All"] + [season_labels.get(s, s) for s in sorted(matches["season"].unique())], index=0)

if selected_region:
    drill = matches[matches["region"] == selected_region]
    if season_filter != "All":
        sel_season = [k for k, v in season_labels.items() if v == season_filter][0] if season_filter in season_labels.values() else season_filter
        drill = drill[drill["season"] == sel_season]

    if len(drill) > 0:
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            st.markdown(stat_card_html("📊", str(len(drill)), "Matches", "accent-red"), unsafe_allow_html=True)
        with d2:
            st.markdown(stat_card_html("📅", str(drill["event_key"].nunique()), "Events", "accent-blue"), unsafe_allow_html=True)
        with d3:
            st.markdown(stat_card_html("🎯", f"{drill[['red_score','blue_score']].values.mean():.1f}", "Avg Score", "accent-orange"), unsafe_allow_html=True)
        with d4:
            close_pct = (drill["score_diff"].abs() <= 15).mean() * 100
            st.markdown(stat_card_html("⚡", f"{close_pct:.0f}%", "Close Matches", "accent-green"), unsafe_allow_html=True)

        # Score distribution for this region
        all_scores = list(drill["red_score"]) + list(drill["blue_score"])
        fig6 = go.Figure(data=[go.Histogram(
            x=all_scores, nbinsx=25,
            marker_color="#E74C3C", opacity=0.75,
            hovertemplate="Score: %{x}<br>Count: %{y}<extra></extra>",
        )])
        fig6.update_layout(
            template="plotly_dark", height=300,
            title=f"Score Distribution — {selected_region}",
            xaxis_title="Score", yaxis_title="Frequency",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f0f0f5"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            bargap=0.05,
        )
        st.plotly_chart(fig6, use_container_width=True)
    else:
        st.info("No matches found for this region/season combination.")
