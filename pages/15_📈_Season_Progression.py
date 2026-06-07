import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, hero_header, render_sidebar

st.set_page_config(page_title="Season Progression", page_icon="📈", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("📈 Season Progression", "Track any team's OPR and ELO journey season-over-season — see how they improved or declined year by year.")

team_list = sorted(teams["team_number"].unique())
team_number = st.selectbox("Search for a team by number", team_list, index=0, label_visibility="collapsed")

if team_number:
    team_info = teams[teams["team_number"] == team_number].iloc[0]
    name = str(team_info["team_name"]) if pd.notna(team_info["team_name"]) else f"Team {team_number}"
    st.markdown(f"### 🤖 Team {team_number} — {name}")

    # Gather season-by-season stats
    te = team_events[team_events["team_number"] == team_number].sort_values("season")
    
    if len(te) == 0:
        st.info("No event data found for this team.")
    else:
        seasons = sorted(te["season"].unique())
        opr_by_season = []
        elo_by_season = []
        wr_by_season = []
        matches_by_season = []
        season_list = []

        for season in seasons:
            season_str = str(season)
            season_te = te[te["season"] == season]
            season_list.append(season_labels.get(season_str, season_str))

            avg_opr = season_te["opr"].mean() if not season_te["opr"].isna().all() else 0
            opr_by_season.append(avg_opr)

            total_matches = int(season_te["wins"].sum() + season_te["losses"].sum() + season_te["ties"].sum())
            matches_by_season.append(total_matches)

            wr = season_te["wins"].sum() / max(total_matches, 1)
            wr_by_season.append(wr * 100)

            # Season-end ELO from historical data
            if elo_df is not None:
                selo = elo_df[(elo_df["team_number"] == team_number) & (elo_df["season"] == season)]
                if len(selo) > 0:
                    elo_by_season.append(selo["elo_after"].iloc[-1])
                else:
                    elo_by_season.append(None)
            else:
                elo_by_season.append(None)

        # OPR + ELO dual-axis chart
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=season_list, y=opr_by_season,
            name="Avg OPR",
            marker_color="#E74C3C", opacity=0.8,
            yaxis="y",
            text=[f"{v:.1f}" if v else "—" for v in opr_by_season],
            textposition="outside",
            textfont=dict(color="#f0f0f5"),
        ))
        
        valid_elos = [(i, e) for i, e in enumerate(elo_by_season) if e is not None]
        if valid_elos:
            e_idx, e_vals = zip(*valid_elos)
            fig.add_trace(go.Scatter(
                x=[season_list[i] for i in e_idx], y=e_vals,
                name="Season-End ELO",
                mode="lines+markers",
                line=dict(color="#3498DB", width=3),
                marker=dict(size=10),
                yaxis="y2",
                text=[f"{v:.0f}" for v in e_vals],
                textposition="top center",
                textfont=dict(color="#3498DB"),
            ))

        fig.update_layout(
            title=f"Team {team_number} Season Progression",
            template="plotly_dark",
            height=450,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f0f0f5"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)"),
            yaxis=dict(title="Avg OPR", gridcolor="rgba(255,255,255,0.08)"),
            yaxis2=dict(title="ELO", overlaying="y", side="right", gridcolor="rgba(255,255,255,0.02)"),
            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="center", x=0.5),
            bargap=0.3,
        )
        st.plotly_chart(fig, use_container_width=True)

        # Season stats table
        st.markdown("---")
        st.markdown("### 📊 Season-by-Season Breakdown")
        rows = []
        for i, season in enumerate(seasons):
            rows.append({
                "Season": season_labels.get(str(season), str(season)),
                "Matches": matches_by_season[i],
                "Avg OPR": round(opr_by_season[i], 1),
                "Season-End ELO": round(elo_by_season[i], 0) if elo_by_season[i] is not None else "—",
                "Win Rate": f"{wr_by_season[i]:.1f}%",
                "Change": "",
            })

        for i in range(1, len(rows)):
            if pd.notna(rows[i]["Avg OPR"]) and pd.notna(rows[i-1]["Avg OPR"]):
                delta = rows[i]["Avg OPR"] - rows[i-1]["Avg OPR"]
                rows[i]["Change"] = f"{'+' if delta > 0 else ''}{delta:.1f}"
            else:
                rows[i]["Change"] = "—"

        display_df = pd.DataFrame(rows)
        st.dataframe(display_df, use_container_width=True, hide_index=True,
            column_config={
                "Avg OPR": st.column_config.NumberColumn(format="%.1f"),
                "Season-End ELO": st.column_config.NumberColumn(format="%.0f"),
            },
        )

        # Improvement/decline summary
        if len(seasons) >= 2:
            st.markdown("---")
            st.markdown("### 📈 Career Trend")
            c1, c2, c3 = st.columns(3)
            first_opr = opr_by_season[0]
            last_opr = opr_by_season[-1]
            opr_change = last_opr - first_opr if pd.notna(first_opr) and pd.notna(last_opr) else 0
            c1.metric("OPR Change", f"{last_opr:.1f}", f"{opr_change:+.1f}")

            first_elo = elo_by_season[0] if elo_by_season[0] is not None else 1500
            last_elo = elo_by_season[-1] if elo_by_season[-1] is not None else first_elo
            elo_change = last_elo - first_elo
            c2.metric("ELO Change", f"{last_elo:.0f}", f"{elo_change:+.0f}")

            seasons_played = len(seasons)
            c3.metric("Seasons Played", seasons_played)
