"""Metric definitions for the metric-replay slice.

The functions here reproduce the notebook's metric definitions without
importing the notebook. Candidate construction lives in ``candidates.py``; this
module keeps the S1 replay and its compatibility entry points.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from conectores.candidates import NO, build_candidates


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


def undetected_labels(
    reference: pd.DataFrame, listing: pd.DataFrame, csl: pd.DataFrame
) -> pd.DataFrame:
    """Return the reference spans the listing never matches.

    S1's compatibility entry point; the candidate builder is authoritative.
    S1's undetected fixtures predate ``is_reply`` and ``text_normalized``, and
    the undetected rows depend on neither, so the wrapper supplies neutral
    values when the columns are absent.
    """
    if "is_reply" not in reference.columns:
        reference = reference.assign(is_reply=False)
    if "text_normalized" not in reference.columns:
        reference = reference.assign(text_normalized="")
    return build_candidates(reference, listing, csl).undetected


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


def count_undetected(
    undetected: pd.DataFrame,
    reference: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
) -> tuple[dict[int, int], dict[int, dict[str, int]]]:
    """Return undetected totals and per-thread counts for each seed."""
    comment_to_thread = dict(
        zip(reference["comment_id"], reference["thread_id"], strict=True)
    )
    totals: dict[int, int] = {}
    per_thread: dict[int, dict[str, int]] = {}
    for seed, ids in test_ids.items():
        test_threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        seed_undetected = undetected[undetected["thread_id"].isin(test_threads)]
        totals[int(seed)] = len(seed_undetected)
        per_thread[int(seed)] = {
            str(thread): int(count)
            for thread, count in seed_undetected.groupby("thread_id").size().items()
        }
    return totals, per_thread


def traceability(predictions: pd.DataFrame) -> dict[str, int]:
    """Return the v4 traceability counts from the published predictions."""
    discourse = predictions[predictions["M2"] != NO]
    list_fixed = discourse[discourse["origen_M2"] == "listado"]
    model_chosen = discourse[discourse["origen_M2"] == "modelo"]
    return {
        "etiquetas_discursivas": len(discourse),
        "fijadas_listado": len(list_fixed),
        "fijadas_listado_correctas": int(
            (list_fixed["oro"] == list_fixed["M2"]).sum()
        ),
        "elegidas_modelo": len(model_chosen),
        "elegidas_modelo_correctas": int(
            (model_chosen["oro"] == model_chosen["M2"]).sum()
        ),
        "revisar_categoria": int(discourse["revisar_categoria"].sum()),
    }


@dataclass(frozen=True)
class ReplayResult:
    """The replayed tables and the deviations from the published ones."""

    systems: pd.DataFrame
    summary: pd.DataFrame
    intervals: pd.DataFrame
    diagnostics: pd.DataFrame
    traceability: Mapping[str, int]
    deviations: list[str]


def replay(
    predictions: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
    published: Mapping[str, pd.DataFrame],
    hashes: Mapping[str, str],
    test_files: Mapping[int, str],
    n: int = 1000,
    margins: Mapping[tuple[int, str], float] | None = None,
) -> ReplayResult:
    """Return the replayed tables and the deviations from the published ones."""
    test_ids = {seed: text.split() for seed, text in test_files.items()}
    undetected = undetected_labels(reference, listing, csl)
    totals, per_thread = count_undetected(undetected, reference, test_ids)
    if margins is None:
        margins = {
            (int(row.semilla), row.sistema): float(row.margen)
            for row in published["systems"].itertuples()
            if row.sistema in ("M1 con abstención", "M2 con abstención")
            and not pd.isna(row.margen)
        }
    systems = replay_systems(predictions, margins, totals)
    summary = summary_systems(systems)
    intervals = replay_intervals(predictions, per_thread, n=n)
    diagnostics = pd.DataFrame(
        [
            {
                "semilla": seed,
                "candidatas": int((predictions["semilla"] == seed).sum()),
                "no_detectadas": totals[seed],
            }
            for seed in sorted(totals)
        ]
    )
    deviations = []
    tables = {
        "systems": (systems, ["sistema", "semilla"]),
        "summary": (summary, ["sistema"]),
        "intervals": (intervals, ["comparacion", "semilla"]),
    }
    for name, (replayed, keys) in tables.items():
        published_table = published.get(name)
        if published_table is None or published_table.empty:
            continue
        deviations.extend(compare_tables(replayed, published_table, keys))
    for seed, text in test_files.items():
        expected = hashes.get(str(seed))
        actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if expected is None:
            deviations.append(f"hash semilla {seed}: missing from hashes.json")
        elif expected != actual:
            deviations.append(
                f"hash semilla {seed}: replay {actual} != published {expected}"
            )
    return ReplayResult(
        systems=systems,
        summary=summary,
        intervals=intervals,
        diagnostics=diagnostics,
        traceability=traceability(predictions),
        deviations=deviations,
    )


def _read_summary(path: Path) -> pd.DataFrame:
    """Read the published summary, flat or with the two-row header."""
    frame = pd.read_csv(path)
    if "sistema" in frame.columns and "F1_etiqueta_mean" in frame.columns:
        return frame
    frame = pd.read_csv(path, header=[0, 1])
    frame.columns = [
        "sistema" if str(first).startswith("Unnamed") else f"{first}_{second}"
        for first, second in frame.columns
    ]
    return frame[frame["sistema"] != "sistema"].reset_index(drop=True)


def _format_report(result: ReplayResult) -> str:
    """Render the replay report without comment text."""
    lines = [
        "# Replay report",
        "",
        f"- Systems rows: {len(result.systems)}",
        f"- Summary rows: {len(result.summary)}",
        f"- Interval rows: {len(result.intervals)}",
        f"- Deviations: {len(result.deviations)}",
        "",
        "## Traceability",
        "",
    ]
    for key, value in result.traceability.items():
        lines.append(f"- {key}: {value}")
    lines.extend(["", "## Deviations", ""])
    if result.deviations:
        lines.extend(f"- {deviation}" for deviation in result.deviations)
    else:
        lines.append("None.")
    lines.append("")
    return "\n".join(lines)


def _run_replay(args: argparse.Namespace) -> int:
    """Read the inputs, replay the tables, and write the outputs."""
    predictions = pd.read_csv(args.predictions)
    reference = pd.read_csv(args.reference)
    listing = pd.read_csv(args.listing)
    csl = pd.read_csv(args.csl)
    published_dir = Path(args.published)
    published = {
        "systems": pd.read_csv(published_dir / "resultados_semillas.csv"),
        "summary": _read_summary(published_dir / "resumen_sistemas.csv"),
        "intervals": pd.read_csv(published_dir / "intervalos_confianza.csv"),
    }
    hashes = json.loads(Path(args.hashes).read_text(encoding="utf-8"))
    test_files = {}
    for path in sorted(Path(args.test_ids).glob("test_semilla*.txt")):
        seed = int(path.stem.split("_")[-1].replace("semilla", ""))
        test_files[seed] = path.read_bytes().decode("utf-8")
    result = replay(predictions, reference, listing, csl, published, hashes, test_files)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    result.systems.to_csv(output / "replay_systems.csv", index=False)
    result.summary.to_csv(output / "replay_summary.csv", index=False)
    result.intervals.to_csv(output / "replay_intervals.csv", index=False)
    result.diagnostics.to_csv(output / "replay_diagnostics.csv", index=False)
    (output / "replay_report.md").write_text(_format_report(result), encoding="utf-8")
    if args.check and result.deviations:
        return 1
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the metric-replay command line."""
    parser = argparse.ArgumentParser(prog="python -m conectores.metrics")
    subparsers = parser.add_subparsers(dest="command", required=True)
    replay_parser = subparsers.add_parser(
        "replay", help="Replay the published metric tables."
    )
    replay_parser.add_argument("--predictions", required=True)
    replay_parser.add_argument("--reference", required=True)
    replay_parser.add_argument("--listing", required=True)
    replay_parser.add_argument("--csl", required=True)
    replay_parser.add_argument("--published", required=True)
    replay_parser.add_argument("--hashes", required=True)
    replay_parser.add_argument("--test-ids", required=True)
    replay_parser.add_argument("--output", required=True)
    replay_parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.command == "replay":
        return _run_replay(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
