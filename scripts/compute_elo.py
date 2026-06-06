#!/usr/bin/env python3
"""
compute_elo.py
--------------
Computes rolling ELO ratings for every FTC team across all matches in
chronological order (by season, event, match_number).

ELO formula:
  expected_A = 1 / (1 + 10^((rating_B - rating_A) / 400))
  new_rating = old_rating + K * (actual - expected)

For 2v2 alliance matches:
  - Alliance rating = average of the two team ratings
  - Each team on the winning alliance gets credited with 1.0 (win)
  - Each team on the losing alliance gets 0.0 (loss)
  - Ties give 0.5 to both sides

K-factor: 32 (standard)
Starting ELO: 1500

Output: data/processed/team_elo.csv with columns:
  team_number, season, event_key, match_number, elo_before, elo_after, elo_change
"""

import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

K_FACTOR = 32
STARTING_ELO = 1500


def expected_score(rating_a, rating_b):
    """Probability team A beats team B given their ELO ratings."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def main():
    print("[+] Computing ELO ratings...")

    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"

    if not matches_file.exists():
        print("[Error] matches.csv not found. Run build_dataset.py first.")
        return

    matches = pd.read_csv(matches_file)

    # Sort matches chronologically: by season, then event_key (alpha = date order proxy),
    # then match_number
    matches = matches.sort_values(["season", "event_key", "match_number"]).reset_index(drop=True)

    # Initialize all team ELOs at 1500
    elo = defaultdict(lambda: STARTING_ELO)

    # Track ELO history for output
    elo_history = []

    total = len(matches)
    for idx, row in matches.iterrows():
        r1, r2 = int(row["red_team_1"]), int(row["red_team_2"])
        b1, b2 = int(row["blue_team_1"]), int(row["blue_team_2"])
        winner = row["winner"]

        # Alliance average ELOs
        red_elo_avg = (elo[r1] + elo[r2]) / 2.0
        blue_elo_avg = (elo[b1] + elo[b2]) / 2.0

        exp_red = expected_score(red_elo_avg, blue_elo_avg)
        exp_blue = 1.0 - exp_red

        # Determine actual outcomes
        if winner == "red":
            actual_red, actual_blue = 1.0, 0.0
        elif winner == "blue":
            actual_red, actual_blue = 0.0, 1.0
        else:  # tie
            actual_red, actual_blue = 0.5, 0.5

        # Store ELO before update
        for team in [r1, r2, b1, b2]:
            elo_history.append({
                "team_number": team,
                "season": row["season"],
                "event_key": row["event_key"],
                "match_number": row["match_number"],
                "elo_before": round(elo[team], 1),
            })

        # Update ELOs
        # Each team on an alliance gets the same delta (based on alliance-level outcome)
        red_delta = K_FACTOR * (actual_red - exp_red)
        blue_delta = K_FACTOR * (actual_blue - exp_blue)

        elo[r1] += red_delta
        elo[r2] += red_delta
        elo[b1] += blue_delta
        elo[b2] += blue_delta

        # Store ELO after update
        for i, team in enumerate([r1, r2, b1, b2]):
            delta = red_delta if i < 2 else blue_delta
            elo_history[-4 + i]["elo_after"] = round(elo[team], 1)
            elo_history[-4 + i]["elo_change"] = round(delta, 2)

        if (idx + 1) % 500 == 0:
            print(f"  Processed {idx + 1}/{total} matches...")

    # Build output DataFrame
    elo_df = pd.DataFrame(elo_history)

    # Also build a "current ELO" snapshot per team
    current_elo = pd.DataFrame([
        {"team_number": t, "current_elo": round(e, 1)}
        for t, e in sorted(elo.items())
    ])

    # Save
    elo_df.to_csv(processed_dir / "team_elo.csv", index=False)
    current_elo.to_csv(processed_dir / "current_elo.csv", index=False)

    print(f"\n[+] ELO computation complete!")
    print(f"    {len(elo_df):,} ELO records written to data/processed/team_elo.csv")
    print(f"    {len(current_elo):,} teams in data/processed/current_elo.csv")
    print(f"    ELO range: {elo_df['elo_after'].min():.0f} – {elo_df['elo_after'].max():.0f}")
    print(f"    Top 5 teams by current ELO:")
    for _, row in current_elo.sort_values("current_elo", ascending=False).head(5).iterrows():
        print(f"      Team {int(row['team_number'])}: {row['current_elo']:.0f}")


if __name__ == "__main__":
    main()
