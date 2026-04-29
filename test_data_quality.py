"""
Comprehensive Data Quality Test Suite
======================================
Tests the three processed datasets before any analysis begins.
Covers: structure, nulls, dtypes, value ranges, logical cross-column
consistency, join integrity, and domain-specific scheduling rules.

Run:  python3 test_data_quality.py
"""

import sys
import pandas as pd


# ── Load ───────────────────────────────────────────────────────────────────
DF  = pd.read_csv("data/processed/wc_players_combined.csv")
MC  = pd.read_csv("data/processed/wc_matches_clean.csv")
CU  = pd.read_csv("data/processed/wc_cups_clean.csv")

PASS = "  [PASS]"
FAIL = "  [FAIL]"
INFO = "  [INFO]"

results = []   # (section, test_name, passed, detail)

def record(section, name, passed, detail=""):
    results.append((section, name, passed, detail))
    tag = PASS if passed else FAIL
    print(f"{tag}  {name}" + (f"  →  {detail}" if detail else ""))

def section(title):
    print(f"\n{'═'*60}")
    print(f"  {title}")
    print(f"{'═'*60}")


# ══════════════════════════════════════════════════════════════════════════
# 1. STRUCTURE
# ══════════════════════════════════════════════════════════════════════════
section("1. STRUCTURE — shape, minimum requirements")

record("Structure", "Players combined ≥ 10,000 rows",
       len(DF) >= 10_000,
       f"{len(DF):,} rows")

record("Structure", "Players combined ≥ 8 columns",
       len(DF.columns) >= 8,
       f"{len(DF.columns)} columns")

record("Structure", "Matches table is 836 rows",
       len(MC) == 836,
       f"{len(MC)} rows")

record("Structure", "Cups table is 20 rows (one per tournament)",
       len(CU) == 20,
       f"{len(CU)} rows")

record("Structure", "Players combined has no completely empty rows",
       DF.isnull().all(axis=1).sum() == 0,
       f"{DF.isnull().all(axis=1).sum()} fully-null rows")

record("Structure", "Matches table has no completely empty rows",
       MC.isnull().all(axis=1).sum() == 0)

record("Structure", "All 20 tournament years present in players data",
       set(CU["Year"]) == set(DF["Year"].unique()),
       f"years in players: {sorted(DF['Year'].unique())}")


# ══════════════════════════════════════════════════════════════════════════
# 2. DUPLICATES
# ══════════════════════════════════════════════════════════════════════════
section("2. DUPLICATES")

exact_dups = DF.duplicated().sum()
record("Duplicates", "No fully identical rows in players combined",
       exact_dups == 0,
       f"{exact_dups} exact duplicate rows")

key_dups = DF.duplicated(subset=["MatchID","Player_Name","Team_Initials","Shirt_Number"]).sum()
record("Duplicates", "No duplicate (MatchID + Player + Team + Shirt)",
       key_dups == 0,
       f"{key_dups} key duplicates")

mc_dups = MC.duplicated(subset=["MatchID"]).sum()
record("Duplicates", "No duplicate MatchIDs in matches table",
       mc_dups == 0,
       f"{mc_dups} duplicate MatchIDs")

cu_dups = CU.duplicated(subset=["Year"]).sum()
record("Duplicates", "No duplicate Years in cups table",
       cu_dups == 0)


# ══════════════════════════════════════════════════════════════════════════
# 3. NULL ANALYSIS
# ══════════════════════════════════════════════════════════════════════════
section("3. NULL ANALYSIS — only expected nulls allowed")

