#!/usr/bin/env python3
"""
build_dataset.py
----------------
Reads all raw JSON files from data/raw/toa/ and data/raw/ftc_events/.
Cleans, normalizes, and packages data into three canonical CSVs:
1. data/processed/matches.csv
2. data/processed/teams.csv
3. data/processed/team_events.csv
Applies data cleaning rules and prints a detailed data quality report.
"""

import json
from pathlib import Path
import pandas as pd
import numpy as np

def clean_string(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def process_toa_data(toa_dir, matches, teams_dict, team_events_records, dropped_counts):
    """
    Processes all raw JSON files in the TOA directory.
    """
    if not toa_dir.exists():
        return
        
    for season_path in sorted(toa_dir.iterdir()):
        if not season_path.is_dir():
            continue
        season = season_path.name
        
        for file_path in season_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                event_key = clean_string(data.get("event_key"))
                event_name = clean_string(data.get("event_name"))
                region = clean_string(data.get("region_key"))
                
                # Process Teams
                for t in data.get("teams", []):
                    t_num = t.get("team_number")
                    if t_num is None:
                        continue
                    try:
                        t_num = int(t_num)
                    except ValueError:
                        continue
                        
                    if t_num not in teams_dict:
                        teams_dict[t_num] = {
                            "team_number": t_num,
                            "team_name": clean_string(t.get("team_name_short") or t.get("team_name")),
                            "country": clean_string(t.get("country")),
                            "state_province": clean_string(t.get("state_code") or t.get("state")),
                            "rookie_year": t.get("rookie_year")
                        }
                
                # Process Matches
                for m in data.get("matches", []):
                    match_key = clean_string(m.get("match_key"))
                    match_number = m.get("match_number")
                    red_score = m.get("red_score")
                    blue_score = m.get("blue_score")
                    
                    # Flag playoff
                    # Level 1 is quals, 2+ is playoff
                    level = m.get("tournament_level", 1)
                    is_playoff = int(level) > 1
                    
                    # Extract teams
                    participants = m.get("participants", [])
                    red_alliance = []
                    blue_alliance = []
                    
                    for p in participants:
                        t_key = p.get("team_key")
                        if not t_key:
                            continue
                        try:
                            t_num = int(t_key)
                        except ValueError:
                            continue
                        
                        station = p.get("station")
                        if isinstance(station, int):
                            if station in [11, 12, 13]:
                                red_alliance.append(t_num)
                            elif station in [21, 22, 23]:
                                blue_alliance.append(t_num)
                        elif isinstance(station, str):
                            if station.lower().startswith("red"):
                                red_alliance.append(t_num)
                            elif station.lower().startswith("blue"):
                                blue_alliance.append(t_num)
                                
                    # Cleaning Rules
                    if not match_key:
                        dropped_counts["missing_match_key"] += 1
                        continue
                    if red_score is None or blue_score is None:
                        dropped_counts["missing_scores"] += 1
                        continue
                    if red_score < 0 or blue_score < 0:
                        dropped_counts["negative_scores"] += 1
                        continue
                    if len(red_alliance) < 2 or len(blue_alliance) < 2:
                        dropped_counts["missing_teams"] += 1
                        continue
                        
                    r1, r2 = red_alliance[0], red_alliance[1]
                    b1, b2 = blue_alliance[0], blue_alliance[1]
                    
                    if r1 == 0 or r2 == 0 or b1 == 0 or b2 == 0:
                        dropped_counts["zero_team_number"] += 1
                        continue
                        
                    # Normalize Winner
                    winner = clean_string(m.get("winner")).lower()
                    if winner not in ["red", "blue", "tie"]:
                        if red_score > blue_score:
                            winner = "red"
                        elif blue_score > red_score:
                            winner = "blue"
                        else:
                            winner = "tie"
                            
                    matches.append({
                        "match_key": match_key,
                        "season": season,
                        "event_key": event_key,
                        "event_name": event_name,
                        "region": region,
                        "match_number": int(match_number) if match_number is not None else 1,
                        "red_team_1": r1,
                        "red_team_2": r2,
                        "blue_team_1": b1,
                        "blue_team_2": b2,
                        "red_score": int(red_score),
                        "blue_score": int(blue_score),
                        "score_diff": int(red_score) - int(blue_score),
                        "winner": winner,
                        "is_playoff": is_playoff,
                        # Pass along raw alliances list for playoffs mapping
                        "playoff_alliances": m.get("playoff_alliances")
                    })
            except Exception as e:
                print(f"[Warning] Failed to process TOA file {file_path}: {e}")

def process_ftc_events_data(ftc_dir, matches, teams_dict, dropped_counts):
    """
    Processes all raw JSON files in the FTC Events directory.
    """
    if not ftc_dir.exists():
        return
        
    for season_path in sorted(ftc_dir.iterdir()):
        if not season_path.is_dir():
            continue
        season = season_path.name
        
        for file_path in season_path.glob("*.json"):
            try:
                with open(file_path, "r") as f:
                    data = json.load(f)
                    
                # Read metadata with fallback to old mock behavior
                event_code = data.get("event_code", file_path.stem)
                event_name = data.get("event_name", f"Event {event_code}")
                region = data.get("region", "TX")
                
                event_key = f"{season}-{region}-{event_code}"
                
                for m in data.get("matches", []):
                    match_number = m.get("matchNumber")
                    red_score = m.get("scoreRedFinal")
                    blue_score = m.get("scoreBlueFinal")
                    
                    # Handle both new uppercase and old mixed case strings
                    level = m.get("tournamentLevel", "Qualification")
                    is_playoff = level.upper() != "QUALIFICATION"
                    lvl_code = "Q" if not is_playoff else "E"
                    
                    match_key = f"{season}-{region}-{event_code}-{lvl_code}-{match_number:03d}"
                    
                    # Extract teams
                    red_alliance = []
                    blue_alliance = []
                    
                    for t in m.get("teams", []):
                        t_num = t.get("teamNumber")
                        if t_num is None:
                            continue
                        try:
                            t_num = int(t_num)
                        except ValueError:
                            continue
                            
                        station = clean_string(t.get("station"))
                        if station.lower().startswith("red"):
                            red_alliance.append(t_num)
                        elif station.lower().startswith("blue"):
                            blue_alliance.append(t_num)
                            
                    # Cleaning Rules
                    if red_score is None or blue_score is None:
                        dropped_counts["missing_scores"] += 1
                        continue
                    if red_score < 0 or blue_score < 0:
                        dropped_counts["negative_scores"] += 1
                        continue
                    if len(red_alliance) < 2 or len(blue_alliance) < 2:
                        dropped_counts["missing_teams"] += 1
                        continue
                        
                    r1, r2 = red_alliance[0], red_alliance[1]
                    b1, b2 = blue_alliance[0], blue_alliance[1]
                    
                    if r1 == 0 or r2 == 0 or b1 == 0 or b2 == 0:
                        dropped_counts["zero_team_number"] += 1
                        continue
                        
                    if red_score > blue_score:
                        winner = "red"
                    elif blue_score > red_score:
                        winner = "blue"
                    else:
                        winner = "tie"
                        
                    matches.append({
                        "match_key": match_key,
                        "season": season,
                        "event_key": event_key,
                        "event_name": event_name,
                        "region": region,
                        "match_number": int(match_number) if match_number is not None else 1,
                        "red_team_1": r1,
                        "red_team_2": r2,
                        "blue_team_1": b1,
                        "blue_team_2": b2,
                        "red_score": int(red_score),
                        "blue_score": int(blue_score),
                        "score_diff": int(red_score) - int(blue_score),
                        "winner": winner,
                        "is_playoff": is_playoff,
                        "playoff_alliances": None
                    })
            except Exception as e:
                print(f"[Warning] Failed to process FTC Events file {file_path}: {e}")

def build_team_events(matches_df):
    """
    Builds the team_events records from the qualification matches of each team.
    Calculates rankings, wins, losses, ties.
    """
    records = []
    
    # We only compute wins, losses, ties from qualification matches
    quals = matches_df[~matches_df["is_playoff"]]
    
    # Group by event_key and find all participating teams
    event_groups = quals.groupby("event_key")
    
    for event_key, event_matches in event_groups:
        season = event_matches["season"].iloc[0]
        
        # Get unique teams at this event
        teams_at_event = set()
        for idx, row in event_matches.iterrows():
            teams_at_event.add(row["red_team_1"])
            teams_at_event.add(row["red_team_2"])
            teams_at_event.add(row["blue_team_1"])
            teams_at_event.add(row["blue_team_2"])
            
        team_stats = {t: {"wins": 0, "losses": 0, "ties": 0, "scores": [], "matches_played": 0} for t in teams_at_event}
        
        # Aggregate match outcomes
        for idx, row in event_matches.iterrows():
            r1, r2, b1, b2 = row["red_team_1"], row["red_team_2"], row["blue_team_1"], row["blue_team_2"]
            r_score, b_score = row["red_score"], row["blue_score"]
            winner = row["winner"]
            
            for t in [r1, r2]:
                team_stats[t]["scores"].append(r_score)
                team_stats[t]["matches_played"] += 1
                if winner == "red":
                    team_stats[t]["wins"] += 1
                elif winner == "blue":
                    team_stats[t]["losses"] += 1
                else:
                    team_stats[t]["ties"] += 1
                    
            for t in [b1, b2]:
                team_stats[t]["scores"].append(b_score)
                team_stats[t]["matches_played"] += 1
                if winner == "blue":
                    team_stats[t]["wins"] += 1
                elif winner == "red":
                    team_stats[t]["losses"] += 1
                else:
                    team_stats[t]["ties"] += 1
                    
        # Compute ranking points (wins * 2 + ties * 1) and average scores to break ties
        team_rank_data = []
        for t, stats in team_stats.items():
            rp = stats["wins"] * 2 + stats["ties"] * 1
            avg_score = np.mean(stats["scores"]) if stats["scores"] else 0
            team_rank_data.append({
                "team_number": t,
                "rp": rp,
                "avg_score": avg_score,
                "wins": stats["wins"],
                "losses": stats["losses"],
                "ties": stats["ties"]
            })
            
        # Sort teams: RP descending, Avg Score descending
        sorted_ranks = sorted(team_rank_data, key=lambda x: (x["rp"], x["avg_score"]), reverse=True)
        
        for rank, data in enumerate(sorted_ranks, 1):
            records.append({
                "team_number": data["team_number"],
                "event_key": event_key,
                "season": season,
                "ranking": rank,
                "wins": data["wins"],
                "losses": data["losses"],
                "ties": data["ties"],
                "opr": np.nan,  # to be computed in next script
                "np_opr": np.nan,
                "ccwm": np.nan
            })
            
    return pd.DataFrame(records)

def main():
    print("[+] Building canonical dataset...")
    
    matches = []
    teams_dict = {}
    team_events_records = []
    
    dropped_counts = {
        "missing_match_key": 0,
        "missing_scores": 0,
        "negative_scores": 0,
        "missing_teams": 0,
        "zero_team_number": 0
    }
    
    # Process raw data
    process_toa_data(Path("data/raw/toa"), matches, teams_dict, team_events_records, dropped_counts)
    process_ftc_events_data(Path("data/raw/ftc_events"), matches, teams_dict, dropped_counts)
    
    total_raw_processed = len(matches) + sum(dropped_counts.values())
    
    # Build Matches DataFrame
    matches_df = pd.DataFrame(matches)
    
    # Drop duplicates by match_key
    before_dedup = len(matches_df)
    matches_df.drop_duplicates(subset=["match_key"], inplace=True)
    dedup_dropped = before_dedup - len(matches_df)
    
    # Build Teams DataFrame
    teams_df = pd.DataFrame(list(teams_dict.values()))
    
    # Build Team Events DataFrame
    team_events_df = build_team_events(matches_df)
    
    # Save files
    processed_dir = Path("data/processed")
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    # Store playoff alliances if any (will drop from final CSV column but keep for temporary mapping)
    # Actually, let's keep playoff_alliances in matches_df for the next steps or write a helper json
    playoff_alliances_mapping = {}
    for idx, row in matches_df.iterrows():
        if row["is_playoff"] and row["playoff_alliances"]:
            playoff_alliances_mapping[row["match_key"]] = row["playoff_alliances"]
            
    # Drop the temporary column before saving matches.csv
    matches_csv_df = matches_df.drop(columns=["playoff_alliances"], errors="ignore")
    matches_csv_df.to_csv(processed_dir / "matches.csv", index=False)
    teams_df.to_csv(processed_dir / "teams.csv", index=False)
    team_events_df.to_csv(processed_dir / "team_events.csv", index=False)
    
    # Save the playoff alliances to a helper json for Step 7
    with open(processed_dir / "playoff_alliances.json", "w") as f:
        json.dump(playoff_alliances_mapping, f, indent=2)
        
    print(f"[+] Processed data written to {processed_dir}/")
    
    # DATA QUALITY REPORT
    print("\n" + "="*50)
    print("DATA QUALITY REPORT")
    print("="*50)
    print(f"Total Raw Records Evaluated: {total_raw_processed}")
    print(f"Total Matches Saved:         {len(matches_df)}")
    print(f"Total Teams Saved:           {len(teams_df)}")
    print(f"Total Team-Event Appearances:{len(team_events_df)}")
    
    print("\nDropped Records Breakdown:")
    total_dropped = sum(dropped_counts.values()) + dedup_dropped
    pct_dropped = (total_dropped / total_raw_processed * 100) if total_raw_processed > 0 else 0
    print(f"Total Dropped: {total_dropped} ({pct_dropped:.2f}%)")
    for reason, count in dropped_counts.items():
        print(f"  - {reason}: {count}")
    print(f"  - duplicates: {dedup_dropped}")
    
    print("\nMatches Per Season:")
    season_counts = matches_df["season"].value_counts().sort_index()
    for s, c in season_counts.items():
        print(f"  - Season {s}: {c} matches")
        
    print("\nScore Distribution Stats:")
    all_scores = pd.concat([matches_df["red_score"], matches_df["blue_score"]])
    print(f"  - Min Score:    {all_scores.min()}")
    print(f"  - Max Score:    {all_scores.max()}")
    print(f"  - Mean Score:   {all_scores.mean():.2f}")
    print(f"  - Median Score: {all_scores.median():.2f}")
    print(f"  - Std Dev:      {all_scores.std():.2f}")
    
    print("\nScore Distribution Per Season:")
    for season in sorted(matches_df["season"].unique()):
        season_df = matches_df[matches_df["season"] == season]
        season_scores = pd.concat([season_df["red_score"], season_df["blue_score"]])
        print(f"  Season {season}: Mean={season_scores.mean():.2f}, Median={season_scores.median():.2f}, Std={season_scores.std():.2f}")
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
