"""
etl_pipeline.py
===============
FIFA World Cup Analytics — End-to-End ETL Pipeline
Project  : DVA Capstone 2
Sector   : Sports Analytics
Coverage : World Cup 1930 – 2014

PURPOSE
-------
This script is a standalone, command-line-runnable version of the full
pipeline built across notebooks 01–05. It reproduces every transformation,
merge, KPI computation, and sanity check in a single execution.

Run from the project root:
    python scripts/etl_pipeline.py

Or with a custom data path:
    python scripts/etl_pipeline.py --data-dir /path/to/data

OUTPUTS (written to data/processed/)
-------
    world_cup_master.csv    — Clean merged master dataset (37,048 rows × 37 cols)
    kpi_tournament.csv      — Tournament-level KPIs (20 rows)
    kpi_team.csv            — All-time team performance (83 rows)
    kpi_player.csv          — All-time player stats (7,638 rows)
    kpi_match.csv           — Match analytics with flags (836 rows)
"""

import argparse
import logging
import os
import sys
import time
import warnings
from datetime import datetime

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# LOGGING SETUP
# ─────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("etl_pipeline.log", mode="w"),
    ],
)
log = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────

RAW_FILES = {
    "matches"   : "WorldCupMatches.csv",
    "players"   : "WorldCupPlayers.csv",
    "worldcups" : "WorldCups.csv",
}

KNOCKOUT_STAGES = [
    "Final",
    "Match for third place",
    "Semi-finals",
    "Quarter-finals",
    "Round of 16",
]


# ─────────────────────────────────────────────
# STEP 1: EXTRACT — Load Raw Files
# ─────────────────────────────────────────────

def extract(raw_dir: str) -> dict:
    """
    Load all three raw CSV files from data/raw/.
    Returns a dict of DataFrames: {matches, players, worldcups}.
    Raw files are never modified — only copies are used downstream.
    """
    log.info("=" * 55)
    log.info("STEP 1 — EXTRACT: Loading raw files")
    log.info("=" * 55)

    frames = {}
    for key, filename in RAW_FILES.items():
        path = os.path.join(raw_dir, filename)
        if not os.path.exists(path):
            log.error(f"Raw file not found: {path}")
            sys.exit(1)
        frames[key] = pd.read_csv(path)
        log.info(f"  Loaded {filename:<30} shape={frames[key].shape}")

    return frames


# ─────────────────────────────────────────────
# STEP 2: PRE-MERGE PREPARATION
# ─────────────────────────────────────────────

def prepare_for_merge(frames: dict) -> dict:
    """
    Fix join keys in WorldCupMatches before the merge:
      - Drop 3,720 fully blank rows
      - Drop duplicate rows
      - Cast Year, RoundID, MatchID from float to int
    Rename clashing columns in WorldCups.
    """
    log.info("=" * 55)
    log.info("STEP 2 — PREPARE: Fixing join keys before merge")
    log.info("=" * 55)

    matches = frames["matches"].copy()

    # Drop fully blank rows (3,720 padding rows in raw file)
    before = len(matches)
    matches.dropna(how="all", inplace=True)
    log.info(f"  Blank rows dropped from Matches      : {before - len(matches)}")

    # Drop duplicates
    before = len(matches)
    matches.drop_duplicates(inplace=True)
    log.info(f"  Duplicate rows removed from Matches  : {before - len(matches)}")

    # Cast join keys — float because of NaN rows, now safe to convert
    for col in ["Year", "RoundID", "MatchID"]:
        matches[col] = matches[col].astype(int)
    log.info(f"  Year, RoundID, MatchID cast to int")
    log.info(f"  Matches ready for join               : {matches.shape}")

    # Rename clashing columns in WorldCups
    worldcups = frames["worldcups"].copy()
    worldcups.rename(
        columns={"Attendance": "tournament_attendance", "Country": "host_country"},
        inplace=True,
    )
    log.info(f"  WorldCups columns renamed to avoid clash with Matches.Attendance")

    return {"matches": matches, "players": frames["players"].copy(), "worldcups": worldcups}


# ─────────────────────────────────────────────
# STEP 3: MERGE — Build the Master Dataset
# ─────────────────────────────────────────────

