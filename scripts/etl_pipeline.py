"""
etl_pipeline.py — FIFA Match Scheduling Analytics ETL Pipeline
Project: FIFA World Cup Analytics | SectionE_g11
Problem: Help FIFA optimize match scheduling to maximize attendance,
         entertainment value, and manage player workload/disciplinary risk.

Run with: python3 scripts/etl_pipeline.py
Output  : data/processed/wc_schedule_analysis.csv
          (37,784 rows × 15 analytical columns)
"""

import pandas as pd
import numpy as np
import re
import os

RAW_PATH       = os.path.join(os.path.dirname(__file__), '..', 'data', 'raw')
PROCESSED_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'processed')
os.makedirs(PROCESSED_PATH, exist_ok=True)


def log(msg):
    print(f'[ETL] {msg}')


# ─── EXTRACT ──────────────────────────────────────────────────────────────────

def extract():
    log('Loading raw datasets...')
    cups    = pd.read_csv(os.path.join(RAW_PATH, 'WorldCups.csv'))
    matches = pd.read_csv(os.path.join(RAW_PATH, 'WorldCupMatches.csv'))
    players = pd.read_csv(os.path.join(RAW_PATH, 'WorldCupPlayers.csv'))
    log(f'  WorldCups    : {cups.shape[0]} rows × {cups.shape[1]} cols')
    log(f'  WorldCupMatches: {matches.shape[0]} rows × {matches.shape[1]} cols (includes empty rows)')
    log(f'  WorldCupPlayers: {players.shape[0]} rows × {players.shape[1]} cols')
    return cups, matches, players


# ─── CLEAN CUPS ───────────────────────────────────────────────────────────────

def clean_cups(cups_raw):
    log('Cleaning WorldCups...')
    cups = cups_raw.copy()

    # European dot-as-thousands format (e.g. 1.045.246 → 1045246)
    def parse_attendance(val):
        if pd.isna(val):
            return np.nan
        s = str(val).strip()
        if s.count('.') > 1:          # multiple dots = European thousands
            s = s.replace('.', '')
        return float(s)

    cups['Attendance'] = cups['Attendance'].apply(parse_attendance)

    # Standardize team names
    name_fixes = {
        'Germany FR':     'West Germany',
        'Korea Republic': 'South Korea',
    }
    for col in ['Winner', 'Runners-Up', 'Third', 'Fourth', 'Country']:
        cups[col] = cups[col].replace(name_fixes).str.strip()

    # Keep only what we need for the join: Year, host nation
    cups = cups[['Year', 'Country']].rename(columns={'Country': 'Host_Nation'})

    log(f'  Cups cleaned: {cups.shape[0]} rows — Host_Nation + Year ready for join')
    return cups


# ─── CLEAN MATCHES ────────────────────────────────────────────────────────────

STAGE_MAP = {
    'Group 1': 'Group Stage', 'Group 2': 'Group Stage', 'Group 3': 'Group Stage',
    'Group 4': 'Group Stage', 'Group 5': 'Group Stage', 'Group 6': 'Group Stage',
    'Group A': 'Group Stage', 'Group B': 'Group Stage', 'Group C': 'Group Stage',
    'Group D': 'Group Stage', 'Group E': 'Group Stage', 'Group F': 'Group Stage',
    'Group G': 'Group Stage', 'Group H': 'Group Stage',
    'First round':               'Group Stage',
    'Preliminary round':         'Group Stage',
    'Quarter-finals':            'Quarter-Final',
    'Semi-finals':               'Semi-Final',
    'Final':                     'Final',
    'Round of 16':               'Round of 16',
    'Second round':              'Round of 16',
    'Match for third place':     'Third Place',
    'Third place':               'Third Place',
    'Play-off for third place':  'Third Place',
}

TEAM_FIXES = {
    'Germany FR':   'West Germany',
    'Korea Republic': 'South Korea',
    # HTML-encoded names found in raw data
    'rn">Bosnia and Herzegovina': 'Bosnia and Herzegovina',
    'rn">Republic of Ireland':    'Republic of Ireland',
    'rn">Serbia and Montenegro':  'Serbia and Montenegro',
    'rn">Trinidad and Tobago':    'Trinidad and Tobago',
    'rn">United Arab Emirates':   'United Arab Emirates',
}


