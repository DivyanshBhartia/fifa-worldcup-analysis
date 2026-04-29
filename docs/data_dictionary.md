# Data Dictionary
**Project:** FIFA World Cup Analytics  
**Sector:** Sports Analytics  
**Coverage:** FIFA World Cup 1930 – 2014 (20 editions)  
**Source:** Kaggle — FIFA World Cup Dataset  
**URL:** https://www.kaggle.com/datasets/abecklas/fifa-world-cup  
**Prepared By:** Ashish Kumar Yadav

---

## Overview

This project uses three raw CSV files that are merged into a single master dataset
and four KPI tables for analysis and Tableau dashboarding.

| File | Location | Rows | Columns | Grain |
|------|----------|------|---------|-------|
| `WorldCupMatches.csv` | `data/raw/` | 4,572 (836 real) | 20 | One row per match |
| `WorldCupPlayers.csv` | `data/raw/` | 37,784 | 9 | One row per player per match |
| `WorldCups.csv` | `data/raw/` | 20 | 10 | One row per tournament edition |
| `world_cup_master.csv` | `data/processed/` | 36,595 | 37 | One row per player per match per tournament |
| `kpi_tournament.csv` | `data/processed/` | 20 | 15 | One row per tournament edition |
| `kpi_team.csv` | `data/processed/` | 83 | 12 | One row per nation (all-time) |
| `kpi_player.csv` | `data/processed/` | 7,638 | 14 | One row per player (all-time) |
| `kpi_match.csv` | `data/processed/` | 836 | 31 | One row per match |

---

## File Integrity Checksums (MD5)

Run `python scripts/etl_pipeline.py` to regenerate all processed files.  
The checksums below confirm the raw files were never modified after download.

| File | MD5 Checksum |
|------|-------------|
| `WorldCupMatches.csv` | [Run: `md5sum data/raw/WorldCupMatches.csv`] |
| `WorldCupPlayers.csv` | [Run: `md5sum data/raw/WorldCupPlayers.csv`] |
| `WorldCups.csv` | [Run: `md5sum data/raw/WorldCups.csv`] |

---

## Join / Merge Logic

```
WorldCupPlayers  (37,784 rows)
    └── LEFT JOIN WorldCupMatches   ON  RoundID + MatchID
            └── LEFT JOIN WorldCups  ON  Year
                    └──> world_cup_master.csv  (36,595 rows × 37 cols)
```

**Why LEFT JOIN?** We keep all player records as the base. Match and tournament
context is added where keys match. No player records are lost.

**Why 36,595 rows and not 37,784?** 736 duplicate records were removed from WorldCupPlayers during data cleaning, and 454 rows with null (NaT) datetime values were dropped.

---

## Section 1 — Raw File: `WorldCupMatches.csv`

**Grain:** One row per match  
**Real rows:** 836 (the file contains 3,720 fully blank padding rows and duplicates — removed in cleaning)  
**Join keys:** `RoundID`, `MatchID` → link to `WorldCupPlayers.csv`; `Year` → link to `WorldCups.csv`

