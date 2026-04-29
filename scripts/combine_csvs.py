"""
combine_csvs.py — Utility to combine multiple CSV files into one dataset.

Use this when you have several CSV files with the same columns and want one
merged CSV output.

Example:
    python scripts/combine_csvs.py \
        --input-dir data/raw/splits \
        --output data/processed/combined.csv \
        --recursive --drop-duplicates
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Combine multiple CSV files into a single CSV.')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--input-dir', help='Directory containing CSV files to combine')
    group.add_argument('--input-files', nargs='+', help='List of CSV files to combine')
    parser.add_argument('--output', required=True, help='Path for the combined CSV output')
    parser.add_argument('--recursive', action='store_true', help='Search for CSV files recursively in the input directory')
    parser.add_argument('--drop-duplicates', action='store_true', help='Drop exact duplicate rows after combining')
    return parser.parse_args()


def collect_csv_files(input_dir: str | None, input_files: list[str] | None, recursive: bool) -> list[Path]:
    if input_files:
        files = [Path(path) for path in input_files]
    else:
        directory = Path(input_dir)
        pattern = '**/*.csv' if recursive else '*.csv'
        files = sorted(directory.glob(pattern))

    files = [path for path in files if path.exists() and path.suffix.lower() == '.csv']
    if not files:
        raise FileNotFoundError('No CSV files were found to combine.')
    return files


def combine_csv_files(csv_files: list[Path], drop_duplicates: bool = False) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    expected_columns: list[str] | None = None

    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        if expected_columns is None:
            expected_columns = list(df.columns)
        elif list(df.columns) != expected_columns:
            raise ValueError(
                f'Column mismatch in {csv_file}. Expected {expected_columns}, got {list(df.columns)}'
            )
        frames.append(df)

    combined = pd.concat(frames, ignore_index=True)
    if drop_duplicates:
        combined = combined.drop_duplicates().reset_index(drop=True)
    return combined


def main() -> None:
    args = parse_args()
    csv_files = collect_csv_files(args.input_dir, args.input_files, args.recursive)

    print(f'Combining {len(csv_files)} CSV files...')
    for file in csv_files:
        print(f'  - {file}')

    combined = combine_csv_files(csv_files, drop_duplicates=args.drop_duplicates)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output_path, index=False)

    print('\nCombine complete')
    print(f'  Rows: {len(combined):,}')
    print(f'  Columns: {combined.shape[1]}')
    print(f'  Saved to: {output_path}')


if __name__ == '__main__':
    main()
