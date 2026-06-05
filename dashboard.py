#!/usr/bin/env python3
"""
FTC Analytics Dashboard
-----------------------
Interactive Streamlit dashboard for exploring the FTC Open Analytics Dataset.
Features: Team Explorer, Event Browser, OPR Leaderboard, Match Predictor, Season Overview.
"""

import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="FTC Analytics Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Load data
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data" / "processed"
RESULTS_DIR = Path(__file__).parent / "results"


@st.cache_data
def load_data():
    matches = pd.read_csv(DATA_DIR / "matches.csv")
    teams = pd.read_csv(DATA_DIR / "teams.csv")
    team_events = pd.read_csv(DATA_DIR / "team_events.csv")
    return matches, teams, team_events


matches, teams, team_events = load_data()

# Pre-compute useful aggregates
season_labels = {
    "1819": "Rover Ruckus",
    "1920": "Skystone",
    "2021": "Ultimate Goal",
    "2122": "Freight Frenzy",
    "2223": "Power Play",
    "2324": "Centerstage",
}

# Build OPR lookup: (team_number) -> average OPR across all events
opr_lookup = {}
opr_counts = {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    opr = row["opr"] if not pd.isna(row["opr"]) else 0
    if tn not in opr_lookup:
        opr_lookup[tn] = 0.0
        opr_counts[tn] = 0
    opr_lookup[tn] += opr
    opr_counts[tn] += 1
for tn in opr_lookup:
    opr_lookup[tn] = opr_lookup[tn] / opr_counts[tn]

# Build win rate lookup: (team_number) -> average win rate
wr_lookup = {}
wr_counts = {}
for _, row in team_events.iterrows():
    tn = int(row["team_number"])
    w, l, t = row["wins"], row["losses"], row["ties"]
    wr = w / (w + l + t) if (w + l + t) > 0 else 0.5
    if tn not in wr_lookup:
        wr_lookup[tn] = 0.0
        wr_counts[tn] = 0
    wr_lookup[tn] += wr
    wr_counts[tn] += 1
for tn in wr_lookup:
    wr_lookup[tn] = wr_lookup[tn] / wr_counts[tn]

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
st.sidebar.title("🤖 FTC Analytics")
page = st.sidebar.radio(
    "Navigate",
    ["🏠 Home", "🔍 Team Explorer", "📅 Event Browser", "🏆 OPR Leaderboard", "🎯 Match Predictor"],
)

# ---------------------------------------------------------------------------
# Home
# ---------------------------------------------------------------------------
if page == "🏠 Home":
    st.title("FTC Open Analytics Dataset")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Matches", f"{len(matches):,}")
    col2.metric("Unique Teams", f"{len(teams):,}")
    col3.metric("Events", matches["event_key"].nunique())
    col4.metric("Regions", matches["region"].nunique())

    st.markdown("---")

    st.subheader("📊 Season Overview")
    season_tab = st.selectbox("Select Season", list(season_labels.keys()), format_func=lambda x: f"{x} — {season_labels[x]}")
    sm = matches[matches["season"] == season_tab]
    quals = sm[~sm["is_playoff"]]
    playoffs = sm[sm["is_playoff"]]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Matches", len(sm))
    c2.metric("Quals", len(quals))
    c3.metric("Playoff", len(playoffs))
    c4.metric("Events", sm["event_key"].nunique())

    scores = pd.concat([sm["red_score"], sm["blue_score"]])
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mean Score", f"{scores.mean():.1f}")
    c2.metric("Median Score", f"{scores.median():.1f}")
    c3.metric("Max Score", f"{scores.max():.0f}")
    c4.metric("Std Dev", f"{scores.std():.1f}")

    # Score distribution
    st.subheader("Score Distribution")
    col_a, col_b = st.columns(2)
    with col_a:
        # Histogram of all scores in this season
        score_vals = pd.concat([sm["red_score"], sm["blue_score"]])
        hist = pd.cut(score_vals, bins=25).value_counts().sort_index()
        hist_df = pd.DataFrame({"Score Range": [str(i) for i in hist.index], "Count": hist.values}).set_index("Score Range")
        st.bar_chart(hist_df, use_container_width=True)
    with col_b:
        winner_counts = sm["winner"].value_counts()
        st.write("**Win Distribution**")
        st.bar_chart(winner_counts, use_container_width=True)

    st.markdown("---")
    st.subheader("🔗 Dataset Quick Stats")
    st.markdown(f"""
    - **1,762 matches** across 6 seasons (2018-19 through 2023-24)
    - **902 unique teams** from **53 events** in **10 regions**
    - Computed metrics: OPR, NP-OPR, CCWM
    - Baseline ML benchmarks: win prediction (88.7% accuracy) and alliance strength
    - [GitHub Repository](https://github.com/kaivalya-cyber/ftc-analytics-dataset)
    """)

# ---------------------------------------------------------------------------
# Team Explorer
# ---------------------------------------------------------------------------
elif page == "🔍 Team Explorer":
    st.title("🔍 Team Explorer")

    team_list = sorted(teams["team_number"].unique())
    team_number = st.selectbox("Search for a team", team_list, index=0, key="team_search")

    if team_number:
        team_info = teams[teams["team_number"] == team_number].iloc[0]
        st.subheader(f"Team {team_number} — {team_info['team_name']}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Country", team_info["country"] if pd.notna(team_info["country"]) else "—")
        c2.metric("State/Province", team_info["state_province"] if pd.notna(team_info["state_province"]) else "—")
        c3.metric("Rookie Year", int(team_info["rookie_year"]) if pd.notna(team_info["rookie_year"]) else "—")
        matches_played = len(matches[(matches["red_team_1"] == team_number) | (matches["red_team_2"] == team_number) | (matches["blue_team_1"] == team_number) | (matches["blue_team_2"] == team_number)])
        c4.metric("Matches Played", matches_played)

        # Team events history
        te = team_events[team_events["team_number"] == team_number].sort_values("season")
        if len(te) > 0:
            st.subheader("Event History & OPR")
            st.dataframe(
                te[["season", "event_key", "wins", "losses", "ties", "opr", "ccwm", "ranking"]].rename(
                    columns={"event_key": "Event", "wins": "W", "losses": "L", "ties": "T", "opr": "OPR", "ccwm": "CCWM", "ranking": "Rank"}
                ),
                use_container_width=True,
                hide_index=True,
            )

            # OPR chart
            if len(te) > 1:
                chart_data = te.set_index("event_key")[["opr", "ccwm"]]
                st.subheader("OPR / CCWM Trend")
                st.line_chart(chart_data, use_container_width=True)
        else:
            st.info("No event data found for this team.")

# ---------------------------------------------------------------------------
# Event Browser
# ---------------------------------------------------------------------------
elif page == "📅 Event Browser":
    st.title("📅 Event Browser")

    season = st.selectbox("Season", sorted(matches["season"].unique()), format_func=lambda x: f"{x} — {season_labels.get(x, x)}")

    season_matches = matches[matches["season"] == season]
    event_list = sorted(season_matches["event_key"].unique())
    event = st.selectbox("Event", event_list)

    if event:
        event_matches = season_matches[season_matches["event_key"] == event].sort_values("match_number")
        quals = event_matches[~event_matches["is_playoff"]]
        playoffs = event_matches[event_matches["is_playoff"]]

        st.subheader(f"{event_matches['event_name'].iloc[0]} ({event})")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Region", event_matches["region"].iloc[0])
        c2.metric("Total Matches", len(event_matches))
        c3.metric("Quals", len(quals))
        c4.metric("Playoff", len(playoffs))

        tab1, tab2 = st.tabs(["Qualification Matches", "Playoff Matches"])

        with tab1:
            if len(quals) > 0:
                quals_display = quals[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]].copy()
                quals_display["result"] = quals_display.apply(
                    lambda r: f"{int(r['red_score'])}–{int(r['blue_score'])}", axis=1
                )
                st.dataframe(
                    quals_display[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "result", "winner"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "match_number": "Match",
                        "red_team_1": "Red 1",
                        "red_team_2": "Red 2",
                        "blue_team_1": "Blue 1",
                        "blue_team_2": "Blue 2",
                        "result": "Score",
                        "winner": "Winner",
                    },
                )
            else:
                st.info("No qualification matches.")

        with tab2:
            if len(playoffs) > 0:
                playoffs_display = playoffs[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner"]].copy()
                playoffs_display["result"] = playoffs_display.apply(
                    lambda r: f"{int(r['red_score'])}–{int(r['blue_score'])}", axis=1
                )
                st.dataframe(
                    playoffs_display[["match_number", "red_team_1", "red_team_2", "blue_team_1", "blue_team_2", "result", "winner"]],
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "match_number": "Match",
                        "red_team_1": "Red 1",
                        "red_team_2": "Red 2",
                        "blue_team_1": "Blue 1",
                        "blue_team_2": "Blue 2",
                        "result": "Score",
                        "winner": "Winner",
                    },
                )
            else:
                st.info("No playoff matches.")

        # Event rankings
        event_te = team_events[team_events["event_key"] == event].sort_values("ranking")
        if len(event_te) > 0:
            st.markdown("---")
            st.subheader("Event Rankings (Qualification)")
            st.dataframe(
                event_te[["ranking", "team_number", "wins", "losses", "ties", "opr", "ccwm"]].rename(
                    columns={"ranking": "Rank", "team_number": "Team", "wins": "W", "losses": "L", "ties": "T", "opr": "OPR", "ccwm": "CCWM"}
                ),
                use_container_width=True,
                hide_index=True,
            )

