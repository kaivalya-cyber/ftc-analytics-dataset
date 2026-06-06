import streamlit as st
import pandas as pd
import numpy as np
from io import BytesIO
from fpdf import FPDF
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Team Explorer", page_icon="🔍", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
season_labels, opr_lookup, wr_lookup, elo_lookup, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🔍 Team Explorer", "Deep-dive into any team's performance history, OPR trends, and event results.")
team_list = sorted(teams["team_number"].unique())
team_number = st.selectbox("Search for a team by number", team_list, index=0, label_visibility="collapsed")

if team_number:
    team_info = teams[teams["team_number"] == team_number].iloc[0]
    st.markdown(f'<div class="section-card" style="margin-top:1rem;"><div style="display:flex;align-items:center;gap:1rem;"><div style="font-size:3rem;">🤖</div><div><div style="font-size:1.6rem;font-weight:700;">Team {team_number}</div><div style="color:var(--text-secondary);font-size:1rem;">{team_info["team_name"] if pd.notna(team_info["team_name"]) else "—"}</div></div></div><div style="display:flex;gap:2rem;margin-top:1.2rem;flex-wrap:wrap;"><div><span style="color:var(--text-secondary);">📍</span> {team_info["country"] if pd.notna(team_info["country"]) else "—"}, {team_info["state_province"] if pd.notna(team_info["state_province"]) else "—"}</div><div><span style="color:var(--text-secondary);">🎂</span> Rookie Year: {int(team_info["rookie_year"]) if pd.notna(team_info["rookie_year"]) else "—"}</div><div><span style="color:var(--text-secondary);">⚔️</span> Matches Played: {(matches[(matches["red_team_1"]==team_number)|(matches["red_team_2"]==team_number)|(matches["blue_team_1"]==team_number)|(matches["blue_team_2"]==team_number)]).shape[0]}</div></div></div>', unsafe_allow_html=True)

    te = team_events[team_events["team_number"] == team_number].sort_values("season")
    if len(te) > 0:
        st.markdown("### 📋 Event History")
        display = te[["season", "event_key", "wins", "losses", "ties", "opr", "ccwm", "ranking"]].copy()
        display["Win Rate"] = (display["wins"] / (display["wins"] + display["losses"] + display["ties"])).round(2)
        st.dataframe(display.rename(columns={"event_key": "Event", "season": "Season", "wins": "W", "losses": "L", "ties": "T", "opr": "OPR", "ccwm": "CCWM", "ranking": "Rank"}), use_container_width=True, hide_index=True, column_config={"OPR": st.column_config.NumberColumn(format="%.1f"), "CCWM": st.column_config.NumberColumn(format="%.1f"), "Win Rate": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1)})
        if len(te) > 1:
            st.markdown("### 📈 OPR / CCWM Trend")
            st.line_chart(te.set_index("event_key")[["opr", "ccwm"]], use_container_width=True)
        if elo_df is not None:
            telo = elo_df[elo_df["team_number"] == team_number].sort_values(["season", "event_key", "match_number"])
            if len(telo) > 1:
                st.markdown("### 📈 ELO Rating Trend")
                telo_chart = telo.reset_index(drop=True)
                telo_chart["Match #"] = range(1, len(telo_chart) + 1)
                st.line_chart(telo_chart.set_index("Match #")[["elo_after"]], use_container_width=True)
                cte = current_elo[current_elo["team_number"] == team_number] if current_elo is not None else None
                if cte is not None and len(cte) > 0:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Current ELO", f"{cte['current_elo'].iloc[0]:.0f}")
                    c2.metric("Peak ELO", f"{telo['elo_after'].max():.0f}")
                    c3.metric("Min ELO", f"{telo['elo_after'].min():.0f}")
        st.markdown("### 📊 Season Summary")
        te_tmp = te.copy()
        te_tmp["total_matches"] = te_tmp["wins"] + te_tmp["losses"] + te_tmp["ties"]
        seasons_played = te_tmp.groupby("season").agg(Matches=("total_matches", "sum"), Wins=("wins", "sum"), Losses=("losses", "sum"), Ties=("ties", "sum"), Best_OPR=("opr", "max"), Avg_OPR=("opr", "mean")).round(2)
        st.dataframe(seasons_played, use_container_width=True)

        # PDF Report generation
        total_matches_played = len(matches[(matches["red_team_1"]==team_number)|(matches["red_team_2"]==team_number)|(matches["blue_team_1"]==team_number)|(matches["blue_team_2"]==team_number)])
        best_opr = te["opr"].max() if len(te) > 0 else 0
        avg_opr = te["opr"].mean() if len(te) > 0 else 0
        current_elo_val = elo_lookup.get(team_number, 1500) if elo_lookup else 1500
        if elo_df is not None:
            telo_all = elo_df[elo_df["team_number"] == team_number]
            peak_elo = telo_all["elo_after"].max() if len(telo_all) > 0 else current_elo_val
        else:
            peak_elo = current_elo_val

        def generate_pdf():
            pdf = FPDF()
            pdf.add_page()
            pdf.set_auto_page_break(auto=True, margin=15)
            # Title
            pdf.set_font("Helvetica", "B", 24)
            pdf.set_text_color(231, 76, 60)
            pdf.cell(0, 12, f"Team {team_number} Report", ln=True, align="C")
            pdf.set_font("Helvetica", "", 12)
            pdf.set_text_color(100, 100, 120)
            name = str(team_info["team_name"]) if pd.notna(team_info["team_name"]) else "—"
            pdf.cell(0, 8, name, ln=True, align="C")
            pdf.ln(6)
            # Stats cards
            pdf.set_font("Helvetica", "B", 11)
            pdf.set_text_color(50, 50, 60)
            pdf.set_fill_color(245, 245, 248)
            col_w = 45
            for label, val in [("Matches", total_matches_played), ("Best OPR", f"{best_opr:.1f}"), ("Avg OPR", f"{avg_opr:.1f}"), ("Current ELO", f"{current_elo_val:.0f}")]:
                pdf.cell(col_w, 14, f"{label}\n{val}", border=1, ln=0, align="C", fill=True)
            pdf.ln(18)
            # Season Summary table
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(231, 76, 60)
            pdf.cell(0, 10, "Season Summary", ln=True)
            pdf.ln(2)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_fill_color(231, 76, 60)
            pdf.set_text_color(255, 255, 255)
            cols_w = [22, 22, 22, 22, 22, 32, 32]
            for w, h in zip(cols_w, ["Season", "Matches", "W", "L", "T", "Best OPR", "Avg OPR"]):
                pdf.cell(w, 8, h, border=1, ln=0, align="C", fill=True)
            pdf.ln()
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(50, 50, 60)
            for idx, (_, row) in enumerate(seasons_played.iterrows()):
                pdf.set_fill_color(250, 250, 252) if idx % 2 == 0 else pdf.set_fill_color(255, 255, 255)
                vals = [str(row.name), str(int(row["Matches"])), str(int(row["Wins"])), str(int(row["Losses"])), str(int(row["Ties"])), f"{row['Best_OPR']:.1f}", f"{row['Avg_OPR']:.1f}"]
                for w, v in zip(cols_w, vals):
                    pdf.cell(w, 7, v, border=1, ln=0, align="C", fill=True)
                pdf.ln()
            pdf.ln(8)
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(150, 150, 160)
            pdf.cell(0, 6, "Generated by FTC Analytics Dashboard  |  github.com/kaivalya-cyber/ftc-analytics-dataset", ln=True, align="C")
            return pdf.output(dest="S")

        pdf_bytes = generate_pdf()
        st.download_button(
            label="📄 Download Team Report (PDF)",
            data=pdf_bytes,
            file_name=f"team_{team_number}_report.pdf",
            mime="application/pdf",
            key="pdf_report",
        )
    else:
        st.info("No event data found for this team.")
