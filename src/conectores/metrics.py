"""Metric definitions for the metric-replay slice.

The functions here reproduce the notebook's metric definitions without
importing the notebook. The replay CLI and the candidate construction live in
later slices.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

NO = "NO_DISCURSIVO"


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