| # | Column | Raw Type | Clean Type | Nullable | Sample Values | Description | Known Issues & Fix |
|---|--------|----------|------------|----------|---------------|-------------|-------------------|
| 1 | Year | float64 | int | No | 1930, 1954, 2014 | Year the World Cup edition took place | Stored as float due to 3,720 blank rows containing NaN — cast to int after blank row removal |
| 2 | Datetime | object | datetime64 | No | `13 Jul 1930 - 15:00` | Date and kick-off time of the match | Plain string — parsed with `pd.to_datetime(format='%d %b %Y - %H:%M')` |
| 3 | Stage | object | object | No | `Group 1`, `Semi-finals`, `Final` | Tournament stage of the match | Clean |
| 4 | Stadium | object | object | No | `Pocitos`, `Maracanã` | Name of the stadium | Clean |
| 5 | City | object | object | No | `Montevideo`, `London` | City where the match was played | Trailing whitespace on many values — stripped |
| 6 | Home Team Name | object | object | No | `France`, `Brazil` | Full name of the home team | Trailing whitespace on some values — stripped |
| 7 | Home Team Goals | float64 | int | No | 0, 1, 2, 3 | Full-time goals scored by the home team | Stored as float due to blank rows — cast to int |
| 8 | Away Team Goals | float64 | int | No | 0, 1, 2 | Full-time goals scored by the away team | Stored as float due to blank rows — cast to int |
| 9 | Away Team Name | object | object | No | `Mexico`, `Germany FR` | Full name of the away team | Trailing whitespace on some values — stripped |
| 10 | Win conditions | object | object | No | `''`, `Austria win after extra time` | Describes how the match was decided beyond 90 minutes | Empty string for regular-time results — filled with `'Normal'` |
| 11 | Attendance | float64 | int | Yes (2) | 4,444, 68,991, 173,850 | Number of spectators at the match | 2 missing values — filled with year-level median attendance; stored as float — cast to int |
| 12 | Half-time Home Goals | float64 | int | No | 0, 1, 2 | Home team goals at half-time | Stored as float due to blank rows — cast to int |
| 13 | Half-time Away Goals | float64 | int | No | 0, 1, 2 | Away team goals at half-time | Stored as float due to blank rows — cast to int |
| 14 | Referee | object | object | No | `LOMBARDI Domingo (URU)` | Referee name and nationality code | Clean |
| 15 | Assistant 1 | object | — | No | `CRISTOPHE Henry (BEL)` | First assistant referee | **Dropped** — no analytical value |
| 16 | Assistant 2 | object | — | No | `WARNKEN Alberto (CHI)` | Second assistant referee | **Dropped** — no analytical value |
| 17 | RoundID | float64 | int | No | 201, 202, 405 | Unique round identifier (join key with WorldCupPlayers) | Stored as float due to blank rows — cast to int |
| 18 | MatchID | float64 | int | No | 1096, 1090, 1093 | Unique match identifier (join key with WorldCupPlayers) | Stored as float due to blank rows — cast to int |
| 19 | Home Team Initials | object | object | No | `FRA`, `BRA`, `GER` | 3-letter FIFA code for home team | Clean |
| 20 | Away Team Initials | object | object | No | `MEX`, `ARG`, `ITA` | 3-letter FIFA code for away team | Clean |

---

## Section 2 — Raw File: `WorldCupPlayers.csv`

**Grain:** One row per player per match  
**Rows:** 37,784 raw → 36,595 after cleaning  
**Join keys:** `RoundID`, `MatchID` → link to `WorldCupMatches.csv`

| # | Column | Raw Type | Clean Type | Nullable | Sample Values | Description | Known Issues & Fix |
|---|--------|----------|------------|----------|---------------|-------------|-------------------|
| 1 | RoundID | int64 | int | No | 201, 202, 405 | Round identifier — links to WorldCupMatches.RoundID | Clean — already int, ready to join |
| 2 | MatchID | int64 | int | No | 1096, 1090, 1093 | Unique match identifier — links to WorldCupMatches.MatchID | Clean — already int, ready to join |
| 3 | Team Initials | object | object | No | `FRA`, `MEX`, `BRA` | 3-letter FIFA code for the player's team | Clean |
| 4 | Coach Name | object | object | No | `CAUDRON Raoul (FRA)` | Coach full name and nationality code in brackets | Clean |
| 5 | Line-up | object | object | No | `S`, `N` | Player's lineup status — S = Starting XI, N = Named substitute | Opaque codes — decoded: `S` → `Starting`, `N` → `Substitute` |
| 6 | Shirt Number | int64 | float | No | 0, 1, 2, ..., 23 | Player jersey number | Value `0` used as placeholder for unknown/unrecorded — replaced with `NaN`. Stored as float after replacement |
| 7 | Player Name | object | object | No | `Alex THEPOT`, `RONALDO` | Player full name | Clean. Note: encoding issues exist for some special characters (e.g. Pelé) in older records |
| 8 | Position | object | object | Yes (33,641) | `GK`, `DF`, `MF`, `FW` | Playing position code | Not recorded for 89% of records — predominantly pre-1980s tournaments. Filled with `'Unknown'`. Do not use for position-based analysis prior to 1982 |
| 9 | Event | object | object | Yes (28,715) | `G40'`, `Y65'`, `R78'`, `SU60'` | In-match event notation: G = goal, Y = yellow card, R = red card, SU/SI = substitute in | Null for players with no recorded action — filled with `'No Event'`. Multiple events in one cell are space-separated (e.g. `G40' G87'`) |

**Event Code Reference:**

