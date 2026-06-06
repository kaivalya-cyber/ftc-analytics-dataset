#!/usr/bin/env python3
"""
analyze_upsets.py
-----------------
Detects match upsets — when the predicted favorite (by OPR or ELO) loses.
Computes upset rates by season, qual vs playoff, and overall.
Saves results to results/upset_analysis.csv.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def main():
    print("[+] Analyzing Match Upsets...")

    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"
    team_events_file = processed_dir / "team_events.csv"
    elo_file = processed_dir / "current_elo.csv"

    if not matches_file.exists():
        print("[Error] matches.csv not found.")
        return

    matches = pd.read_csv(matches_file)

    # Build OPR lookup (average OPR per team across all events)
    opr_lookup = {}
    if team_events_file.exists():
        te = pd.read_csv(team_events_file)
        opr_counts = {}
        for _, row in te.iterrows():
            tn = int(row["team_number"])
            opr = row["opr"] if not pd.isna(row["opr"]) else 0
            if tn not in opr_lookup:
                opr_lookup[tn] = 0.0
                opr_counts[tn] = 0
            opr_lookup[tn] += opr
            opr_counts[tn] += 1
        for tn in opr_lookup:
            opr_lookup[tn] = opr_lookup[tn] / opr_counts[tn]

    # Build ELO lookup (current ELO rating per team)
    elo_lookup = {}
    if elo_file.exists():
        celo = pd.read_csv(elo_file)
        for _, row in celo.iterrows():
            elo_lookup[int(row["team_number"])] = row["current_elo"]

    # Analyze each match for upsets
    results = []
    for _, row in matches.iterrows():
        r1, r2 = int(row["red_team_1"]), int(row["red_team_2"])
        b1, b2 = int(row["blue_team_1"]), int(row["blue_team_2"])
        winner = row["winner"]
        if winner not in ["red", "blue"]:
            continue

        # OPR prediction
        red_opr = opr_lookup.get(r1, 0) + opr_lookup.get(r2, 0)
        blue_opr = opr_lookup.get(b1, 0) + opr_lookup.get(b2, 0)
        opr_favorite = "red" if red_opr > blue_opr else "blue" if blue_opr > red_opr else "tie"
        opr_upset = (opr_favorite != "tie" and opr_favorite != winner)

        # ELO prediction
        red_elo_vals = [elo_lookup.get(r1, 1500), elo_lookup.get(r2, 1500)]
        blue_elo_vals = [elo_lookup.get(b1, 1500), elo_lookup.get(b2, 1500)]
        red_elo = np.mean(red_elo_vals)
        blue_elo = np.mean(blue_elo_vals)
        elo_favorite = "red" if red_elo > blue_elo else "blue" if blue_elo > red_elo else "tie"
        elo_upset = (elo_favorite != "tie" and elo_favorite != winner)

        results.append({
            "season": row["season"],
            "event_key": row["event_key"],
            "match_number": row["match_number"],
            "is_playoff": row["is_playoff"],
            "red_team_1": r1,
            "red_team_2": r2,
            "blue_team_1": b1,
            "blue_team_2": b2,
            "red_score": row["red_score"],
            "blue_score": row["blue_score"],
            "winner": winner,
            "red_opr_sum": round(red_opr, 1),
            "blue_opr_sum": round(blue_opr, 1),
            "opr_favorite": opr_favorite,
            "opr_upset": opr_upset,
            "red_elo_avg": round(red_elo, 0),
            "blue_elo_avg": round(blue_elo, 0),
            "elo_favorite": elo_favorite,
            "elo_upset": elo_upset,
        })

    upset_df = pd.DataFrame(results)

    # Save detailed results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    upset_df.to_csv(results_dir / "upset_analysis.csv", index=False)

    # Print summary
    total = len(upset_df)
    opr_upsets = upset_df["opr_upset"].sum()
    elo_upsets = upset_df["elo_upset"].sum()

    print(f"\n[+] Processed {total:,} matches (ties excluded)")
    print(f"    OPR upsets: {opr_upsets} ({opr_upsets/total*100:.1f}%)")
    print(f"    ELO upsets: {elo_upsets} ({elo_upsets/total*100:.1f}%)")

    # By season
    print("\n  Upsets by Season:")
    print(f"  {'Season':<8} {'Matches':>8} {'OPR Upsets':>12} {'OPR Rate':>10} {'ELO Upsets':>12} {'ELO Rate':>10}")
    print(f"  {'-'*8} {'-'*8} {'-'*12} {'-'*10} {'-'*12} {'-'*10}")
    for s in sorted(upset_df["season"].unique()):
        sm = upset_df[upset_df["season"] == s]
        ou = sm["opr_upset"].sum()
        eu = sm["elo_upset"].sum()
        print(f"  {s:<8} {len(sm):>8} {ou:>12} {ou/len(sm)*100:>9.1f}% {eu:>12} {eu/len(sm)*100:>9.1f}%")

    # Qual vs Playoff
    qual = upset_df[~upset_df["is_playoff"]]
    playoff = upset_df[upset_df["is_playoff"]]
    print(f"\n  Qualification: {qual['opr_upset'].sum()/len(qual)*100:.1f}% OPR upsets, "
          f"{qual['elo_upset'].sum()/len(qual)*100:.1f}% ELO upsets")
    print(f"  Playoff:       {playoff['opr_upset'].sum()/len(playoff)*100:.1f}% OPR upsets, "
          f"{playoff['elo_upset'].sum()/len(playoff)*100:.1f}% ELO upsets")

    # Biggest upsets (largest OPR diff where underdog won)
    upset_df["opr_diff_abs"] = abs(upset_df["red_opr_sum"] - upset_df["blue_opr_sum"])
    biggest = upset_df[upset_df["opr_upset"]].nlargest(10, "opr_diff_abs")
    print(f"\n  Top 10 Biggest OPR Upsets:")
    for _, r in biggest.iterrows():
        print(f"    {r['season']} {r['event_key']} Q{r['match_number']}: "
              f"Red({r['red_team_1']},{r['red_team_2']}) vs Blue({r['blue_team_1']},{r['blue_team_2']}) "
              f"— OPR diff: {r['opr_diff_abs']:.0f}, Winner: {r['winner']}")

    print(f"\n[+] Results saved to results/upset_analysis.csv")


if __name__ == "__main__":
    main()