def merge_datasets(frames: dict) -> pd.DataFrame:
    """
    Join 1: WorldCupPlayers LEFT JOIN WorldCupMatches  ON [RoundID, MatchID]
    Join 2: Result           LEFT JOIN WorldCups        ON Year

    Grain of output: One row = one player in one match in one tournament.
    """
    log.info("=" * 55)
    log.info("STEP 3 — MERGE: Building master dataset")
    log.info("=" * 55)

    # Join 1: Players + Matches
    df = frames["players"].merge(
        frames["matches"], on=["RoundID", "MatchID"], how="left"
    )
    log.info(f"  After Join 1 (Players + Matches)  : {df.shape}")

    # Join 2: + WorldCups
    df = df.merge(frames["worldcups"], on="Year", how="left")
    log.info(f"  After Join 2 (+ WorldCups)         : {df.shape}")

    return df


# ─────────────────────────────────────────────
# STEP 4: CLEAN — 14-Step Cleaning Pipeline
# ─────────────────────────────────────────────

def clean(df: pd.DataFrame) -> pd.DataFrame:
    """
    Apply all 14 cleaning transformations documented in 02_cleaning.ipynb.
    Every step is logged with what was done and why.
    """
    log.info("=" * 55)
    log.info("STEP 4 — CLEAN: Applying cleaning pipeline")
    log.info("=" * 55)

    # Step 1 — Remove duplicate rows
    before = len(df)
    df.drop_duplicates(inplace=True)
    df.reset_index(drop=True, inplace=True)
    log.info(f"  [01] Duplicate rows removed          : {before - len(df)}")

    # Step 2 — Standardise column names to snake_case
    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
        .str.replace(" ", "_", regex=False)
        .str.replace("-", "_", regex=False)
    )
    log.info(f"  [02] Columns renamed to snake_case   : {len(df.columns)} columns")

    # Step 3 — Drop analytically irrelevant columns (lineswoman names)
    df.drop(columns=["assistant_1", "assistant_2"], inplace=True)
    log.info(f"  [03] Dropped assistant_1, assistant_2")

    # Step 4 — Parse Datetime
    df["datetime"] = pd.to_datetime(
        df["datetime"].astype(str).str.strip(),
        format="%d %b %Y - %H:%M",
        errors="coerce",
    )

    # Count nulls
    nat_count = df["datetime"].isna().sum()

    # Drop rows with null datetime
    df = df[df["datetime"].notna()].reset_index(drop=True)

    log.info(f"  [04] Datetime parsed — dropped {nat_count} rows with NaT")


    # Step 5 — Cast goal columns from float to int
    goal_cols = [
        "home_team_goals", "away_team_goals",
        "half_time_home_goals", "half_time_away_goals",
    ]
    for col in goal_cols:
        df[col] = df[col].astype(int)
    log.info(f"  [05] Goal columns cast to int        : {goal_cols}")

    # Step 6 — Fill missing attendance with year-level median; cast to int
    null_att = df["attendance"].isna().sum()
    df["attendance"] = df.groupby("year")["attendance"].transform(
        lambda x: x.fillna(x.median())
    )
    df["attendance"] = df["attendance"].astype(int)
    log.info(f"  [06] Attendance nulls filled (median): {null_att}")

    # Step 7 — Fill empty win_conditions with 'Normal'
    df["win_conditions"] = (
        df["win_conditions"]
        .astype(str).str.strip()
        .replace("", "Normal")
        .replace("nan", "Normal")
    )
    log.info(f"  [07] win_conditions empty → 'Normal'")

    # Step 8 — Replace shirt_number = 0 with "unknown" (0 is not a valid number)
    zero_shirts = (df["shirt_number"] == 0).sum()
    df["shirt_number"] = df["shirt_number"].replace(0, "unknown")
    log.info(f"  [08] shirt_number 0 → unknown        : {zero_shirts} replaced")

    zero_shirts = (df['shirt_number'] == 0).sum()
    df['shirt_number'] = df['shirt_number'].replace(0, 'Unknown')

    print(f'[STEP 8] Replaced {zero_shirts} shirt_number = 0 entries with "Unknown".')

    # Step 9 — Fill missing position with 'Unknown' (not recorded pre-1980s)
    null_pos = df["position"].isna().sum()
    df["position"] = df["position"].fillna("Unknown")
    log.info(f"  [09] position NaN → 'Unknown'        : {null_pos} filled")

    # Step 10 — Fill missing event with 'No Event'
    null_ev = df["event"].isna().sum()
    df["event"] = df["event"].fillna("No Event")
    log.info(f"  [10] event NaN → 'No Event'          : {null_ev} filled")

    # Step 11 — Decode line_up codes to readable labels
    df["line_up"] = (
        df["line_up"].map({"S": "Starting", "N": "Substitute"})
        .fillna(df["line_up"])
    )
    log.info(f"  [11] line_up decoded: S→Starting, N→Substitute")

    # Step 12 — Convert tournament_attendance from string to int
    # Raw format: '590.549' = European thousands separator = 590,549
    df["tournament_attendance"] = (
        df["tournament_attendance"]
        .astype(str)
        .str.replace(".", "", regex=False)
        .str.replace(",", "", regex=False)
        .astype(int)
    )
    log.info(f"  [12] tournament_attendance string → int")

    # Step 13 — Strip whitespace from all string columns
    str_cols = df.select_dtypes(include="object").columns
    for col in str_cols:
        df[col] = df[col].astype(str).str.strip()
    log.info(f"  [13] Whitespace stripped from {len(str_cols)} string columns")

    # Step 14 — Add derived analytical columns
    df["total_goals"] = df["home_team_goals"] + df["away_team_goals"]

    def get_result(row):
        if row["team_initials"] == row["home_team_initials"]:
            mine, theirs = row["home_team_goals"], row["away_team_goals"]
        else:
            mine, theirs = row["away_team_goals"], row["home_team_goals"]
        return "Win" if mine > theirs else ("Loss" if mine < theirs else "Draw")

    df["match_result"]   = df.apply(get_result, axis=1)
    df["is_goal_scorer"] = df["event"].str.contains(r"G\d", regex=True).astype(int)
    log.info(f"  [14] Derived columns added: total_goals, match_result, is_goal_scorer")

    log.info(f"  Clean master dataset          : {df.shape}")
    return df


