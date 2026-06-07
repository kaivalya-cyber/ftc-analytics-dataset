import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Alliance Builder", page_icon="🤝", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

hero_header("🤝 Alliance Builder", "Pick two teams and analyze their alliance synergy — combined strength, complementary skills, and predicted performance.")

# --- Team selection ---
st.markdown("### 🔧 Build Your Alliance")
col1, col2 = st.columns(2)
team_list = sorted(teams["team_number"].unique())
team_name_lookup = dict(zip(teams["team_number"], teams["team_name"]))

with col1:
    t1 = st.selectbox("Team 1 (Captain)", team_list, key="ab_t1", index=0)
with col2:
    t2 = st.selectbox("Team 2 (Partner)", team_list, key="ab_t2", index=min(1, len(team_list)-1))

if t1 == t2:
    st.warning("Select two different teams to form an alliance.")
    st.stop()

# --- Team stats ---
t1_opr = opr_lookup.get(t1, 0)
t2_opr = opr_lookup.get(t2, 0)
t1_elo = elo_lookup.get(t1, 1500) if elo_lookup else 1500
t2_elo = elo_lookup.get(t2, 1500) if elo_lookup else 1500
t1_wr = wr_lookup.get(t1, 0.5)
t2_wr = wr_lookup.get(t2, 0.5)

combined_opr = t1_opr + t2_opr
combined_elo = (t1_elo + t2_elo) / 2

# --- Synergy: historical alliance data ---
alliance_together = matches[
    (((matches["red_team_1"] == t1) & (matches["red_team_2"] == t2)) |
     ((matches["red_team_1"] == t2) & (matches["red_team_2"] == t1)) |
     ((matches["blue_team_1"] == t1) & (matches["blue_team_2"] == t2)) |
     ((matches["blue_team_1"] == t2) & (matches["blue_team_2"] == t1)))
]

together_matches = len(alliance_together)
together_wins = 0
if together_matches > 0:
    for _, row in alliance_together.iterrows():
        is_red = (row["red_team_1"] == t1) or (row["red_team_2"] == t1)
        if (is_red and row["winner"] == "red") or (not is_red and row["winner"] == "blue"):
            together_wins += 1

# --- Alliance strength percentile ---
all_alliances = []
for _, row in matches.iterrows():
    red_opr = opr_lookup.get(row["red_team_1"], 0) + opr_lookup.get(row["red_team_2"], 0)
    blue_opr = opr_lookup.get(row["blue_team_1"], 0) + opr_lookup.get(row["blue_team_2"], 0)
    all_alliances.append(red_opr)
    all_alliances.append(blue_opr)

alliance_percentile = (sum(1 for a in all_alliances if a < combined_opr) / len(all_alliances)) * 100

