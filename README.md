# FTC Open Analytics Dataset

A clean, structured, public dataset of FIRST Tech Challenge (FTC) match results spanning the 2018-19 through 2023-24 seasons, with computed performance metrics (OPR, CCWM, NP-OPR) and baseline machine learning benchmarks for match outcome prediction and playoff alliance strength estimation.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## Dataset Statistics

| Metric | Value |
|:---|---:|
| Seasons Covered | 6 (1819–2324) |
| Events | 24 |
| Total Matches | 877 |
| Qualification Matches | 685 |
| Playoff Matches | 192 |
| Unique Teams | 531 |
| Mean Score | 195.07 |
| Score Range | 20 – 317 |

### Matches Per Season

| Season | Matches | Mean Score | Median Score | Std Dev |
|:---|---:|---:|---:|---:|
| 1819 (Rover Ruckus) | 133 | 200.33 | 205.00 | 46.19 |
| 1920 (Skystone) | 142 | 186.89 | 191.00 | 51.17 |
| 2021 (Ultimate Goal) | 156 | 196.95 | 189.50 | 53.70 |
| 2122 (Freight Frenzy) | 128 | 195.33 | 197.00 | 52.77 |
| 2223 (Power Play) | 171 | 194.43 | 195.00 | 53.35 |
| 2324 (Centerstage) | 147 | 196.75 | 203.00 | 56.98 |

## Data Schema

### `matches.csv` — One row per match

| Column | Type | Description |
|:---|:---|:---|
| `match_key` | String | Unique match identifier (e.g. `1819-TX-AUSTIN-Q1`) |
| `season` | String | FTC season identifier (`1819`–`2324`) |
| `event_key` | String | Event key string |
| `event_name` | String | Human-readable event name |
| `region` | String | Region code (e.g. `TX`) |
| `match_number` | Integer | Match number within the event |
| `red_team_1` | Integer | Red alliance team 1 number |
| `red_team_2` | Integer | Red alliance team 2 number |
| `blue_team_1` | Integer | Blue alliance team 1 number |
| `blue_team_2` | Integer | Blue alliance team 2 number |
| `red_score` | Integer | Final red alliance score |
| `blue_score` | Integer | Final blue alliance score |
| `score_diff` | Integer | Score difference (red − blue) |
| `winner` | String | Outcome: `red`, `blue`, or `tie` |
| `is_playoff` | Boolean | `True` for playoff/elimination matches |

### `teams.csv` — One row per team

| Column | Type | Description |
|:---|:---|:---|
| `team_number` | Integer | Unique FTC team number |
| `team_name` | String | Registered team name |
| `country` | String | Country of origin |
| `state_province` | String | State or province |
| `rookie_year` | Integer | First year the team competed |

### `team_events.csv` — One row per team per event

| Column | Type | Description |
|:---|:---|:---|
| `team_number` | Integer | Team number |
| `event_key` | String | Event identifier |
| `season` | String | Season identifier |
| `ranking` | Integer | Team rank at the event (by ranking points) |
| `wins` | Integer | Qualification match wins |
| `losses` | Integer | Qualification match losses |
| `ties` | Integer | Qualification match ties |
| `opr` | Float | Offensive Power Rating |
| `np_opr` | Float | Non-Penalty OPR |
| `ccwm` | Float | Calculated Contribution to Winning Margin |

### Key Metrics

- **OPR (Offensive Power Rating):** Estimated points contributed by a team per match, solved via least squares regression on the alliance participation matrix.
- **NP-OPR (Non-Penalty OPR):** OPR computed after removing penalty points from scores.
- **CCWM (Calculated Contribution to Winning Margin):** Estimated margin contribution per team per match.

## Baseline Benchmarks

### Win Prediction (Season 2324 Test Set)

| Model | Accuracy | AUC-ROC | Brier Score | Log Loss |
|:---|---:|---:|---:|---:|
| OPR Difference Baseline | 0.8095 | 0.8921 | 0.1594 | 0.4915 |
| Logistic Regression | 0.8639 | 0.9080 | 0.1184 | 0.3820 |
| Gradient Boosted Trees | 0.7551 | 0.8704 | 0.1526 | 0.4651 |

### Alliance Strength Prediction

| Model | Pearson r | MAE | Top-1 Acc | Top-2 Acc |
|:---|---:|---:|---:|---:|
| Naive OPR Sum | 0.1578 | 1.4231 | 0.25 | 0.50 |
| Linear Regression | 0.4060 | 1.1753 | 0.75 | 0.75 |

## Quick Start

### Prerequisites

- Python 3.9+
- Packages: `numpy`, `pandas`, `scipy`, `scikit-learn`, `requests`, `tqdm`, `python-dotenv`, `jupyter` (for notebook)

### Installation

```bash
git clone https://github.com/kaivalyasingh/ftc-analytics-dataset.git
cd ftc-analytics-dataset
pip install -r requirements.txt
```

### Running the Pipeline

The dataset ships with pre-generated mock data (no API keys needed). Run the pipeline sequentially:

```bash
# 1. Collect raw data (mock mode by default)
python scripts/collect_toa.py
python scripts/collect_ftc_events.py

# 2. Build cleaned dataset
python scripts/build_dataset.py

# 3. Compute OPR, CCWM, NP-OPR
python scripts/compute_opr.py

# 4. Run benchmarks
python scripts/benchmark_win_prediction.py
python scripts/benchmark_alliance_strength.py

# Optional: Launch the exploration notebook
jupyter notebook exploration.ipynb
```

### Using Real API Data

Copy `.env.example` to `.env` and fill in your API keys:

```bash
cp .env.example .env
# Edit .env with your TOA_API_KEY and FTC_EVENTS_API_KEY
```

With valid API keys, the collection scripts will fetch live data from The Orange Alliance and FIRST FTC Events APIs.

## Repository Structure

```
ftc-analytics-dataset/
├── data/
│   ├── raw/
│   │   ├── toa/           # Raw JSON from The Orange Alliance API
│   │   └── ftc_events/    # Raw JSON from FTC Events API
│   └── processed/
│       ├── matches.csv    # Canonical match data
│       ├── teams.csv      # Canonical team data
│       └── team_events.csv # Team-event stats with OPR
├── scripts/
│   ├── collect_toa.py
│   ├── collect_ftc_events.py
│   ├── build_dataset.py
│   ├── compute_opr.py
│   ├── benchmark_win_prediction.py
│   └── benchmark_alliance_strength.py
├── results/
│   ├── win_prediction_benchmark.csv
│   └── alliance_strength_benchmark.csv
├── exploration.ipynb
├── dataset_description.md
├── LICENSE
└── README.md
```

## Citation

If you use this dataset in your research, please cite:

```bibtex
@misc{singh2025ftc,
  author       = {Kaivalya Singh},
  title        = {{FTC Open Analytics Dataset}},
  year         = {2026},
  howpublished = {\url{https://github.com/kaivalyasingh/ftc-analytics-dataset}},
  note         = {FIRST Tech Challenge match data (2018-19 to 2023-24) with OPR metrics and ML benchmarks}
}
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

Data sourced from [The Orange Alliance](https://theorangealliance.org) and [FIRST FTC Events API](https://ftc-events.firstinspires.org/services/API).
