#!/usr/bin/env python3
"""
generate_readme_images.py — Generate static chart images for the README.
Creates PNG files in images/ that represent key dashboard visualizations.
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"
IMAGES_DIR = Path(__file__).parent.parent / "images"
IMAGES_DIR.mkdir(exist_ok=True)

# Load data
matches = pd.read_csv(DATA_DIR / "matches.csv")
teams = pd.read_csv(DATA_DIR / "teams.csv")
team_events = pd.read_csv(DATA_DIR / "team_events.csv")

elo_df = None
current_elo = None
if (DATA_DIR / "team_elo.csv").exists():
    elo_df = pd.read_csv(DATA_DIR / "team_elo.csv")
if (DATA_DIR / "current_elo.csv").exists():
    current_elo = pd.read_csv(DATA_DIR / "current_elo.csv")

# Build lookups
opr_lookup, opr_counts = {}, {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    opr = row["opr"] if not pd.isna(row["opr"]) else 0
    opr_lookup[tn] = opr_lookup.get(tn, 0.0) + opr
    opr_counts[tn] = opr_counts.get(tn, 0) + 1
for tn in opr_lookup:
    opr_lookup[tn] /= opr_counts[tn]

wr_lookup, wr_counts = {}, {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    w, l, t = row["wins"], row["losses"], row["ties"]
    wr = w / (w + l + t) if (w + l + t) > 0 else 0.5
    wr_lookup[tn] = wr_lookup.get(tn, 0.0) + wr
    wr_counts[tn] = wr_counts.get(tn, 0) + 1
for tn in wr_lookup:
    wr_lookup[tn] /= wr_counts[tn]

elo_lookup = {}
if current_elo is not None:
    for _, row in current_elo.iterrows():
        elo_lookup[int(row["team_number"])] = row["current_elo"]

season_labels = {
    "1819": "Rover Ruckus", "1920": "Skystone", "2021": "Ultimate Goal",
    "2122": "Freight Frenzy", "2223": "Power Play", "2324": "Centerstage",
}

plotly_template = "plotly_dark"
plotly_bg = dict(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#f0f0f5"))
plotly_grid = dict(gridcolor="rgba(255,255,255,0.08)")

def save_fig(fig, name):
    path = IMAGES_DIR / name
    fig.write_image(str(path), width=1200, height=600, scale=2)
    print(f"  ✓ Saved {name}")

# ── 1. Matches per Season bar chart ──
print("1. Matches per Season")
season_counts = matches["season"].value_counts().sort_index()
season_labels_list = [season_labels.get(str(s), str(s)) for s in season_counts.index]
fig = go.Figure(data=[go.Bar(
    x=season_labels_list,
    y=season_counts.values,
    marker_color=["#E74C3C", "#3498DB", "#F39C12", "#27AE60", "#9B59B6", "#E67E22"],
    text=season_counts.values,
    textposition="outside",
    textfont=dict(color="#f0f0f5"),
)])
fig.update_layout(title="Matches per Season", template=plotly_template, **plotly_bg,
    xaxis=dict(**plotly_grid), yaxis=dict(**plotly_grid, title="Matches"))
save_fig(fig, "matches_per_season.png")

# ── 2. Team Landscape scatter (OPR vs ELO) ──
print("2. Team Landscape")
scatter_rows = []
for tn in opr_lookup:
    opr = opr_lookup.get(tn, 0)
    wr = wr_lookup.get(tn, 0.5)
    elo = elo_lookup.get(tn, 1500) if elo_lookup else 1500
    tm = matches[(matches["red_team_1"] == tn) | (matches["red_team_2"] == tn) | (matches["blue_team_1"] == tn) | (matches["blue_team_2"] == tn)]
    primary_season = tm["season"].mode().iloc[0] if len(tm) > 0 else "unknown"
    scatter_rows.append({"team_number": tn, "opr": opr, "elo": elo, "win_rate": wr, "season": primary_season, "matches": len(tm)})

df_land = pd.DataFrame(scatter_rows)
df_land = df_land[df_land["opr"] > 0]
season_colors = {"1819": "#E74C3C", "1920": "#3498DB", "2021": "#F39C12", "2122": "#27AE60", "2223": "#9B59B6", "2324": "#E67E22"}
fig = go.Figure()
for season in sorted(df_land["season"].unique()):
    season_str = str(season)
    sd = df_land[df_land["season"] == season]
    if len(sd) == 0: continue
    fig.add_trace(go.Scatter(x=sd["opr"], y=sd["elo"], mode="markers",
        name=season_labels.get(season_str, season_str),
        marker=dict(size=np.clip(sd["win_rate"] * 35 + 5, 5, 30), color=season_colors.get(season_str, "#888"), opacity=0.7),
        text=[f"Team {r['team_number']}<br>OPR: {r['opr']:.1f}<br>ELO: {r['elo']:.0f}<br>WR: {r['win_rate']*100:.1f}%" for _, r in sd.iterrows()],
        hoverinfo="text"))
fig.update_layout(title="Team Landscape: OPR vs ELO", xaxis_title="OPR", yaxis_title="ELO",
    template=plotly_template, height=550, **plotly_bg,
    xaxis=dict(**plotly_grid, zerolinecolor="rgba(255,255,255,0.15)"),
    yaxis=dict(**plotly_grid, zerolinecolor="rgba(255,255,255,0.15)"),
    legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
save_fig(fig, "team_landscape.png")

# ── 3. OPR Distribution ──
print("3. OPR Distribution")
opr_vals = [v for v in opr_lookup.values() if v > 0]
fig = go.Figure(data=[go.Histogram(x=opr_vals, nbinsx=50, marker_color="#E74C3C", opacity=0.8)])
fig.update_layout(title="OPR Distribution Across All Teams", xaxis_title="OPR", yaxis_title="Teams",
    template=plotly_template, **plotly_bg, xaxis=dict(**plotly_grid), yaxis=dict(**plotly_grid))
save_fig(fig, "opr_distribution.png")

# ── 4. Score Distribution by Season ──
print("4. Score Distribution")
season_scores = []
for season in sorted(matches["season"].unique()):
    season_str = str(season)
    sm = matches[matches["season"] == season]
    season_scores.append(go.Violin(x=[season_labels.get(season_str, season_str)] * len(sm),
        y=sm["red_score"].tolist() + sm["blue_score"].tolist(),
        name=season_labels.get(season_str, season_str), line_color=season_colors.get(season_str, "#888"),
        box_visible=True, meanline_visible=True))
fig = go.Figure(data=season_scores)
fig.update_layout(title="Score Distribution by Season", yaxis_title="Score",
    template=plotly_template, **plotly_bg, xaxis=dict(**plotly_grid), yaxis=dict(**plotly_grid))
save_fig(fig, "score_distribution.png")

# ── 5. ELO History (sample top team) ──
print("5. ELO History")
if elo_df is not None:
    top_teams = current_elo.nlargest(4, "current_elo")["team_number"].tolist() if current_elo is not None else elo_df["team_number"].unique()[:4]
    fig = go.Figure()
    for tn in top_teams:
        telo = elo_df[elo_df["team_number"] == tn].sort_values(["season", "event_key", "match_number"])
        telo = telo.reset_index(drop=True)
        telo["match_idx"] = range(1, len(telo) + 1)
        fig.add_trace(go.Scatter(x=telo["match_idx"], y=telo["elo_after"], mode="lines", name=f"Team {int(tn)}", line=dict(width=2)))
    fig.update_layout(title="ELO Rating Progression (Top 4 Teams)", xaxis_title="Match #", yaxis_title="ELO",
        template=plotly_template, **plotly_bg, xaxis=dict(**plotly_grid), yaxis=dict(**plotly_grid),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5))
    save_fig(fig, "elo_progression.png")

print("\n✅ All images generated in images/")
