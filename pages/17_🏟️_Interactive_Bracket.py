import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Interactive Bracket", page_icon="🏟️", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

hero_header("🏟️ Interactive Bracket", "Build a knockout tournament bracket and simulate each round — see who advances match by match.")

# --- Team Selection ---
st.markdown("### 🎯 Select Your Competitors")
team_list = sorted(teams["team_number"].unique())

bracket_size = st.radio("Bracket Size", [4, 8], horizontal=True, index=1)
n_teams = bracket_size

cols = st.columns(min(n_teams, 8))
selected_teams = []
for i, col in enumerate(cols):
    with col:
        t = st.selectbox(f"Seed #{i+1}", team_list, key=f"bracket_t{i}", index=i * 3 % len(team_list))
        selected_teams.append(t)

selected_teams = list(dict.fromkeys(selected_teams))
if len(selected_teams) < n_teams:
    st.warning(f"⚠️ Please select {n_teams} unique teams (currently {len(selected_teams)}).")
    st.stop()

selected_teams = selected_teams[:n_teams]

# --- Display team ratings ---
team_name_lookup = dict(zip(teams["team_number"], teams["team_name"]))
st.markdown("### 🤖 Team Ratings")
ratings_cols = st.columns(min(n_teams, 8))
for i, (col, t) in enumerate(zip(ratings_cols, selected_teams)):
    with col:
        opr = opr_lookup.get(t, 0)
        elo = elo_lookup.get(t, 1500) if elo_lookup else 1500
        wr = wr_lookup.get(t, 0.5)
        name = team_name_lookup.get(t, f"Team {t}")
        st.markdown(f"""
        <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:0.8rem; text-align:center; border:1px solid var(--border-subtle);">
            <div style="font-weight:700; font-size:1rem; color:var(--text-primary);">#{i+1} — {t}</div>
            <div style="font-size:0.72rem; color:var(--text-secondary); margin:0.2rem 0;">{name[:22]}</div>
            <div style="display:flex; gap:0.5rem; justify-content:center; margin-top:0.3rem;">
                <span style="font-size:0.7rem; background:rgba(231,76,60,0.12); color:#E74C3C; padding:2px 6px; border-radius:4px;">OPR {opr:.1f}</span>
                <span style="font-size:0.7rem; background:rgba(52,152,219,0.12); color:#3498DB; padding:2px 6px; border-radius:4px;">ELO {elo:.0f}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# --- Simulation ---
def predict_winner(team_a, team_b):
    """Return (winner, prob_a) using OPR+ELO blended probability."""
    a_opr = opr_lookup.get(team_a, 0)
    b_opr = opr_lookup.get(team_b, 0)
    opr_diff = a_opr - b_opr
    prob_opr = 1 / (1 + np.exp(-opr_diff / opr_scale))

    a_elo = elo_lookup.get(team_a, 1500) if elo_lookup else 1500
    b_elo = elo_lookup.get(team_b, 1500) if elo_lookup else 1500
    elo_diff = a_elo - b_elo
    prob_elo = 1 / (1 + np.exp(-elo_diff / 200))

    prob_a = 0.7 * prob_opr + 0.3 * prob_elo
    return (team_a, prob_a) if np.random.random() < prob_a else (team_b, 1 - prob_a)

st.markdown("---")

if st.button("🏆 SIMULATE BRACKET", type="primary", use_container_width=True):
    # Quarterfinals (for 8-team) or Semifinals (for 4-team)
    if n_teams == 8:
        st.markdown("### 🏟️ Quarterfinals")
        qf_winners = []
        qf_probs = []
        qf_cols = st.columns(4)
        for i in range(0, 8, 2):
            w, p = predict_winner(selected_teams[i], selected_teams[i+1])
            qf_winners.append(w)
            qf_probs.append(p)
            loser = selected_teams[i+1] if w == selected_teams[i] else selected_teams[i]
            with qf_cols[i // 2]:
                st.markdown(f"""
                <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:0.8rem; border:1px solid var(--border-subtle); margin-bottom:0.5rem;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:600; color:var(--text-primary);">{w}</span>
                        <span style="font-size:0.7rem; color:var(--text-secondary);">{p*100:.0f}%</span>
                    </div>
                    <div style="font-size:0.7rem; color:var(--text-secondary); margin-top:0.15rem;">def. {loser}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("### 🏟️ Semifinals")
        semi_teams = qf_winners
    else:
        semi_teams = selected_teams

    # Semifinals
    sf_cols = st.columns(2)
    sf_winners = []
    sf_probs = []
    for i in range(0, len(semi_teams), 2):
        w, p = predict_winner(semi_teams[i], semi_teams[i+1])
        sf_winners.append(w)
        sf_probs.append(p)
        loser = semi_teams[i+1] if w == semi_teams[i] else semi_teams[i]
        with sf_cols[i // 2]:
            st.markdown(f"""
            <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:1rem; border:1px solid var(--border-subtle); margin-bottom:0.5rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:700; font-size:1.1rem; color:var(--text-primary);">{w}</span>
                    <span style="font-size:0.75rem; color:var(--text-secondary);">{p*100:.0f}% win prob</span>
                </div>
                <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.2rem;">def. {loser}</div>
                <div style="margin-top:0.4rem;">
                    <span class="chip chip-green">Advances to Final</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🏆 Championship Final")
    w, p = predict_winner(sf_winners[0], sf_winners[1])
    loser = sf_winners[1] if w == sf_winners[0] else sf_winners[0]

    # Champion card
    fcol1, fcol2 = st.columns([2, 1])
    with fcol1:
        champ_name = team_name_lookup.get(w, f"Team {w}")
        st.markdown(f"""
        <div style="background:var(--gradient-hero); border-radius:var(--radius-lg); padding:2rem; text-align:center; border:2px solid #F39C12;">
            <div style="font-size:3rem; margin-bottom:0.5rem;">🏆</div>
            <div class="hero-title" style="font-size:2rem;">{w} — {champ_name[:30]}</div>
            <div style="font-size:1.1rem; color:var(--text-secondary); margin-top:0.5rem;">CHAMPION</div>
            <div style="font-size:0.85rem; color:var(--text-secondary); margin-top:0.3rem;">Win Probability: {p*100:.1f}% &nbsp;|&nbsp; def. {loser}</div>
        </div>
        """, unsafe_allow_html=True)
    with fcol2:
        finalist_name = team_name_lookup.get(loser, f"Team {loser}")
        st.markdown(f"""
        <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:1.5rem; text-align:center; border:1px solid var(--border-subtle);">
            <div style="font-size:2rem; margin-bottom:0.3rem;">🥈</div>
            <div style="font-weight:700; font-size:1.3rem; color:var(--text-primary);">{loser}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary);">{finalist_name[:20]}</div>
            <div style="font-size:0.8rem; color:var(--text-secondary); margin-top:0.3rem;">Runner-Up</div>
        </div>
        """, unsafe_allow_html=True)

    # Bracket tree visualization
    st.markdown("---")
    st.markdown("### 🌳 Bracket Tree")

    # Build bracket structure
    if n_teams == 8:
        rounds = [
            ("Quarterfinals", [
                (selected_teams[0], selected_teams[1], qf_winners[0]),
                (selected_teams[2], selected_teams[3], qf_winners[1]),
                (selected_teams[4], selected_teams[5], qf_winners[2]),
                (selected_teams[6], selected_teams[7], qf_winners[3]),
            ]),
            ("Semifinals", [
                (qf_winners[0], qf_winners[1], sf_winners[0]),
                (qf_winners[2], qf_winners[3], sf_winners[1]),
            ]),
            ("Final", [(sf_winners[0], sf_winners[1], w)]),
        ]
    else:
        rounds = [
            ("Semifinals", [
                (selected_teams[0], selected_teams[1], sf_winners[0]),
                (selected_teams[2], selected_teams[3], sf_winners[1]),
            ]),
            ("Final", [(sf_winners[0], sf_winners[1], w)]),
        ]

    for round_name, matchups in rounds:
        st.markdown(f"**{round_name}**")
        rcols = st.columns(len(matchups))
        for j, (t1, t2, winner) in enumerate(matchups):
            with rcols[j]:
                t1_style = "font-weight:700; color:#F39C12;" if t1 == winner else "color:var(--text-secondary);"
                t2_style = "font-weight:700; color:#F39C12;" if t2 == winner else "color:var(--text-secondary);"
                st.markdown(f"""
                <div style="background:var(--bg-card); border-radius:var(--radius-md); padding:0.6rem 0.8rem; border:1px solid var(--border-subtle); margin-bottom:0.4rem;">
                    <div style="{t1_style} font-size:0.9rem;">{'🏆 ' if t1 == winner else ''}{t1}</div>
                    <div style="font-size:0.65rem; color:var(--text-secondary); text-align:center; margin:0.15rem 0;">vs</div>
                    <div style="{t2_style} font-size:0.9rem;">{'🏆 ' if t2 == winner else ''}{t2}</div>
                </div>
                """, unsafe_allow_html=True)

    # Re-simulate button
    if st.button("🔄 Re-Simulate", use_container_width=True):
        st.rerun()
