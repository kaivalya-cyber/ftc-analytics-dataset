# FTC Open Analytics Dataset - Data Directory

This directory contains the raw collected data from both The Orange Alliance and FTC Events APIs, as well as the processed canonical CSV files.

## Directory Structure

```
data/
├── raw/
│   ├── toa/               # Raw JSON files from The Orange Alliance API grouped by season
│   └── ftc_events/        # Raw JSON files from FIRST FTC Events API grouped by season
└── processed/             # Cleaned canonical CSV files
    ├── matches.csv        # One row per match
    ├── teams.csv          # One row per team
    └── team_events.csv    # One row per team per event appearance
```

## Schema Definitions

### 1. `matches.csv`
- `match_key` (String): Unique identifier of the match (e.g. `1819-TX-AUSTIN-Q1`).
- `season` (String): FTC season identifier (e.g., `1819` for 2018-19).
- `event_key` (String): Unique key representing the event.
- `event_name` (String): Name of the event.
- `region` (String): Region where the event took place.
- `match_number` (Integer): Match number within the event.
- `red_team_1` (Integer): Team number of red alliance team 1.
- `red_team_2` (Integer): Team number of red alliance team 2.
- `blue_team_1` (Integer): Team number of blue alliance team 1.
- `blue_team_2` (Integer): Team number of blue alliance team 2.
- `red_score` (Integer): Final score of the red alliance.
- `blue_score` (Integer): Final score of the blue alliance.
- `score_diff` (Integer): Score difference (red_score - blue_score).
- `winner` (String): Outcome ("red", "blue", or "tie").
- `is_playoff` (Boolean): True if the match is a playoff/elimination match, False if it is qualification.

### 2. `teams.csv`
- `team_number` (Integer): Unique team number.
- `team_name` (String): Registered name of the team.
- `country` (String): Team's country of origin.
- `state_province` (String): Team's state or province.
- `rookie_year` (Integer): First year the team competed.

### 3. `team_events.csv`
- `team_number` (Integer): Unique team number.
- `event_key` (String): Unique key representing the event.
- `season` (String): FTC season identifier.
- `ranking` (Integer): Team's rank at the event.
- `wins` (Integer): Number of qualification match wins for this team.
- `losses` (Integer): Number of qualification match losses for this team.
- `ties` (Integer): Number of qualification match ties for this team.
- `opr` (Float): Computed Offensive Power Rating for the event.
- `np_opr` (Float): Non-Penalty OPR (OPR computed without penalty scores if penalty data is available).
- `ccwm` (Float): Computed Calculated Contribution to Winning Margin for the event.
