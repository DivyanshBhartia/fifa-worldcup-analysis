# FIFA World Cup Analytics — SectionE Group 11

**Newton School of Technology | DVA Capstone 2**
**Sector:** Sports & Entertainment Analytics
**Team ID:** SectionE_g11

---

## Business Problem

Which factors — home advantage, match stage, team historical performance, and player deployment — most significantly predict match outcomes at the FIFA World Cup? How can national football federations use these insights to optimize squad selection and tournament strategy?

---

## Dataset

| File | Rows | Columns | Description |
|------|------|---------|-------------|
| WorldCupPlayers.csv | 37,784 | 9 | Player-level match data (1930–2014) |
| WorldCupMatches.csv | 4,572 | 20 | Match-level data with scores, attendance, referees |
| WorldCups.csv | 20 | 10 | Tournament-level summary per edition |

**Primary analytical dataset:** `data/processed/wc_schedule_analysis.csv` — a merged, cleaned, and deduplicated dataset combining all three sources (6,039 rows × 15 columns), created by the ETL pipeline.

**Source:** [Kaggle — FIFA World Cup](https://www.kaggle.com/datasets/abecklas/fifa-world-cup)

---

## KPI Framework

| KPI | Description |
|-----|-------------|
| Win Rate by Team | Wins / Total matches played per team |
| Goals per Match | Average total goals per match per tournament year |
| Home Advantage Index | Win rate of host nation vs. overall win rate |
| Knockout Qualification Rate | % of group stage teams reaching knockout rounds |
| Attendance Growth Rate | YoY attendance change across tournaments |
| Player Goal Contribution | Goals scored per player per tournament |
| Stage Difficulty Index | Average goals scored by stage (Group → Final) |
| Team Consistency Score | Number of tournaments a team appeared in |

---

## Repository Structure

```
SectionE_g11_FIFA/
├── README.md
├── data/
│   ├── raw/                    ← Original datasets (never edited)
│   └── processed/              ← Cleaned output from ETL pipeline
├── notebooks/
│   ├── 01_extraction.ipynb     ← Load & inspect raw data
│   ├── 02_cleaning.ipynb       ← ETL cleaning pipeline
│   ├── 03_eda.ipynb            ← Exploratory data analysis
│   ├── 04_statistical_analysis.ipynb ← Correlation, regression, hypothesis testing
│   └── 05_final_load_prep.ipynb      ← KPI computation & Tableau export
├── scripts/
│   └── etl_pipeline.py         ← Standalone ETL script
├── tableau/
│   ├── screenshots/            ← Dashboard screenshots
│   └── dashboard_links.md      ← Tableau Public URL
├── reports/
│   ├── project_report.pdf
│   └── presentation.pdf
└── docs/
    └── data_dictionary.md
```

---

## Team Members & Roles

| Role | Member |
|------|--------|
| Project Lead | |
| Data Lead | |
| ETL Lead | |
| Analysis Lead | |
| Visualization Lead | |
| Strategy Lead | |
| PPT & Quality Lead | |

---

## Setup & Installation

### Prerequisites
- [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) or [Anaconda](https://www.anaconda.com/download/) installed

### Option 1: Using Conda (Recommended)

```bash
# Clone the repository
git clone https://github.com/Anugra07/SectionE_g11_FIFA.git
cd SectionE_g11_FIFA

# Create Conda environment from environment.yml
conda env create -f environment.yml

# Activate the environment
conda activate sectione_fifa

# Verify installation
python --version  # Should show Python 3.11.x
```

### Activate or Deactivate the Conda Environment

```bash
conda activate sectione_fifa
conda deactivate
```

---

## How to Run

```bash
# Make sure environment is activated
conda activate sectione_fifa

# Run notebooks in order
jupyter notebook notebooks/01_extraction.ipynb
jupyter notebook notebooks/02_cleaning.ipynb
jupyter notebook notebooks/03_eda.ipynb
jupyter notebook notebooks/04_statistical_analysis.ipynb
jupyter notebook notebooks/05_final_load_prep.ipynb

# Or run the standalone ETL pipeline
python scripts/etl_pipeline.py

# Launch JupyterLab for interactive analysis
jupyter lab
```

---

---

## Data Processing Pipeline

### 1. **Extraction Phase**
- **Input:** 3 raw CSV files (WorldCups, WorldCupMatches, WorldCupPlayers)
- **Records Loaded:** 37,784 players, 4,572 match entries, 20 tournaments
- **Output:** Raw dataframes ready for cleaning

### 2. **Cleaning Phase**
- **Empty Rows Removed:** 3,720 rows (82% of matches data)
- **Duplicate Matches Removed:** 16 duplicate MatchIDs
- **Data Fixes Applied:**
  - Standardized team names (Germany FR → West Germany, Korea Republic → South Korea)
  - Fixed HTML-encoded names (rn">Bosnia and Herzegovina)
  - Parsed European dot-format attendance (1.045.246 → 1,045,246)
  - Extracted goals, yellow cards, and red cards from Event field using regex
  - Normalized match stages (Group 1, Group A → Group Stage)
  - Imputed 2 missing attendance values with yearly median

### 3. **Transformation Phase**
- **Derived Columns Created:**
  - `Match_Result`: Home Win / Away Win / Draw
  - `Total_Goals`: Sum of home and away goals
  - `Goals_Scored`: Extracted from player Event string
  - `Yellow_Cards`, `Red_Cards`: Parsed from Event field
  - `Lineup`: Mapped S→Starter, N→Substitute
  - `Win_Conditions`: Normal / AET / Penalties

### 4. **Merge Phase**
- **Step 1:** Players ← Matches (many-to-one: 37,784 player records per match)
- **Step 2:** Result ← Tournaments (join on Year for Host_Nation context)
- **Final Dataset:** `wc_schedule_analysis.csv` (37,784 rows × 15 columns)

### 5. **Validation Phase**
- **Null Values:** 0 (100% complete dataset)
- **Data Consistency:** 100% (all 37,784 records pass validation)
- **Duplicate Records:** 31,745 (expected—multiple players per match)
- **Data Types:** All correctly typed (int64, str)

---

## Analysis Outputs & Insights

### Data Quality Metrics

| Metric | Value |
|--------|-------|
| Total Records | 6,039 |
| Null Values | 0 |
| Data Consistency | 100% |
| Memory Size | 3.62 MB |

### Descriptive Analytics

#### Teams and Venues
- **Unique Teams:** 83 national teams
- **Unique Venues:** 151 cities across 15 host nations
- **Tournaments:** 20 World Cups (1930-2014)

#### Match Statistics
| Outcome | Count | Notes |
|---------|-------|-------|
| Home Wins | 3,422 | Deduplicated player-level records |
| Away Wins | 1,311 | Deduplicated player-level records |
| Draws | 1,306 | Deduplicated player-level records |
| **Total Unique Matches** | 828 | Use this for true match-level analysis |

#### Goal Scoring
- **Total Goals Scored:** 1,716
- **Average Goals/Player:** 0.284
- **Players with Goals:** 1,421 (23.5%)
- **Max Goals/Player:** 4
- **Score Distribution:** 0-12 goals per match

#### Disciplinary Records
- **Yellow Cards:** 1,420 total (0.235 per player)
- **Red Cards:** 160 total (0.026 per player)
- **Players with Yellows:** 1,324
- **Players with Reds:** 160

#### Attendance Insights
- **Average Attendance:** 45,908 spectators
- **Maximum:** 173,850 (likely World Cup final)
- **Minimum:** 2,000
- **Attendance Std Dev:** 23,019 (high variability)

#### Attendance KPI Snapshot

The file [tableau/kpi_attendance.csv](tableau/kpi_attendance.csv) shows long-term attendance growth across World Cups.

| Year | Attendance | Matches Played | Avg. Attendance per Match |
|------|------------|----------------|---------------------------|
| 1930 | 590,549 | 18 | 32,808 |
| 1950 | 1,045,246 | 22 | 47,511 |
| 1966 | 1,563,135 | 32 | 48,848 |
| 1994 | 3,587,538 | 52 | 68,991 |
| 2014 | 3,386,810 | 64 | 52,919 |

Key pattern: attendance per tournament generally increased over time, and matches played expanded from 18 to 64.

---

## Analysis Deliverables and Expected Outputs

### Phase 1: Exploratory Data Analysis
File: notebooks/03_eda.ipynb

**Expected Outputs:**
1. **Distribution Analysis**
   - Goals per match distribution (histogram)
   - Attendance distribution by tournament stage
   - Player appearance frequency
   - Goals scored distribution (skewed toward 0)

2. **Time Series Analysis**
   - Goals per match trend (1930-2014)
   - Average attendance growth over decades
   - Home win rate evolution
   - Tournament size growth

3. **Categorical Breakdowns**
   - Win rate by stage (Group vs Knockout)
   - Goals by win condition (Normal vs Penalties vs AET)
   - Attendance by host nation
   - Goals per lineup position (Starter vs Substitute)

4. **Correlation Analysis**
   - Attendance vs Total Goals
   - Win Conditions vs Total Goals
   - Stage vs Average Goals
   - Year vs Attendance trends

### Phase 2: Statistical Analysis and Hypothesis Testing
File: notebooks/04_statistical_analysis.ipynb

**Expected Outputs:**
1. **Inferential Statistics**
   - Confidence intervals for win rates
   - T-tests: Home Win % vs Away Win %
   - Chi-square test: Match outcome vs stage
   - ANOVA: Goals per tournament year

2. **Predictive Modeling**
   - Logistic Regression: Predict match outcome (Home/Away/Draw)
   - Features: Attendance, Stage, Team, Win Conditions
   - Model Accuracy: Expected 55-65%
   - Feature Importance ranking

3. **Key Questions to Answer**
   - ✓ Does home advantage significantly impact win rates?
   - ✓ Which tournament stages have highest scoring?
   - ✓ How much does attendance correlate with goals?
   - ✓ Which teams are most consistent?
   - ✓ How has player disciplinary evolved?

### Phase 3: KPI Computation and Tableau Prep
File: notebooks/05_final_load_prep.ipynb

**Expected Outputs:**
1. **Pre-computed KPIs** (ready for dashboard)
   ```
   - Win_Rate_by_Team (83 teams)
   - Goals_per_Match_per_Year (20 years)
   - Home_Advantage_Index (ratio metric)
   - Knockout_Qualification_Rate (group stage → knockout %)
   - Attendance_Growth_Rate (YoY %)
   - Player_Goal_Contribution (top 50 players)
   - Stage_Difficulty_Index (goals by stage)
   - Team_Consistency_Score (tournament appearances)
   ```

2. **Tableau Export Files**
   - `tableau/team_kpis.csv`
   - `tableau/match_kpis.csv`
   - `tableau/player_kpis.csv`
   - `tableau/temporal_trends.csv`

3. **Dashboard Components** (Tableau Public)
   - Team Performance Dashboard (filters: Year, Stage, Host)
   - Match Analysis Dashboard (attendance, goals, outcomes)
   - Player Statistics (top scorers, disciplinary leaders)
   - Temporal Trends (historical patterns 1930-2014)

---

## What Is Necessary for Complete Analysis

### Currently Complete
- [x] Environment setup (Conda + requirements)
- [x] ETL pipeline (extraction, cleaning, transformation)
- [x] Exact duplicate removal from the final dataset
- [x] Data validation & quality checks
- [x] Raw data loading infrastructure
- [x] Data dictionary structure

### In Progress or Required

| Task | Status | Notes |
|------|--------|-------|
| 03_eda.ipynb | Needed | Exploratory visualizations and distributions |
| 04_statistical_analysis.ipynb | Needed | Hypothesis testing and predictive models |
| 05_final_load_prep.ipynb | Needed | KPI computation and Tableau export |
| Tableau Dashboard | Needed | Interactive visualization of all KPIs |
| Project Report | Needed | Statistical findings and business insights |
| Presentation | Needed | Executive summary for stakeholders |
| Data Dictionary | Needed | Document all fields, transformations, definitions |

### Analysis Gap Summary

What We Have
- ✓ 6,039 deduplicated player records
- ✓ 828 unique matches
- ✓ 83 teams across 20 World Cups
- ✓ 100% data quality (zero nulls)

What We Need
1. **Visualizations** (EDA)
   - Distribution plots, time series, scatter plots
   - Correlation heatmaps
   - Box plots by stage/team

2. **Statistical Tests**
   - Home advantage significance testing
   - Logistic regression model (outcome predictor)
   - Feature importance analysis
   - P-values and confidence intervals

3. **Business Insights**
   - Which factors best predict wins?
   - Home advantage impact quantified
   - Team performance ranking
   - Player contribution metrics
   - Attendance optimization strategies

4. **Interactive Dashboard**
   - Team-level KPI filters
   - Year range selection
   - Stage comparison views
   - Player leaderboards

---

## Key Insights Summary

See reports/project_report.pdf for full analysis. Dashboard: see tableau/dashboard_links.md.

Current analysis takeaways:
- The dataset is clean and ready for analysis with 6,039 deduplicated rows and no nulls.
- Attendance has grown strongly over time, from 590,549 in 1930 to 3,386,810 in 2014.
- Average attendance per match increased from about 32.8k in 1930 to about 52.9k in 2014.
- There are 83 teams, 151 venues, and 20 tournaments in scope.
- The merged dataset is still player-level, so match outcome counts should be interpreted carefully and validated again at unique-match level before final conclusions.
- The most important next work is EDA, statistical testing, KPI export, dashboard creation, and report writing.