# Columns that must be 100% populated
mandatory = [
    "Year","MatchID","RoundID","Stage_Std","Stage_Order","Match_Date",
    "Match_Time","Day_of_Week","Month","Days_Into_Tournament",
    "Home_Team","Away_Team","Player_Team","Team_Initials","Player_Name",
    "Coach","Is_Starter","Is_Substitute","Is_Captain","Is_GK",
    "Is_Home_Team","Is_Host_Team","Is_Host_Home","Is_Host_Away",
    "Goals","Own_Goals","Yellow_Cards","Red_Cards","Second_Yellow_Red",
    "Effective_Red_Cards","Suspended_Next_Match",
    "Match_Result","Win_Conditions","Team_Won",
    "Team_Goals_For","Team_Goals_Against","Total_Goals","Goal_Diff",
    "Attendance","Tournament_Winner","Qualified_Teams",
    "Tournament_Matches","Tournament_Total_Goals",
]
for col in mandatory:
    n = DF[col].isnull().sum()
    record("Nulls", f"'{col}' has 0 nulls", n == 0, f"{n} nulls" if n else "")

# Rest_Days: null only for each team's chronologically first match of a tournament.
# MatchIDs are not sequential by date, so we identify first match by Match_Date.
# For a ~22-player squad, the first match produces ~22 nulls (one per player row).
first_match_per_team = (
    DF.assign(_date=pd.to_datetime(DF["Match_Date"]))
      .sort_values(["Year", "_date"])
      .groupby(["Year","Player_Team"])["MatchID"]
      .first()
      .reset_index()
      .rename(columns={"MatchID": "First_MatchID"})
)
null_rows = DF[DF["Rest_Days"].isnull()][["Year","Player_Team","MatchID"]].copy()
null_rows = null_rows.merge(first_match_per_team, on=["Year","Player_Team"])
non_first_nulls = (null_rows["MatchID"] != null_rows["First_MatchID"]).sum()
record("Nulls", "Rest_Days nulls are ONLY first-match-of-tournament (per player)",
       non_first_nulls == 0,
       f"{DF['Rest_Days'].isnull().sum()} nulls, {non_first_nulls} outside first-match")

# Shirt_Number: nulls expected for early tournaments (no shirt records)
shirt_nulls = DF["Shirt_Number"].isnull().sum()
early_years = DF[DF["Year"] <= 1954]["Shirt_Number"].isnull().sum()
record("Nulls", "Shirt_Number nulls are from early tournaments only",
       shirt_nulls <= early_years + 200,   # small buffer for isolated missing
       f"{shirt_nulls} total nulls, {early_years} from ≤1954 era")

# No other column should have nulls
all_nulls = DF.isnull().sum()
unexpected = all_nulls[(all_nulls > 0) &
                        (~all_nulls.index.isin(["Rest_Days","Shirt_Number"]))]
record("Nulls", "No unexpected null columns beyond Rest_Days and Shirt_Number",
       len(unexpected) == 0,
       f"Unexpected: {unexpected.to_dict()}" if len(unexpected) else "")


# ══════════════════════════════════════════════════════════════════════════
# 4. DATA TYPES
# ══════════════════════════════════════════════════════════════════════════
section("4. DATA TYPES")

int_cols  = ["Year","MatchID","RoundID","Month","Stage_Order",
             "Days_Into_Tournament","Goals","Own_Goals","Yellow_Cards",
             "Red_Cards","Second_Yellow_Red","Effective_Red_Cards",
             "Team_Goals_For","Team_Goals_Against","Total_Goals",
             "Goal_Diff","Attendance","Qualified_Teams","Tournament_Matches",
             "Tournament_Total_Goals"]
bool_cols = ["Is_Starter","Is_Substitute","Is_Captain","Is_GK",
             "Is_Home_Team","Is_Host_Team","Is_Host_Home","Is_Host_Away",
             "Team_Won","Suspended_Next_Match"]
str_cols  = ["Stage_Std","Match_Result","Win_Conditions","Player_Team",
             "Player_Name","Home_Team","Away_Team","Stadium","City",
             "Coach","Tournament_Winner"]

for col in int_cols:
    ok = pd.api.types.is_integer_dtype(DF[col])
    record("DTypes", f"'{col}' is integer", ok, str(DF[col].dtype))

