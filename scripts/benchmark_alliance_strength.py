#!/usr/bin/env python3
"""
benchmark_alliance_strength.py
-------------------------------
Predicts expected playoff wins for a 3-team alliance configuration
(captain + pick 1 + pick 2). Evaluates correlation between predicted
and actual playoff wins, top-N accuracy, and compares against a naive
OPR-sum baseline.

Saves results to results/alliance_strength_benchmark.csv.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from scipy.stats import pearsonr

def main():
    print("[+] Running Alliance Strength Benchmark...")

    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"
    team_events_file = processed_dir / "team_events.csv"
    alliances_file = processed_dir / "playoff_alliances.json"

    if not matches_file.exists() or not team_events_file.exists():
        print("[Error] Processed CSV files do not exist. Run build_dataset.py first.")
        return

    matches_df = pd.read_csv(matches_file)
    team_events_df = pd.read_csv(team_events_file)

    # Load playoff alliance mapping (match_key -> {red: [t1,t2,t3], blue: [t1,t2,t3]})
    playoff_alliances = {}
    if alliances_file.exists():
        with open(alliances_file, "r") as f:
            playoff_alliances = json.load(f)

    if not playoff_alliances:
        print("[Warning] No playoff alliance data found. Generating from playoff matches.")

    # ----------------------------------------------------------------
    # Step 1: Build alliance records from playoff matches
    # An "alliance" is a frozen set of 3 teams that competed together
    # in playoffs at a specific event.
    # ----------------------------------------------------------------
    playoff_matches = matches_df[matches_df["is_playoff"]].copy()

    # Build OPR lookup: (event_key, team_number) -> opr
    opr_lookup = {}
    for _, row in team_events_df.iterrows():
        ek = row["event_key"]
        tn = int(row["team_number"])
        opr_val = row["opr"] if not pd.isna(row["opr"]) else 0.0
        opr_lookup[(ek, tn)] = opr_val

    # Collect alliance-level playoff win counts per event
    # key: (event_key, frozenset(team1, team2, team3)) -> wins
    alliance_wins = {}
    alliance_losses = {}

    for _, row in playoff_matches.iterrows():
        match_key = row["match_key"]
        event_key = row["event_key"]
        winner = row["winner"]

        # Try to get 3-team alliance from the mapping
        mapping = playoff_alliances.get(match_key)
        if mapping:
            red_alliance = tuple(sorted(int(t) for t in mapping["red"]))
            blue_alliance = tuple(sorted(int(t) for t in mapping["blue"]))
        else:
            # Fallback: use the 2 teams from match as a proxy alliance
            red_alliance = tuple(sorted([int(row["red_team_1"]), int(row["red_team_2"])]))
            blue_alliance = tuple(sorted([int(row["blue_team_1"]), int(row["blue_team_2"])]))

        red_key = (event_key, red_alliance)
        blue_key = (event_key, blue_alliance)

        alliance_wins.setdefault(red_key, 0)
        alliance_wins.setdefault(blue_key, 0)
        alliance_losses.setdefault(red_key, 0)
        alliance_losses.setdefault(blue_key, 0)

        if winner == "red":
            alliance_wins[red_key] += 1
            alliance_losses[blue_key] += 1
        elif winner == "blue":
            alliance_wins[blue_key] += 1
            alliance_losses[red_key] += 1

    # ----------------------------------------------------------------
    # Step 2: Build feature matrix for alliance strength prediction
    # Features: sum OPR of all alliance members, avg OPR, max OPR,
    #           min OPR, OPR std
    # Target: playoff wins
    # ----------------------------------------------------------------
    records = []
    for (event_key, team_tuple), wins in alliance_wins.items():
        losses = alliance_losses.get((event_key, team_tuple), 0)

        oprs = []
        for t in team_tuple:
            oprs.append(opr_lookup.get((event_key, t), 0.0))

        if not oprs:
            continue

        sum_opr = sum(oprs)
        avg_opr = np.mean(oprs)
        max_opr = max(oprs)
        min_opr = min(oprs)
        std_opr = np.std(oprs) if len(oprs) > 1 else 0.0

        records.append({
            "event_key": event_key,
            "alliance_teams": str(team_tuple),
            "num_teams": len(team_tuple),
            "sum_opr": sum_opr,
            "avg_opr": avg_opr,
            "max_opr": max_opr,
            "min_opr": min_opr,
            "std_opr": std_opr,
            "playoff_wins": wins,
            "playoff_losses": losses,
        })

    if not records:
        print("[Error] No alliance records could be built. Check playoff data.")
        return

    df = pd.DataFrame(records)
    print(f"  - Total alliance records: {len(df)}")
    print(f"  - Mean playoff wins:      {df['playoff_wins'].mean():.2f}")
    print(f"  - Max playoff wins:       {df['playoff_wins'].max()}")

    # ----------------------------------------------------------------
    # Step 3: Train / test split by season (embedded in event_key)
    # Train on everything except the last season (2324)
    # ----------------------------------------------------------------
    df["season"] = df["event_key"].apply(lambda x: x.split("-")[0])

    train_seasons = ["1819", "1920", "2021", "2122", "2223"]
    test_season = "2324"

    train_df = df[df["season"].isin(train_seasons)]
    test_df = df[df["season"] == test_season]

    if len(test_df) == 0:
        # If there is no test data for 2324, use last 20% of data instead
        print("[Warning] No test data for season 2324. Using last 20% of data.")
        split_idx = int(len(df) * 0.8)
        train_df = df.iloc[:split_idx]
        test_df = df.iloc[split_idx:]

    print(f"  - Train alliances: {len(train_df)}")
    print(f"  - Test alliances:  {len(test_df)}")

    feature_cols = ["sum_opr", "avg_opr", "max_opr", "min_opr", "std_opr"]
    X_train = train_df[feature_cols].values
    y_train = train_df["playoff_wins"].values
    X_test = test_df[feature_cols].values
    y_test = test_df["playoff_wins"].values

    # ----------------------------------------------------------------
    # Naive Baseline: sum OPR of 3 teams → predicted wins
    # ----------------------------------------------------------------
    naive_pred = test_df["sum_opr"].values
    # Scale naive predictions to match the target range
    if naive_pred.std() > 0:
        naive_pred_scaled = (naive_pred - naive_pred.mean()) / naive_pred.std()
        naive_pred_scaled = naive_pred_scaled * y_train.std() + y_train.mean()
    else:
        naive_pred_scaled = np.full_like(naive_pred, y_train.mean())

    # ----------------------------------------------------------------
    # Linear Regression model
    # ----------------------------------------------------------------
    lr = LinearRegression()
    lr.fit(X_train, y_train)
    lr_pred = lr.predict(X_test)

    # ----------------------------------------------------------------
    # Evaluation
    # ----------------------------------------------------------------
    def evaluate(name, y_true, y_pred):
        # Correlation
        if len(y_true) < 3 or np.std(y_true) == 0 or np.std(y_pred) == 0:
            corr = 0.0
            p_val = 1.0
        else:
            corr, p_val = pearsonr(y_true, y_pred)

        # MAE
        mae = np.mean(np.abs(y_true - y_pred))

        # Top-N accuracy: for each event, was the alliance with highest
        # predicted strength the one with the most actual wins?
        # Group by event
        events = test_df["event_key"].unique()
        top1_correct = 0
        top2_correct = 0
        events_evaluated = 0

        for ek in events:
            mask = test_df["event_key"].values == ek
            if mask.sum() < 2:
                continue
            events_evaluated += 1
            local_true = y_true[mask]
            local_pred = y_pred[mask]

            best_actual = np.argmax(local_true)
            sorted_pred = np.argsort(-local_pred)

            if sorted_pred[0] == best_actual:
                top1_correct += 1
            if best_actual in sorted_pred[:2]:
                top2_correct += 1

        top1_acc = top1_correct / events_evaluated if events_evaluated > 0 else 0.0
        top2_acc = top2_correct / events_evaluated if events_evaluated > 0 else 0.0

        return {
            "Model": name,
            "Pearson r": round(corr, 4),
            "p-value": round(p_val, 6),
            "MAE": round(mae, 4),
            "Top-1 Acc": round(top1_acc, 4),
            "Top-2 Acc": round(top2_acc, 4),
        }

    naive_results = evaluate("Naive OPR Sum", y_test, naive_pred_scaled)
    lr_results = evaluate("Linear Regression", y_test, lr_pred)

    results_df = pd.DataFrame([naive_results, lr_results])

    # Save results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    results_df.to_csv(results_dir / "alliance_strength_benchmark.csv", index=False)

    print("\n" + "=" * 70)
    print("ALLIANCE STRENGTH BENCHMARK RESULTS")
    print("=" * 70)
    print(results_df.to_markdown(index=False))
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
