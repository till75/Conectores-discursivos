"""Metric definitions for the metric-replay slice.

The functions here reproduce the notebook's metric definitions without
importing the notebook. The replay CLI and the candidate construction live in
later slices.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd

NO = "NO_DISCURSIVO"
LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"
ETIQ = re.compile(r"\[([^\[\]]+?)::([^\[\]]+)\]")


@dataclass(frozen=True)
class Metrics:
    """The five metrics the published table reports for one system and seed."""

    f1_label: float
    f1_discourse: float
    f1_macro: float
    precision: float
    coverage: float


def _macro(label: str) -> str:
    """Return CON, OP or NO for a project label."""
    return label.split(":")[0] if label != NO else NO


def _f1(tp: int, predicted: int, gold: int) -> float:
    """Harmonic mean of precision and recall; zero when there is no match."""
    return 0.0 if tp == 0 else 2 * tp / (predicted + gold)


def compute_metrics(
    gold: Sequence[str], pred: Sequence[str], n_undetected: int
) -> Metrics:
    """Return the five metrics for one system and one test split."""
    pairs = list(zip(gold, pred, strict=True))
    tp = sum(g == p != NO for g, p in pairs)
    predicted = sum(p != NO for p in pred)
    gold_total = sum(g != NO for g in gold) + n_undetected
    tp_discourse = sum(g != NO and p != NO for g, p in pairs)

    macro_scores = []
    for macro in ("CON", "OP"):
        hits = sum(_macro(g) == _macro(p) == macro for g, p in pairs)
        predicted_macro = sum(_macro(p) == macro for p in pred)
        gold_macro = sum(_macro(g) == macro for g in gold)
        macro_scores.append(_f1(hits, predicted_macro, gold_macro))

    return Metrics(
        f1_label=_f1(tp, predicted, gold_total),
        f1_discourse=_f1(tp_discourse, predicted, gold_total),
        f1_macro=sum(macro_scores) / len(macro_scores),
        precision=tp / predicted if predicted else 0.0,
        coverage=tp / gold_total if gold_total else 0.0,
    )


def _normalise_label(label: str) -> str:
    """Apply the project's label normalisation."""
    label = label.strip().upper()
    if label.startswith("CON:REFORMULATIVO"):
        return "CON:REFORMULATIVOS"
    return label.replace("CON:ORDENADOR:", "CON:").replace("CON:ORDENADORES:", "CON:")


def _read_annotation(
    annotation: object,
) -> tuple[str | None, list[tuple[int, int, str, str]]]:
    """Return the plain text and the ``[unidad::ETIQUETA]`` spans."""
    if not isinstance(annotation, str) or "::" not in annotation:
        return None, []
    plain, spans, pos = "", [], 0
    for match in ETIQ.finditer(annotation):
        plain += annotation[pos : match.start()]
        start = len(plain)
        plain += match.group(1)
        spans.append(
            (start, len(plain), match.group(1), _normalise_label(match.group(2)))
        )
        pos = match.end()
    plain += annotation[pos:]
    return plain, spans


def _listing_pattern(listing: pd.DataFrame) -> re.Pattern[str]:
    """Build the case-insensitive, longest-first listing pattern."""
    forms = (
        listing["unidad"]
        .astype(str)
        .str.replace(r"\s*\d+$", "", regex=True)
        .str.strip()
        .str.lower()
    )
    forms = sorted(set(forms), key=len, reverse=True)
    if not forms:
        return re.compile(r"(?!)")
    return re.compile(
        rf"(?<!{LETRA})("
        + "|".join(re.escape(form) for form in forms)
        + rf")(?!{LETRA})",
        re.I,
    )


