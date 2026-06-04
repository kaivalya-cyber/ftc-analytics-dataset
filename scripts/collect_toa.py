#!/usr/bin/env python3
"""
collect_toa.py
--------------
Collects match and team data from The Orange Alliance (TOA) API for seasons 2018-19
through 2023-24. Saves raw JSON files to data/raw/toa/{season}/{event_key}.json.
Implements exponential backoff for rate-limiting and a Mock Mode fallback if API keys
are not configured.
"""

import os
import time
import json
import random
import requests
from pathlib import Path
from tqdm import tqdm
from dotenv import load_dotenv

# Load env variables
load_dotenv()

BASE_URL = "https://theorangealliance.org/api"
SEASONS = ["1819", "1920", "2021", "2122", "2223", "2324"]

def make_request_with_backoff(url, headers, params=None):
    """
    Makes an HTTP GET request with exponential backoff to handle rate limits (429).
    """
    backoff = 1.0
    max_backoff = 30.0
    while True:
        try:
            response = requests.get(url, headers=headers, params=params, timeout=15)
            if response.status_code == 429:
                print(f"\n[Rate Limit] Received 429. Backing off for {backoff:.1f}s...")
                time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue
            return response
        except requests.RequestException as e:
            print(f"\n[Connection Error] {e}. Retrying in {backoff:.1f}s...")
            time.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)

