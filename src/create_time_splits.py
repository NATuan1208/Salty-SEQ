"""Create leakage-safe temporal splits for SaltySeq panel data."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

from src.pipeline_config import (
    HOLDOUT_END_DATE,
    HOLDOUT_START_DATE,
    OUTPUT_DIR,
    START_DATE,
    TRAIN_END_DATE,
)

INPUT_FILE = OUTPUT_DIR / "merged_final.csv"
SPLIT_DIR = OUTPUT_DIR / "splits"
FOLD_DIR = SPLIT_DIR / "folds"

LOGGER = logging.getLogger("saltyseq.splits")


def configure_logging() -> None:
    """Configure logger for script execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def _validate_columns(df: pd.DataFrame) -> None:
    required = {"date", "location_id", "is_stress_event"}
    missing = sorted(required - set(df.columns))
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Input dataset is missing required columns: {joined}")


def load_dataset(path: Path) -> pd.DataFrame:
    """Load merged panel dataset and run baseline integrity checks."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    df = pd.read_csv(path, parse_dates=["date"])
    _validate_columns(df)
    df = df.sort_values(["location_id", "date"]).reset_index(drop=True)

    if df.duplicated(subset=["location_id", "date"]).any():
        raise ValueError("Duplicate key rows detected for location_id + date")

    return df


def _save_panel(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    LOGGER.info("Saved %s rows -> %s", len(df), path)


def split_train_holdout(
    df: pd.DataFrame,
    allow_empty_holdout: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split panel into train universe and final holdout by configured date bounds."""
    train_mask = (df["date"] >= pd.Timestamp(START_DATE)) & (
        df["date"] <= pd.Timestamp(TRAIN_END_DATE)
    )
    holdout_mask = (df["date"] >= pd.Timestamp(HOLDOUT_START_DATE)) & (
        df["date"] <= pd.Timestamp(HOLDOUT_END_DATE)
    )

    train_df = df.loc[train_mask].copy()
    holdout_df = df.loc[holdout_mask].copy()

    if train_df.empty:
        raise ValueError("Train split is empty. Check configured date boundaries.")

    if holdout_df.empty and not allow_empty_holdout:
        raise ValueError(
            "Holdout split is empty. Rerun pipeline with extended date range or use --allow-empty-holdout."
        )

    return train_df, holdout_df


def build_expanding_folds(train_df: pd.DataFrame, n_splits: int) -> pd.DataFrame:
    """Build year-based expanding-window fold manifest for time-series CV."""
    years = sorted(train_df["date"].dt.year.unique().tolist())
    min_years_needed = n_splits + 3
    if len(years) < min_years_needed:
        raise ValueError(
            f"Need at least {min_years_needed} train years for {n_splits} splits, got {len(years)}"
        )

    val_years = years[-n_splits:]
    base_year = years[0]

    rows: list[dict] = []
    for idx, val_year in enumerate(val_years, start=1):
        train_end_year = val_year - 1
        fold_train = train_df[
            (train_df["date"].dt.year >= base_year)
            & (train_df["date"].dt.year <= train_end_year)
        ].copy()
        fold_val = train_df[train_df["date"].dt.year == val_year].copy()

        if fold_train.empty or fold_val.empty:
            raise ValueError(f"Fold {idx} is empty. Check split construction logic.")

        train_loc = fold_train["location_id"].nunique()
        val_loc = fold_val["location_id"].nunique()

        train_path = FOLD_DIR / f"fold_{idx:02d}_train.csv"
        val_path = FOLD_DIR / f"fold_{idx:02d}_val.csv"
        _save_panel(fold_train, train_path)
        _save_panel(fold_val, val_path)

        rows.append(
            {
                "fold": idx,
                "train_start_year": base_year,
                "train_end_year": train_end_year,
                "val_year": val_year,
                "train_rows": len(fold_train),
                "val_rows": len(fold_val),
                "train_locations": train_loc,
                "val_locations": val_loc,
                "train_pos_rate_pct": round(fold_train["is_stress_event"].mean() * 100, 4),
                "val_pos_rate_pct": round(fold_val["is_stress_event"].mean() * 100, 4),
            }
        )

    manifest = pd.DataFrame(rows)
    return manifest


def main() -> None:
    """Generate split artifacts for XGBoost and SPM workflows."""
    parser = argparse.ArgumentParser(description="Create temporal splits for SaltySeq panel data.")
    parser.add_argument(
        "--input",
        type=Path,
        default=INPUT_FILE,
        help="Path to merged panel csv (default: data/merged_final.csv)",
    )
    parser.add_argument(
        "--n-splits",
        type=int,
        default=5,
        help="Number of expanding-window validation folds (default: 5)",
    )
    parser.add_argument(
        "--allow-empty-holdout",
        action="store_true",
        help="Allow split creation even when 2023-2025 rows are not present.",
    )
    args = parser.parse_args()

    configure_logging()
    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    FOLD_DIR.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading dataset: %s", args.input)
    df = load_dataset(args.input)
    LOGGER.info(
        "Loaded rows=%s | locations=%s | range=%s -> %s",
        len(df),
        df["location_id"].nunique(),
        df["date"].min().date(),
        df["date"].max().date(),
    )

    train_df, holdout_df = split_train_holdout(df, args.allow_empty_holdout)
    _save_panel(train_df, SPLIT_DIR / "train_2015_2022.csv")
    _save_panel(holdout_df, SPLIT_DIR / "holdout_test_2023_2025.csv")

    manifest = build_expanding_folds(train_df, args.n_splits)
    manifest.to_csv(SPLIT_DIR / "fold_manifest.csv", index=False)
    LOGGER.info("Saved fold manifest -> %s", SPLIT_DIR / "fold_manifest.csv")

    summary = pd.DataFrame(
        [
            {
                "dataset": "train_2015_2022",
                "rows": len(train_df),
                "locations": train_df["location_id"].nunique(),
                "start": train_df["date"].min().date().isoformat(),
                "end": train_df["date"].max().date().isoformat(),
                "positive_rate_pct": round(train_df["is_stress_event"].mean() * 100, 4),
            },
            {
                "dataset": "holdout_test_2023_2025",
                "rows": len(holdout_df),
                "locations": holdout_df["location_id"].nunique() if not holdout_df.empty else 0,
                "start": holdout_df["date"].min().date().isoformat() if not holdout_df.empty else "NA",
                "end": holdout_df["date"].max().date().isoformat() if not holdout_df.empty else "NA",
                "positive_rate_pct": round(holdout_df["is_stress_event"].mean() * 100, 4)
                if not holdout_df.empty
                else 0.0,
            },
        ]
    )
    summary.to_csv(SPLIT_DIR / "split_summary.csv", index=False)
    LOGGER.info("Saved split summary -> %s", SPLIT_DIR / "split_summary.csv")

    LOGGER.info("Split generation complete.")


if __name__ == "__main__":
    main()
