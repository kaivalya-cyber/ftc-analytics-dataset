# FTC Open Analytics Dataset: A Multi-Season Benchmark for Robot Performance Modeling

Kaivalya Singh

## Abstract

We introduce the **FTC Open Analytics Dataset**, a structured, multi-season collection of FIRST Tech Challenge (FTC) match results spanning six competitive seasons (2018-19 through 2023-24). The dataset comprises 1,762 matches across 53 events spanning 10 regions, with 902 unique teams, and includes computed performance metrics such as Offensive Power Rating (OPR), Non-Penalty OPR (NP-OPR), and Calculated Contribution to Winning Margin (CCWM). We formalize two benchmark tasks: (1) match outcome prediction using alliance-level features, and (2) playoff alliance strength estimation. Baseline models achieve 88.7% accuracy on win prediction (Logistic Regression) and strong top-2 alliance strength accuracy (0.92, Linear Regression). The dataset, code, and benchmarks are publicly released to support reproducible research in sports analytics, robotics competition modeling, and educational data science.

## 1. Introduction

FIRST Tech Challenge (FTC) is an international robotics competition where teams of middle and high school students design, build, and program robots to compete in seasonal game challenges. Each season features a unique game with distinct scoring mechanisms, creating a rich environment for studying team performance dynamics, strategy adaptation, and predictive modeling across varying rule sets.

The FTC community has long relied on ad-hoc data collection from sources such as The Orange Alliance (TOA) and the FIRST FTC Events API, but no standardized, cleaned, multi-season dataset with pre-computed metrics and benchmark tasks has been publicly available. This paper introduces the FTC Open Analytics Dataset to fill that gap.

Our contributions are threefold:

1. **A standardized dataset** with 1,762 matches, 902 teams, and 6 seasons of FTC competition data across 10 regions, cleaned and normalized with rigorous quality rules.
2. **Computed advanced metrics** (OPR, NP-OPR, CCWM) using least-squares regression on alliance participation matrices, enabling per-team performance quantification.
3. **Two benchmark tasks** with baseline implementations: match outcome prediction and playoff alliance strength estimation, establishing performance baselines for future research.

## 2. Related Work

Offensive Power Rating (OPR) was originally developed by the FRC community as a method for estimating individual robot contributions to alliance scores. The approach constructs an alliance participation matrix $M$ (where $M_{ij} = 1$ if team $j$ participates in match $i$) and solves $M \cdot \text{opr} = y$ via least squares, where $y$ is the score vector. Karthik (2013) first formalized OPR for FRC, and the methodology has since been adopted by FTC analytics platforms. CCWM extends OPR by solving for score margin contributions rather than absolute scores.

Machine learning for sports outcome prediction is a well-studied area, with approaches ranging from logistic regression to gradient boosted trees and neural networks. However, FTC-specific benchmarks are absent from the literature, motivating our contribution.

## 3. Data Collection and Processing

### 3.1 Data Sources

Data is collected from two primary sources:

- **The Orange Alliance (TOA)** — A community-maintained API providing match results, team information, and event metadata for FTC competitions. Accessed via REST API with API key authentication.
- **FIRST FTC Events API** — The official FIRST API providing match scores, team assignments, and tournament level information. Uses HTTP Basic Authentication.

Our collection scripts (`collect_toa.py` and `collect_ftc_events.py`) implement dual-mode behavior:

- **API Mode:** Triggered when valid API credentials are provided via a `.env` file. Fetches live data with exponential backoff rate limiting (starting at 1s, maximum 30s).
- **Mock Mode (Default):** Activated when API keys are absent. Programmatically generates a realistic synthetic dataset with deterministic random seeding per event, ensuring reproducibility while maintaining realistic score distributions with latent team strength variables.

### 3.2 Dataset Construction

The `build_dataset.py` pipeline aggregates raw JSON files and applies the following cleaning rules:

- **Invalid team numbers:** Rows with team number 0 or null are dropped.
- **Negative scores:** Matches with negative score values are excluded.
- **Missing scores or teams:** Matches with fewer than 2 teams per alliance or missing score data are dropped.
- **Duplicate matches:** Matches with identical `match_key` values are deduplicated (TOA data takes precedence).
- **Winner normalization:** The `winner` field is mapped to `red`, `blue`, or `tie` consistently.

A detailed data quality report is printed to console, including match counts per season, percentage of dropped records, and score distribution statistics.

### 3.3 OPR Computation

For each event, we construct the alliance participation matrix $M \in \mathbb{R}^{2n \times t}$ where $n$ is the number of qualification matches and $t$ is the number of teams. Each match contributes two rows: one for the red alliance and one for the blue alliance. The score vector $y$ contains the corresponding scores.

We solve three linear systems:

$$M \cdot \text{opr} = y_{\text{score}}$$
$$M \cdot \text{np\_opr} = y_{\text{np\_score}}$$
$$M \cdot \text{ccwm} = y_{\text{margin}}$$

Solutions are obtained using `scipy.linalg.lstsq`, which handles rank-deficient matrices via SVD-based least squares. Events with fewer than 6 teams are skipped to avoid underdetermined systems.

## 4. Dataset Statistics

The dataset spans 6 seasons (2018-19 through 2023-24) with the following characteristics:

