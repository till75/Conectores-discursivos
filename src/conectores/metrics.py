"""Metric definitions for the metric-replay slice.

The functions here reproduce the notebook's metric definitions without
importing the notebook. The replay CLI and the candidate construction live in
later slices.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

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