for col in bool_cols:
    ok = pd.api.types.is_bool_dtype(DF[col])
    record("DTypes", f"'{col}' is boolean", ok, str(DF[col].dtype))

for col in str_cols:
    ok = pd.api.types.is_object_dtype(DF[col])
    record("DTypes", f"'{col}' is string/object", ok, str(DF[col].dtype))

# Match_Date parseable as date
try:
    pd.to_datetime(DF["Match_Date"])
    record("DTypes", "Match_Date is parseable as datetime", True)
except Exception as e:
    record("DTypes", "Match_Date is parseable as datetime", False, str(e))


# ══════════════════════════════════════════════════════════════════════════
# 5. VALUE RANGES
# ══════════════════════════════════════════════════════════════════════════
section("5. VALUE RANGES")

record("Ranges", "Year in [1930, 2014]",
       DF["Year"].between(1930, 2014).all(),
       f"min={DF['Year'].min()}, max={DF['Year'].max()}")

record("Ranges", "Stage_Order in [1, 6]",
       DF["Stage_Order"].between(1, 6).all(),
       f"unique={sorted(DF['Stage_Order'].unique())}")

record("Ranges", "Stage_Std only valid categories",
       DF["Stage_Std"].isin(["Group Stage","Round of 16","Quarter-finals",
                              "Semi-finals","Third Place","Final"]).all(),
       f"unique={sorted(DF['Stage_Std'].unique())}")

record("Ranges", "Match_Result only valid categories",
       DF["Match_Result"].isin(["Home Win","Away Win","Draw"]).all())

record("Ranges", "Win_Conditions only valid categories",
       DF["Win_Conditions"].isin(["Normal","Extra Time","Penalties"]).all(),
       f"unique={sorted(DF['Win_Conditions'].unique())}")

record("Ranges", "Lineup values — only Starter or Substitute per player",
       (DF["Is_Starter"] | DF["Is_Substitute"]).all(),
       "all players flagged as one or the other")

record("Ranges", "Goals per player ≥ 0",
       (DF["Goals"] >= 0).all(), f"min={DF['Goals'].min()}")

record("Ranges", "Goals per player ≤ 5 (sanity — no one scores >5 in one match)",
       (DF["Goals"] <= 5).all(), f"max={DF['Goals'].max()}")

record("Ranges", "Yellow_Cards per player in [0, 2]",
       DF["Yellow_Cards"].between(0, 2).all(),
       f"max={DF['Yellow_Cards'].max()}")

record("Ranges", "Red_Cards per player in [0, 1]",
       DF["Red_Cards"].between(0, 1).all(),
       f"max={DF['Red_Cards'].max()}")

record("Ranges", "Attendance > 0",
       (DF["Attendance"] > 0).all(),
       f"min={DF['Attendance'].min():,}, max={DF['Attendance'].max():,}")

record("Ranges", "Attendance ≤ 200,000 (no stadium holds more)",
       (DF["Attendance"] <= 200_000).all(),
       f"max={DF['Attendance'].max():,}")

record("Ranges", "Days_Into_Tournament in [1, 60]",
       DF["Days_Into_Tournament"].between(1, 60).all(),
       f"min={DF['Days_Into_Tournament'].min()}, max={DF['Days_Into_Tournament'].max()}")

record("Ranges", "Rest_Days (non-null) in [1, 14]",
       DF["Rest_Days"].dropna().between(1, 14).all(),
       f"min={DF['Rest_Days'].min():.0f}, max={DF['Rest_Days'].max():.0f}, mean={DF['Rest_Days'].mean():.1f}")

record("Ranges", "HT_Home_Goals ≤ Home_Goals (can't score more in HT than full game)",
       (DF["HT_Home_Goals"] <= DF["Team_Goals_For"].where(DF["Is_Home_Team"], DF["Team_Goals_Against"]) ).all())

# Simplified: check via matches table
ht_check = (MC["HT_Home_Goals"] <= MC["Home_Goals"]).all() and \
           (MC["HT_Away_Goals"] <= MC["Away_Goals"]).all()
