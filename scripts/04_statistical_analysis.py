"""
Statistical Analysis Script — FIFA World Cup Scheduling
========================================================
Tests scheduling-relevant hypotheses using the cleaned datasets.
Covers: t-tests, chi-square, ANOVA, correlation, logistic regression.
All results printed with p-values and interpretation.
"""

import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy import stats
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score
from sklearn.metrics import classification_report, confusion_matrix

FIG = Path("reports/figures")
FIG.mkdir(parents=True, exist_ok=True)

df = pd.read_csv("data/processed/wc_players_combined.csv")
mc = pd.read_csv("data/processed/wc_matches_clean.csv")

ALPHA = 0.05

def hr(title=""):
    print()
    print("─" * 60)
    if title:
        print(f"  {title}")
        print("─" * 60)

def result(passed, desc):
    tag = "[SIG]" if passed else "[NOT SIG]"
    print(f"  {tag}  {desc}")


hr("TEST 1 — Home Advantage: Are home goals significantly higher than away goals?")
print("  H0: Mean home goals = mean away goals (no home advantage)")
print("  H1: Mean home goals > mean away goals")

home_g = mc["Home_Goals"]
away_g = mc["Away_Goals"]
t1, p1 = stats.ttest_rel(home_g, away_g, alternative="greater")
print(f"\n  Paired t-test (one-tailed, n={len(mc)})")
print(f"  Mean home goals : {home_g.mean():.3f}")
print(f"  Mean away goals : {away_g.mean():.3f}")
print(f"  t-statistic     : {t1:.4f}")
print(f"  p-value         : {p1:.4f}")
result(p1 < ALPHA,
       f"Home teams score significantly more (p={p1:.4f} < {ALPHA})"
       if p1 < ALPHA else
       f"No significant home goal advantage (p={p1:.4f} ≥ {ALPHA})")


hr("TEST 2 — Host Nation: Do host nations win more often?")
print("  H0: Host win rate = general home win rate")
print("  H1: Host win rate > general home win rate")

host_matches   = mc[mc["Is_Host_Home"]]
nonhost_home   = mc[~mc["Is_Host_Home"]]
host_wins      = (host_matches["Match_Result"] == "Home Win").astype(int)
nonhost_wins   = (nonhost_home["Match_Result"] == "Home Win").astype(int)
t2, p2 = stats.ttest_ind(host_wins, nonhost_wins, alternative="greater")
print(f"\n  Independent t-test")
print(f"  Host home win rate    : {host_wins.mean()*100:.1f}% (n={len(host_matches)})")
print(f"  Non-host home win rate: {nonhost_wins.mean()*100:.1f}% (n={len(nonhost_home)})")
print(f"  t-statistic : {t2:.4f}")
print(f"  p-value     : {p2:.4f}")
result(p2 < ALPHA,
       f"Host nations win significantly more at home (p={p2:.4f})"
       if p2 < ALPHA else
       f"Host advantage not statistically significant (p={p2:.4f})")


hr("TEST 3 — Stage Goals: Do knockout matches have fewer goals than group stage?")
print("  H0: Avg goals Group Stage = avg goals Knockout rounds")
print("  H1: Group Stage has more goals (teams play more open football)")

group_goals  = mc[mc["Stage_Std"] == "Group Stage"]["Total_Goals"]
ko_goals     = mc[mc["Stage_Order"] >= 2]["Total_Goals"]
t3, p3 = stats.ttest_ind(group_goals, ko_goals, alternative="greater")
print(f"\n  Independent t-test (one-tailed)")
print(f"  Group Stage avg goals   : {group_goals.mean():.3f} (n={len(group_goals)})")
print(f"  Knockout avg goals      : {ko_goals.mean():.3f} (n={len(ko_goals)})")
print(f"  t-statistic : {t3:.4f}")
print(f"  p-value     : {p3:.4f}")
result(p3 < ALPHA,
       f"Group Stage significantly more goals (p={p3:.4f})"
       if p3 < ALPHA else
       f"No significant difference in goals across stages (p={p3:.4f})")