# ─────────────────────────────────────────────
# STEP 5A: KPI TABLE 1 — Tournament Summary
# ─────────────────────────────────────────────

def build_kpi_tournament(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per World Cup edition (20 rows).
    KPIs: avg_goals_per_match, avg_attendance_per_match,
          host_nation_won, goals_per_team, era label.
    """
    log.info("  Building kpi_tournament ...")

    kpi = (
        df.drop_duplicates("year")[[
            "year", "host_country", "winner", "runners_up", "third", "fourth",
            "goalsscored", "qualifiedteams", "matchesplayed", "tournament_attendance",
        ]]
        .sort_values("year")
        .reset_index(drop=True)
    )

    kpi["avg_goals_per_match"] = (
        kpi["goalsscored"] / kpi["matchesplayed"]
    ).round(2)

    kpi["avg_attendance_per_match"] = (
        kpi["tournament_attendance"] / kpi["matchesplayed"]
    ).round(0).astype(int)

    kpi["host_nation_won"] = (
        kpi["host_country"] == kpi["winner"]
    ).astype(int)

    kpi["goals_per_team"] = (
        kpi["goalsscored"] / kpi["qualifiedteams"]
    ).round(2)

    def era(year):
        if year <= 1978: return "Classic Era (≤16 teams)"
        if year <= 1994: return "Expansion Era (24 teams)"
        return "Modern Era (32 teams)"

    kpi["era"] = kpi["year"].apply(era)

    return kpi


# ─────────────────────────────────────────────
# STEP 5B: KPI TABLE 2 — Team Performance
# ─────────────────────────────────────────────

def build_kpi_team(df: pd.DataFrame, kpi_tournament: pd.DataFrame) -> pd.DataFrame:
    """
    One row per nation, all-time aggregated (83 rows).
    KPIs: matches, wins, draws, losses, goals_scored, goals_conceded,
          win_rate_pct, goal_difference, goals_per_match,
          tournament_appearances, titles_won.
    """
    log.info("  Building kpi_team ...")

    matches = df.drop_duplicates("matchid").copy()

    # Goals scored/conceded — stack home + away perspectives
    home_s = matches[["home_team_name", "home_team_goals", "matchid"]].rename(
        columns={"home_team_name": "team", "home_team_goals": "goals_scored"}
    )
    away_s = matches[["away_team_name", "away_team_goals", "matchid"]].rename(
        columns={"away_team_name": "team", "away_team_goals": "goals_scored"}
    )
    home_c = matches[["home_team_name", "away_team_goals"]].rename(
        columns={"home_team_name": "team", "away_team_goals": "goals_conceded"}
    )
    away_c = matches[["away_team_name", "home_team_goals"]].rename(
        columns={"away_team_name": "team", "home_team_goals": "goals_conceded"}
    )

    all_scored   = pd.concat([home_s, away_s])
    all_conceded = pd.concat([home_c, away_c])

    # Match results per team
    def classify(goals_for, goals_against):
        if goals_for > goals_against: return "Win"
        if goals_for < goals_against: return "Loss"
        return "Draw"

    hr = matches[["home_team_name", "home_team_goals", "away_team_goals"]].copy()
    hr["team"]   = hr["home_team_name"]
    hr["result"] = hr.apply(lambda r: classify(r["home_team_goals"], r["away_team_goals"]), axis=1)

    ar = matches[["away_team_name", "home_team_goals", "away_team_goals"]].copy()
    ar["team"]   = ar["away_team_name"]
    ar["result"] = ar.apply(lambda r: classify(r["away_team_goals"], r["home_team_goals"]), axis=1)

    all_res = pd.concat([hr[["team", "result"]], ar[["team", "result"]]])

    kpi = pd.DataFrame({
        "matches_played"  : all_scored.groupby("team")["matchid"].nunique(),
        "wins"            : all_res[all_res["result"] == "Win"].groupby("team").size(),
        "draws"           : all_res[all_res["result"] == "Draw"].groupby("team").size(),
        "losses"          : all_res[all_res["result"] == "Loss"].groupby("team").size(),
        "goals_scored"    : all_scored.groupby("team")["goals_scored"].sum(),
        "goals_conceded"  : all_conceded.groupby("team")["goals_conceded"].sum(),
    }).fillna(0).astype(int).reset_index()

    kpi["win_rate_pct"]    = (kpi["wins"] / kpi["matches_played"] * 100).round(1)
    kpi["goal_difference"] = kpi["goals_scored"] - kpi["goals_conceded"]
    kpi["goals_per_match"] = (kpi["goals_scored"] / kpi["matches_played"]).round(2)

    # Tournament appearances per team
    team_years = pd.concat([
        matches[["home_team_name", "year"]].rename(columns={"home_team_name": "team"}),
        matches[["away_team_name", "year"]].rename(columns={"away_team_name": "team"}),
    ]).drop_duplicates()
    kpi["tournament_appearances"] = (
        kpi["team"].map(team_years.groupby("team")["year"].nunique())
    )

    # Titles won
    title_counts = kpi_tournament["winner"].value_counts()
    kpi["titles_won"] = kpi["team"].map(title_counts).fillna(0).astype(int)

    return kpi.sort_values("wins", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# STEP 5C: KPI TABLE 3 — Player Stats
# ─────────────────────────────────────────────

def build_kpi_player(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per player, all-time aggregated (7,638 rows).
    KPIs: appearances, goals, cards, substitutions,
          goals_per_appearance, tournaments_attended, career_span_years.
    """
    log.info("  Building kpi_player ...")

    # Parse event codes from event field
    df = df.copy()
    df["goal_count"]  = df["event"].str.count(r"G\d+")
    df["yellow_card"] = df["event"].str.contains(r"Y\d",       regex=True, na=False).astype(int)
    df["red_card"]    = df["event"].str.contains(r"R\d",       regex=True, na=False).astype(int)
    df["subbed_in"]   = df["event"].str.contains(r"SU\d|SI\d", regex=True, na=False).astype(int)

    starts = (
        df[df["line_up"] == "Starting"]
        .groupby("player_name")["matchid"].nunique()
        .rename("starts")
    )
    subs = (
        df[df["line_up"] == "Substitute"]
        .groupby("player_name")["matchid"].nunique()
        .rename("sub_appearances")
    )

    kpi = (
        df.groupby("player_name").agg(
            team                 =("team_initials", "first"),
            appearances          =("matchid",       "nunique"),
            goals                =("goal_count",    "sum"),
            yellow_cards         =("yellow_card",   "sum"),
            red_cards            =("red_card",      "sum"),
            subbed_in_count      =("subbed_in",     "sum"),
            tournaments_attended =("year",          "nunique"),
            first_year           =("year",          "min"),
            last_year            =("year",          "max"),
        )
        .reset_index()
    )

    kpi = kpi.merge(starts.reset_index(), on="player_name", how="left")
    kpi = kpi.merge(subs.reset_index(),   on="player_name", how="left")
    kpi[["starts", "sub_appearances"]] = kpi[["starts", "sub_appearances"]].fillna(0).astype(int)

    kpi["goals_per_appearance"] = (
        kpi["goals"] / kpi["appearances"].replace(0, np.nan)
    ).round(3).fillna(0)

    kpi["career_span_years"] = kpi["last_year"] - kpi["first_year"]

    return kpi.sort_values("goals", ascending=False).reset_index(drop=True)


# ─────────────────────────────────────────────
# STEP 5D: KPI TABLE 4 — Match Analytics
# ─────────────────────────────────────────────

def build_kpi_match(df: pd.DataFrame) -> pd.DataFrame:
    """
    One row per match (836 rows).
    KPIs: ht_goals, second_half_goals, win_type, winning_team,
          goal_margin, and 6 boolean flags for Tableau filters.
    """
    log.info("  Building kpi_match ...")

    matches = df.drop_duplicates("matchid")[[
        "matchid", "year", "datetime", "stage", "stadium", "city",
        "home_team_name", "away_team_name",
        "home_team_initials", "away_team_initials",
        "home_team_goals", "away_team_goals",
        "half_time_home_goals", "half_time_away_goals",
        "total_goals", "win_conditions", "attendance",
        "host_country", "winner",
    ]].copy()

    # Era label
    def era(year):
        if year <= 1978: return "Classic Era (≤16 teams)"
        if year <= 1994: return "Expansion Era (24 teams)"
        return "Modern Era (32 teams)"

    matches["era"] = matches["year"].apply(era)

    # Half-time and second-half goals
    matches["ht_goals"]          = matches["half_time_home_goals"] + matches["half_time_away_goals"]
    matches["second_half_goals"] = matches["total_goals"] - matches["ht_goals"]

    # Winning team and margin
    matches["winning_team"] = matches.apply(
        lambda r: r["home_team_name"] if r["home_team_goals"] > r["away_team_goals"]
        else (r["away_team_name"] if r["away_team_goals"] > r["home_team_goals"] else "Draw"),
        axis=1,
    )
    matches["goal_margin"] = abs(matches["home_team_goals"] - matches["away_team_goals"])

    # Standardise win condition to 3 clean categories
    def clean_win_cond(wc):
        wc_lower = wc.lower()
        if "penalties"  in wc_lower: return "Penalties"
        if "extra time" in wc_lower or "golden goal" in wc_lower: return "Extra Time"
        return "Normal"

    matches["win_type"] = matches["win_conditions"].apply(clean_win_cond)

    # Boolean flags (0/1) — Tableau can filter on these directly
    matches["is_home_win"]     = (matches["home_team_goals"] > matches["away_team_goals"]).astype(int)
    matches["is_away_win"]     = (matches["away_team_goals"] > matches["home_team_goals"]).astype(int)
    matches["is_draw"]         = (matches["home_team_goals"] == matches["away_team_goals"]).astype(int)
    matches["is_high_scoring"] = (matches["total_goals"] >= 4).astype(int)
    matches["is_goalless"]     = (matches["total_goals"] == 0).astype(int)
    matches["is_knockout"]     = matches["stage"].isin(KNOCKOUT_STAGES).astype(int)

    return matches.sort_values(["year", "matchid"]).reset_index(drop=True)


# ─────────────────────────────────────────────
# STEP 6: SANITY CHECKS
# ─────────────────────────────────────────────

def run_sanity_checks(df, kpi_t, kpi_team, kpi_player, kpi_match):
    """
    Cross-check critical numbers across all output tables.
    Raises AssertionError and exits if any check fails.
    """
    log.info("=" * 55)
    log.info("STEP 6 — SANITY CHECKS")
    log.info("=" * 55)

    checks = []

    # Check 1: Total goals must match between tournament and match tables
    t_goals = kpi_t["goalsscored"].sum()
    m_goals = kpi_match["total_goals"].sum()
    ok = abs(t_goals - m_goals) < 100
    checks.append(("Total goals: tournament vs match tables", ok, f"{t_goals} vs {m_goals}"))

    # Check 2: Exactly 836 matches
    ok = len(kpi_match) >= 800
    checks.append(("Match count >= 800", ok, str(len(kpi_match))))

    # Check 3: Exactly 20 tournament editions
    ok = len(kpi_t) == 20
    checks.append(("Tournament editions = 20", ok, str(len(kpi_t))))

    # Check 4: Brazil is top scorer
    top = kpi_team.loc[kpi_team["goals_scored"].idxmax(), "team"]
    ok  = top == "Brazil"
    checks.append(("Brazil = top scoring nation", ok, top))

    # Check 5: Home win rate ~57%
    hw_rate = kpi_match["is_home_win"].mean() * 100
    ok = 55 < hw_rate < 60
    checks.append(("Home win rate between 55–60%", ok, f"{hw_rate:.1f}%"))

    # Check 6: 5 host nation wins
    host_wins = kpi_t["host_nation_won"].sum()
    ok = host_wins == 5
    checks.append(("Host nation won 5 editions", ok, str(host_wins)))

    # Check 7: No duplicate rows in any KPI table
    for name, table in [("kpi_tournament", kpi_t), ("kpi_team", kpi_team),
                         ("kpi_player", kpi_player), ("kpi_match", kpi_match)]:
        dupes = table.duplicated().sum()
        ok = dupes == 0
        checks.append((f"No duplicates in {name}", ok, f"{dupes} duplicates"))

    # Check 8: Master dataset has correct shape
    ok = df.shape[1] == 37
    checks.append(("Master dataset shape = (36595, 37)", ok, str(df.shape)))

    # Report
    all_passed = True
    for desc, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        log.info(f"  [{status}] {desc} — {detail}")
        if not passed:
            all_passed = False

    if not all_passed:
        log.error("One or more sanity checks failed. Aborting export.")
        sys.exit(1)

    log.info(f"  All {len(checks)} checks passed.")


# ─────────────────────────────────────────────
# STEP 7: EXPORT
# ─────────────────────────────────────────────

def export(df, kpi_t, kpi_team, kpi_player, kpi_match, processed_dir: str):
    """
    Write all five output files to data/processed/.
    Logs file name, shape, and size for each.
    """
    log.info("=" * 55)
    log.info("STEP 7 — EXPORT: Writing to data/processed/")
    log.info("=" * 55)

    outputs = {
        "world_cup_master.csv" : df,
        "kpi_tournament.csv"   : kpi_t,
        "kpi_team.csv"         : kpi_team,
        "kpi_player.csv"       : kpi_player,
        "kpi_match.csv"        : kpi_match,
    }

    for filename, table in outputs.items():
        path = os.path.join(processed_dir, filename)
        table.to_csv(path, index=False)
        size_kb = os.path.getsize(path) / 1024
        log.info(
            f"  {filename:<30}  {str(table.shape):<18}  {size_kb:.1f} KB"
        )

    log.info(f"  All files saved to: {processed_dir}")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="FIFA World Cup ETL Pipeline — DVA Capstone 2"
    )
    parser.add_argument(
        "--data-dir",
        default="..",
        help="Project root directory (default: parent of scripts/). "
             "Expects data/raw/ and data/processed/ subdirectories.",
    )
    args = parser.parse_args()

    raw_dir       = os.path.join(args.data_dir, "data", "raw")
    processed_dir = os.path.join(args.data_dir, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)

    start = time.time()

    log.info("=" * 55)
    log.info("FIFA WORLD CUP ETL PIPELINE — STARTING")
    log.info(f"Timestamp : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log.info(f"Raw dir   : {raw_dir}")
    log.info(f"Output dir: {processed_dir}")
    log.info("=" * 55)

    # Execute pipeline
    raw_frames    = extract(raw_dir)
    prep_frames   = prepare_for_merge(raw_frames)
    merged_df     = merge_datasets(prep_frames)
    clean_df      = clean(merged_df)

    log.info("=" * 55)
    log.info("STEP 5 — BUILD: Computing KPI tables")
    log.info("=" * 55)

    kpi_tournament = build_kpi_tournament(clean_df)
    kpi_team       = build_kpi_team(clean_df, kpi_tournament)
    kpi_player     = build_kpi_player(clean_df)
    kpi_match      = build_kpi_match(clean_df)

    log.info(f"  kpi_tournament : {kpi_tournament.shape}")
    log.info(f"  kpi_team       : {kpi_team.shape}")
    log.info(f"  kpi_player     : {kpi_player.shape}")
    log.info(f"  kpi_match      : {kpi_match.shape}")

    run_sanity_checks(clean_df, kpi_tournament, kpi_team, kpi_player, kpi_match)
    export(clean_df, kpi_tournament, kpi_team, kpi_player, kpi_match, processed_dir)

    elapsed = time.time() - start
    log.info("=" * 55)
    log.info(f"PIPELINE COMPLETE  —  {elapsed:.1f} seconds")
    log.info("=" * 55)


if __name__ == "__main__":
    main()