def generate_mock_event_data(season, event_key):
    """
    Generates realistic synthetic data for an event, including matches and teams.
    Used when running in Mock Mode.
    """
    regions = ["TX", "CA", "NY", "MI", "FL", "WA", "IL"]
    region = event_key.split("-")[1] if "-" in event_key else random.choice(regions)
    
    # Generate list of teams for this event
    # We want teams to overlap across events and seasons to make the dataset interesting
    random.seed(event_key)
    num_teams = random.randint(12, 36)
    team_numbers = sorted(random.sample(range(1000, 25000), num_teams))
    
    teams_data = []
    for t_num in team_numbers:
        teams_data.append({
            "team_number": t_num,
            "team_name_short": f"Robot Dogs {t_num}",
            "country": "USA",
            "state_code": region,
            "rookie_year": random.randint(2005, 2023)
        })
        
    matches_data = []
    
    # Generate Qualification Matches
    # Every team plays around 5-6 matches
    num_quals = (num_teams * 5) // 4
    if num_quals < 10:
        num_quals = 15
        
    for m_num in range(1, num_quals + 1):
        # Pick 4 unique teams
        match_teams = random.sample(team_numbers, 4)
        r1, r2, b1, b2 = match_teams
        
        # OPR-based scoring simulation
        # Assign a latent "strength" to each team to make OPR calculation meaningful
        def get_strength(t):
            return 30 + (t % 7) * 15 + (t % 3) * 10
            
        r_strength = get_strength(r1) + get_strength(r2)
        b_strength = get_strength(b1) + get_strength(b2)
        
        # Add score variation and penalties
        r_score = max(0, int(random.normalvariate(r_strength, 20)))
        b_score = max(0, int(random.normalvariate(b_strength, 20)))
        r_pen = random.choice([0, 0, 0, 5, 10, 30])
        b_pen = random.choice([0, 0, 0, 5, 10, 30])
        
        # Add penalties to final scores
        r_score_final = r_score + b_pen
        b_score_final = b_score + r_pen
        
        winner = "red" if r_score_final > b_score_final else ("blue" if b_score_final > r_score_final else "tie")
        
        matches_data.append({
            "match_key": f"{event_key}-Q-{m_num:03d}",
            "event_key": event_key,
            "match_name": f"Quals {m_num}",
            "tournament_level": 1,
            "match_number": m_num,
            "red_score": r_score_final,
            "blue_score": b_score_final,
            "red_min_pen": r_pen,
            "blue_min_pen": b_pen,
            "participants": [
                {"team_key": str(r1), "station": 11, "station_status": 1},
                {"team_key": str(r2), "station": 12, "station_status": 1},
                {"team_key": str(b1), "station": 21, "station_status": 1},
                {"team_key": str(b2), "station": 22, "station_status": 1}
            ],
            "winner": winner
        })
        
    # Generate Playoff Matches (Semi-finals and Finals)
    # 4 Alliances (each has Captain, Pick 1, Pick 2. For match, 2 play)
    # Let's say top 4 teams are captains, next 4 are Pick 1, next 4 are Pick 2
    # Simple simulation: just generate 6 playoff matches (2 Semis best-of-3, 1 Finals best-of-3)
    playoff_alliances = []
    # Sort teams by their mock OPR (strength) to make playoff alliances make sense
    sorted_teams = sorted(team_numbers, key=get_strength, reverse=True)
    if len(sorted_teams) >= 12:
        alliances = {
            1: [sorted_teams[0], sorted_teams[7], sorted_teams[11]],
            2: [sorted_teams[1], sorted_teams[6], sorted_teams[10]],
            3: [sorted_teams[2], sorted_teams[5], sorted_teams[9]],
            4: [sorted_teams[3], sorted_teams[4], sorted_teams[8]]
        }
    else:
        # Fallback if too few teams
        alliances = {
            1: sorted_teams[0:3] if len(sorted_teams) >= 3 else sorted_teams * 3,
            2: sorted_teams[1:4] if len(sorted_teams) >= 4 else sorted_teams * 3,
            3: sorted_teams[2:5] if len(sorted_teams) >= 5 else sorted_teams * 3,
            4: sorted_teams[3:6] if len(sorted_teams) >= 6 else sorted_teams * 3
        }
        
    # Match simulator for playoffs
    def sim_playoff_match(alliance_red_id, alliance_blue_id, m_type, m_num):
        red_t = alliances[alliance_red_id]
        blue_t = alliances[alliance_blue_id]
        # Choose captain + pick 1 for the match
        r1, r2 = red_t[0], red_t[1]
        b1, b2 = blue_t[0], blue_t[1]
        
        r_strength = get_strength(r1) + get_strength(r2) + 15  # playoff boost
        b_strength = get_strength(b1) + get_strength(b2) + 15
        
        r_score = max(0, int(random.normalvariate(r_strength, 15)))
        b_score = max(0, int(random.normalvariate(b_strength, 15)))
        
        r_score_final = r_score
        b_score_final = b_score
        
        winner = "red" if r_score_final > b_score_final else "blue" # no ties in playoffs
        
        return {
            "match_key": f"{event_key}-{m_type}-{m_num}",
            "event_key": event_key,
            "match_name": f"{m_type} {m_num}",
            "tournament_level": 2,
            "match_number": m_num,
            "red_score": r_score_final,
            "blue_score": b_score_final,
            "red_min_pen": 0,
            "blue_min_pen": 0,
            "participants": [
                {"team_key": str(r1), "station": 11, "station_status": 1},
                {"team_key": str(r2), "station": 12, "station_status": 1},
                {"team_key": str(b1), "station": 21, "station_status": 1},
                {"team_key": str(b2), "station": 22, "station_status": 1}
            ],
            "winner": winner,
            # Store alliance selection mapping for alliance strength benchmark
            "playoff_alliances": {
                "red": [str(x) for x in red_t],
                "blue": [str(x) for x in blue_t]
            }
        }

    # Semis: 1 vs 4, 2 vs 3
    # Semi 1 Match 1 & 2 (and 3 if tie)
    matches_data.append(sim_playoff_match(1, 4, "E-SF1", 1))
    matches_data.append(sim_playoff_match(1, 4, "E-SF1", 2))
    if random.choice([True, False]):
        matches_data.append(sim_playoff_match(1, 4, "E-SF1", 3))
        
    matches_data.append(sim_playoff_match(2, 3, "E-SF2", 1))
    matches_data.append(sim_playoff_match(2, 3, "E-SF2", 2))
    if random.choice([True, False]):
        matches_data.append(sim_playoff_match(2, 3, "E-SF2", 3))
        
    # Finals: Winner Semi 1 vs Winner Semi 2 (assume 1 vs 2 for mock simplicity)
    matches_data.append(sim_playoff_match(1, 2, "E-F", 1))
    matches_data.append(sim_playoff_match(1, 2, "E-F", 2))
    if random.choice([True, False]):
        matches_data.append(sim_playoff_match(1, 2, "E-F", 3))
        
    return {
        "event_key": event_key,
        "event_name": f"Mock Event {event_key.split('-')[2]}",
        "region_key": region,
        "season_key": season,
        "matches": matches_data,
        "teams": teams_data
    }