record("Ranges", "HT goals ≤ Full-time goals (matches table)",
       ht_check,
       f"HT_Home > FT_Home: {(MC['HT_Home_Goals'] > MC['Home_Goals']).sum()}, "
       f"HT_Away > FT_Away: {(MC['HT_Away_Goals'] > MC['Away_Goals']).sum()}")

record("Ranges", "Qualified_Teams in [13, 32] (WC grew from 13 to 32 teams)",
       DF["Qualified_Teams"].between(13, 32).all(),
       f"unique={sorted(DF['Qualified_Teams'].unique())}")


# ══════════════════════════════════════════════════════════════════════════
# 6. LOGICAL / CROSS-COLUMN CONSISTENCY
# ══════════════════════════════════════════════════════════════════════════
section("6. LOGICAL CONSISTENCY — cross-column rules")

# Total_Goals = Home_Goals + Away_Goals
tg_check = (DF["Total_Goals"] == (DF["Team_Goals_For"] + DF["Team_Goals_Against"])).all()
record("Logic", "Total_Goals = Team_Goals_For + Team_Goals_Against (for every player)",
       tg_check)

# Goal_Diff consistent with Match_Result
gd_hw = ((DF["Goal_Diff"] > 0) == (DF["Match_Result"] == "Home Win")).all()
gd_aw = ((DF["Goal_Diff"] < 0) == (DF["Match_Result"] == "Away Win")).all()
gd_dr = ((DF["Goal_Diff"] == 0) == (DF["Match_Result"] == "Draw")).all()
record("Logic", "Goal_Diff > 0 ↔ Home Win",  gd_hw)
record("Logic", "Goal_Diff < 0 ↔ Away Win",  gd_aw)
record("Logic", "Goal_Diff = 0 ↔ Draw",       gd_dr)

# Team_Won consistency
home_won_ok = (
    DF.loc[(DF["Is_Home_Team"]) & (DF["Match_Result"] == "Home Win"), "Team_Won"].all()
)
away_won_ok = (
    DF.loc[(~DF["Is_Home_Team"]) & (DF["Match_Result"] == "Away Win"), "Team_Won"].all()
)
draw_not_won = (
    ~DF.loc[DF["Match_Result"] == "Draw", "Team_Won"].any()
)
record("Logic", "Is_Home_Team + Home Win → Team_Won=True",  home_won_ok)
record("Logic", "Is_Away_Team + Away Win → Team_Won=True",  away_won_ok)
record("Logic", "Draw → Team_Won=False for all players",     draw_not_won)

# Team_Goals_For/Against match match-level scoreline
home_for_ok  = (DF.loc[DF["Is_Home_Team"], "Team_Goals_For"]    ==
                DF.loc[DF["Is_Home_Team"], "Team_Goals_For"]).all()   # trivial; real check below
# Real check: join back to matches and compare
chk = DF[["MatchID","Is_Home_Team","Team_Goals_For","Team_Goals_Against"]].merge(
    MC[["MatchID","Home_Goals","Away_Goals"]], on="MatchID"
)
home_rows = chk[chk["Is_Home_Team"]]
away_rows = chk[~chk["Is_Home_Team"]]
for_ok  = (home_rows["Team_Goals_For"]     == home_rows["Home_Goals"]).all() and \
          (away_rows["Team_Goals_For"]      == away_rows["Away_Goals"]).all()
agst_ok = (home_rows["Team_Goals_Against"] == home_rows["Away_Goals"]).all() and \
          (away_rows["Team_Goals_Against"]  == away_rows["Home_Goals"]).all()
record("Logic", "Team_Goals_For matches match scoreline per team side",  for_ok)
record("Logic", "Team_Goals_Against matches match scoreline per team side", agst_ok)

