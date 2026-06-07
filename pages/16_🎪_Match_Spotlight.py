import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Match Spotlight", page_icon="🎪", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

hero_header("🎪 Match Spotlight", "The closest, highest-scoring, and most exciting matches in FTC history.")

# --- Filters ---
season_options = sorted(matches["season"].unique())
col_f1, col_f2, col_f3 = st.columns(3)
with col_f1:
    filter_season = st.selectbox("Season", ["All"] + [season_labels.get(s, s) for s in season_options], index=0)
with col_f2:
    sort_by = st.selectbox("Sort By", ["Closest Margin", "Highest Combined Score", "Biggest Upset (OPR)", "Biggest Upset (ELO)", "Playoff Thrillers"], index=0)
with col_f3:
    top_n = st.slider("Show Top", 5, 30, 15)

# --- Filter matches ---
display = matches.copy()
if filter_season != "All":
    selected_season = [k for k, v in season_labels.items() if v == filter_season][0] if filter_season in season_labels.values() else filter_season
    display = display[display["season"] == selected_season]

# --- Compute match excitement metrics ---
display["combined_score"] = display["red_score"] + display["blue_score"]
display["abs_diff"] = abs(display["score_diff"])

# OPR upset: underdog (lower OPR sum) wins
def compute_opr_favorite(row):
    red_opr = opr_lookup.get(row["red_team_1"], 0) + opr_lookup.get(row["red_team_2"], 0)
    blue_opr = opr_lookup.get(row["blue_team_1"], 0) + opr_lookup.get(row["blue_team_2"], 0)
    return "red" if red_opr > blue_opr else ("blue" if blue_opr > red_opr else "tie")

def compute_elo_favorite(row):
    red_elo = (elo_lookup.get(row["red_team_1"], 1500) + elo_lookup.get(row["red_team_2"], 1500)) / 2
    blue_elo = (elo_lookup.get(row["blue_team_1"], 1500) + elo_lookup.get(row["blue_team_2"], 1500)) / 2
    return "red" if red_elo > blue_elo else ("blue" if blue_elo > red_elo else "tie")

display["opr_fav"] = display.apply(compute_opr_favorite, axis=1)
display["elo_fav"] = display.apply(compute_elo_favorite, axis=1)
display["opr_upset"] = (display["opr_fav"] != display["winner"]) & (display["winner"] != "tie") & (display["opr_fav"] != "tie")
display["elo_upset"] = (display["elo_fav"] != display["winner"]) & (display["winner"] != "tie") & (display["elo_fav"] != "tie")

# OPR upset magnitude
def opr_upset_mag(row):
    red_opr = opr_lookup.get(row["red_team_1"], 0) + opr_lookup.get(row["red_team_2"], 0)
    blue_opr = opr_lookup.get(row["blue_team_1"], 0) + opr_lookup.get(row["blue_team_2"], 0)
    return abs(red_opr - blue_opr)

display["opr_upset_mag"] = display.apply(opr_upset_mag, axis=1)

# --- Sort ---
if sort_by == "Closest Margin":
    spotlight = display[display["abs_diff"] >= 0].nsmallest(top_n, "abs_diff")
elif sort_by == "Highest Combined Score":
    spotlight = display.nlargest(top_n, "combined_score")
elif sort_by == "Biggest Upset (OPR)":
    spotlight = display[display["opr_upset"]].nlargest(top_n, "opr_upset_mag")
elif sort_by == "Biggest Upset (ELO)":
    spotlight = display[display["elo_upset"]].nlargest(top_n, "opr_upset_mag")
elif sort_by == "Playoff Thrillers":
    playoff = display[display["is_playoff"]]
    spotlight = playoff[playoff["abs_diff"] >= 0].nsmallest(top_n, "abs_diff")
else:
    spotlight = display.nsmallest(top_n, "abs_diff")

if len(spotlight) == 0:
    st.info("No matches found with the current filters.")
    st.stop()

# --- Summary stats ---
col_s1, col_s2, col_s3, col_s4 = st.columns(4)
with col_s1:
    st.markdown(stat_card_html("🎪", str(len(spotlight)), "Matches Shown", "accent-red"), unsafe_allow_html=True)
with col_s2:
    st.markdown(stat_card_html("🎯", f"{spotlight['abs_diff'].mean():.1f}", "Avg Margin", "accent-blue"), unsafe_allow_html=True)
with col_s3:
    st.markdown(stat_card_html("📊", f"{spotlight['combined_score'].mean():.0f}", "Avg Combined Score", "accent-orange"), unsafe_allow_html=True)
with col_s4:
    upsets = spotlight["opr_upset"].sum()
    st.markdown(stat_card_html("⚡", str(int(upsets)), "OPR Upsets", "accent-green"), unsafe_allow_html=True)

st.markdown("---")

# --- Match detail cards ---
team_name_lookup = dict(zip(teams["team_number"], teams["team_name"]))