| Code | Meaning | Example |
|------|---------|---------|
| `G` + minute | Goal scored | `G40'` = goal at 40th minute |
| `Y` + minute | Yellow card | `Y65'` = yellow card at 65th minute |
| `R` + minute | Red card | `R78'` = red card at 78th minute |
| `SU` + minute | Substituted in | `SU60'` = subbed on at 60th minute |
| `SI` + minute | Substituted in (alternate code) | `SI72'` |
| `G2` | Own goal | Appears in some records |
| No Event | No recorded action | Filled value for null event |

---

## Section 3 — Raw File: `WorldCups.csv`

**Grain:** One row per tournament edition  
**Rows:** 20 (1930 – 2014, no missing editions)  
**Join key:** `Year` → links to both `WorldCupMatches.csv` and `WorldCupPlayers.csv`

| # | Column | Raw Type | Clean Type | Nullable | Sample Values | Description | Known Issues & Fix |
|---|--------|----------|------------|----------|---------------|-------------|-------------------|
| 1 | Year | int64 | int | No | 1930, 1954, 2014 | Tournament year — primary join key | Clean |
| 2 | Country | object | object | No | `Uruguay`, `Italy`, `Brazil` | Country that hosted the tournament | **Renamed** to `host_country` to avoid ambiguity after merge |
| 3 | Winner | object | object | No | `Uruguay`, `Brazil`, `Germany` | Nation that won the tournament | Clean |
| 4 | Runners-Up | object | object | No | `Argentina`, `Hungary` | Nation that finished as runner-up | Clean |
| 5 | Third | object | object | No | `USA`, `Brazil`, `Sweden` | Nation that finished third | Clean |
| 6 | Fourth | object | object | No | `Yugoslavia`, `Austria` | Nation that finished fourth | Clean |
| 7 | GoalsScored | int64 | int | No | 70, 140, 171 | Total goals scored across all matches in the tournament | Clean |
| 8 | QualifiedTeams | int64 | int | No | 13, 16, 24, 32 | Number of national teams that qualified | Clean |
| 9 | MatchesPlayed | int64 | int | No | 17, 18, 52, 64 | Total number of matches played in the tournament | Clean |
| 10 | Attendance | object | int | No | `590.549`, `363.000` | Total spectators across all tournament matches | **Critical issue:** Stored as string using European dot-thousands separator (590.549 = 590,549). Dot removed and cast to int. **Renamed** to `tournament_attendance` to avoid clash with `WorldCupMatches.Attendance` |

---

## Section 4 — Processed File: `world_cup_master.csv`

**Grain:** One row per player per match per tournament  
**Rows:** 36,595 | **Columns:** 37  
**Produced by:** `02_cleaning.ipynb` and `scripts/etl_pipeline.py`

This is the single analytical dataset used by all downstream notebooks (03, 04, 05).

