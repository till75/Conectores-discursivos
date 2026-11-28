"""End-to-end publication pipeline for S6."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd

from conectores.baselines import baseline_predictions
from conectores.candidates import build_candidates
from conectores.features import Embedder
from conectores.metrics import replay
from conectores.models import replay_m1, replay_m2
from conectores.rules import NLP

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


@dataclass(frozen=True)
class PipelineResult:
    """The rebuilt publication tables and the privacy count."""

    predictions: pd.DataFrame
    systems: pd.DataFrame
    summary: pd.DataFrame
    intervals: pd.DataFrame
    diagnostics: pd.DataFrame
    traceability: Mapping[str, int]
    deviations: list[str]
    privacy_mentions: int


def _privacy_mentions(frame: pd.DataFrame) -> int:
    pattern = re.compile(r"@(?!USER\b)\w+")
    return sum(
        len(pattern.findall(value))
        for value in frame.to_numpy().ravel()
        if isinstance(value, str)
    )


def run_pipeline(
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
    test_files: Mapping[int, str],
    hashes: Mapping[str, str],
    published: Mapping[str, pd.DataFrame],
    embedder: Embedder,
    nlp: NLP,
    n_bootstrap: int = 1000,
) -> PipelineResult:
    """Rebuild the public prediction and metric tables from the inputs."""
    candidate_set = build_candidates(reference, listing, csl)
    test_ids = {
        seed: text.split() for seed, text in test_files.items()
    }
    baselines = baseline_predictions(
        candidate_set.candidates, reference, listing, test_ids
    )
    m1_result = replay_m1(
        candidate_set,
        reference,
        listing,
        test_ids,
        {},
        embedder,
    )
    m2_result = replay_m2(
        candidate_set,
        reference,
        listing,
        test_ids,
        {},
        embedder,
        nlp,
    )
    predictions = combine_predictions(
        baselines, m1_result.predictions, m2_result.predictions
    )
    margins = {}
    for seed, margin in m1_result.margins.items():
        margins[(seed, "M1 con abstención")] = margin
    for seed, margin in m2_result.margins.items():
        margins[(seed, "M2 con abstención")] = margin
    replay_result = replay(
        predictions,
        reference,
        listing,
        csl,
        published,
        hashes,
        test_files,
        n=n_bootstrap,
        margins=margins,
    )
    return PipelineResult(
        predictions=predictions,
        systems=replay_result.systems,
        summary=replay_result.summary,
        intervals=replay_result.intervals,
        diagnostics=replay_result.diagnostics,
        traceability=replay_result.traceability,
        deviations=replay_result.deviations,
        privacy_mentions=_privacy_mentions(predictions),
    )


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
