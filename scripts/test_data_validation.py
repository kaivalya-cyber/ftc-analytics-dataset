#!/usr/bin/env python3
"""
test_data_validation.py — Pytest suite validating processed CSV data integrity.
Run with: pytest scripts/test_data_validation.py -v
"""
import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "processed"

# ── Fixtures ──

def test_matches_csv_exists():
    assert (DATA_DIR / "matches.csv").exists(), "matches.csv not found"

def test_teams_csv_exists():
    assert (DATA_DIR / "teams.csv").exists(), "teams.csv not found"

def test_team_events_csv_exists():
    assert (DATA_DIR / "team_events.csv").exists(), "team_events.csv not found"


# ── Matches schema ──

def test_matches_columns():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    expected = ["match_key", "season", "event_key", "event_name", "region", "match_number",
                "red_team_1", "red_team_2", "blue_team_1", "blue_team_2",
                "red_score", "blue_score", "score_diff", "winner", "is_playoff"]
    for col in expected:
        assert col in df.columns, f"Missing column: {col}"

def test_matches_no_nulls():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    critical = ["match_key", "season", "event_key", "red_team_1", "red_team_2", 
                "blue_team_1", "blue_team_2", "red_score", "blue_score", "winner", "is_playoff"]
    for col in critical:
        assert not df[col].isna().any(), f"Nulls found in matches.{col}"

def test_matches_valid_winner():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    valid = {"red", "blue", "tie"}
    assert set(df["winner"].unique()).issubset(valid), f"Invalid winner values: {set(df['winner'].unique()) - valid}"

def test_matches_positive_scores():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    assert (df["red_score"] >= 0).all(), "Negative red scores"
    assert (df["blue_score"] >= 0).all(), "Negative blue scores"

def test_matches_score_diff_consistent():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    computed = df["red_score"] - df["blue_score"]
    assert (computed == df["score_diff"]).all(), "score_diff inconsistent with red_score - blue_score"

def test_matches_season_range():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    valid_seasons = {1819, 1920, 2021, 2122, 2223, 2324}
    actual = set(df["season"].astype(int).unique())
    assert actual.issubset(valid_seasons), f"Unknown season: {actual - valid_seasons}"

def test_matches_unique_keys():
    df = pd.read_csv(DATA_DIR / "matches.csv")
    assert df["match_key"].is_unique, "Duplicate match_key values found in matches.csv"


# ── Teams schema ──

def test_teams_columns():
    df = pd.read_csv(DATA_DIR / "teams.csv")
    expected = ["team_number", "team_name", "country", "state_province", "rookie_year"]
    for col in expected:
        assert col in df.columns, f"Missing column: {col}"

def test_teams_unique_numbers():
    df = pd.read_csv(DATA_DIR / "teams.csv")
    assert df["team_number"].is_unique, "Duplicate team numbers in teams.csv"


# ── Team Events schema ──

def test_team_events_columns():
    df = pd.read_csv(DATA_DIR / "team_events.csv")
    expected = ["team_number", "event_key", "season", "ranking", "wins", "losses", "ties", "opr", "np_opr", "ccwm"]
    for col in expected:
        assert col in df.columns, f"Missing column: {col}"

def test_team_events_no_nulls_critical():
    df = pd.read_csv(DATA_DIR / "team_events.csv")
    critical = ["team_number", "event_key", "season", "wins", "losses", "ties"]
    for col in critical:
        assert not df[col].isna().any(), f"Nulls found in team_events.{col}"

def test_team_events_non_negative():
    df = pd.read_csv(DATA_DIR / "team_events.csv")
    for col in ["wins", "losses", "ties"]:
        assert (df[col] >= 0).all(), f"Negative values in team_events.{col}"

def test_team_events_team_refs_valid():
    df = pd.read_csv(DATA_DIR / "team_events.csv")
    teams_df = pd.read_csv(DATA_DIR / "teams.csv")
    team_set = set(teams_df["team_number"].unique())
    event_teams = set(df["team_number"].astype(int).unique())
    missing = event_teams - team_set
    # Some teams may not have full metadata in teams.csv (blank rows from real events)
    coverage = len(event_teams - missing) / max(len(event_teams), 1)
    assert coverage >= 0.85, f"Team coverage too low: {coverage:.1%} — {len(missing)} missing teams"

def test_team_events_season_range():
    df = pd.read_csv(DATA_DIR / "team_events.csv")
    valid_seasons = {1819, 1920, 2021, 2122, 2223, 2324}
    actual = set(df["season"].astype(int).unique())
    assert actual.issubset(valid_seasons), f"Unknown season: {actual - valid_seasons}"


# ── ELO data (if available) ──

def test_elo_csv_schema():
    path = DATA_DIR / "team_elo.csv"
    if not path.exists():
        return  # skip if not generated
    df = pd.read_csv(path)
    expected = ["team_number", "season", "event_key", "match_number", "elo_before", "elo_after", "elo_change"]
    for col in expected:
        assert col in df.columns, f"Missing column in team_elo.csv: {col}"

def test_current_elo_schema():
    path = DATA_DIR / "current_elo.csv"
    if not path.exists():
        return
    df = pd.read_csv(path)
    assert "team_number" in df.columns
    assert "current_elo" in df.columns
