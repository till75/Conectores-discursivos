"""B0 and B1 baselines for the baseline-replay slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import pandas as pd

from conectores.candidates import NO, CandidateSet
from conectores.metrics import (
    compare_tables,
    compute_metrics,
    count_undetected,
    summary_systems,
)

METRIC_COLUMNS = [
    "F1_etiqueta",
    "F1_uso_discursivo",
    "F1_macro_CON_OP",
    "precision_etiqueta",
    "cobertura_etiqueta",
]


@dataclass(frozen=True)
class BaselineResult:
    """The rebuilt baselines and their deviations from the published tables."""

    predictions: pd.DataFrame
    metrics: pd.DataFrame
    summary: pd.DataFrame
    deviations: list[str]


def _require(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    """Raise when a required column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"{name} is missing required column: {column}")


def _text(value: object) -> str:
    """Return a stripped string, treating a missing value as empty."""
    return value.strip() if isinstance(value, str) else ""


def listing_label(macro: object, categoria: object, subcategoria: object) -> str:
    """Map one listing row to one project label."""
    categoria = _text(categoria)
    subcategoria = _text(subcategoria)
    if macro == "Operador":
        return "OP:" + categoria.upper()
    if categoria.startswith("Ordenador"):
        return "CON:" + (
            "INICIO" if subcategoria == "De inicio" else subcategoria.upper()
        )
    if categoria.startswith("Reformulativo"):
        return "CON:REFORMULATIVOS"
    return "CON:" + categoria.upper()


def listing_label_map(listing: pd.DataFrame) -> dict[str, list[str]]:
    """Return each listing form's distinct labels in listing row order."""
    _require(
        listing,
        ["unidad", "macrofuncion", "categoria", "subcategoria"],
        "listing",
    )
    forms = (
        listing["unidad"]
        .astype(str)
        .str.replace(r"\s*\d+$", "", regex=True)
        .str.strip()
        .str.lower()
    )
    labels: dict[str, list[str]] = {}
    for form, macro, categoria, subcategoria in zip(
        forms,
        listing["macrofuncion"],
        listing["categoria"],
        listing["subcategoria"],
        strict=True,
    ):
        bucket = labels.setdefault(form, [])
        label = listing_label(macro, categoria, subcategoria)
        if label not in bucket:
            bucket.append(label)
    return labels


def b0_predict(
    test: pd.DataFrame, labels: Mapping[str, Sequence[str]]
) -> list[str]:
    """Label each test row with the first listing label for its form."""
    _require(test, ["unidad"], "test")
    return [labels.get(form, [NO])[0] for form in test["unidad"]]


def _majority(values: pd.Series) -> str:
    """Return the most frequent label, breaking ties by first occurrence."""
    counts = values.value_counts()
    top = counts.iloc[0]
    tied = set(counts[counts == top].index)
    return next(label for label in values if label in tied)


def b1_predict(train: pd.DataFrame, test: pd.DataFrame) -> list[str]:
    """Label each test row with the form's most frequent training label."""
    _require(train, ["unidad", "oro"], "train")
    _require(test, ["unidad", "oro"], "test")
    if train.empty:
        raise ValueError("train is empty")
    majority = {
        form: _majority(group["oro"])
        for form, group in train.groupby("unidad", sort=False)
    }
    global_label = _majority(train["oro"])
    return [majority.get(form, global_label) for form in test["unidad"]]


BASELINE_COLUMNS = [
    "semilla",
    "comment_id",
    "thread_id",
    "unidad",
    "inicio",
    "oro",
    "B0",
    "B1",
]