hr("TEST 4 — Rest Days: Does more rest increase a team's chance of winning?")
print("  H0: Win rate for teams with ≥4 rest days = teams with <4 rest days")
print("  H1: More rest → higher win probability")

rest_df = df[df["Rest_Days"].notna()].drop_duplicates(subset=["MatchID","Player_Team"])
rest_df = rest_df[["Rest_Days","Team_Won"]].copy()
more_rest = rest_df[rest_df["Rest_Days"] >= 4]["Team_Won"].astype(int)
less_rest = rest_df[rest_df["Rest_Days"] <  4]["Team_Won"].astype(int)
t4, p4 = stats.ttest_ind(more_rest, less_rest, alternative="greater")
print(f"\n  Independent t-test (one-tailed)")
print(f"  Win rate ≥4 rest days : {more_rest.mean()*100:.1f}% (n={len(more_rest)})")
print(f"  Win rate <4 rest days : {less_rest.mean()*100:.1f}% (n={len(less_rest)})")
print(f"  t-statistic : {t4:.4f}")
print(f"  p-value     : {p4:.4f}")
result(p4 < ALPHA,
       f"More rest significantly improves win chance (p={p4:.4f})"
       if p4 < ALPHA else
       f"Rest days alone not significant predictor (p={p4:.4f})")


hr("TEST 5 — Cards & Outcome: Chi-square: Do yellow cards affect match result?")
print("  H0: Yellow cards per team and match result are independent")
print("  H1: Carded teams have different win rates")

match_team = df.groupby(["MatchID","Player_Team"]).agg(
    Yellows=("Yellow_Cards","sum"),
    Won=("Team_Won","max")
).reset_index()
match_team["Carded"] = match_team["Yellows"] > 0
ct5 = pd.crosstab(match_team["Carded"], match_team["Won"])
chi5, p5, dof5, _ = stats.chi2_contingency(ct5)
print(f"\n  Contingency Table:")
print(ct5.rename(index={True:"Carded",False:"No Card"},
                 columns={True:"Won",False:"Lost/Drew"}).to_string())
print(f"\n  Chi-square : {chi5:.4f}")
print(f"  p-value    : {p5:.4f}  (dof={dof5})")
result(p5 < ALPHA,
       f"Significant association between yellow cards and result (p={p5:.4f})"
       if p5 < ALPHA else
       f"No significant association between yellow cards and result (p={p5:.4f})")


hr("TEST 6 — ANOVA: Does attendance differ significantly across stages?")
print("  H0: Mean attendance is equal across all stages")

STAGE_ORDER = ["Group Stage","Round of 16","Quarter-finals","Semi-finals","Third Place","Final"]
groups = [mc[mc["Stage_Std"] == s]["Attendance"].dropna().values for s in STAGE_ORDER]
f6, p6 = stats.f_oneway(*groups)
print(f"\n  One-way ANOVA (6 stage groups)")
for s, g in zip(STAGE_ORDER, groups):
    print(f"  {s:<20} n={len(g):3d}  mean={np.mean(g)/1000:.0f}K  sd={np.std(g)/1000:.0f}K")
print(f"\n  F-statistic : {f6:.4f}")
print(f"  p-value     : {p6:.6f}")
result(p6 < ALPHA,
       f"Attendance differs significantly across stages (p={p6:.6f})"
       if p6 < ALPHA else
       f"No significant attendance difference across stages (p={p6:.6f})")


hr("TEST 7 — Win Conditions × Stage: Chi-square test")
print("  H0: Win conditions (Normal/ET/Pens) are independent of match stage")

wc_stage_ct = pd.crosstab(mc["Stage_Std"], mc["Win_Conditions"])
chi7, p7, dof7, _ = stats.chi2_contingency(wc_stage_ct)
print(f"\n  Contingency Table:")
print(wc_stage_ct.reindex(STAGE_ORDER).to_string())
print(f"\n  Chi-square : {chi7:.4f}")
print(f"  p-value    : {p7:.6f}  (dof={dof7})")
result(p7 < ALPHA,
       f"Win conditions strongly depend on stage (p={p7:.6f})"
       if p7 < ALPHA else
       f"No significant stage-win condition link (p={p7:.6f})")


