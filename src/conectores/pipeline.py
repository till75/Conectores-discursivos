"""End-to-end publication pipeline for S6."""

from __future__ import annotations

import pandas as pd

PIPELINE_COLUMNS = [
    "comment_id",
    "thread_id",
    "semilla",
    "unidad",
    "inicio",
    "oro",
    "B0",
    "B1",
    "M1",
    "M2",
    "p_M1",
    "p_M2",
    "origen_M2",
    "revisar_categoria",
    "abstiene_M2",
]


MERGE_KEYS = ["semilla", "comment_id", "unidad", "inicio"]


def _format_key(row: pd.Series) -> str:
    return ", ".join(f"{key}={row[key]}" for key in MERGE_KEYS)


def combine_predictions(
    baselines: pd.DataFrame,
    m1: pd.DataFrame,
    m2: pd.DataFrame,
) -> pd.DataFrame:
    """Merge the system predictions into the public 15-column frame."""
    merged = baselines.merge(
        m1,
        on=MERGE_KEYS,
        how="outer",
        suffixes=("", "_m1"),
        indicator="_merge_m1",
    )
    merged = merged.merge(
        m2,
        on=MERGE_KEYS,
        how="outer",
        suffixes=("", "_m2"),
        indicator="_merge_m2",
    )
    for _, row in merged.iterrows():
        key = _format_key(row)
        if row["_merge_m1"] != "both" or row["_merge_m2"] != "both":
            raise ValueError(f"predictions are missing a key: {key}")
        if row["oro"] != row["oro_m1"] or row["oro"] != row["oro_m2"]:
            raise ValueError(f"predictions disagree on oro: {key}")
        if (
            row["thread_id"] != row["thread_id_m1"]
            or row["thread_id"] != row["thread_id_m2"]
        ):
            raise ValueError(f"predictions disagree on thread_id: {key}")
    return merged.sort_values(MERGE_KEYS).reset_index(drop=True)[
        PIPELINE_COLUMNS
    ]