| # | Column | Type | Source | Description |
|---|--------|------|--------|-------------|
| 1 | roundid | int | WorldCupPlayers | Tournament round identifier |
| 2 | matchid | int | WorldCupPlayers | Unique match identifier |
| 3 | team_initials | str | WorldCupPlayers | 3-letter FIFA code for player's team |
| 4 | coach_name | str | WorldCupPlayers | Coach full name and nationality |
| 5 | line_up | str | WorldCupPlayers | `Starting` or `Substitute` |
| 6 | shirt_number | float | WorldCupPlayers | Jersey number (NaN if unknown) |
| 7 | player_name | str | WorldCupPlayers | Player full name |
| 8 | position | str | WorldCupPlayers | `GK` / `DF` / `MF` / `FW` / `Unknown` |
| 9 | event | str | WorldCupPlayers | Goal/card/sub notation or `No Event` |
| 10 | year | int | WorldCupMatches | World Cup edition year |
| 11 | datetime | datetime | WorldCupMatches | Match date and kick-off time |
| 12 | stage | str | WorldCupMatches | Tournament stage |
| 13 | stadium | str | WorldCupMatches | Stadium name |
| 14 | city | str | WorldCupMatches | Host city |
| 15 | home_team_name | str | WorldCupMatches | Home team full name |
| 16 | home_team_goals | int | WorldCupMatches | Full-time home goals |
| 17 | away_team_goals | int | WorldCupMatches | Full-time away goals |
| 18 | away_team_name | str | WorldCupMatches | Away team full name |
| 19 | win_conditions | str | WorldCupMatches | `Normal` / `[Team] win after extra time` / penalties description |
| 20 | attendance | int | WorldCupMatches | Match attendance (2 nulls filled with year median) |
| 21 | half_time_home_goals | int | WorldCupMatches | Home team goals at half-time |
| 22 | half_time_away_goals | int | WorldCupMatches | Away team goals at half-time |
| 23 | referee | str | WorldCupMatches | Referee name and nationality |
| 24 | home_team_initials | str | WorldCupMatches | Home team 3-letter FIFA code |
| 25 | away_team_initials | str | WorldCupMatches | Away team 3-letter FIFA code |
| 26 | host_country | str | WorldCups | Country that hosted the tournament |
| 27 | winner | str | WorldCups | Tournament winner |
| 28 | runners_up | str | WorldCups | Tournament runner-up |
| 29 | third | str | WorldCups | Third-place nation |
| 30 | fourth | str | WorldCups | Fourth-place nation |
| 31 | goalsscored | int | WorldCups | Total goals in the full tournament |
| 32 | qualifiedteams | int | WorldCups | Number of qualified nations |
| 33 | matchesplayed | int | WorldCups | Total matches in the tournament |
| 34 | tournament_attendance | int | WorldCups | Total tournament attendance |
| 35 | total_goals | int | Derived | `home_team_goals + away_team_goals` for the match |
| 36 | match_result | str | Derived | `Win` / `Loss` / `Draw` from the player's team perspective |
| 37 | is_goal_scorer | int | Derived | `1` if player scored at least one goal in this match, else `0` |

---

## Section 5 — KPI Files (Tableau-Ready)

### `kpi_tournament.csv` — 20 rows × 15 cols

| Column | Type | Description |
|--------|------|-------------|
| year | int | Tournament year |
| host_country | str | Hosting nation |
| winner | str | Tournament winner |
| runners_up | str | Runner-up |
| third | str | Third place |
| fourth | str | Fourth place |
| goalsscored | int | Total goals in tournament |
| qualifiedteams | int | Qualified nations |
| matchesplayed | int | Total matches played |
| tournament_attendance | int | Total spectators |
| avg_goals_per_match | float | `goalsscored / matchesplayed` |
| avg_attendance_per_match | int | `tournament_attendance / matchesplayed` |
| host_nation_won | int | `1` if host won the tournament, else `0` |
| goals_per_team | float | `goalsscored / qualifiedteams` |
| era | str | `Classic Era (≤16 teams)` / `Expansion Era (24 teams)` / `Modern Era (32 teams)` |

### `kpi_team.csv` — 83 rows × 12 cols

| Column | Type | Description |
|--------|------|-------------|
| team | str | Full team name |
| matches_played | int | Total matches across all World Cups |
| wins | int | Total wins |
| draws | int | Total draws |
| losses | int | Total losses |
| goals_scored | int | Total goals scored across all World Cups |
| goals_conceded | int | Total goals conceded |
| win_rate_pct | float | `wins / matches_played × 100` |
| goal_difference | int | `goals_scored − goals_conceded` |
| goals_per_match | float | `goals_scored / matches_played` |
| tournament_appearances | int | Number of distinct World Cups the team participated in |
| titles_won | int | Number of World Cup titles |

### `kpi_player.csv` — 7,638 rows × 14 cols

| Column | Type | Description |
|--------|------|-------------|
| player_name | str | Full player name |
| team | str | 3-letter FIFA team code |
| appearances | int | Unique matches played |
| goals | int | Total goals scored |
| yellow_cards | int | Total yellow cards received |
| red_cards | int | Total red cards received |
| subbed_in_count | int | Times substituted on |
| tournaments_attended | int | Number of distinct World Cups attended |
| first_year | int | First World Cup year |
| last_year | int | Last World Cup year |
| starts | int | Matches started in the Starting XI |
| sub_appearances | int | Matches entered as substitute |
| goals_per_appearance | float | `goals / appearances` |
| career_span_years | int | `last_year − first_year` |

### `kpi_match.csv` — 836 rows × 31 cols

