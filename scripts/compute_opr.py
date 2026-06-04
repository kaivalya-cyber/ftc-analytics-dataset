#!/usr/bin/env python3
"""
compute_opr.py
--------------
Loads matches.csv and team_events.csv from data/processed/.
For each event, solves least squares M * x = y to compute:
- OPR (Offensive Power Rating)
- CCWM (Calculated Contribution to Winning Margin)
- NP_OPR (Non-Penalty OPR) using raw penalty data where available.
Updates team_events.csv with the computed metrics.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np
from scipy.linalg import lstsq

def load_penalties():
    """
    Loads penalty information from raw JSON files to compute NP_OPR.
    Returns a dictionary mapping match_key to (red_penalty, blue_penalty).
    """
    penalties = {}
    
    # Scan TOA raw data
    toa_dir = Path("data/raw/toa")
    if toa_dir.exists():
        for season_dir in toa_dir.iterdir():
            if not season_dir.is_dir():
                continue
            for file_path in season_dir.glob("*.json"):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    for m in data.get("matches", []):
                        m_key = m.get("match_key")
                        if m_key:
                            r_pen = m.get("red_min_pen", 0)
                            b_pen = m.get("blue_min_pen", 0)
                            penalties[m_key] = (r_pen, b_pen)
                except Exception:
                    pass
                    
    # Scan FTC Events raw data
    ftc_dir = Path("data/raw/ftc_events")
    if ftc_dir.exists():
        for season_dir in ftc_dir.iterdir():
            if not season_dir.is_dir():
                continue
            for file_path in season_dir.glob("*.json"):
                try:
                    event_code = file_path.stem
                    season = season_dir.name
                    with open(file_path, "r") as f:
                        data = json.load(f)
                    for m in data.get("matches", []):
                        m_num = m.get("matchNumber")
                        level = m.get("tournamentLevel", "Qualification")
                        lvl_code = "Q" if level == "Qualification" else "E"
                        m_key = f"{season}-TX-{event_code}-{lvl_code}-{m_num:03d}"
                        # Note: FTC Events API does not always have explicit penalties in matches payload,
                        # so we default to 0 if not present.
                        penalties[m_key] = (0, 0)
                except Exception:
                    pass
                    
    return penalties

def main():
    print("[+] Calculating OPR, CCWM, and NP_OPR...")
    
    processed_dir = Path("data/processed")
    matches_file = processed_dir / "matches.csv"
    team_events_file = processed_dir / "team_events.csv"
    
    if not matches_file.exists() or not team_events_file.exists():
        print("[Error] Processed CSV files do not exist. Please run build_dataset.py first.")
        return
        
    matches_df = pd.read_csv(matches_file)
    team_events_df = pd.read_csv(team_events_file)
    
    # Load penalties for NP_OPR computation
    penalties = load_penalties()
    
    # Add temporary penalty columns to matches_df
    def get_red_pen(key):
        return penalties.get(key, (0, 0))[0]
    def get_blue_pen(key):
        return penalties.get(key, (0, 0))[1]
        
    matches_df["red_penalty"] = matches_df["match_key"].apply(get_red_pen)
    matches_df["blue_penalty"] = matches_df["match_key"].apply(get_blue_pen)
    
    # Calculate non-penalty scores
    # Red non-penalty score = red_score - blue_penalty (the penalty points awarded to red)
    # Blue non-penalty score = blue_score - red_penalty (the penalty points awarded to blue)
    matches_df["red_np_score"] = matches_df["red_score"] - matches_df["blue_penalty"]
    matches_df["blue_np_score"] = matches_df["blue_score"] - matches_df["red_penalty"]
    
    # We only compute OPRs based on qualification matches
    quals = matches_df[~matches_df["is_playoff"]]
    
    # Pre-populate OPR columns in team_events as float
    team_events_df["opr"] = np.nan
    team_events_df["np_opr"] = np.nan
    team_events_df["ccwm"] = np.nan
    
    grouped_events = quals.groupby("event_key")
    
    for event_key, event_matches in grouped_events:
        # Get unique teams at this event
        teams_at_event = sorted(list(set(
            event_matches["red_team_1"].tolist() +
            event_matches["red_team_2"].tolist() +
            event_matches["blue_team_1"].tolist() +
            event_matches["blue_team_2"].tolist()
        )))
        
        num_teams = len(teams_at_event)
        num_matches = len(event_matches)
        
        # Check edge cases: events with fewer than 6 teams (skip)
        if num_teams < 6:
            print(f"  - Skipping event {event_key} due to low team count ({num_teams} teams).")
            continue
            
        # Map team numbers to matrix indices
        team_idx_map = {t: i for i, t in enumerate(teams_at_event)}
        
        # Build alliance participation matrix M (2 * num_matches rows, num_teams columns)
        M = np.zeros((2 * num_matches, num_teams))
        y_opr = np.zeros(2 * num_matches)
        y_ccwm = np.zeros(2 * num_matches)
        y_np_opr = np.zeros(2 * num_matches)
        
        for idx, (_, row) in enumerate(event_matches.iterrows()):
            r1_idx = team_idx_map[row["red_team_1"]]
            r2_idx = team_idx_map[row["red_team_2"]]
            b1_idx = team_idx_map[row["blue_team_1"]]
            b2_idx = team_idx_map[row["blue_team_2"]]
            
            # Red alliance row
            M[2 * idx, r1_idx] = 1.0
            M[2 * idx, r2_idx] = 1.0
            y_opr[2 * idx] = row["red_score"]
            y_np_opr[2 * idx] = row["red_np_score"]
            y_ccwm[2 * idx] = row["red_score"] - row["blue_score"]
            
            # Blue alliance row
            M[2 * idx + 1, b1_idx] = 1.0
            M[2 * idx + 1, b2_idx] = 1.0
            y_opr[2 * idx + 1] = row["blue_score"]
            y_np_opr[2 * idx + 1] = row["blue_np_score"]
            y_ccwm[2 * idx + 1] = row["blue_score"] - row["red_score"]
            
        # Solve least squares M * x = y
        # We use scipy.linalg.lstsq which returns least-squares solution.
        # It handles rank deficient matrices gracefully via SVD.
        try:
            opr_sol, _, _, _ = lstsq(M, y_opr)
            np_opr_sol, _, _, _ = lstsq(M, y_np_opr)
            ccwm_sol, _, _, _ = lstsq(M, y_ccwm)
            
            # Map solutions back to team_events
            for t_num in teams_at_event:
                t_idx = team_idx_map[t_num]
                
                # Update team_events_df where event_key and team_number match
                mask = (team_events_df["event_key"] == event_key) & (team_events_df["team_number"] == t_num)
                team_events_df.loc[mask, "opr"] = round(float(opr_sol[t_idx]), 2)
                team_events_df.loc[mask, "np_opr"] = round(float(np_opr_sol[t_idx]), 2)
                team_events_df.loc[mask, "ccwm"] = round(float(ccwm_sol[t_idx]), 2)
        except Exception as e:
            print(f"[Warning] Failed to solve OPR for event {event_key}: {e}")
            
    # Save updated team_events.csv
    team_events_df.to_csv(team_events_file, index=False)
    print(f"[+] OPR, CCWM, and NP_OPR calculations completed and saved to {team_events_file}!")
    
    # Print sample stats
    print("\nSummary Statistics of Computed Metrics:")
    valid_oprs = team_events_df["opr"].dropna()
    valid_ccwms = team_events_df["ccwm"].dropna()
    print(f"  - Total Computed OPRs: {len(valid_oprs)}")
    print(f"  - Mean OPR:            {valid_oprs.mean():.2f}")
    print(f"  - Max OPR:             {valid_oprs.max():.2f}")
    print(f"  - Min OPR:             {valid_oprs.min():.2f}")
    print(f"  - Mean CCWM:           {valid_ccwms.mean():.2f}")
    print(f"  - Max CCWM:            {valid_ccwms.max():.2f}")
    print(f"  - Min CCWM:            {valid_ccwms.min():.2f}")

if __name__ == "__main__":
    main()
