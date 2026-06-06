import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Team Clustering", page_icon="🧬", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🧬 Team Clustering", "K-Means clustering of teams into competitive tiers based on OPR, ELO, and Win Rate.")

# Build feature matrix
feature_rows = []
for tn in opr_lookup:
    if opr_lookup.get(tn, 0) <= 0:
        continue
    name = teams[teams["team_number"] == tn]["team_name"].iloc[0] if len(teams[teams["team_number"] == tn]) > 0 else f"Team {tn}"
    feature_rows.append({
        "team_number": tn, "name": name,
        "opr": opr_lookup.get(tn, 0),
        "elo": elo_lookup.get(tn, 1500) if elo_lookup else 1500,
        "win_rate": wr_lookup.get(tn, 0.5),
    })

df = pd.DataFrame(feature_rows)

# Number of clusters
n_clusters = st.slider("Number of tiers", 3, 8, 5, key="n_clusters")
features = ["opr", "elo", "win_rate"]
X = df[features].values

# Standardize
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# KMeans
kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
df["cluster"] = kmeans.fit_predict(X_scaled)

# Map cluster labels to tier names (sorted by average composite score)
df["composite"] = (df["opr"].rank(pct=True) + df["elo"].rank(pct=True) + df["win_rate"].rank(pct=True)) / 3
cluster_avg = df.groupby("cluster")["composite"].mean().sort_values(ascending=False)
tier_labels = {old: ["🏆 Elite", "🥈 Contender", "🥉 Mid-Pack", "4️⃣ Developing", "5️⃣ Rookie"][i] if i < 5 else f"Tier {i+1}" 
               for i, old in enumerate(cluster_avg.index)}
df["tier"] = df["cluster"].map(tier_labels)

# Tier stat cards
st.markdown("### 📊 Tier Distribution")
cols = st.columns(min(n_clusters, 5))
for i, (cluster_id, _) in enumerate(cluster_avg.items()):
    cdf = df[df["cluster"] == cluster_id]
    tier_name = tier_labels[cluster_id]
    accent = ["accent-red", "accent-blue", "accent-orange", "accent-green", "accent-red"][i % 5]
    with cols[i % 5]:
        st.markdown(stat_card_html(
            ["🏆", "🥈", "🥉", "4️⃣", "5️⃣"][i] if i < 5 else "📊",
            str(len(cdf)),
            tier_name,
            accent,
        ), unsafe_allow_html=True)
        st.caption(f"OPR: {cdf['opr'].mean():.1f}  ·  ELO: {cdf['elo'].mean():.0f}")

st.markdown("---")

# 3D scatter plot
st.markdown("### 🗺️ Cluster Visualization")
fig = go.Figure()
tier_colors = ["#E74C3C", "#3498DB", "#F39C12", "#27AE60", "#9B59B6", "#E67E22", "#1ABC9C", "#E91E63"]
for i, cluster_id in enumerate(cluster_avg.index):
    cdf = df[df["cluster"] == cluster_id]
    fig.add_trace(go.Scatter3d(
        x=cdf["opr"], y=cdf["elo"], z=cdf["win_rate"],
        mode="markers",
        name=tier_labels[cluster_id],
        marker=dict(size=5, color=tier_colors[i % len(tier_colors)], opacity=0.7),
        text=[f"Team {r['team_number']}: {r['name']}<br>OPR: {r['opr']:.1f}<br>ELO: {r['elo']:.0f}<br>WR: {r['win_rate']*100:.1f}%" for _, r in cdf.iterrows()],
        hoverinfo="text",
    ))

fig.update_layout(
    scene=dict(
        xaxis_title="OPR", yaxis_title="ELO", zaxis_title="Win Rate",
        xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        zaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
        bgcolor="rgba(0,0,0,0)",
    ),
    template="plotly_dark", height=600,
    paper_bgcolor="rgba(0,0,0,0)",
    legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(color="#f0f0f5")),
)
st.plotly_chart(fig, use_container_width=True)

# Per-tier tables
st.markdown("---")
st.markdown("### 📋 Team Tiers")
selected_tier = st.selectbox("Select tier to explore", list(tier_labels.values()), key="tier_select")

tier_df = df[df["tier"] == selected_tier].nlargest(30, "composite")
tier_display = tier_df[["team_number", "name", "opr", "elo", "win_rate"]].copy()
tier_display["opr"] = tier_display["opr"].round(1)
tier_display["elo"] = tier_display["elo"].round(0).astype(int)
tier_display["win_rate"] = (tier_display["win_rate"] * 100).round(1)

st.dataframe(
    tier_display.rename(columns={"team_number": "Team", "name": "Name", "opr": "OPR", "elo": "ELO", "win_rate": "Win %"}),
    use_container_width=True, hide_index=True,
    column_config={
        "OPR": st.column_config.NumberColumn(format="%.1f"),
        "ELO": st.column_config.NumberColumn(format="%d"),
        "Win %": st.column_config.NumberColumn(format="%.1f%%"),
    },
)

# Silhouette-like summary
st.markdown("---")
st.markdown("### 📊 Cluster Summary")
summary_rows = []
for cluster_id in sorted(cluster_avg.index):
    cdf = df[df["cluster"] == cluster_id]
    summary_rows.append({
        "Tier": tier_labels[cluster_id],
        "Teams": len(cdf),
        "Avg OPR": round(cdf["opr"].mean(), 1),
        "Avg ELO": round(cdf["elo"].mean(), 0),
        "Avg Win Rate": round(cdf["win_rate"].mean() * 100, 1),
        "Top Team": f"#{int(cdf.loc[cdf['composite'].idxmax(), 'team_number'])}",
    })
summary_df = pd.DataFrame(summary_rows)
st.dataframe(summary_df, use_container_width=True, hide_index=True,
    column_config={
        "Avg OPR": st.column_config.NumberColumn(format="%.1f"),
        "Avg ELO": st.column_config.NumberColumn(format="%.0f"),
        "Avg Win Rate": st.column_config.NumberColumn(format="%.1f%%"),
    },
)