# ---------------------------------------------------------------------------
# OPR Leaderboard
# ---------------------------------------------------------------------------
elif page == "🏆 OPR Leaderboard":
    st.title("🏆 OPR Leaderboard")

    show_season = st.selectbox("Filter by Season", ["All Seasons"] + sorted(matches["season"].unique()), format_func=lambda x: f"{x} — {season_labels[x]}" if x in season_labels else x)

    if show_season == "All Seasons":
        df = team_events.copy()
    else:
        df = team_events[team_events["season"] == show_season].copy()

    df = df.dropna(subset=["opr"]).sort_values("opr", ascending=False)

    top_n = st.slider("Show top N", 10, 100, 15)

    st.subheader(f"Top {top_n} Teams by OPR")
    display = df.head(top_n)[["team_number", "event_key", "season", "opr", "ccwm", "wins", "losses", "ties", "ranking"]].copy()
    display["win_rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
    display["opr"] = display["opr"].round(2)
    display["ccwm"] = display["ccwm"].round(2)

    st.dataframe(
        display.rename(
            columns={
                "team_number": "Team",
                "event_key": "Event",
                "season": "Season",
                "opr": "OPR",
                "ccwm": "CCWM",
                "win_rate": "Win %",
                "wins": "W",
                "losses": "L",
                "ties": "T",
                "ranking": "Rank",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # OPR distribution
    st.markdown("---")
    st.subheader("OPR Distribution")

    valid_oprs = df["opr"].dropna()
    hist_data = pd.cut(valid_oprs, bins=30).value_counts().sort_index()
    hist_df = pd.DataFrame({"OPR Range": [str(i) for i in hist_data.index], "Count": hist_data.values}).set_index("OPR Range")
    st.bar_chart(hist_df, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    c1.metric("Mean OPR", f"{valid_oprs.mean():.2f}")
    c2.metric("Max OPR", f"{valid_oprs.max():.2f}")
    c3.metric("Std Dev", f"{valid_oprs.std():.2f}")

# ---------------------------------------------------------------------------
# Match Predictor
# ---------------------------------------------------------------------------
elif page == "🎯 Match Predictor":
    st.title("🎯 Match Predictor")
    st.markdown("Predict the winner of a theoretical FTC match, based on each team's OPR and win rate.")

    col1, col2 = st.columns(2)

    team_list = sorted(teams["team_number"].unique())
    default_red = team_list[0] if team_list else None
    default_blue = team_list[-1] if len(team_list) > 1 else None

    with col1:
        st.subheader("🔴 Red Alliance")
        r1 = st.selectbox("Red Team 1", team_list, key="r1", index=0)
        r2 = st.selectbox("Red Team 2", team_list, key="r2", index=min(1, len(team_list) - 1))

    with col2:
        st.subheader("🔵 Blue Alliance")
        b1 = st.selectbox("Blue Team 1", team_list, key="b1", index=min(2, len(team_list) - 1))
        b2 = st.selectbox("Blue Team 2", team_list, key="b2", index=min(3, len(team_list) - 1))

    if st.button("🔮 Predict Winner", type="primary", use_container_width=True):
        # Gather stats
        red_teams = [r1, r2]
        blue_teams = [b1, b2]

        def get_team_stats(tn):
            opr = opr_lookup.get(tn)
            wr = wr_lookup.get(tn)
            if opr is None:
                st.warning(f"⚠️ Team {tn} has no OPR data in the dataset")
                opr = 0.0
            if wr is None:
                wr = 0.5
            return opr, wr

        red_oprs = [get_team_stats(t)[0] for t in red_teams]
        blue_oprs = [get_team_stats(t)[0] for t in blue_teams]
        red_wrs = [get_team_stats(t)[1] for t in red_teams]
        blue_wrs = [get_team_stats(t)[1] for t in blue_teams]

        red_opr_sum = sum(red_oprs)
        blue_opr_sum = sum(blue_oprs)
        opr_diff = red_opr_sum - blue_opr_sum
        red_wr_avg = np.mean(red_wrs)
        blue_wr_avg = np.mean(blue_wrs)

        # Compute probability using logistic function scaled by OPR std deviation
        # Divisor = std of OPR differences in the training set, computed from data
        all_diffs = []
        for _, row in matches.iterrows():
            r1_o = opr_lookup.get(row["red_team_1"], 0)
            r2_o = opr_lookup.get(row["red_team_2"], 0)
            b1_o = opr_lookup.get(row["blue_team_1"], 0)
            b2_o = opr_lookup.get(row["blue_team_2"], 0)
            all_diffs.append((r1_o + r2_o) - (b1_o + b2_o))
        scale = max(np.std(all_diffs), 1.0)
        prob_red = 1 / (1 + np.exp(-opr_diff / scale))

        c1, c2, c3 = st.columns(3)
        c1.metric("🔴 Red OPR Sum", f"{red_opr_sum:.1f}")
        c2.metric("🔵 Blue OPR Sum", f"{blue_opr_sum:.1f}")
        c3.metric("OPR Differential", f"{opr_diff:+.1f}")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("🔴 Red Win Probability", f"{prob_red:.1%}")
            st.caption(f"Based on OPR difference of {opr_diff:+.1f}")

            # Team details
            for t in red_teams:
                opr, wr = get_team_stats(t)
                st.write(f"**Team {t}** — OPR: {opr:.1f}, Win Rate: {wr:.1%}")

        with col_b:
            st.metric("🔵 Blue Win Probability", f"{1 - prob_red:.1%}")
            st.caption(f"OPR difference: {opr_diff:+.1f}")

            for t in blue_teams:
                opr, wr = get_team_stats(t)
                st.write(f"**Team {t}** — OPR: {opr:.1f}, Win Rate: {wr:.1%}")

        winner = "🔴 RED" if prob_red > 0.5 else "🔵 BLUE"
        margin = abs(prob_red - 0.5) * 200
        st.success(f"**Predicted Winner: {winner}** (confidence: {max(prob_red, 1-prob_red):.0%} margin)")
        st.caption(f"Expected score margin: ~{abs(opr_diff):.0f} points")

# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.caption(
    f"Data: {len(matches):,} matches | {len(teams):,} teams | 6 seasons\n\n"
    "[GitHub](https://github.com/kaivalya-cyber/ftc-analytics-dataset) | "
    "[License: MIT](LICENSE)"
)
