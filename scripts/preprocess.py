"""
FIFA World Cup Data Preprocessing Pipeline — Player-Match Grain
================================================================
Problem Statement:
  Analyze player-level deployment, disciplinary patterns, and performance
  across FIFA World Cup history (1930-2014) to identify scheduling factors
  — squad fatigue, suspension risk from card accumulation, host-nation
  advantage, and stage-by-stage workload — that FIFA should account for
  when planning match fixtures.

Grain: One row per player per match appearance.
Output: ~37,000 rows × 25+ columns — no duplicates, no empty rows.

Raw inputs  (data/raw/):
  WorldCups.csv       — 20 rows,  tournament summaries
  WorldCupMatches.csv — 4,572 raw rows (852 valid, 836 unique matches)
  WorldCupPlayers.csv — 37,784 raw rows (player appearances)

Output (data/processed/):
  wc_players_combined.csv  — main analytical dataset (player-match grain)
  wc_matches_clean.csv     — supporting match-level table (836 rows)
  wc_cups_clean.csv        — supporting tournament table (20 rows)
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path

RAW       = Path("data/raw")
PROCESSED = Path("data/processed")
PROCESSED.mkdir(parents=True, exist_ok=True)

pd.set_option("display.max_columns", None)


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def parse_attendance(val):
    """'1.045.246' (European dot-thousands) → 1045246 (int)."""
    if pd.isna(val):
        return np.nan
    return int(float(str(val).strip().replace(".", "")))


REPLACEMENT_CHAR = "\ufffd"   # U+FFFD — what the raw CSVs use instead of lost accented chars

def clean_string(s):
    """
    Strip Unicode replacement characters (U+FFFD) that are permanently
    baked into the raw CSVs where accented characters once existed,
    and remove any HTML parsing artifacts (rn\">) left by the original
    web-scraping process. Returns clean ASCII text.
    """
    if pd.isna(s):
        return s
    s = str(s)
    s = s.replace(REPLACEMENT_CHAR, "")   # remove ? from Pele, Juergen, etc.
    s = re.sub(r'^rn">', "", s)            # strip HTML artifact prefix
    return s.strip()


# Unified team-name map — applied after clean_string so names are already stripped
TEAM_MAP = {
    # Germany era names
    "Germany FR":                  "West Germany",
    "German DR":                   "East Germany",
    # HTML-artifact team names (rn"> prefix already stripped by clean_string,
    # but kept here as a safety net in case order changes)
    "rn\">Republic of Ireland":    "Ireland",
    "rn\">Bosnia and Herzegovina": "Bosnia and Herzegovina",
    "rn\">Serbia and Montenegro":  "Serbia and Montenegro",
    "rn\">Trinidad and Tobago":    "Trinidad and Tobago",
    "rn\">United Arab Emirates":   "United Arab Emirates",
    # Iran — two spellings coexist in the raw data
    "IR Iran":                     "Iran",
    # Other standardisations
    "Republic of Ireland":         "Ireland",
    "Korea Republic":              "South Korea",
    "Korea DPR":                   "North Korea",
}

def normalize_team(name):
    if pd.isna(name):
        return name
    name = clean_string(name)
    return TEAM_MAP.get(name, name)


# Stage → (standard label, sort order 1–6)
STAGE_MAP = {
    "Preliminary round":        ("Group Stage",    1),
    "First round":              ("Group Stage",    1),
    **{f"Group {x}": ("Group Stage", 1) for x in
       ["1","2","3","4","5","6","A","B","C","D","E","F","G","H"]},
    "Round of 16":              ("Round of 16",    2),
    "Quarter-finals":           ("Quarter-finals", 3),
    "Semi-finals":              ("Semi-finals",    4),
    "Match for third place":    ("Third Place",    5),
    "Play-off for third place": ("Third Place",    5),
    "Third place":              ("Third Place",    5),
    "Final":                    ("Final",          6),
}


def parse_win_conditions(val):
    v = str(val).strip().lower() if pd.notna(val) else ""
    if "penalt"    in v: return "Penalties"
    if "extra time" in v: return "Extra Time"
    return "Normal"


def parse_match_datetime(s):
    """Handle both 'Jul' and 'July' month formats."""
    s = str(s).strip()
    for fmt in ("%d %b %Y - %H:%M", "%d %B %Y - %H:%M"):
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    return pd.NaT


def parse_events(event_str):
    """
    Parse a player's Event field into numeric counters.

    Event codes (from data dictionary):
      G   = goal scored
      W   = own goal (credited to opposition)
      Y   = yellow card
      R   = red card (straight)
      RSY = red card issued as second yellow
      P   = penalty scored
      MP  = missed penalty
      I   = substitution in  (IH = first-half sub in)
      O   = substitution out (OH = first-half sub out)
    """
    out = dict(Goals=0, Own_Goals=0, Yellow_Cards=0, Red_Cards=0,
               Second_Yellow_Red=0, Penalties_Scored=0, Missed_Penalties=0,
               Subbed_In=0, Subbed_Out=0)
    if pd.isna(event_str) or not str(event_str).strip():
        return out
    for tok in re.findall(r"[A-Z]+\d*'?", str(event_str)):
        code = re.match(r"([A-Z]+)", tok).group(1)
        if   code == "G":   out["Goals"]             += 1
        elif code == "W":   out["Own_Goals"]          += 1
        elif code == "Y":   out["Yellow_Cards"]       += 1
        elif code == "R":   out["Red_Cards"]          += 1
        elif code == "RSY": out["Second_Yellow_Red"]  += 1
        elif code == "P":   out["Penalties_Scored"]   += 1
        elif code == "MP":  out["Missed_Penalties"]   += 1
        elif code in ("I","IH"): out["Subbed_In"]     += 1
        elif code in ("O","OH"): out["Subbed_Out"]    += 1
    return out


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 — Clean WorldCups (tournament level, 20 rows)
# ═══════════════════════════════════════════════════════════════════════════
print("─" * 60)
print("STEP 1  WorldCups.csv — tournament context")
print("─" * 60)

cups = pd.read_csv(RAW / "WorldCups.csv")
print(f"  Raw: {cups.shape}")

cups["Attendance"] = cups["Attendance"].apply(parse_attendance)
for col in ["Winner","Runners-Up","Third","Fourth"]:
    cups[col] = cups[col].apply(normalize_team)

cups = cups.rename(columns={
    "Country":      "Host_Country",
    "Runners-Up":   "Runners_Up",
    "GoalsScored":  "Tournament_Total_Goals",
    "QualifiedTeams":  "Qualified_Teams",
    "MatchesPlayed":   "Tournament_Matches",
    "Attendance":      "Tournament_Attendance",
})
cups.to_csv(PROCESSED / "wc_cups_clean.csv", index=False)
print(f"  Clean: {cups.shape}  → wc_cups_clean.csv")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2 — Clean WorldCupMatches (match level → 836 unique matches)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("STEP 2  WorldCupMatches.csv — match context")
print("─" * 60)

m_raw = pd.read_csv(RAW / "WorldCupMatches.csv")
print(f"  Raw: {m_raw.shape}")

# Drop 3,720 completely empty rows
m = m_raw.dropna(subset=["MatchID","Home Team Name","Away Team Name"]).copy()
print(f"  After removing empty rows: {len(m)}")

# Strip whitespace, remove U+FFFD replacement chars, strip HTML artifacts
for col in m.select_dtypes("object").columns:
    m[col] = m[col].apply(clean_string)

# Resolve 16 duplicate MatchIDs — keep row with Attendance (preferred) else first
m = (m.sort_values("Attendance", ascending=False)
      .drop_duplicates(subset=["MatchID"], keep="first")
      .sort_values(["Year","RoundID","MatchID"])
      .reset_index(drop=True))
print(f"  After dedup on MatchID: {len(m)} unique matches")

# Cast numeric types
m["Year"]    = m["Year"].astype(int)
m["MatchID"] = m["MatchID"].astype(int)
m["RoundID"] = m["RoundID"].astype(int)
for col in ["Home Team Goals","Away Team Goals",
            "Half-time Home Goals","Half-time Away Goals"]:
    m[col] = m[col].astype(int)

# Parse datetime (handles 'Jul' and 'July' month variants)
m["Match_Datetime"] = m["Datetime"].apply(parse_match_datetime)
m["Match_Date"]     = m["Match_Datetime"].dt.date
m["Match_Time"]     = m["Match_Datetime"].dt.strftime("%H:%M")
m["Day_of_Week"]    = m["Match_Datetime"].dt.day_name()
m["Month"]          = m["Match_Datetime"].dt.month

# Days into tournament (day 1 = first match of that year's WC)
t_start = m.groupby("Year")["Match_Datetime"].min().rename("T_Start")
m = m.join(t_start, on="Year")
m["Days_Into_Tournament"] = (m["Match_Datetime"] - m["T_Start"]).dt.days + 1
m.drop(columns=["T_Start"], inplace=True)

# Fix 2 null Attendance values → year median
med_att = m.groupby("Year")["Attendance"].median()
m["Attendance"] = m.apply(
    lambda r: int(med_att[r["Year"]]) if pd.isna(r["Attendance"]) else int(r["Attendance"]),
    axis=1,
)

# Normalize team names
m["Home Team Name"] = m["Home Team Name"].apply(normalize_team)
m["Away Team Name"] = m["Away Team Name"].apply(normalize_team)

# Standardize stage
m["Stage_Std"]   = m["Stage"].str.strip().map(lambda s: STAGE_MAP.get(s, (s,0))[0])
m["Stage_Order"] = m["Stage"].str.strip().map(lambda s: STAGE_MAP.get(s, (s,0))[1])

# Win conditions
m["Win_Conditions"] = m["Win conditions"].apply(parse_win_conditions)

# Derived match columns
m["Total_Goals"]    = m["Home Team Goals"] + m["Away Team Goals"]
m["Goal_Diff"]      = m["Home Team Goals"] - m["Away Team Goals"]
m["SH_Home_Goals"]  = m["Home Team Goals"] - m["Half-time Home Goals"]
m["SH_Away_Goals"]  = m["Away Team Goals"] - m["Half-time Away Goals"]
m["Match_Result"]   = np.where(m["Goal_Diff"] > 0, "Home Win",
                      np.where(m["Goal_Diff"] < 0, "Away Win", "Draw"))

# Host-nation flag
host_map = cups.set_index("Year")["Host_Country"].to_dict()
m["Tournament_Host"] = m["Year"].map(host_map)
m["Is_Host_Home"]    = (m["Home Team Name"] == m["Tournament_Host"])
m["Is_Host_Away"]    = (m["Away Team Name"] == m["Tournament_Host"])

# Within-tournament rest days per team
# Reset tracker each year so cross-tournament gaps aren't computed
m_sorted = m.sort_values(["Year","Match_Datetime"]).reset_index(drop=True)
home_rest, away_rest = [], []
for year, grp in m_sorted.groupby("Year"):
    last = {}
    for idx in grp.index:
        row = m_sorted.loc[idx]
        h, a, dt = row["Home Team Name"], row["Away Team Name"], row["Match_Datetime"]
        home_rest.append((dt - last[h]).days if h in last and pd.notna(dt) else np.nan)
        away_rest.append((dt - last[a]).days if a in last and pd.notna(dt) else np.nan)
        if pd.notna(dt):
            last[h] = dt
            last[a] = dt

m_sorted["Rest_Days_Home"] = home_rest
m_sorted["Rest_Days_Away"] = away_rest
m_sorted = m_sorted.sort_values(["Year","Stage_Order","MatchID"]).reset_index(drop=True)

# Clean column rename for export
matches_clean = m_sorted.rename(columns={
    "Home Team Name":       "Home_Team",
    "Away Team Name":       "Away_Team",
    "Home Team Goals":      "Home_Goals",
    "Away Team Goals":      "Away_Goals",
    "Half-time Home Goals": "HT_Home_Goals",
    "Half-time Away Goals": "HT_Away_Goals",
    "Home Team Initials":   "Home_Initials",
    "Away Team Initials":   "Away_Initials",
    "Stage":                "Stage_Raw",
    "Win conditions":       "Win_Conditions_Raw",
})[[
    "Year","MatchID","RoundID","Match_Date","Match_Time","Day_of_Week","Month",
    "Stage_Raw","Stage_Std","Stage_Order","Days_Into_Tournament",
    "Home_Team","Away_Team","Home_Initials","Away_Initials",
    "Tournament_Host","Is_Host_Home","Is_Host_Away",
    "Home_Goals","Away_Goals","HT_Home_Goals","HT_Away_Goals",
    "SH_Home_Goals","SH_Away_Goals","Total_Goals","Goal_Diff",
    "Match_Result","Win_Conditions",
    "Attendance","Stadium","City","Referee",
    "Rest_Days_Home","Rest_Days_Away",
]]

matches_clean.to_csv(PROCESSED / "wc_matches_clean.csv", index=False)
print(f"  Clean: {matches_clean.shape}  → wc_matches_clean.csv")
print(f"  Null Attendance: {matches_clean['Attendance'].isnull().sum()}")
print(f"  Null Match_Date: {matches_clean['Match_Date'].isnull().sum()}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 — Clean WorldCupPlayers (player level)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("STEP 3  WorldCupPlayers.csv — player appearances")
print("─" * 60)

p_raw = pd.read_csv(RAW / "WorldCupPlayers.csv")
print(f"  Raw: {p_raw.shape}")

p = p_raw.copy()

# Strip whitespace, remove U+FFFD replacement chars, strip HTML artifacts
for col in p.select_dtypes("object").columns:
    p[col] = p[col].apply(clean_string)

# Drop FULLY identical rows (every column same value — pure data entry duplicates)
before = len(p)
p = p.drop_duplicates()
print(f"  After removing {before - len(p)} fully identical duplicate rows: {len(p)}")

# Shirt Number 0 = placeholder / unknown → NaN
p["Shirt Number"] = p["Shirt Number"].replace(0, np.nan)

# Is_Captain: Position field encodes captain ('C' or 'GKC')
p["Is_Captain"] = p["Position"].isin(["C", "GKC"])
p["Is_GK"]      = p["Position"].isin(["GK", "GKC"])

# Is_Starter vs substitute — set initially from Line-up field
p["Is_Starter"]    = (p["Line-up"] == "S")
p["Is_Substitute"] = (p["Line-up"] == "N")

# Parse Event column into individual counters
event_df = pd.DataFrame(p["Event"].apply(parse_events).tolist())
p = pd.concat([p.reset_index(drop=True), event_df], axis=1)

# FIX ISSUE 5 — Correct Subbed_In/Out contradictions caused by wrong Line-up flags.
#
# Rule A: Subbed_In > 0 → player entered mid-match → always a substitute.
#         Takes highest priority — applied last so it wins all conflicts.
#
# Rule B: Subbed_Out > 0 AND Subbed_In = 0 → player started and was replaced.
#         Only applies when there is NO sub-in event (so we don't mis-classify
#         players who came on as a sub AND were then taken off, e.g. Battiston 1982).
#
# Priority: Rule A overrides Rule B — a player with both events came on as a sub.
mask_subout_only = (p["Subbed_Out"] > 0) & (p["Subbed_In"] == 0)
p.loc[mask_subout_only, "Is_Starter"]    = True
p.loc[mask_subout_only, "Is_Substitute"] = False

mask_subin = p["Subbed_In"] > 0      # applied after Rule B so it wins conflicts
p.loc[mask_subin, "Is_Starter"]    = False
p.loc[mask_subin, "Is_Substitute"] = True

# Rename for clarity
p = p.rename(columns={
    "Team Initials": "Team_Initials",
    "Coach Name":    "Coach",
    "Shirt Number":  "Shirt_Number",
    "Player Name":   "Player_Name",
    "Line-up":       "Lineup",
})

# Effective red cards: straight red OR second-yellow red
p["Effective_Red_Cards"] = p["Red_Cards"] + p["Second_Yellow_Red"]

# Suspension flag: player got a red (any kind) → suspended for next match
p["Suspended_Next_Match"] = p["Effective_Red_Cards"] > 0

print(f"  Player data shape after cleaning: {p.shape}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 4 — Join players → matches → tournament (player-match grain)
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("STEP 4  Joining all three datasets")
print("─" * 60)

# 4a. Build lookup: MatchID → match context columns needed per player row
match_lookup = matches_clean[[
    "MatchID","Year","Match_Date","Match_Time","Day_of_Week","Month",
    "Stage_Std","Stage_Order","Stage_Raw","Days_Into_Tournament",
    "Home_Team","Away_Team","Home_Initials","Away_Initials",
    "Tournament_Host","Is_Host_Home","Is_Host_Away",
    "Home_Goals","Away_Goals","Total_Goals","Goal_Diff",
    "HT_Home_Goals","HT_Away_Goals",
    "Match_Result","Win_Conditions",
    "Attendance","Stadium","City",
    "Rest_Days_Home","Rest_Days_Away",
]].copy()

# 4b. Merge players → matches on MatchID
combined = p.merge(match_lookup, on="MatchID", how="inner")
print(f"  After join players↔matches: {combined.shape}")

# 4c. Derive player-specific context columns
#     Is this player on the home or away team?
combined["Is_Home_Team"] = combined["Team_Initials"] == combined["Home_Initials"]
combined["Is_Away_Team"] = combined["Team_Initials"] == combined["Away_Initials"]

#     Full team name (from match context, matched by initials)
combined["Player_Team"] = np.where(
    combined["Is_Home_Team"],
    combined["Home_Team"],
    combined["Away_Team"]
)

#     Did this player's team win?
combined["Team_Won"] = (
    ((combined["Is_Home_Team"]) & (combined["Match_Result"] == "Home Win")) |
    ((combined["Is_Away_Team"]) & (combined["Match_Result"] == "Away Win"))
)

#     Goals for and against this player's team in this match
combined["Team_Goals_For"] = np.where(
    combined["Is_Home_Team"],
    combined["Home_Goals"],
    combined["Away_Goals"]
)
combined["Team_Goals_Against"] = np.where(
    combined["Is_Home_Team"],
    combined["Away_Goals"],
    combined["Home_Goals"]
)

#     Is this player's team the host nation?
combined["Is_Host_Team"] = combined["Player_Team"] == combined["Tournament_Host"]

#     Rest days for this player's team specifically
combined["Rest_Days"] = np.where(
    combined["Is_Home_Team"],
    combined["Rest_Days_Home"],
    combined["Rest_Days_Away"]
)

# FIX ISSUE 4 — Goals reliability flag
# In 200/1672 team-match combos, sum(player Goals) < Team_Goals_For.
# This happens because the original WorldCupPlayers.csv didn't record which
# player scored for every goal (common in early tournaments and some later ones).
# The scoreline columns (Team_Goals_For / Team_Goals_Against) are ALWAYS correct
# as they come from WorldCupMatches. The player-level Goals column is unreliable
# for reconstructing scorelines — use it only for individual player analysis.
# We add a flag so analysts know which rows have complete goal attribution.
goals_check = (
    combined.groupby(["MatchID", "Team_Initials"])
    .apply(lambda g: g["Goals"].sum() == g["Team_Goals_For"].iloc[0])
    .reset_index()
    .rename(columns={0: "Goals_Fully_Attributed"})
)
combined = combined.merge(goals_check, on=["MatchID", "Team_Initials"], how="left")

# 4d. Join tournament context from cups
cups_lookup = cups[["Year","Host_Country","Winner","Qualified_Teams",
                     "Tournament_Matches","Tournament_Total_Goals",
                     "Tournament_Attendance"]].rename(
    columns={"Winner": "Tournament_Winner"}
)
combined = combined.merge(cups_lookup, on="Year", how="left")
print(f"  After join ↔ tournament: {combined.shape}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 5 — Final column selection & ordering
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("STEP 5  Final column selection")
print("─" * 60)

final_cols = [
    # Identity
    "Year", "MatchID", "RoundID",

    # Scheduling / timing
    "Match_Date", "Match_Time", "Day_of_Week", "Month",
    "Stage_Std", "Stage_Order", "Stage_Raw",
    "Days_Into_Tournament", "Rest_Days",

    # Venue
    "Stadium", "City", "Host_Country",

    # Teams
    "Home_Team", "Away_Team", "Tournament_Host",
    "Is_Host_Home", "Is_Host_Away",

    # Player identity
    "Player_Team", "Team_Initials", "Player_Name",
    "Shirt_Number", "Coach",
    "Is_Starter", "Is_Substitute", "Is_Captain", "Is_GK",
    "Is_Home_Team", "Is_Host_Team",

    # Player events
    # NOTE: Goals = player-attributed goals only. Use Team_Goals_For for scorelines.
    # Goals_Fully_Attributed = True means every goal has a named scorer in this match.
    "Goals", "Own_Goals", "Goals_Fully_Attributed",
    "Yellow_Cards", "Red_Cards", "Second_Yellow_Red", "Effective_Red_Cards",
    "Suspended_Next_Match",
    "Penalties_Scored", "Missed_Penalties",
    "Subbed_In", "Subbed_Out",

    # Match outcome context (from player's perspective)
    "Match_Result", "Win_Conditions", "Team_Won",
    "Team_Goals_For", "Team_Goals_Against",
    "Total_Goals", "Goal_Diff",
    "HT_Home_Goals", "HT_Away_Goals",

    # Venue demand
    "Attendance",

    # Tournament context
    "Tournament_Winner", "Qualified_Teams",
    "Tournament_Matches", "Tournament_Total_Goals",
]

# Keep only cols that exist
final_cols = [c for c in final_cols if c in combined.columns]
df = combined[final_cols].copy()

print(f"  Columns selected: {len(final_cols)}")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — Validation
# ═══════════════════════════════════════════════════════════════════════════
print("\n" + "─" * 60)
print("STEP 6  Validation")
print("─" * 60)

# No true duplicates (unique on MatchID + Player_Name + Team_Initials + Shirt_Number)
dups = df.duplicated(subset=["MatchID","Player_Name","Team_Initials","Shirt_Number"])
print(f"  Duplicate rows (MatchID+Player+Team+Shirt): {dups.sum()}")

# No empty rows
empty = df.isnull().all(axis=1).sum()
print(f"  Completely empty rows: {empty}")

# Null summary
nulls = df.isnull().sum()
print(f"\n  Columns with nulls:")
print(nulls[nulls > 0].to_string())

# Logical checks
assert (df["Goals"]         >= 0).all(), "Negative goals"
assert (df["Yellow_Cards"]  >= 0).all(), "Negative yellow cards"
assert (df["Red_Cards"]     >= 0).all(), "Negative red cards"
assert (df["Attendance"]    > 0).all(),  "Zero or negative attendance"
assert df["Match_Result"].isin(["Home Win","Away Win","Draw"]).all(), "Bad match result"
assert df["Stage_Order"].between(1,6).all(), "Stage order out of range"
assert df["Year"].between(1930,2014).all(), "Year out of range"

print("\n  All logical assertions passed.")

print(f"\n  ── FINAL DATASET ──────────────────────────────────")
print(f"  Rows:    {len(df):,}")
print(f"  Columns: {len(df.columns)}")
print(f"  Years:   {df['Year'].min()} – {df['Year'].max()}")
print(f"\n  Stage breakdown (rows):")
print(df["Stage_Std"].value_counts().to_string())
print(f"\n  Players total (unique names): {df['Player_Name'].nunique():,}")
print(f"  Teams:                        {df['Player_Team'].nunique()}")
print(f"  Starters vs Subs:             {df['Is_Starter'].sum():,} starters, {df['Is_Substitute'].sum():,} subs")
print(f"  Captains:                     {df['Is_Captain'].sum():,}")
print(f"  Goals scored (events):        {df['Goals'].sum():,}")
print(f"  Yellow cards:                 {df['Yellow_Cards'].sum():,}")
print(f"  Red cards (straight):         {df['Red_Cards'].sum():,}")
print(f"  Second-yellow reds:           {df['Second_Yellow_Red'].sum():,}")
print(f"  Suspended next match:         {df['Suspended_Next_Match'].sum():,}")
print(f"  Host-nation players:          {df['Is_Host_Team'].sum():,}")
print(f"  Avg rest days (intra-tourn):  {df['Rest_Days'].mean():.1f} days")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 7 — Save
# ═══════════════════════════════════════════════════════════════════════════
out = PROCESSED / "wc_players_combined.csv"
df.to_csv(out, index=False)
print(f"\n  Saved → {out}")
print("\nDone.")
