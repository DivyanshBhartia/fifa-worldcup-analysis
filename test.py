"""
test.py — Comprehensive Data Quality, Cleaning & Join Integrity Validation
Project: FIFA World Cup Analytics | SectionE_g11
Grain  : One row = one player appearance in one match (player-match grain).
         37,048 rows ≠ 836 matches — this is intentional.

Run with: python test.py
"""

import re
import pandas as pd
import numpy as np
from pathlib import Path


# Actual columns of wc_players_combined.csv (player-match grain, 56 cols)
EXPECTED_COLUMNS = [
    'Year', 'MatchID', 'RoundID',
    'Match_Date', 'Match_Time', 'Day_of_Week', 'Month',
    'Stage_Std', 'Stage_Order', 'Stage_Raw',
    'Days_Into_Tournament', 'Rest_Days',
    'Stadium', 'City', 'Host_Country',
    'Home_Team', 'Away_Team', 'Tournament_Host',
    'Is_Host_Home', 'Is_Host_Away',
    'Player_Team', 'Team_Initials', 'Player_Name',
    'Shirt_Number', 'Coach',
    'Is_Starter', 'Is_Substitute', 'Is_Captain', 'Is_GK',
    'Is_Home_Team', 'Is_Host_Team',
    'Goals', 'Own_Goals', 'Goals_Fully_Attributed',
    'Yellow_Cards', 'Red_Cards', 'Second_Yellow_Red', 'Effective_Red_Cards',
    'Suspended_Next_Match',
    'Penalties_Scored', 'Missed_Penalties',
    'Subbed_In', 'Subbed_Out',
    'Match_Result', 'Win_Conditions', 'Team_Won',
    'Team_Goals_For', 'Team_Goals_Against',
    'Total_Goals', 'Goal_Diff',
    'HT_Home_Goals', 'HT_Away_Goals',
    'Attendance',
    'Tournament_Winner', 'Qualified_Teams',
    'Tournament_Matches', 'Tournament_Total_Goals',
]

# Stage names as produced by preprocess.py STAGE_MAP
VALID_STAGES = {'Group Stage', 'Round of 16', 'Quarter-finals', 'Semi-finals',
                'Third Place', 'Final'}

# Win condition values produced by preprocess.py parse_win_conditions()
VALID_WIN_CONDITIONS = {'Normal', 'Extra Time', 'Penalties'}