def undetected_labels(
    reference: pd.DataFrame, listing: pd.DataFrame, csl: pd.DataFrame
) -> pd.DataFrame:
    """Return the reference spans the listing never matches."""
    csl_set = set(zip(csl["comment_id"], csl["unidad"], strict=True))
    pattern = _listing_pattern(listing)
    rows = []
    for row in reference.itertuples():
        plain, spans = _read_annotation(row.anotacion)
        if plain is None:
            continue
        spans = [span for span in spans if (row.comment_id, span[2]) not in csl_set]
        matches = [(match.start(), match.end()) for match in pattern.finditer(plain)]
        for start, end, unit, label in spans:
            if not any(
                start < match_end and match_start < end
                for match_start, match_end in matches
            ):
                rows.append(
                    {
                        "comment_id": row.comment_id,
                        "thread_id": row.thread_id,
                        "unidad": unit,
                        "oro": label,
                    }
                )
    return pd.DataFrame(rows, columns=["comment_id", "thread_id", "unidad", "oro"])


def bootstrap_difference(
    gold: Sequence[str],
    pred_a: Sequence[str],
    pred_b: Sequence[str],
    thread_id: Sequence[str],
    n_undetected_by_thread: Mapping[str, int],
    n: int = 1000,
    seed: int = 0,
) -> tuple[float, float]:
    """Return the 95% interval of the F1 difference, resampling threads."""
    rng = np.random.default_rng(seed)
    threads = list(dict.fromkeys(thread_id))
    indices_by_thread = {
        thread: [index for index, value in enumerate(thread_id) if value == thread]
        for thread in threads
    }
    differences = []
    for _ in range(n):
        sample = rng.choice(len(threads), size=len(threads), replace=True)
        chosen = [threads[index] for index in sample]
        indices = [index for thread in chosen for index in indices_by_thread[thread]]
        undetected = sum(n_undetected_by_thread.get(thread, 0) for thread in chosen)
        gold_sample = [gold[index] for index in indices]
        a_sample = [pred_a[index] for index in indices]
        b_sample = [pred_b[index] for index in indices]
        f1_a = compute_metrics(gold_sample, a_sample, undetected).f1_label
        f1_b = compute_metrics(gold_sample, b_sample, undetected).f1_label
        differences.append(f1_a - f1_b)
    return tuple(float(value) for value in np.percentile(differences, [2.5, 97.5]))


def replay_systems(
    predictions: pd.DataFrame,
    margins: Mapping[tuple[int, str], float],
    undetected_by_seed: Mapping[int, int],
) -> pd.DataFrame:
    """Return the six system rows for each seed."""
    rows = []
    for seed, group in predictions.groupby("semilla", sort=True):
        n_undetected = undetected_by_seed.get(seed, 0)
        for system in ("B0", "B1", "M1", "M2"):
            metrics = compute_metrics(group["oro"], group[system], n_undetected)
            rows.append(
                {
                    "sistema": system,
                    "semilla": seed,
                    "F1_etiqueta": metrics.f1_label,
                    "F1_uso_discursivo": metrics.f1_discourse,
                    "F1_macro_CON_OP": metrics.f1_macro,
                    "precision_etiqueta": metrics.precision,
                    "cobertura_etiqueta": metrics.coverage,
                    "abstencion": np.nan,
                    "margen": np.nan,
                }
            )
        for system, probability, flag in (
            ("M1 con abstención", "p_M1", None),
            ("M2 con abstención", "p_M2", "abstiene_M2"),
        ):
            margin = margins[(seed, system)]
            if flag is None:
                abstention = (group[probability] - 0.5).abs() < margin
            else:
                abstention = group[flag].astype(bool)
            kept = group[~abstention]
            metrics = compute_metrics(
                kept["oro"], kept[system.replace(" con abstención", "")], n_undetected
            )
            rows.append(
                {
                    "sistema": system,
                    "semilla": seed,
                    "F1_etiqueta": metrics.f1_label,
                    "F1_uso_discursivo": metrics.f1_discourse,
                    "F1_macro_CON_OP": metrics.f1_macro,
                    "precision_etiqueta": metrics.precision,
                    "cobertura_etiqueta": metrics.coverage,
                    "abstencion": float(abstention.mean()),
                    "margen": margin,
                }
            )
    return pd.DataFrame(rows)


