# Data Dictionary

**Project:** FIFA World Cup Analytics | SectionE_g11
**Last Updated:** 2026-04-20

---

## 1. WorldCups.csv (Raw — Tournament Level)

| Column | Type | Description | Example | Issues Found |
|--------|------|-------------|---------|--------------|
| Year | Integer | Year of the World Cup tournament | 1930, 1966, 2014 | None |
| Country | String | Host country/countries | Uruguay, Korea/Japan | Multi-host format (e.g., "Korea/Japan") |
| Winner | String | Champion nation | Brazil, Germany FR | "Germany FR" vs "Germany" inconsistency |
| Runners-Up | String | Runner-up nation | Argentina | Same name inconsistency as Winner |
| Third | String | Third-place nation | Sweden | Same |
| Fourth | String | Fourth-place nation | Yugoslavia | Same |
| GoalsScored | Integer | Total goals in the tournament | 171 | None |
| QualifiedTeams | Integer | Number of teams that qualified | 32 | None |
| MatchesPlayed | Integer | Total matches played | 64 | None |
| Attendance | String/Float | Total attendance (thousands) | 590.549, 1.045.246 | **European number format** (dots as thousand separators in some rows) — requires cleaning |

---

## 2. WorldCupMatches.csv (Raw — Match Level)

| Column | Type | Description | Example | Issues Found |
|--------|------|-------------|---------|--------------|
| Year | Integer | Year of the tournament | 1930, 2014 | None |
| Datetime | String | Match date and time | "13 Jul 1930 - 15:00 " | **Trailing spaces**, mixed formats |
| Stage | String | Tournament stage | Group 1, Quarter-finals, Final | Inconsistent naming across years |
| Stadium | String | Stadium name | Estadio Centenario | Some missing |
| City | String | Host city | "Montevideo " | **Trailing spaces** |
| Home Team Name | String | Home team | France, Brazil | "Germany FR" vs "Germany" |
| Home Team Goals | Integer | Goals scored by home team | 4 | None |
| Away Team Goals | Integer | Goals scored by away team | 1 | None |
| Away Team Name | String | Away team | Mexico | Same name inconsistencies |
| Win conditions | String | Extra time / penalty notes | " ", "After extra time" | **Mostly blank/whitespace** |
| Attendance | Float | Match attendance | 4444.0 | **NaN values** present |
| Half-time Home Goals | Integer | Home goals at half time | 3 | Some NaN |
| Half-time Away Goals | Integer | Away goals at half time | 0 | Some NaN |
| Referee | String | Referee name and country | LOMBARDI Domingo (URU) | Format varies |
| Assistant 1 | String | First assistant referee | CRISTOPHE Henry (BEL) | Some missing |
| Assistant 2 | String | Second assistant referee | REGO Gilberto (BRA) | Some missing |
| RoundID | Integer | Round identifier | 201 | None |
| MatchID | Integer | Unique match identifier | 1096 | Join key with Players table |
| Home Team Initials | String | 3-letter home team code | FRA | None |
| Away Team Initials | String | 3-letter away team code | MEX | None |

---

## 3. WorldCupPlayers.csv (Raw — Player Level) — **Primary Dataset**

| Column | Type | Description | Example | Issues Found |
|--------|------|-------------|---------|--------------|
| RoundID | Integer | Round identifier | 201 | Join key |
| MatchID | Integer | Unique match identifier | 1096 | Join key with Matches table |
| Team Initials | String | 3-letter team code | FRA | None |
| Coach Name | String | Coach name and country | CAUDRON Raoul (FRA) | Format varies, some blanks |
| Line-up | String | S = Starting XI, N = Substitute | S, N | None |
| Shirt Number | Integer | Player shirt number | 0, 7 | **0 used as placeholder** for missing numbers |
| Player Name | String | Full player name | Alex THEPOT | Name format FIRSTNAME LASTNAME (ALL CAPS surname) |
| Position | String | Player position | GK, C (Captain) | **Inconsistent coding** — many blanks, C=Captain not a position |
| Event | String | Match events for player | G40', Y76', R88' | **Multi-event strings**, blank for no events |

---

## 4. Processed Master Dataset: wc_master.csv

Created by joining all three tables. Final schema after cleaning:

| Column | Type | Description |
|--------|------|-------------|
| MatchID | Integer | Unique match identifier |
| Year | Integer | Tournament year |
| Stage | String | Standardized stage name |
| Home_Team | String | Standardized home team name |
| Away_Team | String | Standardized away team name |
| Home_Goals | Integer | Full-time home goals |
| Away_Goals | Integer | Full-time away goals |
| Total_Goals | Integer | Sum of home + away goals |
| Attendance | Float | Match attendance |
| HT_Home_Goals | Integer | Half-time home goals |
| HT_Away_Goals | Integer | Half-time away goals |
| Stadium | String | Stadium name (cleaned) |
| City | String | City name (cleaned) |
| Win_Conditions | String | AET / Penalties / Normal |
| Player_Name | String | Player full name |
| Team_Initials | String | Player's team |
| Lineup | String | S=Starter, N=Sub |
| Shirt_Number | Integer | Jersey number (NaN where 0) |
| Position | String | GK / DF / MF / FW / C |
| Goals_Scored | Integer | Goals scored by player in match |
| Yellow_Cards | Integer | Yellow cards received |
| Red_Cards | Integer | Red cards received |
| Is_Substitute | Integer | 1 if substituted on |
| Match_Result | String | Home Win / Away Win / Draw |
| Host_Nation | String | Tournament host country |
| Tournament_Winner | String | That year's champion |

---

## Event Code Legend (WorldCupPlayers — Event column)

| Code | Meaning |
|------|---------|
| G{minute}' | Goal scored at given minute |
| Y{minute}' | Yellow card at given minute |
| R{minute}' | Red card at given minute |
| SY{minute}' | Second yellow (= Red) |
| I{minute}' | Player substituted in |
| O{minute}' | Player substituted out |

---

## Known Data Quality Issues

1. **Attendance format** in WorldCups.csv uses European number format (dots as thousand separators) — converted to integers in cleaning pipeline.
2. **"Germany FR"** appears in older records; standardized to "West Germany" in cleaning.
3. **Shirt Number = 0** used as placeholder for unknown numbers — converted to NaN.
4. **Position column** conflates roles (GK/C for Captain) — split into `Position` and `Is_Captain`.
5. **Trailing whitespace** in City and Datetime columns — stripped.
6. **Win conditions** column is mostly blank spaces — normalized to "Normal", "AET", or "Penalties".
7. **Duplicate match rows** in WorldCupMatches.csv for some matches — deduplicated on MatchID.