# --- Team stat cards ---
st.markdown("### 🤖 Alliance Members")
tc1, tc2 = st.columns(2)
with tc1:
    name1 = team_name_lookup.get(t1, f"Team {t1}")
    st.markdown(f"""
    <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:1.2rem; border:1px solid var(--border-subtle);">
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Captain</div>
        <div style="font-size:1.5rem; font-weight:800; color:var(--text-primary); margin:0.2rem 0;">{t1}</div>
        <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.6rem;">{name1[:28]}</div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
            <span class="chip chip-red">OPR {t1_opr:.1f}</span>
            <span class="chip chip-blue">ELO {t1_elo:.0f}</span>
            <span class="chip chip-green">WR {t1_wr:.0%}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
with tc2:
    name2 = team_name_lookup.get(t2, f"Team {t2}")
    st.markdown(f"""
    <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:1.2rem; border:1px solid var(--border-subtle);">
        <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Partner</div>
        <div style="font-size:1.5rem; font-weight:800; color:var(--text-primary); margin:0.2rem 0;">{t2}</div>
        <div style="font-size:0.85rem; color:var(--text-secondary); margin-bottom:0.6rem;">{name2[:28]}</div>
        <div style="display:flex; gap:0.5rem; flex-wrap:wrap;">
            <span class="chip chip-orange">OPR {t2_opr:.1f}</span>
            <span class="chip chip-blue">ELO {t2_elo:.0f}</span>
            <span class="chip chip-green">WR {t2_wr:.0%}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Alliance strength cards ---
st.markdown("---")
st.markdown("### 💪 Alliance Strength")
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(stat_card_html("📊", f"{combined_opr:.1f}", "Combined OPR", "accent-red"), unsafe_allow_html=True)
with c2:
    st.markdown(stat_card_html("🎯", f"{combined_elo:.0f}", "Avg ELO", "accent-blue"), unsafe_allow_html=True)
with c3:
    st.markdown(stat_card_html("🏆", f"{alliance_percentile:.0f}%", "Percentile", "accent-orange"), unsafe_allow_html=True)
with c4:
    synergy_label = "Great" if together_matches > 0 and together_wins / together_matches >= 0.6 else ("New" if together_matches == 0 else "Developing")
    st.markdown(stat_card_html("🤝", synergy_label, "Synergy", "accent-green"), unsafe_allow_html=True)

# --- Historical alliance record ---
if together_matches > 0:
    st.markdown("---")
    st.markdown("### 📜 Historical Alliance Record")
    st.caption(f"Team {t1} and Team {t2} have been on the same alliance **{together_matches}** times.")
    cw1, cw2, cw3 = st.columns(3)
    with cw1:
        st.metric("Together Wins", together_wins)
    with cw2:
        st.metric("Together Losses", together_matches - together_wins)
    with cw3:
        st.metric("Win Rate", f"{together_wins/together_matches*100:.0f}%")

    # Recent alliance matches
    recent_together = alliance_together.sort_values(["season", "match_number"], ascending=False).head(5)
    for _, row in recent_together.iterrows():
        is_red = (row["red_team_1"] == t1) or (row["red_team_2"] == t1)
        alliance_score = row["red_score"] if is_red else row["blue_score"]
        opp_score = row["blue_score"] if is_red else row["red_score"]
        won = (is_red and row["winner"] == "red") or (not is_red and row["winner"] == "blue")
        border = "#27AE60" if won else "#E74C3C"
        st.markdown(f"""
        <div style="background:var(--bg-card); border-radius:var(--radius-sm); padding:0.5rem 0.8rem; border-left:3px solid {border}; margin-bottom:0.3rem; display:flex; justify-content:space-between; align-items:center;">
            <span style="font-size:0.8rem; color:var(--text-secondary);">{season_labels.get(row['season'], row['season'])} · {row['event_name']} · M#{int(row['match_number'])}</span>
            <span style="font-weight:600; font-size:0.85rem; color:var(--text-primary);">{int(alliance_score)} – {int(opp_score)}</span>
            <span style="font-size:0.75rem; font-weight:600; color:{border};">{'WIN' if won else 'LOSS'}</span>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("---")
    st.info(f"Team {t1} and Team {t2} have never been on the same alliance in this dataset. This is a theoretical pairing!")

# --- Complementary strengths ---
st.markdown("---")
st.markdown("### 🧩 Complementary Analysis")

# OPR complementarity: are they both high OPR or balanced?
opr_diff = abs(t1_opr - t2_opr)
opr_balance = 1 - (opr_diff / max(combined_opr, 1))
balance_label = "Very Balanced" if opr_balance > 0.7 else ("Balanced" if opr_balance > 0.4 else "One-Sided")

# Radar-like comparison
categories = ["OPR", "ELO (norm)", "Win Rate"]
max_vals = {"OPR": max(opr_lookup.values()) if opr_lookup else 100, "ELO (norm)": 2000, "Win Rate": 1.0}
t1_vals = [t1_opr / max_vals["OPR"], t1_elo / max_vals["ELO (norm)"], t1_wr / max_vals["Win Rate"]]
t2_vals = [t2_opr / max_vals["OPR"], t2_elo / max_vals["ELO (norm)"], t2_wr / max_vals["Win Rate"]]

coll, colr = st.columns(2)
with coll:
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=t1_vals, theta=categories, fill="toself", name=f"Team {t1}",
        marker_color="#E74C3C", opacity=0.4,
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatterpolar(
        r=t2_vals, theta=categories, fill="toself", name=f"Team {t2}",
        marker_color="#3498DB", opacity=0.4,
        hovertemplate="%{theta}: %{r:.2f}<extra></extra>",
    ))
    fig.update_layout(
        template="plotly_dark", height=380,
        title="Strength Profile Comparison",
        polar=dict(
            radialaxis=dict(range=[0, 1], gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#f0f0f5")),
            angularaxis=dict(gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#f0f0f5")),
            bgcolor="rgba(0,0,0,0)",
        ),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#f0f0f5"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.15),
    )
    st.plotly_chart(fig, use_container_width=True)

with colr:
    st.markdown(f"""
    <div style="background:var(--bg-card); border-radius:var(--radius-lg); padding:1.5rem; border:1px solid var(--border-subtle); height:100%;">
        <div style="font-size:1.2rem; font-weight:700; margin-bottom:1rem; color:var(--text-primary);">📋 Alliance Summary</div>
        <div style="margin-bottom:1rem;">
            <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Balance</div>
            <div style="font-size:1.5rem; font-weight:700; color:var(--text-primary);">{balance_label}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">OPR diff: {opr_diff:.1f}</div>
        </div>
        <div style="margin-bottom:1rem;">
            <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Combined Firepower</div>
            <div style="font-size:1.5rem; font-weight:700; color:var(--text-primary);">{combined_opr:.1f} OPR</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">Stronger than {alliance_percentile:.0f}% of all alliances</div>
        </div>
        <div style="margin-bottom:1rem;">
            <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Expected Match Score</div>
            <div style="font-size:1.5rem; font-weight:700; color:var(--text-primary);">{combined_opr*2:.0f} points</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">Rough estimate: sum OPR × 2</div>
        </div>
        <div>
            <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em;">Experience</div>
            <div style="font-size:1.5rem; font-weight:700; color:var(--text-primary);">{together_matches}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">Matches played together</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Predicted vs top alliance comparison ---
st.markdown("---")
st.markdown("### 🏆 How This Alliance Compares")

# Get top 10 alliances by combined OPR
top_pairs = []
seen = set()
for _, row in matches.iterrows():
    for teams_pair, color in [(("red_team_1", "red_team_2"), "red"), (("blue_team_1", "blue_team_2"), "blue")]:
        a, b = int(row[teams_pair[0]]), int(row[teams_pair[1]])
        key = tuple(sorted([a, b]))
        if key not in seen:
            seen.add(key)
            a_opr = opr_lookup.get(a, 0) + opr_lookup.get(b, 0)
            top_pairs.append({"team_a": a, "team_b": b, "combined_opr": a_opr})
            if len(top_pairs) > 5000:
                break
    if len(top_pairs) > 5000:
        break

top_pairs = sorted(top_pairs, key=lambda x: x["combined_opr"], reverse=True)[:15]

fig2 = go.Figure(data=[go.Bar(
    x=[f"{p['team_a']}+{p['team_b']}" for p in top_pairs],
    y=[p["combined_opr"] for p in top_pairs],
    marker_color=["#E74C3C" if (p["team_a"] == t1 and p["team_b"] == t2) or (p["team_a"] == t2 and p["team_b"] == t1) else "#3498DB" for p in top_pairs],
    text=[f"{p['combined_opr']:.1f}" for p in top_pairs],
    textposition="outside",
    textfont=dict(color="#f0f0f5"),
    hovertemplate="%{x}<br>Combined OPR: %{y:.1f}<extra></extra>",
)])
fig2.add_hline(y=combined_opr, line_dash="dash", line_color="#F39C12", line_width=2, annotation_text=f"Your Alliance ({combined_opr:.1f})")
fig2.update_layout(
    template="plotly_dark", height=400,
    title="Top Alliances by Combined OPR",
    xaxis_title="Alliance Pair",
    yaxis_title="Combined OPR",
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.05)", tickangle=45),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    showlegend=False,
)
st.plotly_chart(fig2, use_container_width=True)
