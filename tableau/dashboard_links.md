# Tableau Dashboard Links

**Project:** FIFA World Cup Analytics | SectionE_g11

---

## Published Dashboard

| Dashboard | URL | Status |
|-----------|-----|--------|
| FIFA World Cup Analytics — Executive View | _To be added after publishing_ | Pending |

---

## How to Publish

1. Open Tableau Desktop or Tableau Public (free at public.tableau.com)
2. Connect to the CSV files in `tableau/` folder — start with `tableau_master.csv`
3. Build dashboards as per the design spec below
4. Click **Server → Tableau Public → Save to Tableau Public**
5. Copy the public URL and paste it in the table above

---

## Dashboard Design Spec

### Sheet 1 — Tournament Overview
- Line chart: Total Attendance over Years
- Line chart: Average Goals/Match over Years
- Filter: Year range slider
- KPI cards: Total tournaments, Total goals, Max attendance

### Sheet 2 — Team Performance
- Horizontal bar: Top 15 teams by Win Rate (filter: min matches)
- Scatter: Win Rate vs Goal Difference (bubble = tournaments)
- Filter: Minimum matches played

### Sheet 3 — Match Analysis
- Bar chart: Average goals by Stage (ordered Group → Final)
- Pie/donut: Match outcome distribution (Home Win / Away Win / Draw)
- Box plot: Goals distribution by Stage
- Filter: Year, Stage

### Sheet 4 — Home Advantage
- Dual-axis: Home Goals vs Away Goals trend by Year
- Bar: Home Advantage Index by Year
- KPI: Overall home win rate

### Sheet 5 — Player Goals
- Ranked bar: Top 20 all-time scorers
- Filter: Team, Year

### Dashboard — Executive View (combine Sheets 1, 2, 4)
### Dashboard — Operational View (combine Sheets 3, 5)

---

## Data Sources for Tableau

| File | Use |
|------|-----|
| `tableau_master.csv` | Primary — player-match level, 37K rows |
| `tableau_matches.csv` | Match-level summary, ~850 rows |
| `kpi_team_performance.csv` | Team KPI table |
| `kpi_goals_by_year.csv` | Goals trend |
| `kpi_goals_by_stage.csv` | Stage analysis |
| `kpi_home_advantage.csv` | Home advantage KPI |
| `kpi_player_goals.csv` | Player scoring KPI |
| `kpi_attendance.csv` | Attendance KPI |