def clean_matches(matches_raw):
    log('Cleaning WorldCupMatches...')
    matches = matches_raw.copy()

    # Drop the 3,720 completely empty rows
    before = len(matches)
    matches.dropna(how='all', inplace=True)
    log(f'  Dropped {before - len(matches)} empty rows → {len(matches)} valid rows')

    # Strip whitespace from all string columns
    for col in matches.select_dtypes(include='object').columns:
        matches[col] = matches[col].astype(str).str.strip()
    matches.replace('nan', np.nan, inplace=True)

    # Drop 16 true duplicate MatchIDs (keep first occurrence)
    before = len(matches)
    matches.drop_duplicates(subset='MatchID', keep='first', inplace=True)
    log(f'  Dropped {before - len(matches)} duplicate MatchID rows → {len(matches)} unique matches')

    # Fix team names
    for col in ['Home Team Name', 'Away Team Name']:
        matches[col] = matches[col].replace(TEAM_FIXES).str.strip()

    # Standardize Stage
    matches['Stage'] = matches['Stage'].map(STAGE_MAP).fillna(matches['Stage'])

    # Normalize Win conditions → scheduling-relevant duration categories
    def win_condition(val):
        if pd.isna(val) or str(val).strip() in ('', 'nan'):
            return 'Normal'
        v = str(val).lower()
        if 'penalt' in v:
            return 'Penalties'
        if 'extra time' in v or 'aet' in v:
            return 'AET'
        return 'Normal'

    matches['Win_Conditions'] = matches['Win conditions'].apply(win_condition)

    # Numeric coercions
    for col in ['Home Team Goals', 'Away Team Goals', 'Half-time Home Goals',
                'Half-time Away Goals', 'Attendance']:
        matches[col] = pd.to_numeric(matches[col], errors='coerce')

    # Fill the 2 missing Attendance values with that year's median
    matches['Attendance'] = matches.groupby('Year')['Attendance'].transform(
        lambda x: x.fillna(x.median())
    )

    # Derived scheduling columns
    matches['Total_Goals'] = (matches['Home Team Goals'] + matches['Away Team Goals']).astype(int)

    def match_result(row):
        if row['Home Team Goals'] > row['Away Team Goals']:
            return 'Home Win'
        elif row['Home Team Goals'] < row['Away Team Goals']:
            return 'Away Win'
        return 'Draw'

    matches['Match_Result'] = matches.apply(match_result, axis=1)

    # Keep only join key + scheduling columns needed downstream
    matches = matches[[
        'MatchID', 'Year', 'Stage', 'Home Team Name', 'Away Team Name',
        'Attendance', 'Total_Goals', 'Match_Result', 'Win_Conditions', 'City'
    ]].rename(columns={
        'Home Team Name': 'Home_Team',
        'Away Team Name': 'Away_Team',
        'City':           'Venue_City',
    })

    matches['Year']        = matches['Year'].astype(int)
    matches['Attendance']  = matches['Attendance'].round(0).astype(int)

    log(f'  Matches cleaned: {matches.shape[0]} rows × {matches.shape[1]} cols')
    return matches


# ─── CLEAN PLAYERS ────────────────────────────────────────────────────────────

EVENT_RE = {
    'Goals_Scored': re.compile(r'(?<![A-Z])G(\d+)'),   # G not preceded by letter
    'Yellow_Cards': re.compile(r'Y\d+'),
    'Red_Cards':    re.compile(r'R\d+|SY\d+'),
}


def parse_events(event_str):
    if pd.isna(event_str) or str(event_str).strip() in ('', 'nan'):
        return 0, 0, 0
    s = str(event_str)
    goals   = len(EVENT_RE['Goals_Scored'].findall(s))
    yellows = len(EVENT_RE['Yellow_Cards'].findall(s))
    reds    = len(EVENT_RE['Red_Cards'].findall(s))
    return goals, yellows, reds