SUMMARY_METRICS = [
    "F1_etiqueta",
    "F1_uso_discursivo",
    "F1_macro_CON_OP",
    "precision_etiqueta",
    "cobertura_etiqueta",
]


def summary_systems(systems: pd.DataFrame) -> pd.DataFrame:
    """Return the mean and sample standard deviation for each system."""
    grouped = systems.groupby("sistema", sort=False)[SUMMARY_METRICS]
    summary = grouped.agg(["mean", "std"]).reset_index()
    summary.columns = ["sistema"] + [
        f"{metric}_{stat}" for metric in SUMMARY_METRICS for stat in ("mean", "std")
    ]
    return summary


COMPARISONS = [("M2", "B1"), ("M2", "M1"), ("M1", "B1")]


def replay_intervals(
    predictions: pd.DataFrame,
    undetected_by_thread: Mapping[int, Mapping[str, int]],
    n: int = 1000,
) -> pd.DataFrame:
    """Return the 95% interval for each comparison and seed."""
    rows = []
    for seed in sorted(predictions["semilla"].unique()):
        group = predictions[predictions["semilla"] == seed]
        n_undetected = undetected_by_thread.get(int(seed), {})
        for system_a, system_b in COMPARISONS:
            low, high = bootstrap_difference(
                group["oro"].tolist(),
                group[system_a].tolist(),
                group[system_b].tolist(),
                group["thread_id"].tolist(),
                n_undetected,
                n=n,
                seed=int(seed),
            )
            rows.append(
                {
                    "comparacion": f"{system_a} − {system_b}",
                    "semilla": int(seed),
                    "IC_inf": low,
                    "IC_sup": high,
                    "excluye_cero": low > 0 or high < 0,
                }
            )
    return pd.DataFrame(rows)


def _format_key(keys: Sequence[str], key: object) -> str:
    """Format a row key as ``sistema=B0, semilla=0``."""
    if len(keys) == 1:
        return f"{keys[0]}={key}"
    return ", ".join(
        f"{name}={value}" for name, value in zip(keys, key, strict=True)
    )


def _values_differ(expected: object, actual: object, decimals: int) -> bool:
    """Compare two cells, treating NaN as equal and rounding numbers."""
    expected_missing = pd.isna(expected)
    actual_missing = pd.isna(actual)
    if expected_missing and actual_missing:
        return False
    if expected_missing or actual_missing:
        return True
    if isinstance(expected, (bool, np.bool_)) or isinstance(actual, (bool, np.bool_)):
        return bool(expected) != bool(actual)
    try:
        return abs(
            round(float(expected), decimals) - round(float(actual), decimals)
        ) > 1e-9
    except (TypeError, ValueError):
        return expected != actual


def compare_tables(
    replayed: pd.DataFrame,
    published: pd.DataFrame,
    key_columns: Sequence[str],
    decimals: int = 3,
) -> list[str]:
    """Return one named deviation per mismatched cell."""
    keys = list(key_columns)
    value_columns = [column for column in published.columns if column not in keys]
    replayed_by_key = replayed.set_index(keys)
    published_by_key = published.set_index(keys)
    deviations = []
    for key, expected_row in published_by_key.iterrows():
        if key not in replayed_by_key.index:
            deviations.append(f"{_format_key(keys, key)}: missing from replay")
            continue
        actual_row = replayed_by_key.loc[key]
        for column in value_columns:
            expected = expected_row[column]
            actual = actual_row[column]
            if _values_differ(expected, actual, decimals):
                deviations.append(
                    f"{_format_key(keys, key)}, {column}: "
                    f"replay {actual!r} != published {expected!r}"
                )
    return deviations