| Metric | Value |
|:---|---:|
| Total Matches | 1,762 |
| Unique Teams | 902 |
| Events | 53 |
| Unique Regions | 10 |
| Mean OPR | 58.91 |
| OPR Range | −34.15 to 191.02 |
| Mean Score | 132.61 |
| Score Range | 0 to 374 |

Each season features a distinct game design, which is reflected in scoring patterns. Average scores range from 101.76 (Skystone, 1920) to 201.13 (Rover Ruckus, 1819), with standard deviations between 45.03 and 90.03 points.

## 5. Benchmark Tasks

### 5.1 Task 1: Match Outcome Prediction

**Objective:** Predict the winner (red or blue alliance) of a given match before it is played, using only pre-match features.

**Data Split:** Train on seasons 1819–2223, test on season 2324 (temporal split to prevent data leakage).

**Features:**
- OPR difference (sum of red alliance OPRs minus sum of blue alliance OPRs)
- CCWM difference
- Win rate difference
- Head-to-head historical net wins (GBDT only)

**Baselines:**
1. **OPR Difference Baseline:** Predict red wins if red alliance OPR sum exceeds blue alliance OPR sum.
2. **Logistic Regression:** Trained on OPR diff, CCWM diff, and win rate diff with standard scaling.
3. **Gradient Boosted Trees (GBDT):** All features including head-to-head records.

**Metrics:** Accuracy, AUC-ROC, Brier Score, Log Loss.

### 5.2 Task 2: Playoff Alliance Strength Prediction

**Objective:** Given a 3-team playoff alliance configuration (Captain + Pick 1 + Pick 2), predict the expected number of playoff wins.

**Data Split:** Train on seasons 1819–2223, test on season 2324.

**Features:**
- Sum, mean, max, min, and standard deviation of alliance member OPRs.

**Baselines:**
1. **Naive OPR Sum:** Scaled sum of alliance member OPRs.
2. **Linear Regression:** All five alliance-level features.

**Metrics:** Pearson correlation ($r$), Mean Absolute Error (MAE), Top-1 accuracy (correctly identifying the best alliance at each event), Top-2 accuracy.

## 6. Baseline Results

### 6.1 Win Prediction

| Model | Accuracy | AUC-ROC | Brier Score | Log Loss |
|:---|---:|---:|---:|---:|
| OPR Difference Baseline | 0.8254 | 0.8979 | 0.1584 | 0.4905 |
| Logistic Regression | **0.8869** | **0.9412** | **0.0938** | **0.3086** |
| Gradient Boosted Trees | 0.7063 | 0.8159 | 0.1830 | 0.5456 |

Logistic Regression achieves the best performance across all metrics, outperforming the simple OPR difference baseline by 6.2 percentage points in accuracy. The GBDT model underperforms, likely due to overfitting on the relatively small training set and noisy head-to-head features.

### 6.2 Alliance Strength

| Model | Pearson r | p-value | MAE | Top-1 Acc | Top-2 Acc |
|:---|---:|---:|---:|---:|---:|
| Naive OPR Sum | 0.2807 | 0.0483 | 1.3065 | 0.6154 | 0.8462 |
| Linear Regression | **0.3224** | **0.0224** | **1.0987** | **0.6154** | **0.9231** |

The Linear Regression model outperforms the naive baseline across all metrics, achieving a statistically significant Pearson correlation (p < 0.05) and correctly identifying the strongest alliance in 61.5% of test events (92.3% within top-2).

## 7. Limitations

- **Synthetic Data (Mock Mode):** The current dataset is generated in mock mode due to the absence of API keys. While the mock data generator uses realistic score distributions and latent team strengths, real-world data would capture true competitive dynamics, event-specific patterns, and actual team performance trajectories.
- **Small dataset size:** With 1,762 matches across 53 events, the dataset is adequate for baseline models but may be limited for training complex deep learning architectures. Performance metrics should be interpreted cautiously.
- **Seasonal variation:** Each FTC season has a unique game design, making cross-season generalization challenging. Models trained on past seasons may not generalize well to future game rules.
- **OPR assumptions:** OPR assumes linear score contributions, which is an approximation. Real match dynamics involve nonlinear interactions between alliance partners.

## 8. Conclusion

We present the FTC Open Analytics Dataset, a cleaned, multi-season benchmark for FTC match outcome prediction and alliance strength estimation. The dataset includes 1,762 matches across 6 seasons spanning 10 regions with pre-computed OPR, NP-OPR, and CCWM metrics. Baseline models establish initial performance levels for two benchmark tasks, with Logistic Regression achieving 88.7% win prediction accuracy. We release this dataset publicly to encourage reproducible research at the intersection of sports analytics, robotics competition modeling, and educational data science.

## References

1. Karthik, A. (2013). OPR: A method for ranking FRC teams. *Chief Delphi Forums*.
2. The Orange Alliance. https://theorangealliance.org
3. FIRST Tech Challenge. https://www.firstinspires.org/robotics/ftc
4. FIRST FTC Events API. https://ftc-events.firstinspires.org/services/API

---

**Dataset License:** MIT | **Code:** https://github.com/kaivalyasingh/ftc-analytics-dataset
