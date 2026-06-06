import streamlit as st
import pandas as pd
import numpy as np
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Season Simulator", page_icon="🏆", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
_, opr_lookup, _, elo_lookup, opr_scale = build_lookups(matches, teams, team_events, current_elo)

hero_header("🏆 Season Simulator", "Build a bracket tournament with 8 teams and simulate matches using OPR + ELO win probabilities. Run multiple simulations to see who wins most often.")

team_list = sorted(teams["team_number"].unique())

st.markdown("### 🎯 Select 8 Teams for Your Bracket")
cols = st.columns(8)
selected_teams = []
for i, col in enumerate(cols):
    with col:
        t = st.selectbox(f"Seed #{i+1}", team_list, key=f"sim_t{i}", index=i)
        selected_teams.append(t)

# Remove duplicates
selected_teams = list(set(selected_teams))
if len(selected_teams) < 8:
    st.warning(f"⚠️ Please select 8 unique teams (currently {len(selected_teams)}). Use different teams for each seed.")
    st.stop()

    n_sims = st.slider("Number of simulations", 10, 500, 50)

    if st.button("🏆 RUN SIMULATION", type="primary", use_container_width=True):
        win_counts = {t: 0 for t in selected_teams}
        final_appearances = {t: 0 for t in selected_teams}
        semi_appearances = {t: 0 for t in selected_teams}

        def simulate_match(team_a, team_b):
            """Return winner using OPR+ELO blended probability."""
            a_opr = opr_lookup.get(team_a, 0)
            b_opr = opr_lookup.get(team_b, 0)
            opr_diff = a_opr - b_opr
            prob_opr = 1 / (1 + np.exp(-opr_diff / opr_scale))

            a_elo = elo_lookup.get(team_a, 1500) if elo_lookup else 1500
            b_elo = elo_lookup.get(team_b, 1500) if elo_lookup else 1500
            elo_diff = a_elo - b_elo
            prob_elo = 1 / (1 + np.exp(-elo_diff / 200))

            prob_a = 0.7 * prob_opr + 0.3 * prob_elo
            return team_a if np.random.random() < prob_a else team_b

        for sim in range(n_sims):
            teams_pool = selected_teams.copy()
            np.random.shuffle(teams_pool)
            # Quarterfinals
            qf_winners = []
            for i in range(0, 8, 2):
                w = simulate_match(teams_pool[i], teams_pool[i+1])
                qf_winners.append(w)
            # Semifinals
            sf1 = simulate_match(qf_winners[0], qf_winners[1])
            sf2 = simulate_match(qf_winners[2], qf_winners[3])
            for t in [sf1, sf2]:
                semi_appearances[t] += 1
            # Finals
            champion = simulate_match(sf1, sf2)
            final_appearances[sf1 if champion == sf2 else sf2] += 1
            final_appearances[champion] += 1
            win_counts[champion] += 1

        # Results
        st.markdown("### 🏆 Tournament Results")
        results_df = pd.DataFrame({
            "Team": selected_teams,
            "Championships": [win_counts[t] for t in selected_teams],
            "Win Rate": [win_counts[t]/n_sims*100 for t in selected_teams],
            "Finalist": [final_appearances[t] for t in selected_teams],
            "Semifinalist": [semi_appearances[t] for t in selected_teams],
        }).sort_values("Win Rate", ascending=False)
        results_df["Rank"] = range(1, len(results_df)+1)

        # Champion stat card
        champ = results_df.iloc[0]
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(stat_card_html("🏆", f"Team {int(champ['Team'])}", "Champion", "accent-red"), unsafe_allow_html=True)
        with c2: st.markdown(stat_card_html("📊", f"{champ['Win Rate']:.1f}%", "Win Rate", "accent-blue"), unsafe_allow_html=True)
        with c3: st.markdown(stat_card_html("🔄", f"{n_sims:,}", "Simulations", "accent-orange"), unsafe_allow_html=True)
        with c4: st.markdown(stat_card_html("🎯", f"{int(champ['Championships'])}", "Championships", "accent-green"), unsafe_allow_html=True)

        # Bar chart of win rates
        st.markdown("### 📊 Championship Win Rates")
        chart_data = results_df.set_index("Team")["Win Rate"]
        st.bar_chart(chart_data, use_container_width=True)

        # Full table
        st.dataframe(
            results_df[["Rank", "Team", "Win Rate", "Championships", "Finalist", "Semifinalist"]].rename(
                columns={"Rank": "Rank", "Team": "Team", "Win Rate": "Win %", "Championships": "🏆 Wins", "Finalist": "Finals", "Semifinalist": "Semis"}
            ),
            use_container_width=True, hide_index=True,
            column_config={"Win %": st.column_config.NumberColumn(format="%.1f%%")},
        )

        # Show team stats in the simulation
        st.markdown("### 🤖 Team Ratings Used")
        team_stats = pd.DataFrame({
            "Team": selected_teams,
            "OPR": [opr_lookup.get(t, 0) for t in selected_teams],
            "ELO": [elo_lookup.get(t, 1500) if elo_lookup else 1500 for t in selected_teams],
        }).sort_values("OPR", ascending=False)
        team_stats["OPR"] = team_stats["OPR"].round(1)
        team_stats["ELO"] = team_stats["ELO"].round(0).astype(int)
        st.dataframe(team_stats, use_container_width=True, hide_index=True)
