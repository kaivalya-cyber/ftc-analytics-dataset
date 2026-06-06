#!/usr/bin/env python3
"""
tune_models.py
--------------
Hyperparameter tuning for Random Forest and XGBoost classifiers
using GridSearchCV with time-series-aware cross-validation on the
training set (seasons 1819-2223). Reports best parameters and
evaluates on the held-out test set (season 2324).

Saves best params to results/tuned_params.json and prints comparison.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import GridSearchCV, TimeSeriesSplit
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss
from sklearn.preprocessing import StandardScaler

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


def calculate_h2h_matrix(train_matches_df):
    """Build head-to-head record dictionary from training set."""
    h2h = {}
    for _, row in train_matches_df.iterrows():
        r1, r2, b1, b2 = row["red_team_1"], row["red_team_2"], row["blue_team_1"], row["blue_team_2"]
        winner = row["winner"]
        if winner not in ["red", "blue"]:
            continue
        red_teams = [r1, r2]
        blue_teams = [b1, b2]
        for r in red_teams:
            for b in blue_teams:
                if winner == "red":
                    h2h[(r, b)] = h2h.get((r, b), 0) + 1
                    h2h[(b, r)] = h2h.get((b, r), 0) - 1
                else:
                    h2h[(r, b)] = h2h.get((r, b), 0) - 1
                    h2h[(b, r)] = h2h.get((b, r), 0) + 1
    return h2h


def get_h2h_feature(r1, r2, b1, b2, h2h_matrix):
    """Net wins for red alliance teams vs blue alliance teams."""
    net_wins = 0
    for r in [r1, r2]:
        for b in [b1, b2]:
            net_wins += h2h_matrix.get((r, b), 0)
    return net_wins

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False


def main():
    print("[+] Running Hyperparameter Tuning...")

    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"
    team_events_file = processed_dir / "team_events.csv"

    if not matches_file.exists() or not team_events_file.exists():
        print("[Error] Processed CSV files not found. Run build_dataset.py first.")
        return

    matches_df = pd.read_csv(matches_file)
    team_events_df = pd.read_csv(team_events_file)

    # Filter ties
    matches_df = matches_df[matches_df["winner"].isin(["red", "blue"])].copy()
    matches_df["label"] = (matches_df["winner"] == "red").astype(int)

    # Build stats lookup
    stats_lookup = {}
    for _, row in team_events_df.iterrows():
        event_key = row["event_key"]
        t_num = row["team_number"]
        opr = row["opr"] if not pd.isna(row["opr"]) else 0.0
        ccwm = row["ccwm"] if not pd.isna(row["ccwm"]) else 0.0
        wins, losses, ties = row["wins"], row["losses"], row["ties"]
        denom = wins + losses + ties
        wr = wins / denom if denom > 0 else 0.0
        stats_lookup[(event_key, t_num)] = (opr, ccwm, wr)

    # Split
    train_seasons = ["1819", "1920", "2021", "2122", "2223"]
    test_seasons = ["2324"]
    train_matches = matches_df[matches_df["season"].astype(str).isin(train_seasons)].copy()
    test_matches = matches_df[matches_df["season"].astype(str).isin(test_seasons)].copy()

    print(f"  Train: {len(train_matches)} matches, Test: {len(test_matches)} matches")

    # Compute head-to-head from training set
    h2h_matrix = calculate_h2h_matrix(train_matches)

    # Build features (matching benchmark: opr_diff, ccwm_diff, wr_diff, h2h)
    def extract_features(df, h2h_mat):
        rows = []
        for _, row in df.iterrows():
            ek = row["event_key"]
            r1, r2 = int(row["red_team_1"]), int(row["red_team_2"])
            b1, b2 = int(row["blue_team_1"]), int(row["blue_team_2"])

            r1_o, r1_c, r1_w = stats_lookup.get((ek, r1), (0, 0, 0))
            r2_o, r2_c, r2_w = stats_lookup.get((ek, r2), (0, 0, 0))
            b1_o, b1_c, b1_w = stats_lookup.get((ek, b1), (0, 0, 0))
            b2_o, b2_c, b2_w = stats_lookup.get((ek, b2), (0, 0, 0))

            rows.append({
                "opr_diff": (r1_o + r2_o) - (b1_o + b2_o),
                "ccwm_diff": (r1_c + r2_c) - (b1_c + b2_c),
                "wr_diff": (r1_w + r2_w) - (b1_w + b2_w),
                "h2h": get_h2h_feature(r1, r2, b1, b2, h2h_mat),
                "label": row["label"],
            })
        return pd.DataFrame(rows)

    train_feat = extract_features(train_matches, h2h_matrix)
    test_feat = extract_features(test_matches, h2h_matrix)

    X_train = train_feat[["opr_diff", "ccwm_diff", "wr_diff", "h2h"]]
    y_train = train_feat["label"]
    X_test = test_feat[["opr_diff", "ccwm_diff", "wr_diff", "h2h"]]
    y_test = test_feat["label"]

    # Time-series cross-validation (5 splits, no shuffling for temporal data)
    tscv = TimeSeriesSplit(n_splits=5)

    results = {}

    # ---- Random Forest Grid Search ----
    print("\n[+] Tuning Random Forest...")
    rf_params = {
        "n_estimators": [50, 100, 200],
        "max_depth": [3, 5, 8, None],
        "min_samples_split": [2, 5, 10],
        "min_samples_leaf": [1, 2, 4],
    }
    rf_grid = GridSearchCV(
        RandomForestClassifier(random_state=42),
        rf_params,
        cv=tscv,
        scoring="roc_auc",
        n_jobs=-1,
        verbose=1,
    )
    rf_grid.fit(X_train, y_train)

    rf_best = rf_grid.best_estimator_
    rf_pred = rf_best.predict(X_test)
    rf_prob = rf_best.predict_proba(X_test)[:, 1]

    rf_acc = accuracy_score(y_test, rf_pred)
    rf_auc = roc_auc_score(y_test, rf_prob)
    rf_brier = brier_score_loss(y_test, rf_prob)
    rf_ll = log_loss(y_test, rf_prob)

    print(f"  Best RF params: {rf_grid.best_params_}")
    print(f"  RF Best CV AUC: {rf_grid.best_score_:.4f}")
    print(f"  RF Test Accuracy: {rf_acc:.4f}, AUC: {rf_auc:.4f}")

    results["RandomForest"] = {
        "best_params": rf_grid.best_params_,
        "best_cv_auc": round(float(rf_grid.best_score_), 4),
        "test_accuracy": round(float(rf_acc), 4),
        "test_auc": round(float(rf_auc), 4),
        "test_brier": round(float(rf_brier), 4),
        "test_logloss": round(float(rf_ll), 4),
    }

    # ---- XGBoost Grid Search ----
    if HAS_XGBOOST:
        print("\n[+] Tuning XGBoost...")
        xgb_params = {
            "n_estimators": [50, 100, 200],
            "max_depth": [2, 3, 5],
            "learning_rate": [0.01, 0.1, 0.2],
            "subsample": [0.8, 1.0],
            "colsample_bytree": [0.8, 1.0],
        }
        xgb_grid = GridSearchCV(
            XGBClassifier(random_state=42, verbosity=0),
            xgb_params,
            cv=tscv,
            scoring="roc_auc",
            n_jobs=-1,
            verbose=1,
        )
        xgb_grid.fit(X_train, y_train)

        xgb_best = xgb_grid.best_estimator_
        xgb_pred = xgb_best.predict(X_test)
        xgb_prob = xgb_best.predict_proba(X_test)[:, 1]

        xgb_acc = accuracy_score(y_test, xgb_pred)
        xgb_auc = roc_auc_score(y_test, xgb_prob)
        xgb_brier = brier_score_loss(y_test, xgb_prob)
        xgb_ll = log_loss(y_test, xgb_prob)

        print(f"  Best XGB params: {xgb_grid.best_params_}")
        print(f"  XGB Best CV AUC: {xgb_grid.best_score_:.4f}")
        print(f"  XGB Test Accuracy: {xgb_acc:.4f}, AUC: {xgb_auc:.4f}")

        results["XGBoost"] = {
            "best_params": xgb_grid.best_params_,
            "best_cv_auc": round(float(xgb_grid.best_score_), 4),
            "test_accuracy": round(float(xgb_acc), 4),
            "test_auc": round(float(xgb_auc), 4),
            "test_brier": round(float(xgb_brier), 4),
            "test_logloss": round(float(xgb_ll), 4),
        }

    # Save results
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    with open(results_dir / "tuned_params.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\n[+] Results saved to results/tuned_params.json")

    # Summary table
    print("\n" + "=" * 70)
    print("TUNING SUMMARY (Test Set: Season 2324)")
    print("=" * 70)
    print(f"{'Model':<16} {'Accuracy':>10} {'AUC':>8} {'Brier':>8} {'LogLoss':>8}")
    print("-" * 54)
    for model, r in results.items():
        print(f"{model:<16} {r['test_accuracy']:>10.4f} {r['test_auc']:>8.4f} {r['test_brier']:>8.4f} {r['test_logloss']:>8.4f}")
    print("=" * 70)

    # Comparison with defaults
    print("\n📊 Improvement over defaults:")
    # Default RF (100 trees, no tuning): 0.6508 acc, 0.7752 AUC
    print(f"  RF default:  0.6508 acc, 0.7752 AUC")
    print(f"  RF tuned:    {rf_acc:.4f} acc, {rf_auc:.4f} AUC (Δ [acc]: {rf_acc - 0.6508:+.4f}, Δ [auc]: {rf_auc - 0.7752:+.4f})")
    if HAS_XGBOOST:
        print(f"  XGB default: 0.6746 acc, 0.7734 AUC")
        print(f"  XGB tuned:   {xgb_acc:.4f} acc, {xgb_auc:.4f} AUC (Δ [acc]: {xgb_acc - 0.6746:+.4f}, Δ [auc]: {xgb_auc - 0.7734:+.4f})")
    print()


if __name__ == "__main__":
    main()
