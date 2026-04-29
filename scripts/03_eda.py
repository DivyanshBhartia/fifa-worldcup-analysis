"""
EDA Script — FIFA World Cup Scheduling Analysis
================================================
Explores the wc_players_combined + wc_matches_clean datasets.
All plots saved to reports/figures/.
Focus: scheduling-relevant patterns (rest, fatigue, host advantage,
       attendance, stage workload, discipline, timing).
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ── Paths & Data ──────────────────────────────────────────────────────────
FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)

df  = pd.read_csv("data/processed/wc_players_combined.csv")
mc  = pd.read_csv("data/processed/wc_matches_clean.csv")
cu  = pd.read_csv("data/processed/wc_cups_clean.csv")

df["Match_Date"] = pd.to_datetime(df["Match_Date"])
mc["Match_Date"] = pd.to_datetime(mc["Match_Date"])

STAGE_ORDER = ["Group Stage","Round of 16","Quarter-finals","Semi-finals","Third Place","Final"]
PALETTE     = "Set2"
sns.set_theme(style="whitegrid", font_scale=1.1)

print("Data loaded:")
print(f"  Players combined : {df.shape}")
print(f"  Matches clean    : {mc.shape}")
print(f"  Cups clean       : {cu.shape}")
print()

# ─────────────────────────────────────────────────────────────────────────
# FIG 1 — Tournament Growth Over Time
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 4))
fig.suptitle("FIFA World Cup — Tournament Growth (1930–2014)", fontsize=13, fontweight="bold")

axes[0].bar(cu["Year"], cu["Qualified_Teams"], color="#4C72B0")
axes[0].set(title="Qualified Teams per Tournament", xlabel="Year", ylabel="Teams")
axes[0].tick_params(axis="x", rotation=45)

axes[1].bar(cu["Year"], cu["Tournament_Matches"], color="#DD8452")
axes[1].set(title="Matches Played per Tournament", xlabel="Year", ylabel="Matches")
axes[1].tick_params(axis="x", rotation=45)

axes[2].bar(cu["Year"], cu["Tournament_Attendance"] / 1e6, color="#55A868")
axes[2].set(title="Total Attendance per Tournament (M)", xlabel="Year", ylabel="Millions")
axes[2].tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig(FIG / "01_tournament_growth.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 01_tournament_growth.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 2 — Match Results Distribution (overall + by stage)
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Match Result Patterns", fontsize=13, fontweight="bold")

result_counts = mc["Match_Result"].value_counts()
axes[0].pie(result_counts, labels=result_counts.index,
            autopct="%1.1f%%", colors=["#4C72B0","#DD8452","#55A868"],
            startangle=90)
axes[0].set_title("Overall (n=836 matches)")

result_stage = (mc.groupby(["Stage_Std","Match_Result"])
                  .size().unstack(fill_value=0)
                  .reindex(STAGE_ORDER))
result_pct   = result_stage.div(result_stage.sum(axis=1), axis=0) * 100
result_pct[["Home Win","Draw","Away Win"]].plot(
    kind="bar", stacked=True, ax=axes[1],
    color=["#4C72B0","#55A868","#DD8452"], edgecolor="white"
)
axes[1].set(title="Result Distribution by Stage (%)",
            xlabel="Stage", ylabel="Percentage")
axes[1].tick_params(axis="x", rotation=30)
axes[1].legend(loc="upper right", fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "02_match_results.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 02_match_results.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 3 — Goals per Match: by Stage and by Year
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Goals Patterns", fontsize=13, fontweight="bold")

goals_stage = mc.groupby("Stage_Std")["Total_Goals"].mean().reindex(STAGE_ORDER)
axes[0].bar(goals_stage.index, goals_stage.values, color=sns.color_palette(PALETTE, 6))
axes[0].set(title="Avg Goals per Match by Stage", xlabel="Stage", ylabel="Avg Goals")
axes[0].tick_params(axis="x", rotation=30)
for i, v in enumerate(goals_stage.values):
    axes[0].text(i, v + 0.05, f"{v:.2f}", ha="center", fontsize=9)

goals_year = mc.groupby("Year")["Total_Goals"].mean()
axes[1].plot(goals_year.index, goals_year.values, marker="o", color="#4C72B0", linewidth=2)
axes[1].fill_between(goals_year.index, goals_year.values, alpha=0.15, color="#4C72B0")
axes[1].set(title="Avg Goals per Match by Year", xlabel="Year", ylabel="Avg Goals")
axes[1].tick_params(axis="x", rotation=45)

plt.tight_layout()
plt.savefig(FIG / "03_goals_patterns.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 03_goals_patterns.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 4 — Host Nation Advantage
# ─────────────────────────────────────────────────────────────────────────
# Match-level: home team is host vs not
mc["Home_Is_Host"] = mc["Is_Host_Home"]
mc["Away_Is_Host"] = mc["Is_Host_Away"]

host_home   = mc[mc["Home_Is_Host"]]
non_host    = mc[~mc["Home_Is_Host"] & ~mc["Away_Is_Host"]]

host_win_rt = (host_home["Match_Result"] == "Home Win").mean() * 100
nhost_home_win = (non_host["Match_Result"] == "Home Win").mean() * 100
host_goals  = host_home["Home_Goals"].mean()
nhost_goals = non_host["Home_Goals"].mean()

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Host Nation Advantage Analysis", fontsize=13, fontweight="bold")

cats   = ["Host as Home", "Non-Host as Home"]
wr     = [host_win_rt, nhost_home_win]
colors = ["#4C72B0","#DD8452"]
axes[0].bar(cats, wr, color=colors)
axes[0].set(title="Win Rate When Playing at Home (%)", ylabel="%")
for i, v in enumerate(wr):
    axes[0].text(i, v + 0.5, f"{v:.1f}%", ha="center", fontweight="bold")

gl = [host_goals, nhost_goals]
axes[1].bar(cats, gl, color=colors)
axes[1].set(title="Avg Goals Scored at Home", ylabel="Goals")
for i, v in enumerate(gl):
    axes[1].text(i, v + 0.03, f"{v:.2f}", ha="center", fontweight="bold")

# Attendance when host plays vs doesn't
host_att   = mc[mc["Home_Is_Host"] | mc["Away_Is_Host"]]["Attendance"].mean()
no_host_att = mc[~mc["Home_Is_Host"] & ~mc["Away_Is_Host"]]["Attendance"].mean()
axes[2].bar(["Host In Match","No Host"], [host_att/1000, no_host_att/1000], color=colors)
axes[2].set(title="Avg Attendance (thousands)", ylabel="Thousands")
for i, v in enumerate([host_att/1000, no_host_att/1000]):
    axes[2].text(i, v + 0.3, f"{v:.1f}K", ha="center", fontweight="bold")

plt.tight_layout()
plt.savefig(FIG / "04_host_advantage.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 04_host_advantage.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 5 — Rest Days Analysis (scheduling core)
# ─────────────────────────────────────────────────────────────────────────
rest_df = df[df["Rest_Days"].notna()].drop_duplicates(subset=["MatchID","Player_Team"])

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Rest Days Between Matches (Within-Tournament)", fontsize=13, fontweight="bold")

axes[0].hist(rest_df["Rest_Days"], bins=range(1, 12), color="#4C72B0",
             edgecolor="white", align="left")
axes[0].set(title="Distribution of Rest Days", xlabel="Days", ylabel="Team-Match Count")
axes[0].axvline(rest_df["Rest_Days"].mean(), color="red", linestyle="--", label=f"Mean={rest_df['Rest_Days'].mean():.1f}")
axes[0].legend()

rest_stage = rest_df.groupby("Stage_Std")["Rest_Days"].mean().reindex(STAGE_ORDER).dropna()
axes[1].bar(rest_stage.index, rest_stage.values, color=sns.color_palette(PALETTE, len(rest_stage)))
axes[1].set(title="Avg Rest Days by Stage", xlabel="Stage", ylabel="Avg Days")
axes[1].tick_params(axis="x", rotation=30)
for i, v in enumerate(rest_stage.values):
    axes[1].text(i, v + 0.05, f"{v:.1f}", ha="center", fontsize=9)

# Rest days → win rate
rest_df2 = rest_df.copy()
rest_df2["Won"] = rest_df2["Team_Won"].astype(int)
rest_win = rest_df2.groupby("Rest_Days")["Won"].mean() * 100
axes[2].bar(rest_win.index, rest_win.values, color="#55A868")
axes[2].set(title="Win Rate by Rest Days (%)", xlabel="Rest Days", ylabel="Win Rate %")
for i, (idx, v) in enumerate(rest_win.items()):
    axes[2].text(idx - 1, v + 0.5, f"{v:.0f}%", ha="center", fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "05_rest_days.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 05_rest_days.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 6 — Disciplinary Patterns (Yellow/Red Cards by Stage & Year)
# ─────────────────────────────────────────────────────────────────────────
# Aggregate to match-team level for card rates
match_team = df.groupby(["MatchID","Year","Stage_Std","Stage_Order","Player_Team"]).agg(
    Yellow=("Yellow_Cards","sum"),
    Red=("Effective_Red_Cards","sum"),
    Suspended=("Suspended_Next_Match","sum")
).reset_index()

fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Disciplinary Patterns — Scheduling Impact", fontsize=13, fontweight="bold")

cards_stage = match_team.groupby("Stage_Std")[["Yellow","Red"]].mean().reindex(STAGE_ORDER)
x = range(len(cards_stage))
w = 0.35
axes[0].bar([i - w/2 for i in x], cards_stage["Yellow"], width=w,
            label="Yellow Cards", color="#FFC107")
axes[0].bar([i + w/2 for i in x], cards_stage["Red"], width=w,
            label="Red Cards", color="#DC3545")
axes[0].set(title="Avg Cards per Team per Match by Stage", ylabel="Cards")
axes[0].set_xticks(list(x))
axes[0].set_xticklabels(cards_stage.index, rotation=30, ha="right", fontsize=8)
axes[0].legend(fontsize=8)

cards_year = match_team.groupby("Year")[["Yellow","Red"]].mean()
axes[1].plot(cards_year.index, cards_year["Yellow"], marker="o",
             color="#FFC107", label="Yellow", linewidth=2)
axes[1].plot(cards_year.index, cards_year["Red"], marker="s",
             color="#DC3545", label="Red", linewidth=2)
axes[1].set(title="Avg Cards per Team per Match by Year", xlabel="Year")
axes[1].legend()
axes[1].tick_params(axis="x", rotation=45)

# Suspensions per stage
susp_stage = match_team.groupby("Stage_Std")["Suspended"].sum().reindex(STAGE_ORDER)
axes[2].bar(susp_stage.index, susp_stage.values, color="#DC3545")
axes[2].set(title="Total Players Suspended (Next Match) by Stage",
            xlabel="Stage", ylabel="Players Suspended")
axes[2].tick_params(axis="x", rotation=30)
for i, v in enumerate(susp_stage.values):
    axes[2].text(i, v + 0.3, str(int(v)), ha="center", fontsize=9)

plt.tight_layout()
plt.savefig(FIG / "06_disciplinary.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 06_disciplinary.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 7 — Attendance Patterns
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 3, figsize=(15, 5))
fig.suptitle("Attendance Patterns", fontsize=13, fontweight="bold")

att_stage = mc.groupby("Stage_Std")["Attendance"].mean().reindex(STAGE_ORDER) / 1000
axes[0].bar(att_stage.index, att_stage.values, color=sns.color_palette(PALETTE, 6))
axes[0].set(title="Avg Attendance by Stage (thousands)", ylabel="K")
axes[0].tick_params(axis="x", rotation=30)
for i, v in enumerate(att_stage.values):
    axes[0].text(i, v + 0.5, f"{v:.0f}K", ha="center", fontsize=8)

att_year = mc.groupby("Year")["Attendance"].mean() / 1000
axes[1].plot(att_year.index, att_year.values, marker="o", color="#4C72B0", linewidth=2)
axes[1].fill_between(att_year.index, att_year.values, alpha=0.15, color="#4C72B0")
axes[1].set(title="Avg Attendance per Match by Year", xlabel="Year", ylabel="K")
axes[1].tick_params(axis="x", rotation=45)

att_result = mc.groupby("Match_Result")["Attendance"].mean() / 1000
axes[2].bar(att_result.index, att_result.values,
            color=["#4C72B0","#55A868","#DD8452"])
axes[2].set(title="Avg Attendance by Match Result", ylabel="K")
for i, v in enumerate(att_result.values):
    axes[2].text(i, v + 0.3, f"{v:.0f}K", ha="center", fontweight="bold")

plt.tight_layout()
plt.savefig(FIG / "07_attendance.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 07_attendance.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 8 — Win Conditions by Stage
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Win Conditions by Stage", fontsize=13, fontweight="bold")

wc_stage = (mc.groupby(["Stage_Std","Win_Conditions"])
              .size().unstack(fill_value=0)
              .reindex(STAGE_ORDER))
wc_pct   = wc_stage.div(wc_stage.sum(axis=1), axis=0) * 100
wc_pct.plot(kind="bar", stacked=True, ax=axes[0],
            color=["#55A868","#FFC107","#DC3545"], edgecolor="white")
axes[0].set(title="Win Conditions % by Stage", xlabel="Stage", ylabel="%")
axes[0].tick_params(axis="x", rotation=30)
axes[0].legend(loc="upper right", fontsize=8)

wc_overall = mc["Win_Conditions"].value_counts()
axes[1].pie(wc_overall, labels=wc_overall.index,
            autopct="%1.1f%%", colors=["#55A868","#FFC107","#DC3545"],
            startangle=90)
axes[1].set_title("Overall Win Conditions (n=836)")

plt.tight_layout()
plt.savefig(FIG / "08_win_conditions.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 08_win_conditions.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 9 — Match Timing: Day of Week & Kick-off Time
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Match Scheduling Patterns — Timing", fontsize=13, fontweight="bold")

day_order = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
day_counts = mc["Day_of_Week"].value_counts().reindex(day_order, fill_value=0)
axes[0].bar(day_counts.index, day_counts.values, color="#4C72B0")
axes[0].set(title="Matches by Day of Week", xlabel="Day", ylabel="Matches")
axes[0].tick_params(axis="x", rotation=30)
for i, v in enumerate(day_counts.values):
    axes[0].text(i, v + 0.3, str(v), ha="center", fontsize=9)

mc["Hour"] = mc["Match_Time"].str.split(":").str[0].astype(int)
hour_counts = mc["Hour"].value_counts().sort_index()
axes[1].bar(hour_counts.index, hour_counts.values, color="#DD8452")
axes[1].set(title="Matches by Kick-off Hour (UTC)", xlabel="Hour of Day", ylabel="Matches")
axes[1].xaxis.set_major_locator(mticker.MultipleLocator(2))

plt.tight_layout()
plt.savefig(FIG / "09_match_timing.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 09_match_timing.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 10 — Top Teams: Appearances, Win Rate, Goals
# ─────────────────────────────────────────────────────────────────────────
teams_all = pd.concat([
    mc[["Year","Home_Team","Home_Goals","Away_Goals","Match_Result"]].rename(
        columns={"Home_Team":"Team","Home_Goals":"GF","Away_Goals":"GA"}),
    mc[["Year","Away_Team","Away_Goals","Home_Goals","Match_Result"]].rename(
        columns={"Away_Team":"Team","Away_Goals":"GF","Home_Goals":"GA"})
])
teams_all["Won"]  = ((teams_all["Team"] == mc["Home_Team"].reindex(teams_all.index)) &
                     (teams_all["Match_Result"] == "Home Win")).fillna(False)

# Simpler recalculation
home = mc[["Year","Home_Team","Home_Goals","Away_Goals","Match_Result"]].copy()
home["Team"] = home["Home_Team"]
home["GF"]   = home["Home_Goals"]
home["GA"]   = home["Away_Goals"]
home["Won"]  = home["Match_Result"] == "Home Win"
home["Drew"] = home["Match_Result"] == "Draw"

away = mc[["Year","Away_Team","Away_Goals","Home_Goals","Match_Result"]].copy()
away["Team"] = away["Away_Team"]
away["GF"]   = away["Away_Goals"]
away["GA"]   = away["Home_Goals"]
away["Won"]  = away["Match_Result"] == "Away Win"
away["Drew"] = away["Match_Result"] == "Draw"

teams_df = pd.concat([home[["Team","GF","GA","Won","Drew"]],
                      away[["Team","GF","GA","Won","Drew"]]])
team_stats = teams_df.groupby("Team").agg(
    Matches=("GF","count"), Goals_For=("GF","sum"), Goals_Against=("GA","sum"),
    Wins=("Won","sum"), Draws=("Drew","sum")
).assign(
    Win_Rate=lambda x: x["Wins"] / x["Matches"] * 100
).sort_values("Matches", ascending=False)

top15 = team_stats.head(15)
fig, axes = plt.subplots(1, 2, figsize=(16, 5))
fig.suptitle("Top 15 Teams — Historical Performance", fontsize=13, fontweight="bold")

axes[0].barh(top15.index[::-1], top15["Matches"][::-1], color="#4C72B0")
axes[0].set(title="Total Matches Played", xlabel="Matches")

wr_sorted = top15.sort_values("Win_Rate", ascending=False).head(15)
axes[1].barh(wr_sorted.index[::-1], wr_sorted["Win_Rate"][::-1], color="#55A868")
axes[1].set(title="Win Rate (%)", xlabel="%")
for i, v in enumerate(wr_sorted["Win_Rate"][::-1]):
    axes[1].text(v + 0.3, i, f"{v:.1f}%", va="center", fontsize=8)

plt.tight_layout()
plt.savefig(FIG / "10_team_performance.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 10_team_performance.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 11 — Player Workload: Starters vs Subs by Stage
# ─────────────────────────────────────────────────────────────────────────
workload = df.groupby("Stage_Std").agg(
    Starters=("Is_Starter","sum"),
    Subs=("Is_Substitute","sum")
).reindex(STAGE_ORDER)
workload_pct = workload.div(workload.sum(axis=1), axis=0) * 100

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
fig.suptitle("Player Deployment by Stage", fontsize=13, fontweight="bold")

workload_pct.plot(kind="bar", ax=axes[0], color=["#4C72B0","#DD8452"], edgecolor="white")
axes[0].set(title="Starter vs Substitute Split (%)", xlabel="Stage", ylabel="%")
axes[0].tick_params(axis="x", rotation=30)
axes[0].legend(["Starter","Substitute"])

# GK usage
gk_rate = df.groupby("Stage_Std")["Is_GK"].mean().reindex(STAGE_ORDER) * 100
axes[1].bar(gk_rate.index, gk_rate.values, color="#8B5CF6")
axes[1].set(title="GK % of Squad by Stage", xlabel="Stage", ylabel="%")
axes[1].tick_params(axis="x", rotation=30)

plt.tight_layout()
plt.savefig(FIG / "11_player_workload.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 11_player_workload.png")

# ─────────────────────────────────────────────────────────────────────────
# FIG 12 — Correlation Heatmap (match-level scheduling features)
# ─────────────────────────────────────────────────────────────────────────
corr_cols = [
    "Total_Goals","Attendance","Stage_Order","Days_Into_Tournament",
    "HT_Home_Goals","HT_Away_Goals","Goal_Diff"
]
mc_corr = mc[corr_cols].copy()
mc_corr["Home_Win"] = (mc["Match_Result"] == "Home Win").astype(int)
mc_corr["Has_Extra_Time"] = (mc["Win_Conditions"] != "Normal").astype(int)
mc_corr["Rest_Home"] = mc["Rest_Days_Home"]
mc_corr["Rest_Away"] = mc["Rest_Days_Away"]

corr = mc_corr.dropna().corr()

fig, ax = plt.subplots(figsize=(10, 8))
mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", center=0,
            ax=ax, square=True, linewidths=0.5, cbar_kws={"shrink":0.8})
ax.set_title("Correlation Matrix — Scheduling Variables", fontsize=13, fontweight="bold")
plt.tight_layout()
plt.savefig(FIG / "12_correlation_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("Saved: 12_correlation_heatmap.png")

print()
print("=" * 50)
print("EDA complete. All 12 figures saved to reports/figures/")
print("=" * 50)

# ─────────────────────────────────────────────────────────────────────────
# PRINT KEY EDA FINDINGS
# ─────────────────────────────────────────────────────────────────────────
print()
print("KEY FINDINGS:")
print(f"  Home Win Rate (overall):    {(mc['Match_Result']=='Home Win').mean()*100:.1f}%")
print(f"  Host Home Win Rate:         {(host_home['Match_Result']=='Home Win').mean()*100:.1f}%")
print(f"  Non-Host Home Win Rate:     {(non_host['Match_Result']=='Home Win').mean()*100:.1f}%")
print(f"  Avg Goals/Match (Group):    {mc[mc['Stage_Std']=='Group Stage']['Total_Goals'].mean():.2f}")
print(f"  Avg Goals/Match (Final):    {mc[mc['Stage_Std']=='Final']['Total_Goals'].mean():.2f}")
print(f"  Avg Rest Days:              {df['Rest_Days'].mean():.1f} days")
print(f"  Min Rest Days Observed:     {df['Rest_Days'].min():.0f} days")
print(f"  Matches with < 3 rest days: {(mc[mc['Rest_Days_Home'].notna()]['Rest_Days_Home'] < 3).sum() + (mc[mc['Rest_Days_Away'].notna()]['Rest_Days_Away'] < 3).sum()} team-match instances")
print(f"  Finals avg attendance:      {mc[mc['Stage_Std']=='Final']['Attendance'].mean()/1000:.0f}K")
print(f"  Group Stage avg attendance: {mc[mc['Stage_Std']=='Group Stage']['Attendance'].mean()/1000:.0f}K")
print(f"  Total suspensions tracked:  {df['Suspended_Next_Match'].sum()}")
print(f"  Extra Time matches:         {(mc['Win_Conditions']=='Extra Time').sum()}")
print(f"  Penalty shootout matches:   {(mc['Win_Conditions']=='Penalties').sum()}")