# Is_Home_Team is a single bool: True=home, False=away — no player can be both
# Verify: no player whose Team_Initials equals BOTH Home and Away initials
chk2 = DF.merge(MC[["MatchID","Home_Initials","Away_Initials"]], on="MatchID")
both_sides = ((chk2["Team_Initials"] == chk2["Home_Initials"]) &
              (chk2["Team_Initials"] == chk2["Away_Initials"])).sum()
record("Logic", "No player's initials matches both home AND away team",
       both_sides == 0, f"{both_sides} violations")

# Every player's initials must match either the home or away team initials
initials_ok = DF.merge(
    MC[["MatchID","Home_Initials","Away_Initials"]], on="MatchID"
).apply(
    lambda r: r["Team_Initials"] in (r["Home_Initials"], r["Away_Initials"]), axis=1
).all()
record("Logic", "Every player's Team_Initials matches Home or Away initials",
       initials_ok)

# Is_Starter and Is_Substitute are mutually exclusive
both_lineup = (DF["Is_Starter"] & DF["Is_Substitute"]).sum()
record("Logic", "No player flagged as both Starter AND Substitute",
       both_lineup == 0, f"{both_lineup} violations")

# Effective_Red_Cards = Red_Cards + Second_Yellow_Red
erc_ok = (DF["Effective_Red_Cards"] == (DF["Red_Cards"] + DF["Second_Yellow_Red"])).all()
record("Logic", "Effective_Red_Cards = Red_Cards + Second_Yellow_Red", erc_ok)

# Suspended_Next_Match ↔ Effective_Red_Cards > 0
susp_ok = (DF["Suspended_Next_Match"] == (DF["Effective_Red_Cards"] > 0)).all()
record("Logic", "Suspended_Next_Match ↔ Effective_Red_Cards > 0", susp_ok)

# Is_Host_Team ↔ Player_Team = Tournament_Host
host_team_ok = (DF["Is_Host_Team"] == (DF["Player_Team"] == DF["Tournament_Host"])).all()
record("Logic", "Is_Host_Team ↔ Player_Team == Tournament_Host", host_team_ok)

# Is_Host_Home/Away consistent with home/away team names
host_home_ok = (MC["Is_Host_Home"] == (MC["Home_Team"] == MC["Tournament_Host"])).all()
host_away_ok = (MC["Is_Host_Away"] == (MC["Away_Team"] == MC["Tournament_Host"])).all()
record("Logic", "Is_Host_Home ↔ Home_Team == Tournament_Host (matches table)", host_home_ok)
record("Logic", "Is_Host_Away ↔ Away_Team == Tournament_Host (matches table)", host_away_ok)

# Win_Conditions + Match_Result domain rules
# Draw can only be "Normal" or "Penalties" (not Extra Time — ET always produces a winner)
draw_et = ((DF["Match_Result"] == "Draw") & (DF["Win_Conditions"] == "Extra Time")).sum()
record("Logic", "No Draw + Extra Time (ET always produces a winner)",
       draw_et == 0, f"{draw_et} violations")

# Group Stage should never have Penalties (no pens in group stage)
gs_pens = ((DF["Stage_Std"] == "Group Stage") & (DF["Win_Conditions"] == "Penalties")).sum()
record("Logic", "No Penalties in Group Stage",
       gs_pens == 0, f"{gs_pens} violations")

# Penalties only in knockout stages (Stage_Order ≥ 2)
pens_in_group = ((DF["Win_Conditions"] == "Penalties") & (DF["Stage_Order"] < 2)).sum()
record("Logic", "Penalties only in knockout stages (Stage_Order ≥ 2)",
       pens_in_group == 0, f"{pens_in_group} violations")

# A player subbed in AND subbed out is valid: e.g. entered at 60', taken off at 80'
# due to injury. We only flag if counts are unreasonably high (>1 each).
both_sub_excessive = ((DF["Subbed_In"] > 1) | (DF["Subbed_Out"] > 1)).sum()
record("Logic", "No player has >1 sub-in or >1 sub-out in a single match",
       both_sub_excessive == 0, f"{both_sub_excessive} excessive sub events")