def main():
    toa_api_key = os.getenv("TOA_API_KEY")
    # Check if we should run in Mock Mode
    is_mock = not toa_api_key or toa_api_key == "your_toa_api_key_here"
    
    if is_mock:
        print("[!] TOA_API_KEY is not configured. Running in MOCK MODE to generate synthetic dataset.")
    else:
        print("[+] TOA_API_KEY found. Fetching real data from The Orange Alliance API.")
        
    raw_dir = Path("data/raw/toa")
    raw_dir.mkdir(parents=True, exist_ok=True)
    
    headers = {
        "X-TOA-Key": toa_api_key if toa_api_key else "",
        "X-Application-Origin": "FTC Open Analytics Dataset",
        "Accept": "application/json"
    }
    
    for season in SEASONS:
        print(f"\nProcessing Season {season}...")
        season_dir = raw_dir / season
        season_dir.mkdir(exist_ok=True)
        
        if is_mock:
            # Generate synthetic events
            # Let's say 4 events per season
            num_events = 4
            event_keys = [f"{season}-TX-E0{i}" for i in range(1, num_events + 1)]
            
            pbar = tqdm(event_keys, desc=f"Generating season {season} mock data")
            for event_key in pbar:
                event_data = generate_mock_event_data(season, event_key)
                # Save file
                file_path = season_dir / f"{event_key}.json"
                with open(file_path, "w") as f:
                    json.dump(event_data, f, indent=2)
                pbar.set_postfix_str(f"{len(event_data['matches'])} matches, {len(event_data['teams'])} teams")
                time.sleep(0.05)
        else:
            # Hit actual API to fetch events for this season
            events_url = f"{BASE_URL}/event"
            params = {"season_key": season}
            resp = make_request_with_backoff(events_url, headers, params=params)
            
            if resp.status_code != 200:
                print(f"Error fetching events for season {season}: {resp.status_code} - {resp.text}")
                print("[!] Falling back to mock data generation for this season.")
                # generate mock instead
                num_events = 4
                event_keys = [f"{season}-TX-E0{i}" for i in range(1, num_events + 1)]
                for event_key in event_keys:
                    event_data = generate_mock_event_data(season, event_key)
                    with open(season_dir / f"{event_key}.json", "w") as f:
                        json.dump(event_data, f, indent=2)
                continue
                
            events = resp.json()
            # Filter events to avoid massive payload during testing, take up to 5 events
            events_to_fetch = events[:5]
            print(f"Found {len(events)} events. Fetching details for first {len(events_to_fetch)} events to respect rate limits.")
            
            for event in tqdm(events_to_fetch, desc=f"Fetching season {season} events"):
                event_key = event.get("event_key")
                if not event_key:
                    continue
                    
                # Fetch matches
                matches_url = f"{BASE_URL}/event/{event_key}/matches"
                matches_resp = make_request_with_backoff(matches_url, headers)
                matches_data = matches_resp.json() if matches_resp.status_code == 200 else []
                
                # Fetch teams
                teams_url = f"{BASE_URL}/event/{event_key}/teams"
                teams_resp = make_request_with_backoff(teams_url, headers)
                teams_data = teams_resp.json() if teams_resp.status_code == 200 else []
                
                event_details = {
                    "event_key": event_key,
                    "event_name": event.get("event_name"),
                    "region_key": event.get("region_key"),
                    "season_key": season,
                    "matches": matches_data,
                    "teams": teams_data
                }
                
                # Save file
                file_path = season_dir / f"{event_key}.json"
                with open(file_path, "w") as f:
                    json.dump(event_details, f, indent=2)
                time.sleep(0.5) # rate limit politeness

    print("\n[+] TOA data collection completed successfully!")

if __name__ == "__main__":
    main()