hr("TEST 8 — Correlation: Attendance, Goals, Stage")
print("  Pearson correlations with Total_Goals and Match_Result (home win=1)")

mc2 = mc.copy()
mc2["Home_Win"] = (mc2["Match_Result"] == "Home Win").astype(int)
mc2["Is_Knockout"] = (mc2["Stage_Order"] >= 2).astype(int)

vars_of_interest = ["Total_Goals","Attendance","Stage_Order",
                    "Days_Into_Tournament","Home_Win"]
corr_matrix = mc2[vars_of_interest].corr(method="pearson")
print("\n  Pearson Correlation Matrix:")
print(corr_matrix.round(3).to_string())

# Spearman for non-normal
print("\n  Spearman rho (Total_Goals vs Attendance):")
rho, p_rho = stats.spearmanr(mc2["Total_Goals"].dropna(), mc2["Attendance"].dropna())
print(f"  rho={rho:.4f}  p={p_rho:.4f}")
result(p_rho < ALPHA, f"Goals and Attendance {'are' if p_rho < ALPHA else 'are not'} significantly correlated")


hr("TEST 9 — Logistic Regression: Predicting Team Win from Scheduling Factors")
print("  Target: Team_Won (1=win, 0=draw/loss)")
print("  Features: Rest_Days, Is_Home_Team, Is_Host_Team, Stage_Order,")
print("            Yellow_Cards, Effective_Red_Cards")

# Match-team level aggregated features
feat_df = df.groupby(["MatchID","Player_Team"]).agg(
    Rest_Days=("Rest_Days","first"),
    Is_Home=("Is_Home_Team","first"),
    Is_Host=("Is_Host_Team","first"),
    Stage_Order=("Stage_Order","first"),
    Yellow_Cards=("Yellow_Cards","sum"),
    Red_Cards=("Effective_Red_Cards","sum"),
    Team_Won=("Team_Won","first")
).reset_index().dropna(subset=["Rest_Days"])

X = feat_df[["Rest_Days","Is_Home","Is_Host","Stage_Order","Yellow_Cards","Red_Cards"]].astype(float)
y = feat_df["Team_Won"].astype(int)

scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

model = LogisticRegression(max_iter=1000, random_state=42)
cv_scores = cross_val_score(model, X_scaled, y, cv=5, scoring="accuracy")
model.fit(X_scaled, y)
y_pred = model.predict(X_scaled)

print(f"\n  Training samples   : {len(y)}")
print(f"  5-fold CV Accuracy : {cv_scores.mean()*100:.1f}% ± {cv_scores.std()*100:.1f}%")
print(f"\n  Feature Coefficients (standardized):")
feat_names = ["Rest_Days","Is_Home","Is_Host","Stage_Order","Yellow_Cards","Red_Cards"]
for fname, coef in sorted(zip(feat_names, model.coef_[0]), key=lambda x: abs(x[1]), reverse=True):
    direction = "+" if coef > 0 else "-"
    print(f"    {direction}  {fname:<20} coef={coef:+.4f}")

print(f"\n  Classification Report:")
print(classification_report(y, y_pred, target_names=["No Win","Win"]))


hr("TEST 10 — Home Advantage by Era: Has home advantage changed over time?")
print("  Split: pre-1970 (old) vs post-1970 (modern) tournaments")

mc_early  = mc[mc["Year"] <= 1966]
mc_modern = mc[mc["Year"] >= 1970]
early_hr  = (mc_early["Match_Result"]  == "Home Win").mean()
modern_hr = (mc_modern["Match_Result"] == "Home Win").mean()

t10, p10 = stats.ttest_ind(
    (mc_early["Match_Result"]  == "Home Win").astype(int),
    (mc_modern["Match_Result"] == "Home Win").astype(int)
)
print(f"\n  Pre-1970 home win rate  : {early_hr*100:.1f}% (n={len(mc_early)})")
print(f"  Post-1970 home win rate : {modern_hr*100:.1f}% (n={len(mc_modern)})")
print(f"  t-statistic : {t10:.4f}")
print(f"  p-value     : {p10:.4f}")
result(p10 < ALPHA,
       f"Home advantage has changed significantly across eras (p={p10:.4f})"
       if p10 < ALPHA else
       f"Home advantage is consistent across eras (p={p10:.4f})")


