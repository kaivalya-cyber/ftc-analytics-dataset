import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Match Predictor", page_icon="🎯", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
_, opr_lookup, wr_lookup, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

hero_header("🎯 Match Predictor", "Predict the winner of a theoretical match using OPR, ELO ratings, and historical win rates.")

team_list = sorted(teams["team_number"].unique())
st.markdown("### ⚔️ Select Alliances")
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div style="background:linear-gradient(135deg, rgba(231,76,60,0.08), rgba(231,76,60,0.02)); border:1px solid rgba(231,76,60,0.2); border-radius:12px; padding:1.2rem 1.2rem 0.8rem 1.2rem;"><div style="font-size:1.1rem; font-weight:700; color:#E74C3C; margin-bottom:0.6rem;">🔴 RED ALLIANCE</div>', unsafe_allow_html=True)
    r1 = st.selectbox("Red Team 1", team_list, key="r1", index=0, label_visibility="collapsed")
    r2 = st.selectbox("Red Team 2", team_list, key="r2", index=min(1, len(team_list)-1), label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
with col2:
    st.markdown('<div style="background:linear-gradient(135deg, rgba(52,152,219,0.08), rgba(52,152,219,0.02)); border:1px solid rgba(52,152,219,0.2); border-radius:12px; padding:1.2rem 1.2rem 0.8rem 1.2rem;"><div style="font-size:1.1rem; font-weight:700; color:#3498DB; margin-bottom:0.6rem;">🔵 BLUE ALLIANCE</div>', unsafe_allow_html=True)
    b1 = st.selectbox("Blue Team 1", team_list, key="b1", index=min(2, len(team_list)-1), label_visibility="collapsed")
    b2 = st.selectbox("Blue Team 2", team_list, key="b2", index=min(3, len(team_list)-1), label_visibility="collapsed")
    st.markdown("</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

if st.button("🔮 PREDICT WINNER", type="primary", use_container_width=True):
    red_teams, blue_teams = [r1, r2], [b1, b2]
    def get_team_stats(tn):
        opr = opr_lookup.get(tn); wr = wr_lookup.get(tn); elo = elo_lookup.get(tn) if elo_lookup else None
        if opr is None: opr = 0.0
        if wr is None: wr = 0.5
        if elo is None and elo_lookup: elo = 1500
        return opr, wr, elo
    red_oprs = [get_team_stats(t)[0] for t in red_teams]
    blue_oprs = [get_team_stats(t)[0] for t in blue_teams]
    red_wrs = [get_team_stats(t)[1] for t in red_teams]
    blue_wrs = [get_team_stats(t)[1] for t in blue_teams]
    red_elos = [get_team_stats(t)[2] for t in red_teams]
    blue_elos = [get_team_stats(t)[2] for t in blue_teams]
    red_opr_sum = sum(red_oprs); blue_opr_sum = sum(blue_oprs)
    opr_diff = red_opr_sum - blue_opr_sum
    red_elo_avg = (sum(e for e in red_elos if e is not None) / sum(1 for e in red_elos if e is not None)) if any(e is not None for e in red_elos) else 1500
    blue_elo_avg = (sum(e for e in blue_elos if e is not None) / sum(1 for e in blue_elos if e is not None)) if any(e is not None for e in blue_elos) else 1500
    elo_diff = red_elo_avg - blue_elo_avg
    prob_opr = 1 / (1 + np.exp(-opr_diff / opr_scale))
    prob_elo = 1 / (1 + np.exp(-elo_diff / 200))
    prob_red = 0.7 * prob_opr + 0.3 * prob_elo
    prob_blue = 1 - prob_red

    st.markdown("### 📊 Team Ratings")
    st.markdown(f'<div style="display:flex;align-items:center;gap:1rem;margin:0.5rem 0 1.5rem 0;"><div style="flex:{prob_red};min-width:80px;"><div style="font-weight:700;font-size:1.1rem;color:#E74C3C;">🔴 OPR {red_opr_sum:.1f}</div><div class="prediction-bar"><div class="prediction-fill-red" style="width:100%;"></div></div><div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.2rem;">Avg ELO: {red_elo_avg:.0f}<br>Team {r1}: {red_oprs[0]:.1f} OPR / ELO {red_elos[0] if red_elos[0] else "—"}<br>Team {r2}: {red_oprs[1]:.1f} OPR / ELO {red_elos[1] if red_elos[1] else "—"}</div></div><div style="font-weight:600;color:var(--text-secondary);font-size:0.85rem;text-align:center;">vs</div><div style="flex:{prob_blue};min-width:80px;"><div style="font-weight:700;font-size:1.1rem;color:#3498DB;">🔵 OPR {blue_opr_sum:.1f}</div><div class="prediction-bar"><div class="prediction-fill-blue" style="width:100%;"></div></div><div style="font-size:0.75rem;color:var(--text-secondary);margin-top:0.2rem;">Avg ELO: {blue_elo_avg:.0f}<br>Team {b1}: {blue_oprs[0]:.1f} OPR / ELO {blue_elos[0] if blue_elos[0] else "—"}<br>Team {b2}: {blue_oprs[1]:.1f} OPR / ELO {blue_elos[1] if blue_elos[1] else "—"}</div></div></div>', unsafe_allow_html=True)

    winner_emoji = "🔴" if prob_red > 0.5 else "🔵"
    winner_color = "RED" if prob_red > 0.5 else "BLUE"
    st.markdown(f'<div class="section-card" style="text-align:center;"><div style="font-size:1.3rem;font-weight:700;margin-bottom:0.5rem;">{winner_emoji} {winner_color} WINS</div><div style="font-size:2.5rem;font-weight:800;background:linear-gradient(135deg,{"#E74C3C" if prob_red>0.5 else "#3498DB"},{"#F39C12" if prob_red>0.5 else "#2980B9"});-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">{max(prob_red,prob_blue):.1%}</div><div style="color:var(--text-secondary);margin-top:0.3rem;">confidence · OPR diff: {opr_diff:+.0f} · ELO diff: {elo_diff:+.0f}</div></div>', unsafe_allow_html=True)

    st.markdown("### 🎯 Win Probability Breakdown")
    st.markdown(f'<div style="display:flex;gap:1rem;margin-top:0.5rem;"><div style="flex:1;text-align:center;"><div style="font-weight:700;color:#E74C3C;margin-bottom:0.3rem;">🔴 RED</div><div class="prediction-bar"><div class="prediction-fill-red" style="width:{prob_red*100:.0f}%;"></div></div><div style="font-weight:600;margin-top:0.3rem;font-size:1.1rem;">{prob_red:.1%}</div></div><div style="flex:1;text-align:center;"><div style="font-weight:700;color:#3498DB;margin-bottom:0.3rem;">🔵 BLUE</div><div class="prediction-bar"><div class="prediction-fill-blue" style="width:{prob_blue*100:.0f}%;"></div></div><div style="font-weight:600;margin-top:0.3rem;font-size:1.1rem;">{prob_blue:.1%}</div></div></div>', unsafe_allow_html=True)

    st.markdown("### 📋 Team Details")
    detail_cols = st.columns(4)
    for i, (t, opr, wr, elo) in enumerate([(r1, red_oprs[0], red_wrs[0], red_elos[0]), (r2, red_oprs[1], red_wrs[1], red_elos[1]), (b1, blue_oprs[0], blue_wrs[0], blue_elos[0]), (b2, blue_oprs[1], blue_wrs[1], blue_elos[1])]):
        alliance = "🔴" if i < 2 else "🔵"
        elo_str = f"{elo:.0f}" if elo is not None else "—"
        with detail_cols[i]:
            st.markdown(f'<div class="stat-card" style="padding:0.8rem 1rem;"><div style="font-weight:600;">{alliance} Team {t}</div><div style="font-size:1.3rem;font-weight:700;margin-top:0.3rem;">OPR {opr:.1f}</div><div style="color:var(--text-secondary);font-size:0.8rem;">ELO {elo_str} · WR {wr:.0%}</div></div>', unsafe_allow_html=True)