| Column | Type | Description |
|--------|------|-------------|
| matchid | int | Unique match identifier |
| year | int | Tournament year |
| datetime | datetime | Match date and kick-off time |
| stage | str | Tournament stage |
| stadium | str | Stadium name |
| city | str | Host city |
| home_team_name | str | Home team full name |
| away_team_name | str | Away team full name |
| home_team_initials | str | Home team 3-letter code |
| away_team_initials | str | Away team 3-letter code |
| home_team_goals | int | Full-time home goals |
| away_team_goals | int | Full-time away goals |
| half_time_home_goals | int | Half-time home goals |
| half_time_away_goals | int | Half-time away goals |
| total_goals | int | Full-time total goals |
| win_conditions | str | Raw win condition string |
| attendance | int | Match attendance |
| host_country | str | Tournament host nation |
| winner | str | Tournament winner (for context) |
| era | str | Era label for the edition |
| ht_goals | int | `half_time_home_goals + half_time_away_goals` |
| second_half_goals | int | `total_goals − ht_goals` |
| winning_team | str | Team that won the match (or `'Draw'`) |
| goal_margin | int | `abs(home_team_goals − away_team_goals)` |
| win_type | str | `Normal` / `Extra Time` / `Penalties` |
| is_home_win | int | `1` if home team won, else `0` |
| is_away_win | int | `1` if away team won, else `0` |
| is_draw | int | `1` if match ended in a draw, else `0` |
| is_high_scoring | int | `1` if total goals ≥ 4, else `0` |
| is_goalless | int | `1` if total goals = 0, else `0` |
| is_knockout | int | `1` if knockout stage match, else `0` |

---

## Section 6 — Known Limitations

| # | Limitation | Impact | Acknowledged In |
|---|-----------|--------|----------------|
| 1 | Position data missing for 89% of players (pre-1980s not recorded) | Position-based analysis is limited to modern tournaments | EDA Section 5, Report Section 8 |
| 2 | Attendance missing for 2 matches — filled with year median | Minor distortion in match-level attendance stats | Cleaning Step 6 |
| 3 | Dataset ends at 2014 — excludes 2018 and 2022 World Cups | Trends may not reflect post-2014 developments | Report Section 8 |
| 4 | Germany FR and Germany treated as separate teams | All-time German totals are split across two team names | Team KPI table |
| 5 | Datetime unparseable for 454 rows after merge | Rows with NaT datetime cannot be used in time-of-day analysis | Cleaning Step 4 |
| 6 | Player names have encoding issues for special characters | Player lookup by name may fail for accented characters | EDA Section 5 |
| 7 | Event column stores multiple events in one cell | Counting goals from event requires regex — covered in KPI build | Player KPI table |

---

## Section 7 — Cleaning Transformation Summary

All transformations are applied in `02_cleaning.ipynb` and `scripts/etl_pipeline.py`.

| Step | Column(s) | Issue | Transformation Applied |
|------|-----------|-------|----------------------|
| 1 | All rows | 3,720 fully blank rows in WorldCupMatches | `dropna(how='all')` |
| 2 | All rows | 736 duplicate rows in merged dataset | `drop_duplicates()` |
| 3 | All columns | Mixed case with spaces in column names | Renamed to `snake_case` |
| 4 | assistant_1, assistant_2 | No analytical value (linesman names) | Dropped |
| 5 | datetime | Plain string — not a datetime type | `pd.to_datetime(format='%d %b %Y - %H:%M')` |
| 6 | home/away goals, half-time goals | Stored as float due to blank rows | Cast to `int` |
| 7 | attendance | 2 nulls + stored as float | Filled with year-level median, cast to `int` |
| 8 | win_conditions | Empty string for regular-time results | Replaced empty string / `'nan'` with `'Normal'` |
| 9 | shirt_number | Value `0` used as unknown placeholder | Replaced `0` with `Unknown` |
| 10 | position | 33,641 nulls (pre-1980s not recorded) | `fillna('Unknown')` |
| 11 | event | 28,715 nulls (no action in match) | `fillna('No Event')` |
| 12 | line_up | Opaque codes `S` / `N` | Mapped to `Starting` / `Substitute` |
| 13 | tournament_attendance | String with European dot-thousands separator | Removed `.`, cast to `int` |
| 14 | All string columns | Leading/trailing whitespace | `.str.strip()` on all object columns |
| 15 | — | Missing derived KPI columns | Added `total_goals`, `match_result`, `is_goal_scorer` |

---

*Last updated: [24 Apr 2026] | Maintained by: Ashish Kumar Yadav*