# ─────────────────────────────────────────────────────────────────────────
# FIG 13 — Statistical Summary Plot
# ─────────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle("Statistical Analysis Summary", fontsize=13, fontweight="bold")

# Home vs Away Goals distribution
axes[0,0].hist(mc["Home_Goals"], bins=range(0,11), alpha=0.6, color="#4C72B0",
               label=f"Home (μ={mc['Home_Goals'].mean():.2f})", density=True)
axes[0,0].hist(mc["Away_Goals"], bins=range(0,11), alpha=0.6, color="#DD8452",
               label=f"Away (μ={mc['Away_Goals'].mean():.2f})", density=True)
axes[0,0].set(title=f"Home vs Away Goals Distribution\nt={t1:.2f}, p={p1:.4f}",
              xlabel="Goals", ylabel="Density")
axes[0,0].legend()

# Attendance by Stage (box plot)
att_data = [mc[mc["Stage_Std"]==s]["Attendance"].values/1000 for s in STAGE_ORDER]
axes[0,1].boxplot(att_data, labels=[s.replace(" ","\n") for s in STAGE_ORDER],
                  patch_artist=True,
                  boxprops=dict(facecolor="#4C72B0", alpha=0.6))
axes[0,1].set(title=f"Attendance by Stage (ANOVA F={f6:.1f}, p={p6:.4f})",
              ylabel="Thousands")
axes[0,1].tick_params(axis="x", labelsize=7)

# Rest days vs Win rate
rest_win = rest_df.groupby("Rest_Days")["Team_Won"].mean() * 100
axes[1,0].bar(rest_win.index, rest_win.values, color="#55A868")
axes[1,0].axhline(50, color="red", linestyle="--", label="50% baseline")
axes[1,0].set(title=f"Win Rate by Rest Days\nt={t4:.2f}, p={p4:.4f}",
              xlabel="Rest Days", ylabel="Win Rate %")
axes[1,0].legend()

# Logistic regression: coefficient magnitude
coefs = dict(zip(feat_names, model.coef_[0]))
coef_sorted = sorted(coefs.items(), key=lambda x: x[1])
colors_lr = ["#DC3545" if v < 0 else "#28A745" for _, v in coef_sorted]
axes[1,1].barh([k for k,_ in coef_sorted], [v for _,v in coef_sorted], color=colors_lr)
axes[1,1].axvline(0, color="black", linewidth=0.8)
axes[1,1].set(title=f"Logistic Regression Coefficients\n(CV Accuracy={cv_scores.mean()*100:.1f}%)",
              xlabel="Coefficient (standardized)")

plt.tight_layout()
plt.savefig(FIG / "13_statistical_summary.png", dpi=150, bbox_inches="tight")
plt.close()
print()
print("Saved: 13_statistical_summary.png")


hr("STATISTICAL ANALYSIS COMPLETE")
print("  Summary of significance findings:")
tests = [
    ("Home Goal Advantage",         p1 < ALPHA, f"p={p1:.4f}"),
    ("Host Nation Win Boost",        p2 < ALPHA, f"p={p2:.4f}"),
    ("Group Stage More Goals",       p3 < ALPHA, f"p={p3:.4f}"),
    ("Rest Days → Win Rate",         p4 < ALPHA, f"p={p4:.4f}"),
    ("Yellow Cards vs Outcome",      p5 < ALPHA, f"p={p5:.4f}"),
    ("Attendance Varies by Stage",   p6 < ALPHA, f"p={p6:.6f}"),
    ("Win Conditions vs Stage",      p7 < ALPHA, f"p={p7:.6f}"),
    ("Era Home Advantage Change",    p10 < ALPHA, f"p={p10:.4f}"),
]
for name, sig, pv in tests:
    tag = "✓ SIGNIFICANT" if sig else "✗ NOT SIGNIFICANT"
    print(f"  {tag:<20}  {name:<35} {pv}")