for idx, (_, row) in enumerate(spotlight.iterrows()):
    diff = int(row["score_diff"])
    red_won = row["winner"] == "red"
    blue_won = row["winner"] == "blue"
    is_tie = row["winner"] == "tie"

    # Border accent color
    if is_tie:
        border_color = "#F39C12"
        result_text = "🤝 TIE"
    elif red_won:
        border_color = "#E74C3C"
        result_text = "🔴 Red Wins"
    else:
        border_color = "#3498DB"
        result_text = "🔵 Blue Wins"

    opr_upset = row["opr_upset"]
    elo_upset = row["elo_upset"]
    upset_badges = ""
    if opr_upset:
        upset_badges += '<span class="chip chip-orange" style="margin-left:6px;">⚡ OPR Upset</span>'
    if elo_upset:
        upset_badges += '<span class="chip chip-red" style="margin-left:6px;">🔥 ELO Upset</span>'

    playoff_badge = '<span class="chip chip-red" style="margin-left:6px;">🏆 Playoff</span>' if row["is_playoff"] else '<span class="chip chip-blue" style="margin-left:6px;">📋 Qual</span>'

    st.markdown(f"""
    <div style="background:var(--bg-card); border-radius:var(--radius-lg); padding:1.25rem 1.5rem; border:1px solid {border_color}; border-left:4px solid {border_color}; margin-bottom:0.8rem;">
        <div style="display:flex; align-items:center; justify-content:space-between; margin-bottom:0.6rem;">
            <div>
                <span style="font-size:0.9rem; color:var(--text-secondary);">{season_labels.get(row['season'], row['season'])} · {row['event_name']} · Match #{int(row['match_number'])}</span>
            </div>
            <div style="display:flex; align-items:center; gap:8px;">
                {playoff_badge}
                {upset_badges}
                <span style="font-weight:700; font-size:1.1rem; color:{border_color};">{result_text}</span>
            </div>
        </div>
        <div style="display:flex; gap:1rem; align-items:stretch;">
            <div style="flex:1; background:rgba(231,76,60,0.08); border-radius:var(--radius-md); padding:1rem; text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">Red Alliance</div>
                <div style="font-size:2.2rem; font-weight:800; color:#E74C3C; line-height:1.1;">{int(row['red_score'])}</div>
                <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:0.4rem;">
                    {row['red_team_1']} ({team_name_lookup.get(row['red_team_1'], '?')[:18]})<br>
                    {row['red_team_2']} ({team_name_lookup.get(row['red_team_2'], '?')[:18]})
                </div>
            </div>
            <div style="display:flex; align-items:center; font-size:0.85rem; color:var(--text-secondary); font-weight:600; padding:0 0.5rem;">
                VS
            </div>
            <div style="flex:1; background:rgba(52,152,219,0.08); border-radius:var(--radius-md); padding:1rem; text-align:center;">
                <div style="font-size:0.75rem; color:var(--text-secondary); text-transform:uppercase; letter-spacing:0.05em; margin-bottom:0.3rem;">Blue Alliance</div>
                <div style="font-size:2.2rem; font-weight:800; color:#3498DB; line-height:1.1;">{int(row['blue_score'])}</div>
                <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:0.4rem;">
                    {row['blue_team_1']} ({team_name_lookup.get(row['blue_team_1'], '?')[:18]})<br>
                    {row['blue_team_2']} ({team_name_lookup.get(row['blue_team_2'], '?')[:18]})
                </div>
            </div>
        </div>
        <div style="margin-top:0.6rem; display:flex; gap:0.8rem; flex-wrap:wrap;">
            <span style="font-size:0.78rem; color:var(--text-secondary);">Margin: <b>{abs(diff)}</b> pts</span>
            <span style="font-size:0.78rem; color:var(--text-secondary);">Combined: <b>{int(row['combined_score'])}</b></span>
            <span style="font-size:0.78rem; color:var(--text-secondary);">Match Key: <code style="background:var(--bg-main); padding:2px 6px; border-radius:4px;">{row['match_key']}</code></span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# --- Scatter chart: all matches colored by closeness ---
st.markdown("---")
st.markdown("### 📊 Match Excitement Map")
st.caption("Score differential vs combined score. Closer matches = larger, darker circles.")

chart_data = display.copy()
chart_data["closeness"] = 1 - (chart_data["abs_diff"] / (chart_data["abs_diff"].max() + 1))
chart_data["marker_size"] = np.clip(chart_data["closeness"] * 20 + 4, 4, 22)

fig = go.Figure()
fig.add_trace(go.Scatter(
    x=chart_data["combined_score"],
    y=chart_data["abs_diff"].apply(lambda x: -x),
    mode="markers",
    marker=dict(
        size=chart_data["marker_size"],
        color=chart_data["closeness"],
        colorscale="RdYlGn",
        showscale=True,
        colorbar=dict(title="Closeness", tickformat=".0%"),
        line=dict(width=0.5, color="rgba(255,255,255,0.3)"),
    ),
    text=[f"{season_labels.get(s, s)} · {en} · M#{int(mn)}<br>Red {int(rs)} – Blue {int(bs)} | Margin: {abs(int(d))}" for s, en, mn, rs, bs, d in zip(chart_data["season"], chart_data["event_name"], chart_data["match_number"], chart_data["red_score"], chart_data["blue_score"], chart_data["score_diff"])],
    hoverinfo="text",
    name="Match",
))

fig.update_layout(
    title="All Matches — Closeness to Center Line",
    xaxis_title="Combined Score (higher = more scoring)",
    yaxis_title="Score Differential (− closer to zero = tighter match)",
    template="plotly_dark",
    height=500,
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#f0f0f5"),
    xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
    yaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.3)", zerolinewidth=2),
)
st.plotly_chart(fig, use_container_width=True)