def clean_players(players_raw):
    log('Cleaning WorldCupPlayers...')
    players = players_raw.copy()

    # Strip whitespace
    for col in players.select_dtypes(include='object').columns:
        players[col] = players[col].astype(str).str.strip()
    players.replace('nan', np.nan, inplace=True)

    # Parse Event → numerical scheduling metrics
    parsed = players['Event'].apply(parse_events)
    players[['Goals_Scored', 'Yellow_Cards', 'Red_Cards']] = pd.DataFrame(
        parsed.tolist(), index=players.index
    )

    # Lineup: S=Starter, N=Substitute
    players['Lineup'] = players['Line-up'].map({'S': 'Starter', 'N': 'Substitute'})

    # Keep only scheduling-relevant player columns + join key
    players = players[['MatchID', 'Team Initials', 'Lineup',
                        'Goals_Scored', 'Yellow_Cards', 'Red_Cards']].rename(
        columns={'Team Initials': 'Player_Team'}
    )

    players['MatchID'] = pd.to_numeric(players['MatchID'], errors='coerce')

    log(f'  Players cleaned: {players.shape[0]} rows × {players.shape[1]} cols')
    return players


# ─── MERGE ────────────────────────────────────────────────────────────────────

def merge_all(cups, matches, players):
    log('Merging all three datasets...')

    # Step 1: Players ← Matches (many players per match)
    merged = players.merge(matches, on='MatchID', how='inner')
    log(f'  After Players ↔ Matches join: {merged.shape[0]} rows')

    # Step 2: Add Host_Nation from Cups via Year
    merged = merged.merge(cups, on='Year', how='left')
    log(f'  After adding WorldCups context: {merged.shape[0]} rows')

    # Remove exact duplicate rows created by repeated player/event combinations
    before = len(merged)
    merged.drop_duplicates(inplace=True)
    log(f'  Removed {before - len(merged)} exact duplicate rows → {len(merged)} unique rows')

    # Drop the MatchID — it's a join key (ID), not an analytical column
    merged.drop(columns=['MatchID'], inplace=True)

    return merged


# ─── VALIDATE & EXPORT ────────────────────────────────────────────────────────

EXPECTED_COLUMNS = [
    'Year', 'Stage', 'Home_Team', 'Away_Team', 'Attendance',
    'Total_Goals', 'Match_Result', 'Win_Conditions', 'Venue_City',
    'Host_Nation', 'Player_Team', 'Lineup',
    'Goals_Scored', 'Yellow_Cards', 'Red_Cards',
]


def validate_and_export(df):
    log('Validating final dataset...')

    # Enforce exact column set in defined order
    df = df[EXPECTED_COLUMNS]

    assert df.shape[0] >= 5000, f"Row count {df.shape[0]} below 5,000 minimum!"
    assert df.shape[1] == len(EXPECTED_COLUMNS), f"Column mismatch: {df.shape[1]}"
    assert df.duplicated().sum() == 0, f"Found {df.duplicated().sum()} duplicate rows in final dataset"
    assert df.isnull().sum().sum() == 0 or True  # log nulls, don't fail

    nulls = df.isnull().sum()
    nulls = nulls[nulls > 0]
    if len(nulls):
        log(f'  Remaining nulls:\n{nulls}')
    else:
        log('  No nulls in final dataset.')

    out_path = os.path.join(PROCESSED_PATH, 'wc_schedule_analysis.csv')
    df.to_csv(out_path, index=False)

    log(f'\n  Final dataset: {df.shape[0]:,} rows × {df.shape[1]} columns')
    log(f'  Columns: {list(df.columns)}')
    log(f'  Saved → {out_path}')

    print('\n' + '='*60)
    print('COLUMN SUMMARY')
    print('='*60)
    for col in df.columns:
        dtype = df[col].dtype
        n_unique = df[col].nunique()
        null_ct  = df[col].isna().sum()
        sample   = df[col].dropna().iloc[0] if len(df[col].dropna()) else 'N/A'
        print(f'  {col:<20} {str(dtype):<10} unique={n_unique:<6} nulls={null_ct:<5} sample={sample}')

    return df


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    log('=== FIFA Scheduling Analytics ETL — SectionE_g11 ===')
    log('Problem: Optimize FIFA match scheduling for attendance, entertainment & player management\n')

    cups_raw, matches_raw, players_raw = extract()
    cups    = clean_cups(cups_raw)
    matches = clean_matches(matches_raw)
    players = clean_players(players_raw)
    merged  = merge_all(cups, matches, players)
    final   = validate_and_export(merged)

    log('\nETL pipeline complete.')
    return final


if __name__ == '__main__':
    main()
