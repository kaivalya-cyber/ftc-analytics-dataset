#!/usr/bin/env python3
"""
benchmark_win_prediction.py
---------------------------
Loads matches.csv and team_events.csv.
Splits events into train (seasons 1819 through 2223) and test (season 2324).
Builds features: OPR diff, CCWM diff, win rate diff, and historical head-to-head.
Trains three models:
1. OPR Difference Baseline
2. Logistic Regression
3. Gradient Boosted Trees (GBDT)
Evaluates Accuracy, AUC-ROC, Brier Score, and Log Loss.
Saves results to results/win_prediction_benchmark.csv.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, roc_auc_score, brier_score_loss, log_loss

try:
    from xgboost import XGBClassifier
    HAS_XGBOOST = True
except ImportError:
    HAS_XGBOOST = False

def calculate_h2h_matrix(train_matches_df):
    """
    Computes a head-to-head record dictionary from the training set.
    Maps (team_A, team_B) -> net wins for team_A against team_B.
    """
    h2h = {}
    for idx, row in train_matches_df.iterrows():
        r1, r2, b1, b2 = row["red_team_1"], row["red_team_2"], row["blue_team_1"], row["blue_team_2"]
        winner = row["winner"]
        if winner not in ["red", "blue"]:
            continue
            
        red_teams = [r1, r2]
        blue_teams = [b1, b2]
        
        for r in red_teams:
            for b in blue_teams:
                # If red won, net win for r vs b increases by 1, and decreases for b vs r
                if winner == "red":
                    h2h[(r, b)] = h2h.get((r, b), 0) + 1
                    h2h[(b, r)] = h2h.get((b, r), 0) - 1
                else:
                    h2h[(r, b)] = h2h.get((r, b), 0) - 1
                    h2h[(b, r)] = h2h.get((b, r), 0) + 1
    return h2h

def get_h2h_feature(r1, r2, b1, b2, h2h_matrix):
    """
    Calculates the sum of net wins for red alliance teams against blue alliance teams.
    """
    net_wins = 0
    red_teams = [r1, r2]
    blue_teams = [b1, b2]
    for r in red_teams:
        for b in blue_teams:
            net_wins += h2h_matrix.get((r, b), 0)
    return net_wins

def main():
    print("[+] Running Win Prediction Benchmark...")
    
    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"
    team_events_file = processed_dir / "team_events.csv"
    
    if not matches_file.exists() or not team_events_file.exists():
        print("[Error] Processed CSV files do not exist. Please run build_dataset.py first.")
        return
        
    matches_df = pd.read_csv(matches_file)
    team_events_df = pd.read_csv(team_events_file)
    
    # Filter out ties for binary classification
    matches_df = matches_df[matches_df["winner"].isin(["red", "blue"])].copy()
    matches_df["label"] = (matches_df["winner"] == "red").astype(int)
    
    # Create lookup dictionary for team stats at each event
    # key: (event_key, team_number) -> (opr, ccwm, win_rate)
    stats_lookup = {}
    for idx, row in team_events_df.iterrows():
        event_key = row["event_key"]
        t_num = row["team_number"]
        opr = row["opr"] if not pd.isna(row["opr"]) else 0.0
        ccwm = row["ccwm"] if not pd.isna(row["ccwm"]) else 0.0
        
        wins = row["wins"]
        losses = row["losses"]
        ties = row["ties"]
        denom = wins + losses + ties
        win_rate = wins / denom if denom > 0 else 0.0
        
        stats_lookup[(event_key, t_num)] = (opr, ccwm, win_rate)
        
    # Split train/test by event
    # Train: seasons 1819 through 2223
    # Test: season 2324
    train_seasons = ["1819", "1920", "2021", "2122", "2223"]
    test_seasons = ["2324"]
    
    train_matches = matches_df[matches_df["season"].astype(str).isin(train_seasons)].copy()
    test_matches = matches_df[matches_df["season"].astype(str).isin(test_seasons)].copy()
    
    print(f"  - Training matches: {len(train_matches)}")
    print(f"  - Testing matches:  {len(test_matches)}")
    
    # Compute head-to-head records from training set
    h2h_matrix = calculate_h2h_matrix(train_matches)
    
    # Build feature sets
    def extract_features(df, is_train):
        features_list = []
        for idx, row in df.iterrows():
            event_key = row["event_key"]
            r1, r2 = row["red_team_1"], row["red_team_2"]
            b1, b2 = row["blue_team_1"], row["blue_team_2"]
            
            # Lookup stats (default to 0 if not found)
            r1_opr, r1_ccwm, r1_wr = stats_lookup.get((event_key, r1), (0.0, 0.0, 0.0))
            r2_opr, r2_ccwm, r2_wr = stats_lookup.get((event_key, r2), (0.0, 0.0, 0.0))
            b1_opr, b1_ccwm, b1_wr = stats_lookup.get((event_key, b1), (0.0, 0.0, 0.0))
            b2_opr, b2_ccwm, b2_wr = stats_lookup.get((event_key, b2), (0.0, 0.0, 0.0))
            
            red_opr_sum = r1_opr + r2_opr
            blue_opr_sum = b1_opr + b2_opr
            opr_diff = red_opr_sum - blue_opr_sum
            
            red_ccwm_sum = r1_ccwm + r2_ccwm
            blue_ccwm_sum = b1_ccwm + b2_ccwm
            ccwm_diff = red_ccwm_sum - blue_ccwm_sum
            
            red_wr_sum = r1_wr + r2_wr
            blue_wr_sum = b1_wr + b2_wr
            wr_diff = red_wr_sum - blue_wr_sum
            
            # Head to head record
            h2h = get_h2h_feature(r1, r2, b1, b2, h2h_matrix)
            
            features_list.append({
                "opr_diff": opr_diff,
                "ccwm_diff": ccwm_diff,
                "wr_diff": wr_diff,
                "h2h": h2h,
                "label": row["label"]
            })
        return pd.DataFrame(features_list)
        
    train_feat = extract_features(train_matches, is_train=True)
    test_feat = extract_features(test_matches, is_train=False)
    
    # Define models
    X_train = train_feat[["opr_diff", "ccwm_diff", "wr_diff", "h2h"]]
    y_train = train_feat["label"]
    
    X_test = test_feat[["opr_diff", "ccwm_diff", "wr_diff", "h2h"]]
    y_test = test_feat["label"]
    
    # 1. OPR Difference Baseline
    # Predict red wins if opr_diff > 0 (probability = 1 if >0 else 0)
    # To compute Log Loss and Brier Score, we'll map opr_diff to a sigmoid probability
    opr_diff_std = X_test["opr_diff"].std()
    # Simple sigmoid to output soft probabilities for baseline metrics
    opr_prob = 1 / (1 + np.exp(-X_test["opr_diff"] / (opr_diff_std + 1e-5)))
    opr_pred = (X_test["opr_diff"] > 0).astype(int)
    # 2. Logistic Regression
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train[["opr_diff", "ccwm_diff", "wr_diff"]])
    X_test_scaled = scaler.transform(X_test[["opr_diff", "ccwm_diff", "wr_diff"]])
    
    lr = LogisticRegression()
    lr.fit(X_train_scaled, y_train)
    lr_pred = lr.predict(X_test_scaled)
    lr_prob = lr.predict_proba(X_test_scaled)[:, 1]
    
    # 3. GBDT Classifier
    gb = GradientBoostingClassifier(random_state=42)
    gb.fit(X_train, y_train)
    gb_pred = gb.predict(X_test)
    gb_prob = gb.predict_proba(X_test)[:, 1]
    
    # 4. Random Forest (with tuned params if available)
    rf_params_override = {}
    tuned_json = Path("results/tuned_params.json")
    if tuned_json.exists():
        import json
        with open(tuned_json) as f:
            tuned = json.load(f)
        if "RandomForest" in tuned:
            rf_params_override = tuned["RandomForest"]["best_params"]
            print(f"  Using tuned RF params: {rf_params_override}")
    rf = RandomForestClassifier(random_state=42, **rf_params_override)
    rf.fit(X_train, y_train)
    rf_pred = rf.predict(X_test)
    rf_prob = rf.predict_proba(X_test)[:, 1]
    
    # 5. XGBoost (with tuned params if available)
    xgb_pred, xgb_prob = None, None
    acc_xgb, auc_xgb, brier_xgb, logloss_xgb = None, None, None, None
    if HAS_XGBOOST:
        xgb_params_override = {}
        if tuned_json.exists():
            with open(tuned_json) as f:
                tuned = json.load(f)
            if "XGBoost" in tuned:
                xgb_params_override = tuned["XGBoost"]["best_params"]
                print(f"  Using tuned XGB params: {xgb_params_override}")
        xgb = XGBClassifier(random_state=42, verbosity=0, **xgb_params_override)
        xgb.fit(X_train, y_train)
        xgb_pred = xgb.predict(X_test)
        xgb_prob = xgb.predict_proba(X_test)[:, 1]
    
    # Evaluation helper
    def evaluate_model(y_true, y_pred, y_prob):
        acc = accuracy_score(y_true, y_pred)
        auc = roc_auc_score(y_true, y_prob)
        brier = brier_score_loss(y_true, y_prob)
        logloss = log_loss(y_true, y_prob)
        return acc, auc, brier, logloss
        
    acc_opr, auc_opr, brier_opr, logloss_opr = evaluate_model(y_test, opr_pred, opr_prob)
    acc_lr, auc_lr, brier_lr, logloss_lr = evaluate_model(y_test, lr_pred, lr_prob)
    acc_gb, auc_gb, brier_gb, logloss_gb = evaluate_model(y_test, gb_pred, gb_prob)
    acc_rf, auc_rf, brier_rf, logloss_rf = evaluate_model(y_test, rf_pred, rf_prob)
    
    if HAS_XGBOOST and xgb_pred is not None:
        acc_xgb, auc_xgb, brier_xgb, logloss_xgb = evaluate_model(y_test, xgb_pred, xgb_prob)
    
    results = [
        {"Model": "OPR Difference Baseline", "Accuracy": acc_opr, "AUC-ROC": auc_opr, "Brier Score": brier_opr, "Log Loss": logloss_opr},
        {"Model": "Logistic Regression", "Accuracy": acc_lr, "AUC-ROC": auc_lr, "Brier Score": brier_lr, "Log Loss": logloss_lr},
        {"Model": "Gradient Boosted Trees", "Accuracy": acc_gb, "AUC-ROC": auc_gb, "Brier Score": brier_gb, "Log Loss": logloss_gb},
        {"Model": "Random Forest (tuned)", "Accuracy": acc_rf, "AUC-ROC": auc_rf, "Brier Score": brier_rf, "Log Loss": logloss_rf},
    ]
    
    if HAS_XGBOOST and xgb_pred is not None:
        results.append(
            {"Model": "XGBoost (tuned)", "Accuracy": acc_xgb, "AUC-ROC": auc_xgb, "Brier Score": brier_xgb, "Log Loss": logloss_xgb}
        )
    
    results_df = pd.DataFrame(results)
    
    # Write to CSV
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    results_df.to_csv(results_dir / "win_prediction_benchmark.csv", index=False)
    
    print("\n" + "="*70)
    print("WIN PREDICTION BENCHMARK RESULTS (TEST SET: SEASON 2324)")
    print("="*70)
    print(results_df.to_markdown(index=False))
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