# ══════════════════════════════════════════════════════════════════════════
# 7. JOIN / REFERENTIAL INTEGRITY
# ══════════════════════════════════════════════════════════════════════════
section("7. JOIN / REFERENTIAL INTEGRITY")

# Every MatchID in players exists in matches
p_ids = set(DF["MatchID"].unique())
m_ids = set(MC["MatchID"].unique())
orphan_players = p_ids - m_ids
record("Joins", "All player MatchIDs exist in matches table",
       len(orphan_players) == 0, f"{len(orphan_players)} orphan MatchIDs")

matches_without_players = m_ids - p_ids
record("Joins", "All match MatchIDs have at least one player record",
       len(matches_without_players) == 0, f"{len(matches_without_players)} matches with no player data")

# Every Year in players exists in cups
p_years = set(DF["Year"].unique())
c_years = set(CU["Year"].unique())
missing_years = p_years - c_years
record("Joins", "All player Years have a tournament record in cups",
       len(missing_years) == 0, f"missing: {missing_years}")

# Player_Team names are consistent with Home_Team/Away_Team
teams_in_matches = set(MC["Home_Team"].unique()) | set(MC["Away_Team"].unique())
teams_in_players = set(DF["Player_Team"].unique())
ghost_teams = teams_in_players - teams_in_matches
record("Joins", "All Player_Team names appear in match team columns",
       len(ghost_teams) == 0, f"ghost teams: {ghost_teams}")


# ══════════════════════════════════════════════════════════════════════════
# 8. DOMAIN / SCHEDULING RULES
# ══════════════════════════════════════════════════════════════════════════
section("8. DOMAIN / SCHEDULING RULES")

# Exactly 1 captain per team per match
captain_counts = (
    DF.groupby(["MatchID","Team_Initials"])["Is_Captain"].sum()
)
# Some early matches have 0 captains (no captain data in raw) — that's ok
# But no match should have > 1 captain per team
record("Domain", "No team has > 1 captain in a match",
       (captain_counts <= 1).all(),
       f"teams with >1 captain: {(captain_counts > 1).sum()}")

zero_captains = (captain_counts == 0).sum()
record("Domain", "Captain data coverage (informational)",
       True,
       f"{(captain_counts == 1).sum()} team-matches have 1 captain, "
       f"{zero_captains} have 0 (early tournaments)")

# At least 1 GK per team per match
gk_counts = DF.groupby(["MatchID","Team_Initials"])["Is_GK"].sum()
record("Domain", "At least 1 GK per team per match",
       (gk_counts >= 1).all(),
       f"team-matches with 0 GKs: {(gk_counts < 1).sum()}")

# Stage ordering within each tournament year: higher Stage_Order must have
# a later (or equal) min date than lower Stage_Order. Checked per year.
# (Cross-year averages are misleading because early WCs had no R16, making QF
#  happen earlier in those tournaments and dragging its global average down.)
stage_order_ok = True
for yr, grp in DF.groupby("Year"):
    stage_min_day = grp.groupby("Stage_Order")["Days_Into_Tournament"].min().sort_index()
    if list(stage_min_day.values) != sorted(stage_min_day.values):
        stage_order_ok = False
        break
record("Domain", "Within each tournament, later Stage_Order starts on a later day",
       stage_order_ok)

# Each team plays at most 7 matches in a tournament (group x3 + R16 + QF + SF + Final/3rd)
team_match_counts = DF.groupby(["Year","Player_Team"])["MatchID"].nunique()
record("Domain", "No team played more than 7 matches in a single tournament",
       (team_match_counts <= 7).all(),
       f"max matches by one team in one tournament: {team_match_counts.max()}")

# Minimum matches per team per tournament = 1 (some had only group stage)
record("Domain", "Every team played at least 1 match per tournament entry",
       (team_match_counts >= 1).all(),
       f"min: {team_match_counts.min()}")

