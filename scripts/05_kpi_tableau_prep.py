"""
KPI Computation & Tableau Export Script
=========================================
Computes all scheduling-relevant KPIs and exports Tableau-ready CSVs.

Outputs to tableau/:
  kpi_team_performance.csv     — per team wins/losses/goals/win rate
  kpi_stage_analysis.csv       — avg goals/cards/attendance/ET% per stage
  kpi_yearly_trends.csv        — year-over-year tournament trends
  kpi_host_advantage.csv       — host vs non-host comparison per year
  kpi_rest_days_impact.csv     — rest days bucket → win rate, goals
  kpi_disciplinary.csv         — cards + suspensions by team & stage
  kpi_player_stats.csv         — top players: goals, cards, appearances
  tableau_main.csv             — full player-match dataset for Tableau
  tableau_matches.csv          — match-level for Tableau
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from pathlib import Path

TABLEAU = Path("tableau")
TABLEAU.mkdir(exist_ok=True)

df  = pd.read_csv("data/processed/wc_players_combined.csv")
mc  = pd.read_csv("data/processed/wc_matches_clean.csv")
cu  = pd.read_csv("data/processed/wc_cups_clean.csv")

STAGE_ORDER = ["Group Stage","Round of 16","Quarter-finals","Semi-finals","Third Place","Final"]

print("Building KPIs...")

# ─────────────────────────────────────────────────────────────────────────
# KPI 1 — Team Performance (Tableau: Team Performance sheet)
# ─────────────────────────────────────────────────────────────────────────
home = mc[["Year","Home_Team","Home_Goals","Away_Goals","Match_Result","Stage_Std"]].copy()
home.columns = ["Year","Team","GF","GA","Match_Result","Stage_Std"]
home["Won"]  = (home["Match_Result"] == "Home Win").astype(int)
home["Lost"] = (home["Match_Result"] == "Away Win").astype(int)
home["Drew"] = (home["Match_Result"] == "Draw").astype(int)

away = mc[["Year","Away_Team","Away_Goals","Home_Goals","Match_Result","Stage_Std"]].copy()
away.columns = ["Year","Team","GF","GA","Match_Result","Stage_Std"]
away["Won"]  = (away["Match_Result"] == "Away Win").astype(int)
away["Lost"] = (away["Match_Result"] == "Home Win").astype(int)
away["Drew"] = (away["Match_Result"] == "Draw").astype(int)

all_teams = pd.concat([home, away], ignore_index=True)

team_perf = all_teams.groupby("Team").agg(
    Matches=("GF","count"),
    Wins=("Won","sum"),
    Losses=("Lost","sum"),
    Draws=("Drew","sum"),
    Goals_For=("GF","sum"),
    Goals_Against=("GA","sum"),
    Tournaments=("Year","nunique")
).reset_index()

team_perf["Win_Rate_Pct"]     = (team_perf["Wins"] / team_perf["Matches"] * 100).round(1)
team_perf["Goal_Diff"]        = team_perf["Goals_For"] - team_perf["Goals_Against"]
team_perf["Goals_Per_Match"]  = (team_perf["Goals_For"] / team_perf["Matches"]).round(2)
team_perf["Loss_Rate_Pct"]    = (team_perf["Losses"] / team_perf["Matches"] * 100).round(1)
team_perf = team_perf.sort_values("Matches", ascending=False)

team_perf.to_csv(TABLEAU / "kpi_team_performance.csv", index=False)
print(f"  kpi_team_performance.csv        {team_perf.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 2 — Stage Analysis (Tableau: Stage Analysis sheet)
# ─────────────────────────────────────────────────────────────────────────
mt = df.groupby(["MatchID","Stage_Std","Stage_Order","Year"]).agg(
    Total_Goals=("Total_Goals","first"),
    Attendance=("Attendance","first"),
    Win_Conditions=("Win_Conditions","first"),
    Match_Result=("Match_Result","first"),
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Effective_Red_Cards","sum"),
    Suspended=("Suspended_Next_Match","sum"),
    Rest_Days_Avg=("Rest_Days","mean"),
).reset_index()

stage_kpi = mt.groupby("Stage_Std").agg(
    Total_Matches=("MatchID","nunique"),
    Avg_Goals_Per_Match=("Total_Goals","mean"),
    Avg_Attendance=("Attendance","mean"),
    Pct_Extra_Time=("Win_Conditions", lambda x: (x=="Extra Time").mean()*100),
    Pct_Penalties=("Win_Conditions",  lambda x: (x=="Penalties").mean()*100),
    Pct_Home_Win=("Match_Result",     lambda x: (x=="Home Win").mean()*100),
    Pct_Draw=("Match_Result",         lambda x: (x=="Draw").mean()*100),
    Avg_Yellow_Cards_Per_Match=("Yellow_Cards","mean"),
    Avg_Red_Cards_Per_Match=("Red_Cards","mean"),
    Total_Suspensions=("Suspended","sum"),
    Avg_Rest_Days=("Rest_Days_Avg","mean"),
).reset_index()

stage_kpi["Stage_Order"] = stage_kpi["Stage_Std"].map(
    {s: i+1 for i, s in enumerate(STAGE_ORDER)}
)
stage_kpi = stage_kpi.sort_values("Stage_Order")
stage_kpi = stage_kpi.round(2)

stage_kpi.to_csv(TABLEAU / "kpi_stage_analysis.csv", index=False)
print(f"  kpi_stage_analysis.csv          {stage_kpi.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 3 — Yearly Trends (Tableau: Year Trends sheet)
# ─────────────────────────────────────────────────────────────────────────
yearly = mc.groupby("Year").agg(
    Matches=("MatchID","count"),
    Total_Goals=("Total_Goals","sum"),
    Avg_Goals_Per_Match=("Total_Goals","mean"),
    Avg_Attendance=("Attendance","mean"),
    Total_Attendance=("Attendance","sum"),
    Home_Win_Count=("Match_Result", lambda x: (x=="Home Win").sum()),
    Draw_Count=("Match_Result",     lambda x: (x=="Draw").sum()),
    Away_Win_Count=("Match_Result", lambda x: (x=="Away Win").sum()),
    ET_Count=("Win_Conditions",     lambda x: (x=="Extra Time").sum()),
    Pens_Count=("Win_Conditions",   lambda x: (x=="Penalties").sum()),
).reset_index()

yearly["Home_Win_Rate_Pct"] = (yearly["Home_Win_Count"] / yearly["Matches"] * 100).round(1)
yearly["Goals_Per_Match"]   = (yearly["Total_Goals"] / yearly["Matches"]).round(2)

# Card trends from player data
cards_yr = df.groupby("Year").agg(
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Effective_Red_Cards","sum"),
    Suspensions=("Suspended_Next_Match","sum"),
).reset_index()

yearly = yearly.merge(cards_yr, on="Year")
yearly["Yellow_Per_Match"] = (yearly["Yellow_Cards"] / yearly["Matches"]).round(2)
yearly["Red_Per_Match"]    = (yearly["Red_Cards"]    / yearly["Matches"]).round(2)

# Merge cups for context
yearly = yearly.merge(cu[["Year","Qualified_Teams","Tournament_Attendance","Winner"]]
                       .rename(columns={"Winner":"Tournament_Winner"}), on="Year")

yearly.to_csv(TABLEAU / "kpi_yearly_trends.csv", index=False)
print(f"  kpi_yearly_trends.csv           {yearly.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 4 — Host Nation Advantage per Year (Tableau: Host Advantage sheet)
# ─────────────────────────────────────────────────────────────────────────
host_rows = mc[mc["Is_Host_Home"]].copy()
host_rows["Host_Won"]   = (host_rows["Match_Result"] == "Home Win").astype(int)
host_rows["Host_Goals"] = host_rows["Home_Goals"]
host_rows["Opp_Goals"]  = host_rows["Away_Goals"]

host_kpi = host_rows.groupby("Year").agg(
    Host_Matches=("MatchID","count"),
    Host_Wins=("Host_Won","sum"),
    Host_Goals_For=("Host_Goals","mean"),
    Host_Goals_Against=("Opp_Goals","mean"),
    Host_Avg_Attendance=("Attendance","mean"),
).reset_index()
host_kpi["Host_Win_Rate_Pct"] = (host_kpi["Host_Wins"] / host_kpi["Host_Matches"] * 100).round(1)

# Overall home win rate same year (non-host)
nonhost_yr = mc[~mc["Is_Host_Home"]].groupby("Year").agg(
    NonHost_Win_Rate=("Match_Result", lambda x: (x=="Home Win").mean()*100)
).reset_index()
host_kpi = host_kpi.merge(nonhost_yr, on="Year", how="left")
host_kpi["Host_Advantage_Delta"] = (host_kpi["Host_Win_Rate_Pct"] - host_kpi["NonHost_Win_Rate"]).round(1)
host_kpi = host_kpi.merge(cu[["Year","Host_Country"]], on="Year")
host_kpi = host_kpi.round(2)

host_kpi.to_csv(TABLEAU / "kpi_host_advantage.csv", index=False)
print(f"  kpi_host_advantage.csv          {host_kpi.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 5 — Rest Days Impact (Tableau: Rest Days sheet)
# ─────────────────────────────────────────────────────────────────────────
rest_base = df[df["Rest_Days"].notna()].drop_duplicates(
    subset=["MatchID","Player_Team"]
)[["MatchID","Player_Team","Rest_Days","Team_Won","Team_Goals_For",
   "Team_Goals_Against","Stage_Std","Year"]].copy()

rest_base["Rest_Bucket"] = pd.cut(
    rest_base["Rest_Days"],
    bins=[0,2,4,6,10],
    labels=["1-2 days","3-4 days","5-6 days","7+ days"]
)

rest_kpi = rest_base.groupby("Rest_Bucket", observed=True).agg(
    Team_Match_Count=("MatchID","count"),
    Win_Rate_Pct=("Team_Won", lambda x: x.mean()*100),
    Avg_Goals_Scored=("Team_Goals_For","mean"),
    Avg_Goals_Conceded=("Team_Goals_Against","mean"),
).reset_index().round(2)
rest_kpi.columns = ["Rest_Bucket","Team_Match_Count","Win_Rate_Pct",
                    "Avg_Goals_Scored","Avg_Goals_Conceded"]

# Also by stage
rest_stage_kpi = rest_base.groupby(["Stage_Std","Rest_Bucket"], observed=True).agg(
    Count=("MatchID","count"),
    Win_Rate=("Team_Won",lambda x: x.mean()*100),
    Avg_Goals=("Team_Goals_For","mean"),
).reset_index().round(2)

rest_kpi.to_csv(TABLEAU / "kpi_rest_days_impact.csv", index=False)
rest_stage_kpi.to_csv(TABLEAU / "kpi_rest_days_by_stage.csv", index=False)
print(f"  kpi_rest_days_impact.csv        {rest_kpi.shape}")
print(f"  kpi_rest_days_by_stage.csv      {rest_stage_kpi.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 6 — Disciplinary (Tableau: Discipline sheet)
# ─────────────────────────────────────────────────────────────────────────
# Per team
disc_team = df.groupby("Player_Team").agg(
    Matches=("MatchID","nunique"),
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Red_Cards","sum"),
    Second_Yellow_Reds=("Second_Yellow_Red","sum"),
    Total_Effective_Reds=("Effective_Red_Cards","sum"),
    Players_Suspended=("Suspended_Next_Match","sum"),
    Goals_Scored=("Goals","sum"),
).reset_index()
disc_team["Yellow_Per_Match"] = (disc_team["Yellow_Cards"] / disc_team["Matches"]).round(2)
disc_team["Red_Per_Match"]    = (disc_team["Total_Effective_Reds"] / disc_team["Matches"]).round(3)
disc_team = disc_team.sort_values("Yellow_Cards", ascending=False)
disc_team.to_csv(TABLEAU / "kpi_disciplinary_by_team.csv", index=False)

# Per stage
disc_stage = df.groupby("Stage_Std").agg(
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Red_Cards","sum"),
    Second_Yellow_Reds=("Second_Yellow_Red","sum"),
    Total_Effective_Reds=("Effective_Red_Cards","sum"),
    Players_Suspended=("Suspended_Next_Match","sum"),
    Matches=("MatchID","nunique"),
).reset_index()
disc_stage["Stage_Order"] = disc_stage["Stage_Std"].map(
    {s: i+1 for i, s in enumerate(STAGE_ORDER)}
)
disc_stage = disc_stage.sort_values("Stage_Order")
disc_stage["Yellow_Per_Match"] = (disc_stage["Yellow_Cards"] / disc_stage["Matches"]).round(2)
disc_stage["Red_Per_Match"]    = (disc_stage["Total_Effective_Reds"] / disc_stage["Matches"]).round(3)
disc_stage.to_csv(TABLEAU / "kpi_disciplinary_by_stage.csv", index=False)
print(f"  kpi_disciplinary_by_team.csv    {disc_team.shape}")
print(f"  kpi_disciplinary_by_stage.csv   {disc_stage.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 7 — Player Stats (Tableau: Player Leaders sheet)
# ─────────────────────────────────────────────────────────────────────────
player_kpi = df.groupby("Player_Name").agg(
    Team=("Player_Team","first"),
    Matches=("MatchID","nunique"),
    Tournaments=("Year","nunique"),
    Goals=("Goals","sum"),
    Own_Goals=("Own_Goals","sum"),
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Effective_Red_Cards","sum"),
    Times_Suspended=("Suspended_Next_Match","sum"),
    Times_Captain=("Is_Captain","sum"),
    Times_Starter=("Is_Starter","sum"),
    Times_Sub=("Is_Substitute","sum"),
    Penalties_Scored=("Penalties_Scored","sum"),
    Missed_Penalties=("Missed_Penalties","sum"),
).reset_index()

player_kpi["Goals_Per_Match"]  = (player_kpi["Goals"] / player_kpi["Matches"]).round(3)
player_kpi["Cards_Per_Match"]  = ((player_kpi["Yellow_Cards"] + player_kpi["Red_Cards"])
                                   / player_kpi["Matches"]).round(3)
player_kpi = player_kpi[player_kpi["Matches"] >= 2].sort_values("Goals", ascending=False)
player_kpi.to_csv(TABLEAU / "kpi_player_stats.csv", index=False)
print(f"  kpi_player_stats.csv            {player_kpi.shape}")


# ─────────────────────────────────────────────────────────────────────────
# KPI 8 — Match Timing (Tableau: Schedule Timing sheet)
# ─────────────────────────────────────────────────────────────────────────
mc2 = mc.copy()
mc2["Hour"] = mc2["Match_Time"].str.split(":").str[0].astype(int)
mc2["Time_Block"] = pd.cut(mc2["Hour"], bins=[0,11,14,17,23],
                            labels=["Morning","Afternoon","Evening","Night"])

timing_day = mc2.groupby("Day_of_Week").agg(
    Matches=("MatchID","count"),
    Avg_Attendance=("Attendance","mean"),
    Avg_Goals=("Total_Goals","mean"),
    Home_Win_Rate=("Match_Result", lambda x: (x=="Home Win").mean()*100),
).reset_index()

timing_block = mc2.groupby("Time_Block", observed=True).agg(
    Matches=("MatchID","count"),
    Avg_Attendance=("Attendance","mean"),
    Avg_Goals=("Total_Goals","mean"),
).reset_index()

timing_day.to_csv(TABLEAU / "kpi_match_timing_day.csv", index=False)
timing_block.to_csv(TABLEAU / "kpi_match_timing_block.csv", index=False)
print(f"  kpi_match_timing_day.csv        {timing_day.shape}")
print(f"  kpi_match_timing_block.csv      {timing_block.shape}")


# ─────────────────────────────────────────────────────────────────────────
# Main Tableau Exports
# ─────────────────────────────────────────────────────────────────────────
df.to_csv(TABLEAU / "tableau_main.csv", index=False)
mc.to_csv(TABLEAU / "tableau_matches.csv", index=False)
cu.to_csv(TABLEAU / "tableau_cups.csv", index=False)
print(f"  tableau_main.csv                {df.shape}")
print(f"  tableau_matches.csv             {mc.shape}")
print(f"  tableau_cups.csv                {cu.shape}")


# ─────────────────────────────────────────────────────────────────────────
# VALIDATION CHECK
# ─────────────────────────────────────────────────────────────────────────
print()
print("─" * 50)
print("VALIDATION CHECKS:")

# Verify team_perf sums
assert team_perf["Matches"].sum() == len(mc) * 2, "Team match counts mismatch"
assert (team_perf["Wins"] + team_perf["Losses"] + team_perf["Draws"] == team_perf["Matches"]).all(), \
    "W+L+D != Matches"
assert (team_perf["Win_Rate_Pct"].between(0,100)).all(), "Win rate out of range"
print("  [PASS]  team_performance: W+L+D = Matches for all teams")

assert len(stage_kpi) == 6, f"Expected 6 stages, got {len(stage_kpi)}"
assert (stage_kpi["Pct_Extra_Time"] + stage_kpi["Pct_Penalties"] <= 100).all()
print("  [PASS]  stage_analysis: 6 stages, ET+Pens ≤ 100%")

assert len(yearly) == 20, f"Expected 20 years, got {len(yearly)}"
print("  [PASS]  yearly_trends: 20 tournament years")

assert (rest_kpi["Win_Rate_Pct"].between(0, 100)).all(), "Rest win rate out of range"
print("  [PASS]  rest_days_impact: win rates in valid range")

assert (disc_team["Yellow_Cards"] >= 0).all()
print("  [PASS]  disciplinary: no negative card counts")

# Cross-check: total goals in stage_kpi × matches should approximately equal yearly totals
total_goals_stage = (stage_kpi["Avg_Goals_Per_Match"] * stage_kpi["Total_Matches"]).sum()
total_goals_actual = mc["Total_Goals"].sum()
diff_pct = abs(total_goals_stage - total_goals_actual) / total_goals_actual * 100
assert diff_pct < 2, f"Stage goals total too far off: {diff_pct:.1f}%"
print(f"  [PASS]  goals cross-check: stage totals match actual within {diff_pct:.2f}%")


# ─────────────────────────────────────────────────────────────────────────
# PRINT KPI SUMMARY
# ─────────────────────────────────────────────────────────────────────────
print()
print("=" * 50)
print("KPI SUMMARY HIGHLIGHTS:")
print()
top5 = team_perf.head(5)
print("Top 5 Teams by Matches:")
print(top5[["Team","Matches","Wins","Win_Rate_Pct","Goals_For"]].to_string(index=False))
print()
print("Stage Analysis:")
print(stage_kpi[["Stage_Std","Total_Matches","Avg_Goals_Per_Match",
                  "Pct_Home_Win","Avg_Attendance","Pct_Extra_Time","Pct_Penalties"]].to_string(index=False))
print()
print("Rest Days Impact on Win Rate:")
print(rest_kpi.to_string(index=False))
print()
print("Host Advantage (recent 6 tournaments):")
print(host_kpi.tail(6)[["Year","Host_Country","Host_Matches","Host_Win_Rate_Pct",
                          "NonHost_Win_Rate","Host_Advantage_Delta"]].to_string(index=False))
print()
print("=" * 50)
print("All KPI files saved to tableau/")
print("=" * 50)