def baseline_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
) -> pd.DataFrame:
    """Return B0 and B1 for every test candidate in each frozen split."""
    _require(
        candidates,
        ["comment_id", "thread_id", "unidad", "oro", "inicio"],
        "candidates",
    )
    _require(reference, ["comment_id", "thread_id"], "reference")
    labels = listing_label_map(listing)
    comment_to_thread = dict(
        zip(reference["comment_id"], reference["thread_id"], strict=True)
    )
    frames = []
    for seed, ids in test_ids.items():
        threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        test = candidates[candidates["thread_id"].isin(threads)]
        train = candidates[~candidates["thread_id"].isin(threads)]
        if test.empty:
            continue
        frames.append(
            test.assign(
                semilla=int(seed),
                B0=b0_predict(test, labels),
                B1=b1_predict(train, test),
            )
        )
    if not frames:
        return pd.DataFrame(columns=BASELINE_COLUMNS)
    return pd.concat(frames, ignore_index=True)[BASELINE_COLUMNS]


def _format_key(keys: Sequence[str], key: Sequence[object]) -> str:
    """Format a row key as ``semilla=0, comment_id=c1``."""
    return ", ".join(
        f"{name}={value}" for name, value in zip(keys, key, strict=True)
    )


def _compare_predictions(
    rebuilt: pd.DataFrame, published: pd.DataFrame
) -> list[str]:
    """Return one named deviation per missing row or changed prediction."""
    keys = ["semilla", "comment_id", "unidad", "inicio"]
    values = ["oro", "B0", "B1"]
    merged = rebuilt.merge(
        published,
        on=keys,
        how="outer",
        suffixes=("_replay", "_published"),
        indicator=True,
    )
    deviations = []
    for _, row in merged.iterrows():
        key = _format_key(keys, tuple(row[column] for column in keys))
        if row["_merge"] == "left_only":
            deviations.append(f"{key}: missing from published")
            continue
        if row["_merge"] == "right_only":
            deviations.append(f"{key}: missing from replay")
            continue
        for column in values:
            actual = row[f"{column}_replay"]
            expected = row[f"{column}_published"]
            if actual != expected:
                deviations.append(
                    f"{key}, {column}: replay {actual!r} != published {expected!r}"
                )
    return deviations


def replay_baselines(
    candidate_set: CandidateSet,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    published: Mapping[str, pd.DataFrame],
) -> BaselineResult:
    """Rebuild B0 and B1 and compare them with the published tables."""
    predictions = baseline_predictions(
        candidate_set.candidates, reference, listing, test_ids
    )
    totals, _ = count_undetected(candidate_set.undetected, reference, test_ids)
    rows = []
    for seed, group in predictions.groupby("semilla", sort=True):
        for system in ("B0", "B1"):
            metrics = compute_metrics(
                group["oro"], group[system], totals.get(int(seed), 0)
            )
            rows.append(
                {
                    "sistema": system,
                    "semilla": int(seed),
                    "F1_etiqueta": metrics.f1_label,
                    "F1_uso_discursivo": metrics.f1_discourse,
                    "F1_macro_CON_OP": metrics.f1_macro,
                    "precision_etiqueta": metrics.precision,
                    "cobertura_etiqueta": metrics.coverage,
                    "abstencion": float("nan"),
                    "margen": float("nan"),
                }
            )
    metrics_frame = pd.DataFrame(
        rows,
        columns=["sistema", "semilla", *METRIC_COLUMNS, "abstencion", "margen"],
    )
    summary = summary_systems(metrics_frame)

    deviations = []
    published_predictions = published.get("predictions")
    if published_predictions is not None and not published_predictions.empty:
        deviations.extend(_compare_predictions(predictions, published_predictions))
    published_systems = published.get("systems")
    if published_systems is not None and not published_systems.empty:
        filtered = published_systems[published_systems["sistema"].isin(["B0", "B1"])]
        deviations.extend(
            compare_tables(metrics_frame, filtered, ["sistema", "semilla"])
        )
    published_summary = published.get("summary")
    if published_summary is not None and not published_summary.empty:
        filtered = published_summary[published_summary["sistema"].isin(["B0", "B1"])]
        deviations.extend(compare_tables(summary, filtered, ["sistema"]))
    return BaselineResult(
        predictions=predictions,
        metrics=metrics_frame,
        summary=summary,
        deviations=deviations,
    )