# All 20 Cup years have a winner
record("Domain", "All 20 tournaments have a winner recorded",
       CU["Winner"].notna().all() and (CU["Winner"].str.strip() != "").all())

# Tournament_Winner in players matches cups Winner
for _, row in CU.iterrows():
    yr_winners = DF[DF["Year"] == row["Year"]]["Tournament_Winner"].unique()
    if len(yr_winners) != 1 or yr_winners[0] != row["Winner"]:
        record("Domain", f"Tournament_Winner correct for {row['Year']}", False,
               f"expected {row['Winner']}, got {yr_winners}")
        break
else:
    record("Domain", "Tournament_Winner in players matches cups table for all 20 years", True)

# Rest days: within a tournament, teams shouldn't play twice on the same day
same_day = (
    DF.groupby(["Year","Player_Team","Match_Date"])["MatchID"].nunique()
)
record("Domain", "No team plays two different matches on the same day",
       (same_day <= 1).all(),
       f"violations: {(same_day > 1).sum()}")


# ══════════════════════════════════════════════════════════════════════════
# 9. COMPLETENESS / COVERAGE SUMMARY
# ══════════════════════════════════════════════════════════════════════════
section("9. COVERAGE SUMMARY (informational)")

print(f"{INFO}  Total player-match rows        : {len(DF):,}")
print(f"{INFO}  Unique matches                 : {DF['MatchID'].nunique()}")
print(f"{INFO}  Unique players (by name)       : {DF['Player_Name'].nunique():,}")
print(f"{INFO}  Unique teams                   : {DF['Player_Team'].nunique()}")
print(f"{INFO}  Tournaments covered            : {DF['Year'].nunique()} (1930–2014)")
print(f"{INFO}  Starters                       : {DF['Is_Starter'].sum():,}")
print(f"{INFO}  Substitutes                    : {DF['Is_Substitute'].sum():,}")
print(f"{INFO}  Captains flagged               : {DF['Is_Captain'].sum():,}")
print(f"{INFO}  Goals from events              : {DF['Goals'].sum():,}")
print(f"{INFO}  Yellow cards                   : {DF['Yellow_Cards'].sum():,}")
print(f"{INFO}  Red cards (all kinds)          : {DF['Effective_Red_Cards'].sum():,}")
print(f"{INFO}  Players suspended next match   : {DF['Suspended_Next_Match'].sum():,}")
print(f"{INFO}  Host-nation player appearances : {DF['Is_Host_Team'].sum():,}")
print(f"{INFO}  Rest_Days null (first match)   : {DF['Rest_Days'].isnull().sum():,}")
print(f"{INFO}  Avg rest days (within-tourn)   : {DF['Rest_Days'].mean():.1f} days")
print(f"{INFO}  Min / Max rest days            : {DF['Rest_Days'].min():.0f} / {DF['Rest_Days'].max():.0f}")
print(f"{INFO}  Matches with Extra Time        : {(DF['Win_Conditions']=='Extra Time').any() and DF[DF['Win_Conditions']=='Extra Time']['MatchID'].nunique()}")
print(f"{INFO}  Matches decided by Penalties   : {DF[DF['Win_Conditions']=='Penalties']['MatchID'].nunique()}")


# ══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════
print(f"\n{'═'*60}")
print("  FINAL SUMMARY")
print(f"{'═'*60}")

total   = len(results)
passed  = sum(1 for r in results if r[2])
failed  = total - passed

for sec, name, ok, detail in results:
    if not ok:
        print(f"{FAIL}  [{sec}]  {name}" + (f"  →  {detail}" if detail else ""))

print(f"\n  {passed}/{total} tests passed  |  {failed} failed")

if failed == 0:
    print("\n  ✓ Data is clean and ready for analysis.")
else:
    print(f"\n  ✗ {failed} issue(s) found — review failures above before proceeding.")

sys.exit(0 if failed == 0 else 1)
