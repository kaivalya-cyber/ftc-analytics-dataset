import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from shared import inject_css, load_data, build_lookups, stat_card_html, hero_header, render_sidebar

st.set_page_config(page_title="Head-to-Head", page_icon="🤝", layout="wide")
inject_css()
matches, teams, team_events, elo_df, current_elo = load_data()
render_sidebar(matches, teams)
_, _, _, _, _ = build_lookups(matches, teams, team_events, current_elo)

hero_header("🤝 Head-to-Head", "Compare any two teams — see their full match history, win/loss records, and score timelines.")
team_list = sorted(teams["team_number"].unique())
col_a, col_b = st.columns(2)
with col_a: team_a = st.selectbox("Team A", team_list, key="h2h_a", index=0)
with col_b: team_b = st.selectbox("Team B", team_list, key="h2h_b", index=min(1, len(team_list)-1))

if team_a and team_b and team_a != team_b:
    h2h_matches = matches[(((matches["red_team_1"]==team_a)|(matches["red_team_2"]==team_a))&((matches["blue_team_1"]==team_b)|(matches["blue_team_2"]==team_b)))|(((matches["red_team_1"]==team_b)|(matches["red_team_2"]==team_b))&((matches["blue_team_1"]==team_a)|(matches["blue_team_2"]==team_a)))].sort_values(["season","event_key","match_number"])
    if len(h2h_matches)==0:
        st.info(f"Team {team_a} and Team {team_b} have never faced each other in this dataset.")
    else:
        a_is_red=(h2h_matches["red_team_1"]==team_a)|(h2h_matches["red_team_2"]==team_a)
        a_wins=((a_is_red)&(h2h_matches["winner"]=="red")).sum()+((~a_is_red)&(h2h_matches["winner"]=="blue")).sum()
        b_wins=((a_is_red)&(h2h_matches["winner"]=="blue")).sum()+((~a_is_red)&(h2h_matches["winner"]=="red")).sum()
        ties=(h2h_matches["winner"]=="tie").sum()
        c1,c2,c3,c4=st.columns(4)
        with c1: st.markdown(stat_card_html("⚔️",str(len(h2h_matches)),"Total Matches","accent-red"), unsafe_allow_html=True)
        with c2: st.markdown(stat_card_html("🏆",str(a_wins),f"Team {team_a} Wins","accent-blue"), unsafe_allow_html=True)
        with c3: st.markdown(stat_card_html("🏆",str(b_wins),f"Team {team_b} Wins","accent-orange"), unsafe_allow_html=True)
        with c4: st.markdown(stat_card_html("🤝",str(ties),"Ties","accent-green"), unsafe_allow_html=True)
        a_scores,b_scores=[],[]
        for _,r in h2h_matches.iterrows():
            a_red=(r["red_team_1"]==team_a)or(r["red_team_2"]==team_a)
            a_scores.append(r["red_score"] if a_red else r["blue_score"])
            b_scores.append(r["blue_score"] if a_red else r["red_score"])
        st.markdown("---")
        cc1,cc2=st.columns(2)
        with cc1:
            cc1.metric(f"Team {team_a} Avg Score",f"{np.mean(a_scores):.1f}")
            cc1.metric(f"Team {team_b} Avg Score",f"{np.mean(b_scores):.1f}")
        with cc2:
            c1,c2,_=st.columns([1,1,1])
            with c1: st.metric("Max Margin",f"{max(abs(np.array(a_scores)-np.array(b_scores))):.0f}")
            with c2: st.metric("Seasons",str(h2h_matches["season"].nunique()))
        st.markdown("### 📋 Match History")
        h2h_d=h2h_matches[["season","event_key","match_number","red_team_1","red_team_2","blue_team_1","blue_team_2","red_score","blue_score","winner","is_playoff"]].copy()
        h2h_d["Result"]=h2h_d.apply(lambda r:f"{int(r['red_score'])}–{int(r['blue_score'])}",axis=1)
        st.dataframe(h2h_d[["season","event_key","match_number","Result","winner","is_playoff"]].rename(columns={"season":"Season","event_key":"Event","match_number":"Match #","is_playoff":"Playoff","winner":"Winner"}),use_container_width=True,hide_index=True)
        st.markdown("### 📈 Score Timeline")
        st.caption(f"Red = Team {team_a}, Blue = Team {team_b}")
        timeline=pd.DataFrame({"Match #":range(1,len(h2h_matches)+1),f"Team {team_a}":a_scores,f"Team {team_b}":b_scores}).set_index("Match #")
        st.line_chart(timeline,use_container_width=True)

        # Score differential bar chart
        st.markdown("### 📊 Score Differential")
        diffs = np.array(a_scores) - np.array(b_scores)
        colors = ["#E74C3C" if d > 0 else ("#3498DB" if d < 0 else "#888888") for d in diffs]
        fig = go.Figure(data=[go.Bar(
            x=list(range(1, len(diffs) + 1)),
            y=diffs,
            marker_color=colors,
            text=[f"+{int(d)}" if d > 0 else (f"{int(d)}" if d < 0 else "TIE") for d in diffs],
            textposition="outside",
            textfont=dict(color="#f0f0f5"),
            hovertemplate=f"Team {team_a} %{{text}} vs Team {team_b}<extra></extra>"
        )])
        fig.update_layout(
            title=f"Team {team_a} Margin Over Team {team_b}",
            xaxis_title="Match #",
            yaxis_title=f"Score Differential (+{team_a} / −{team_b})",
            template="plotly_dark",
            height=400,
            bargap=0.25,
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#f0f0f5"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.08)", dtick=1),
            yaxis=dict(gridcolor="rgba(255,255,255,0.08)", zerolinecolor="rgba(255,255,255,0.2)"),
        )
        st.plotly_chart(fig, use_container_width=True)
elif team_a==team_b:
    st.info("Please select two different teams to compare.")