class DataValidator:
    def __init__(self, processed_path='data/processed/wc_players_combined.csv'):
        self.df = pd.read_csv(processed_path)
        self.report = {}
        self.schema_report = {}
        self.before_after_report = {}
        self.raw_cups = None
        self.raw_matches = None
        self.raw_players = None
        self._load_raw_datasets()

    def _load_raw_datasets(self):
        try:
            self.raw_cups = pd.read_csv('data/raw/WorldCups.csv')
            self.raw_matches = pd.read_csv('data/raw/WorldCupMatches.csv')
            self.raw_players = pd.read_csv('data/raw/WorldCupPlayers.csv')
        except Exception as e:
            print(f'⚠️  Warning: Could not load raw datasets: {e}')

    def validate_all(self):
        print('\n' + '='*80)
        print('FIFA WORLD CUP DATA QUALITY & JOIN INTEGRITY REPORT')
        print('  Grain: player-match (one row per player per match appearance)')
        print('='*80 + '\n')

        self.show_before_after_cleaning_metrics()
        self.check_structure()
        self.check_schema()
        self.check_nulls()
        self.check_dtypes()
        self.check_duplicates()
        self.check_value_ranges()
        self.check_join_integrity()
        self.check_referential_consistency()
        self.check_data_cleaning_quality()
        self.check_data_consistency()
        self.compute_analytics_metrics()
        self.print_summary()

        return self.report

    # ─── BEFORE / AFTER METRICS ───────────────────────────────────────────────

    def show_before_after_cleaning_metrics(self):
        print('🧪 BEFORE vs AFTER CLEANING METRICS')
        print('-' * 70)

        if self.raw_cups is None or self.raw_matches is None or self.raw_players is None:
            print('  Raw datasets not available. Skipping before-cleaning comparison.\n')
            return

        cups_raw    = self.raw_cups
        matches_raw = self.raw_matches
        players_raw = self.raw_players

        before = {
            'raw_players_rows':              len(players_raw),
            'raw_matches_rows':              len(matches_raw),
            'raw_cups_rows':                 len(cups_raw),
            'raw_matches_empty_rows':        int(matches_raw.isna().all(axis=1).sum()),
            'raw_matches_duplicate_matchid': int(
                matches_raw.dropna(subset=['MatchID']).duplicated(subset=['MatchID']).sum()
            ),
            'raw_total_nulls': int(
                players_raw.isna().sum().sum() +
                matches_raw.isna().sum().sum() +
                cups_raw.isna().sum().sum()
            ),
        }

        unique_matches = self.df['MatchID'].nunique() if 'MatchID' in self.df.columns else 'N/A'
        after = {
            'processed_rows':             len(self.df),
            'processed_columns':          self.df.shape[1],
            'processed_exact_duplicates': int(self.df.duplicated().sum()),
            'processed_total_nulls':      int(self.df.isna().sum().sum()),
            'processed_unique_matches':   unique_matches,
            'processed_unique_teams':     int(
                len(set(self.df['Home_Team'].unique()) | set(self.df['Away_Team'].unique()))
            ),
        }

        self.before_after_report = {'before': before, 'after': after}
        self.report['before_after'] = self.before_after_report

        print('  Before Cleaning:')
        print(f"    - Raw players rows (player appearances): {before['raw_players_rows']:,}")
        print(f"    - Raw matches rows (incl. empty):        {before['raw_matches_rows']:,}")
        print(f"    - Raw cups rows:                         {before['raw_cups_rows']:,}")
        print(f"    - Empty rows in matches:                 {before['raw_matches_empty_rows']:,}")
        print(f"    - Duplicate MatchID rows:                {before['raw_matches_duplicate_matchid']:,}")
        print(f"    - Total nulls (all raw files):           {before['raw_total_nulls']:,}")
        print('  After Cleaning:')
        print(f"    - Processed rows (player-match grain):   {after['processed_rows']:,}")
        print(f"    - Processed columns:                     {after['processed_columns']:,}")
        print(f"    - Unique matches:                        {after['processed_unique_matches']:,}")
        print(f"    - Exact duplicate rows:                  {after['processed_exact_duplicates']:,}")
        print(f"    - Total nulls:                           {after['processed_total_nulls']:,}")
        print(f"    - Unique teams:                          {after['processed_unique_teams']:,}")
        print()

    # ─── STRUCTURE ────────────────────────────────────────────────────────────

    def check_structure(self):
        print('📊 DATASET STRUCTURE')
        print('-' * 80)
        unique_matches = self.df['MatchID'].nunique() if 'MatchID' in self.df.columns else 'N/A'
        print(f'  Grain          : one row per player per match appearance')
        print(f'  Total Rows     : {len(self.df):,}  (= player appearances)')
        print(f'  Unique Matches : {unique_matches:,}')
        print(f'  Total Columns  : {self.df.shape[1]}')
        print(f'  Memory Usage   : {self.df.memory_usage(deep=True).sum() / 1024**2:.2f} MB')
        print(f'\n  Column Inventory:')
        print(f'  {self.df.columns.tolist()}')

        self.report['structure'] = {
            'rows': len(self.df),
            'unique_matches': unique_matches,
            'columns': self.df.shape[1],
            'memory_mb': round(self.df.memory_usage(deep=True).sum() / 1024**2, 2),
        }
        print()

    # ─── SCHEMA ───────────────────────────────────────────────────────────────

    def check_schema(self):
        print('🧩 SCHEMA CHECK')
        print('-' * 70)

        actual_columns = list(self.df.columns)
        missing = [col for col in EXPECTED_COLUMNS if col not in actual_columns]
        extra   = [col for col in actual_columns   if col not in EXPECTED_COLUMNS]

        print(f'  Expected Columns : {len(EXPECTED_COLUMNS)}')
        print(f'  Actual Columns   : {len(actual_columns)}')
        print(f'  Missing Columns  : {missing if missing else "None"}')
        print(f'  Extra Columns    : {extra   if extra   else "None"}')

        self.schema_report = {
            'expected': EXPECTED_COLUMNS,
            'actual': actual_columns,
            'missing': missing,
            'extra': extra,
            'matches_expected': not missing and not extra,
        }
        self.report['schema'] = self.schema_report

        if missing:
            print(f'  ⚠️  MISSING expected columns: {missing}')
        if extra:
            print(f'  ℹ️  Extra columns (not in template): {extra}')
        if not missing and not extra:
            print('  ✓ Schema matches expected combined dataset')
        print()

    # ─── NULL VALUES ──────────────────────────────────────────────────────────

    def check_nulls(self):
        print('✅ NULL VALUES CHECK')
        print('-' * 80)

        nulls      = self.df.isnull().sum()
        total_nulls = nulls.sum()
        expected_null_cols = {
            'Rest_Days':    'first match of each year has no prior match to compute rest from',
            'Shirt_Number': 'historical tournaments (pre-1954) did not use numbered shirts',
        }

        if total_nulls == 0:
            print('  ✓ NO NULL VALUES — Dataset is complete!')
        else:
            print(f'  ⚠️  Found {total_nulls:,} null values:')
            for col, count in nulls[nulls > 0].items():
                pct  = count / len(self.df) * 100
                note = f'  ← expected: {expected_null_cols[col]}' if col in expected_null_cols else ''
                print(f'     - {col}: {count:,} ({pct:.2f}%){note}')

        self.report['nulls'] = {
            'total_nulls': int(total_nulls),
            'complete': total_nulls == 0,
        }
        print()

    # ─── DATA TYPES ───────────────────────────────────────────────────────────

    def check_dtypes(self):
        print('🔍 DATA TYPES CHECK')
        print('-' * 80)
        print('  Column              | Type       | Unique Values')
        print('  ' + '-' * 74)

        dtype_report = {}
        for col in self.df.columns:
            dtype  = str(self.df[col].dtype)
            unique = self.df[col].nunique()
            dtype_report[col] = dtype
            print(f'  {col:<30} | {dtype:<10} | {unique:>6,}')

        self.report['dtypes'] = dtype_report
        print()

    # ─── DUPLICATES ───────────────────────────────────────────────────────────

    def check_duplicates(self):
        """
        At player-match grain the natural key is (MatchID, Player_Name, Team_Initials).
        Multiple players from the same team in the same match is NOT a duplicate — it
        is the expected structure of the dataset.
        """
        print('🔄 DUPLICATE RECORDS CHECK')
        print('-' * 80)
        print('  Note: grain = player-match. Multiple rows per match are expected.')
        print()

        exact_duplicates = int(self.df.duplicated().sum())
        print(f'  ✓ Exact Row Duplicates: {exact_duplicates}')
        if exact_duplicates == 0:
            print(f'    ✓ No fully identical rows — dataset is clean')
        else:
            print(f'    ⚠️  Found {exact_duplicates} fully identical rows')

        # Expected: many rows per match (multiple players per team)
        match_rows = self.df['MatchID'].value_counts()
        print(f'\n  ✓ Rows per match (expected ~44, i.e. 22 players × 2 teams):')
        print(f'    - Min rows per match  : {match_rows.min():,}')
        print(f'    - Max rows per match  : {match_rows.max():,}')
        print(f'    - Median rows per match: {match_rows.median():.0f}')

        # TRUE player-level duplicates: same player in same match more than once
        if 'Player_Name' in self.df.columns and 'Team_Initials' in self.df.columns:
            player_match_key = ['MatchID', 'Player_Name', 'Team_Initials']
            player_dupes = int(self.df.duplicated(subset=player_match_key, keep=False).sum())
            print(f'\n  ✓ True player-match duplicates (same player twice in same match): {player_dupes:,}')
            if player_dupes == 0:
                print(f'    ✓ Each player appears at most once per match')
            else:
                print(f'    ⚠️  {player_dupes} rows have the same MatchID+Player_Name+Team_Initials')
                print(self.df[self.df.duplicated(subset=player_match_key, keep=False)]
                      [player_match_key].head(6).to_string(index=False))

        self.report['duplicates'] = {
            'exact_duplicates': exact_duplicates,
            'is_clean': exact_duplicates == 0,
        }
        print()

    # ─── VALUE RANGES ─────────────────────────────────────────────────────────

    def check_value_ranges(self):
        print('📏 VALUE RANGES CHECK')
        print('-' * 80)

        numeric_cols = self.df.select_dtypes(include=[np.number]).columns
        range_report = {}

        for col in numeric_cols:
            min_val  = self.df[col].min()
            max_val  = self.df[col].max()
            mean_val = self.df[col].mean()
            std_val  = self.df[col].std()
            range_report[col] = {
                'min': float(min_val), 'max': float(max_val),
                'mean': float(mean_val), 'std': float(std_val),
            }
            print(f'  {col:<30} | Min: {min_val:>8} | Max: {max_val:>8} | '
                  f'Mean: {mean_val:>8.2f} | Std: {std_val:>7.2f}')

        self.report['value_ranges'] = range_report
        print()

    # ─── JOIN INTEGRITY ───────────────────────────────────────────────────────

    def check_join_integrity(self):
        print('🔗 JOIN INTEGRITY CHECK')
        print('-' * 80)

        # Check 1: match-level columns should be constant within each MatchID
        match_consistency = self.df.groupby('MatchID').agg({
            'Home_Team':    'nunique',
            'Away_Team':    'nunique',
            'Year':         'nunique',
            'Stage_Std':    'nunique',
            'Attendance':   'nunique',
            'Total_Goals':  'nunique',
        }).reset_index()

        inconsistent = int((match_consistency[match_consistency.columns[1:]] > 1).any(axis=1).sum())
        total_matches = len(match_consistency)
        print(f'  ✓ Match-level column consistency (same value for every player in a match):')
        print(f'    - Consistent matches: {total_matches - inconsistent} / {total_matches}')
        if inconsistent > 0:
            print(f'    ⚠️  INCONSISTENT MATCHES: {inconsistent}')

        # Check 2: player's team must be either Home_Team or Away_Team
        home_players = int((self.df['Player_Team'] == self.df['Home_Team']).sum())
        away_players = int((self.df['Player_Team'] == self.df['Away_Team']).sum())
        orphaned     = len(self.df) - home_players - away_players

        print(f'\n  ✓ Player-Team-Match assignment:')
        print(f'    - On Home Team : {home_players:,}')
        print(f'    - On Away Team : {away_players:,}')
        print(f'    - Total rows   : {len(self.df):,}')
        if orphaned == 0:
            print(f'    ✓ ALL PLAYERS CORRECTLY ASSIGNED TO HOME or AWAY TEAM')
        else:
            print(f'    ⚠️  ORPHANED RECORDS: {orphaned} players not in Home_Team or Away_Team')

        # Check 3: each Year has exactly one Host_Country
        year_hosts     = self.df.groupby('Year')['Host_Country'].nunique()
        consistent_host = bool((year_hosts == 1).all())
        print(f'\n  ✓ Year → Host_Country consistency:')
        if consistent_host:
            print(f'    ✓ Each year maps to exactly ONE host country')
        else:
            print(f'    ⚠️  INCONSISTENT: {(year_hosts > 1).sum()} year(s) with multiple host values')

        # Check 4: unique match coverage vs raw source
        unique_matches = int(self.df['MatchID'].nunique())
        print(f'\n  ✓ Unique Match Coverage:')
        print(f'    - Unique matches in dataset : {unique_matches:,}')
        if self.raw_matches is not None:
            raw_unique = self.raw_matches['MatchID'].nunique()
            print(f'    - Unique matches in raw file: {raw_unique}')
            print(f'    - Coverage: {unique_matches / raw_unique * 100:.1f}%')

        self.report['join_integrity'] = {
            'consistent_matches': total_matches - inconsistent,
            'home_team_players': home_players,
            'away_team_players': away_players,
            'orphaned_records': orphaned,
            'year_host_consistent': consistent_host,
            'unique_matches': unique_matches,
        }
        print()

    # ─── REFERENTIAL CONSISTENCY ──────────────────────────────────────────────

    def check_referential_consistency(self):
        print('🔐 REFERENTIAL CONSISTENCY CHECK')
        print('-' * 80)

        invalid_years = set()
        if self.raw_cups is not None:
            valid_years   = set(self.raw_cups['Year'].unique())
            df_years      = set(self.df['Year'].unique())
            invalid_years = df_years - valid_years
            print(f'  ✓ Year validity:')
            print(f'    - Valid years: {len(df_years - invalid_years)} / {len(df_years)}')
            if invalid_years:
                print(f'    ⚠️  INVALID YEARS: {sorted(invalid_years)}')
            else:
                print(f'    ✓ All years are valid World Cup tournaments')

        # Team name cross-check
        home_teams   = set(self.df['Home_Team'].unique())
        away_teams   = set(self.df['Away_Team'].unique())
        player_teams = set(self.df['Player_Team'].unique())
        all_teams    = home_teams | away_teams | player_teams

        print(f'\n  ✓ Team name consistency:')
        print(f'    - Unique home teams   : {len(home_teams)}')
        print(f'    - Unique away teams   : {len(away_teams)}')
        print(f'    - Unique player teams : {len(player_teams)}')
        print(f'    - Total unique teams  : {len(all_teams)}')

        # Flag any remaining HTML artifacts (rn"> prefix not cleaned)
        html_pattern = re.compile(r'^rn">')
        artifact_teams = [t for t in all_teams if isinstance(t, str) and html_pattern.match(t)]
        if artifact_teams:
            print(f'\n    ⚠️  HTML artifact team names still present: {artifact_teams}')
            print(f'       Fix: re-run preprocess.py (clean_string strips rn"> prefix)')
        else:
            print(f'    ✓ No HTML artifact team names detected')

        # Win conditions
        actual_wc   = set(self.df['Win_Conditions'].dropna().unique())
        invalid_wc  = actual_wc - VALID_WIN_CONDITIONS
        print(f'\n  ✓ Win_Conditions values:')
        print(f'    - Found   : {sorted(actual_wc)}')
        print(f'    - Expected: {sorted(VALID_WIN_CONDITIONS)}')
        if invalid_wc:
            print(f'    ⚠️  INVALID: {invalid_wc}')
        else:
            print(f'    ✓ All Win_Conditions values are valid')

        # Match Result values
        valid_results  = {'Home Win', 'Away Win', 'Draw'}
        invalid_results = set(self.df['Match_Result'].unique()) - valid_results
        print(f'\n  ✓ Match_Result values: {sorted(self.df["Match_Result"].unique())}')
        if invalid_results:
            print(f'    ⚠️  INVALID: {invalid_results}')
        else:
            print(f'    ✓ All Match_Result values are valid')

        # Lineup status
        if 'Is_Starter' in self.df.columns and 'Is_Substitute' in self.df.columns:
            valid_lineup = int((self.df['Is_Starter'] | self.df['Is_Substitute']).sum())
            print(f'\n  ✓ Lineup status (Is_Starter or Is_Substitute must be True):')
            print(f'    - Valid: {valid_lineup:,} / {len(self.df):,}')
            if valid_lineup == len(self.df):
                print(f'    ✓ All players correctly classified as starter or substitute')
            else:
                print(f'    ⚠️  {len(self.df) - valid_lineup} rows have neither flag set')

        self.report['referential_consistency'] = {
            'valid_years': not bool(invalid_years),
            'unique_teams': len(all_teams),
            'html_artifact_teams': artifact_teams,
            'valid_win_conditions': not bool(invalid_wc),
            'valid_match_results': not bool(invalid_results),
        }
        print()

    # ─── DATA CLEANING QUALITY ────────────────────────────────────────────────

    def check_data_cleaning_quality(self):
        print('🧹 DATA CLEANING QUALITY CHECK')
        print('-' * 80)

        str_cols = self.df.select_dtypes(include='object').columns

        # 1. HTML encoding artifacts (substring check is appropriate here)
        html_re   = re.compile(r'rn">|&[a-zA-Z]+;|&#\d+;|<[^>]+>')
        html_hits = []
        for col in str_cols:
            for val in self.df[col].dropna().unique():
                if isinstance(val, str) and html_re.search(val):
                    html_hits.append((col, val))
                    break
        print(f'  ✓ HTML encoding artifacts:')
        if html_hits:
            for col, sample in html_hits:
                print(f'    ⚠️  {col}: sample value = {repr(sample)}')
            print(f'       Fix: re-run preprocess.py — clean_string() handles rn"> and HTML entities')
        else:
            print(f'    ✓ None detected')

        # 2. Literal "nan"/"None"/"NULL" strings (exact match — not substring)
        sentinel_values = {'nan', 'None', 'NULL'}
        sentinel_hits   = []
        for col in str_cols:
            found = [v for v in self.df[col].dropna().unique()
                     if isinstance(v, str) and v.strip() in sentinel_values]
            if found:
                sentinel_hits.append((col, found[:3]))
        print(f'\n  ✓ Literal null-sentinel strings (exact "nan"/"None"/"NULL"):')
        if sentinel_hits:
            for col, samples in sentinel_hits:
                print(f'    ⚠️  {col}: {samples}')
            print(f'       Fix: re-run preprocess.py — replace("nan", np.nan) is already applied')
        else:
            print(f'    ✓ None detected')

        # 3. Numeric column dtype correctness
        numeric_cols   = ['Goals', 'Yellow_Cards', 'Red_Cards', 'Attendance', 'Total_Goals']
        non_numeric    = [c for c in numeric_cols
                          if c in self.df.columns and not pd.api.types.is_numeric_dtype(self.df[c])]
        print(f'\n  ✓ Numeric column dtypes:')
        if non_numeric:
            print(f'    ⚠️  Non-numeric: {non_numeric}')
        else:
            print(f'    ✓ All numeric columns have correct dtype')

        # 4. Leading / trailing whitespace in string columns
        leading_trailing = 0
        for col in str_cols:
            leading_trailing += int(
                self.df[col].astype(str).apply(lambda x: x != x.strip() and len(x.strip()) > 0).sum()
            )
        print(f'\n  ✓ Leading/trailing whitespace:')
        if leading_trailing == 0:
            print(f'    ✓ All string values are properly trimmed')
        else:
            print(f'    ⚠️  {leading_trailing:,} cells have leading/trailing whitespace')

        # 5. Key string column fill-rates
        key_str_cols = ['Home_Team', 'Away_Team', 'Player_Team', 'Stage_Std', 'Host_Country']
        print(f'\n  ✓ Key string column fill-rates:')
        for col in key_str_cols:
            if col in self.df.columns:
                empty = int(self.df[col].isna().sum() + (self.df[col] == '').sum())
                print(f'    - {col:<18}: {empty} empty')

        self.report['cleaning_quality'] = {
            'html_artifacts': len(html_hits) > 0,
            'sentinel_strings': len(sentinel_hits) > 0,
            'numeric_dtype_valid': not bool(non_numeric),
            'whitespace_trimmed': leading_trailing == 0,
        }
        print()

    # ─── DATA CONSISTENCY ─────────────────────────────────────────────────────

    def check_data_consistency(self):
        print('🎯 DATA CONSISTENCY CHECKS')
        print('-' * 80)

        year_valid = (self.df['Year'] >= 1930) & (self.df['Year'] <= 2026)
        print(f'  ✓ Year range ({self.df["Year"].min()}–{self.df["Year"].max()}):')
        print(f'    - Within 1930–2026: {year_valid.sum():,} / {len(self.df):,}')

        if 'Stage_Std' in self.df.columns:
            stage_valid   = self.df['Stage_Std'].isin(VALID_STAGES)
            invalid_stages = set(self.df['Stage_Std'].unique()) - VALID_STAGES
            print(f'\n  ✓ Stage_Std values:')
            print(f'    - Valid : {stage_valid.sum():,} / {len(self.df):,}')
            print(f'    - Found : {sorted(self.df["Stage_Std"].unique())}')
            if invalid_stages:
                print(f'    ⚠️  Unknown stages: {invalid_stages}')
            else:
                print(f'    ✓ All stage values match expected set')

        valid_results = {'Home Win', 'Away Win', 'Draw'}
        result_valid  = self.df['Match_Result'].isin(valid_results)
        print(f'\n  ✓ Match Results:')
        print(f'    - Valid : {result_valid.sum():,} / {len(self.df):,}')
        print(f'    - Found : {sorted(self.df["Match_Result"].unique())}')

        cards_valid = (self.df['Yellow_Cards'] >= 0) & (self.df['Red_Cards'] >= 0)
        print(f'\n  ✓ Card counts (non-negative):')
        print(f'    - Valid: {cards_valid.sum():,} / {len(self.df):,}')

        goals_valid = self.df['Goals'] >= 0
        print(f'\n  ✓ Player Goals (non-negative):')
        print(f'    - Valid: {goals_valid.sum():,} / {len(self.df):,}')

        attendance_valid = self.df['Attendance'] > 0
        print(f'\n  ✓ Attendance (> 0):')
        print(f'    - Valid: {attendance_valid.sum():,} / {len(self.df):,}')

        # Total_Goals is match-level (same per MatchID) — check on unique matches
        match_totals = self.df.drop_duplicates('MatchID')[['MatchID', 'Total_Goals']]
        print(f'\n  ✓ Total_Goals per match (unique-match basis):')
        print(f'    - Unique matches      : {len(match_totals):,}')
        print(f'    - Sum of match goals  : {int(match_totals["Total_Goals"].sum()):,}')
        print(f'    - Avg goals per match : {match_totals["Total_Goals"].mean():.2f}')

        all_valid = (year_valid & result_valid & cards_valid & goals_valid & attendance_valid).sum()
        print(f'\n  Overall row consistency: {all_valid:,} / {len(self.df):,} '
              f'({all_valid / len(self.df) * 100:.2f}%)')

        self.report['consistency'] = {
            'year_valid':       int(year_valid.sum()),
            'result_valid':     int(result_valid.sum()),
            'cards_valid':      int(cards_valid.sum()),
            'goals_valid':      int(goals_valid.sum()),
            'attendance_valid': int(attendance_valid.sum()),
            'overall_valid':    int(all_valid),
            'overall_pct':      round(all_valid / len(self.df) * 100, 2),
        }
        print()

    # ─── ANALYTICS METRICS (KPI) ──────────────────────────────────────────────

    def compute_analytics_metrics(self):
        """
        KPIs computed at correct grain:
          - Player-level stats   → aggregate over all rows (37,048)
          - Match-level stats    → deduplicate by MatchID first (836 unique matches)
          - Attendance / goals per match use the deduplicated match view
        """
        print('📈 ANALYTICS METRICS  (player-match grain)')
        print('-' * 80)
        print(f'  Dataset grain: {len(self.df):,} player appearances across '
              f'{self.df["MatchID"].nunique():,} unique matches\n')

        metrics = {}

        # ── Teams ──────────────────────────────────────────────────────────────
        unique_teams = set(self.df['Home_Team'].unique()) | set(self.df['Away_Team'].unique())
        print(f'  Teams              : {len(unique_teams)} unique nations')
        print(f'    - Unique home teams   : {self.df["Home_Team"].nunique()}')
        print(f'    - Unique away teams   : {self.df["Away_Team"].nunique()}')
        print(f'    - Unique player teams : {self.df["Player_Team"].nunique()}')
        metrics['unique_teams'] = len(unique_teams)

        # ── Venues ─────────────────────────────────────────────────────────────
        if 'City' in self.df.columns:
            venues = self.df['City'].nunique()
            print(f'\n  Venues             : {venues} unique cities')
            metrics['venues'] = venues

        # ── Tournaments ────────────────────────────────────────────────────────
        tournaments = self.df['Year'].nunique()
        year_range  = f"{self.df['Year'].min()}–{self.df['Year'].max()}"
        print(f'\n  Tournaments        : {tournaments} World Cups ({year_range})')
        print(f'    Years: {sorted(self.df["Year"].unique())}')
        metrics['tournaments'] = tournaments

        # ── Player appearances (primary grain) ─────────────────────────────────
        starters = int(self.df['Is_Starter'].sum()) if 'Is_Starter' in self.df.columns else 'N/A'
        subs     = int(self.df['Is_Substitute'].sum()) if 'Is_Substitute' in self.df.columns else 'N/A'
        unique_players = self.df['Player_Name'].nunique() if 'Player_Name' in self.df.columns else 'N/A'
        print(f'\n  Player Appearances : {len(self.df):,} total rows')
        print(f'    - Unique players      : {unique_players:,}')
        print(f'    - Starters            : {starters:,}')
        print(f'    - Substitutes         : {subs:,}')
        metrics['player_appearances'] = {
            'total': len(self.df),
            'unique_players': unique_players,
            'starters': starters,
            'substitutes': subs,
        }

        # ── Goals (player-attributed events) ───────────────────────────────────
        total_player_goals  = int(self.df['Goals'].sum())
        records_with_goals  = int((self.df['Goals'] > 0).sum())
        print(f'\n  Goals (player-attributed events):')
        print(f'    - Total attributed goals  : {total_player_goals:,}')
        print(f'    - Player-rows with goals  : {records_with_goals:,}')
        print(f'    Note: use Team_Goals_For for accurate scorelines (always correct).')
        metrics['goals'] = {
            'player_attributed_total': total_player_goals,
            'rows_with_goals': records_with_goals,
        }

        # ── Match-level KPIs (deduplicate by MatchID) ──────────────────────────
        matches_view = self.df.drop_duplicates(subset='MatchID')
        unique_match_count = len(matches_view)
        total_match_goals  = int(matches_view['Total_Goals'].sum())
        avg_goals_per_match = matches_view['Total_Goals'].mean()

        print(f'\n  Match-Level Statistics ({unique_match_count:,} unique matches):')
        print(f'    - Total goals (scoreline)  : {total_match_goals:,}')
        print(f'    - Avg goals per match      : {avg_goals_per_match:.2f}')
        metrics['match_goals'] = {
            'unique_matches': unique_match_count,
            'total_scoreline_goals': total_match_goals,
            'avg_per_match': round(avg_goals_per_match, 2),
        }

        # ── Disciplinary ───────────────────────────────────────────────────────
        total_yellows      = int(self.df['Yellow_Cards'].sum())
        total_reds         = int(self.df['Effective_Red_Cards'].sum()) if 'Effective_Red_Cards' in self.df.columns else int(self.df['Red_Cards'].sum())
        records_w_yellow   = int((self.df['Yellow_Cards'] > 0).sum())
        records_w_red      = int((self.df['Red_Cards'] > 0).sum())
        print(f'\n  Disciplinary Statistics:')
        print(f'    - Total yellow cards      : {total_yellows:,}')
        print(f'    - Total effective reds    : {total_reds:,}')
        print(f'    - Player-rows with yellow : {records_w_yellow:,}')
        print(f'    - Player-rows with red    : {records_w_red:,}')
        metrics['cards'] = {
            'yellows': total_yellows, 'effective_reds': total_reds,
            'rows_with_yellow': records_w_yellow, 'rows_with_red': records_w_red,
        }

        # ── Match outcomes (dedup by MatchID — count unique matches, not rows) ──
        home_wins    = int((matches_view['Match_Result'] == 'Home Win').sum())
        away_wins    = int((matches_view['Match_Result'] == 'Away Win').sum())
        draws        = int((matches_view['Match_Result'] == 'Draw').sum())
        home_win_pct = home_wins / unique_match_count * 100
        print(f'\n  Match Outcomes ({unique_match_count:,} unique matches):')
        print(f'    - Home Wins : {home_wins:,}  ({home_win_pct:.1f}%)')
        print(f'    - Away Wins : {away_wins:,}')
        print(f'    - Draws     : {draws:,}')
        metrics['match_outcomes'] = {
            'unique_matches': unique_match_count,
            'home_wins': home_wins, 'away_wins': away_wins, 'draws': draws,
            'home_win_pct': round(home_win_pct, 1),
        }

        # ── Attendance (per unique match) ───────────────────────────────────────
        avg_att = matches_view['Attendance'].mean()
        max_att = int(matches_view['Attendance'].max())
        min_att = int(matches_view['Attendance'].min())
        print(f'\n  Attendance (per unique match):')
        print(f'    - Average : {avg_att:,.0f}')
        print(f'    - Maximum : {max_att:,}')
        print(f'    - Minimum : {min_att:,}')
        metrics['attendance'] = {
            'average': round(avg_att), 'maximum': max_att, 'minimum': min_att,
        }

        self.report['analytics_metrics'] = metrics
        print()

    # ─── SUMMARY ──────────────────────────────────────────────────────────────

    def print_summary(self):
        print('='*80)
        print('✅ DATA VALIDATION COMPLETE')
        print('='*80)
        passed = self._count_passed_checks()
        total  = self._count_total_checks()
        print(f'\n  Dataset grain  : player-match (one row per player per match appearance)')
        print(f'  Total Records  : {len(self.df):,}  player appearances')
        print(f'  Unique Matches : {self.df["MatchID"].nunique():,}')
        print(f'  Quality Checks : {passed}/{total} passed')
        print(f'\n  Next Steps:')
        print(f'    1. Run scripts/preprocess.py if any cleaning issues were flagged above')
        print(f'    2. Run scripts/05_kpi_tableau_prep.py to regenerate Tableau KPI files')
        print(f'    3. Load tableau/ files into Tableau for visualization')
        print(f'    4. Run EDA notebook: scripts/03_eda.py')
        print('\n')

    def _count_passed_checks(self):
        count = 0
        if self.report.get('nulls', {}).get('complete'):
            count += 1
        if self.report.get('duplicates', {}).get('is_clean'):
            count += 1
        if self.report.get('join_integrity', {}).get('orphaned_records') == 0:
            count += 1
        if self.report.get('referential_consistency', {}).get('valid_match_results'):
            count += 1
        if self.report.get('cleaning_quality', {}).get('whitespace_trimmed'):
            count += 1
        return count

    def _count_total_checks(self):
        return 5


def main():
    processed_file = Path('data/processed/wc_players_combined.csv')

    if not processed_file.exists():
        print(f'❌ ERROR: {processed_file} not found!')
        print('   Run: python scripts/preprocess.py')
        return

    validator = DataValidator(processed_file)
    report    = validator.validate_all()
    return report


if __name__ == '__main__':
    main()
