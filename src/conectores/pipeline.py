"""End-to-end publication pipeline for S6."""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from conectores.baselines import baseline_predictions
from conectores.candidates import build_candidates
from conectores.features import Embedder, sentence_embedder
from conectores.metrics import _read_summary, replay
from conectores.models import replay_m1, replay_m2
from conectores.rules import NLP, load_nlp

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


def _format_pipeline_report(result: PipelineResult) -> str:
    lines = [
        "# Pipeline report",
        "",
        f"- Predictions: {len(result.predictions)}",
        f"- Systems rows: {len(result.systems)}",
        f"- Summary rows: {len(result.summary)}",
        f"- Interval rows: {len(result.intervals)}",
        f"- Diagnostics rows: {len(result.diagnostics)}",
        f"- Deviations: {len(result.deviations)}",
        f"- Privacy mentions: {result.privacy_mentions}",
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


def write_pipeline_outputs(
    result: PipelineResult, output_dir: Path
) -> None:
    """Write the public tables and the report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    result.predictions.to_csv(
        output_dir / "predicciones_test.csv", index=False
    )
    result.systems.to_csv(
        output_dir / "resultados_semillas.csv", index=False
    )
    result.summary.to_csv(
        output_dir / "resumen_sistemas.csv", index=False
    )
    result.intervals.to_csv(
        output_dir / "intervalos_confianza.csv", index=False
    )
    result.diagnostics.to_csv(
        output_dir / "diagnosticos.csv", index=False
    )
    (output_dir / "trazabilidad.json").write_text(
        json.dumps(dict(result.traceability), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / "pipeline_report.md").write_text(
        _format_pipeline_report(result), encoding="utf-8"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the publication pipeline command line."""
    parser = argparse.ArgumentParser(prog="python -m conectores.pipeline")
    parser.add_argument("--reference", required=True)
    parser.add_argument("--listing", required=True)
    parser.add_argument("--csl", required=True)
    parser.add_argument("--test-ids", required=True)
    parser.add_argument("--hashes", required=True)
    parser.add_argument("--published", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--n-bootstrap", type=int, default=1000)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    reference = pd.read_csv(args.reference)
    listing = pd.read_csv(args.listing)
    csl = pd.read_csv(args.csl)
    test_files = {}
    for path in sorted(Path(args.test_ids).glob("test_semilla*.txt")):
        seed = int(path.stem.split("_")[-1].replace("semilla", ""))
        test_files[seed] = path.read_text(encoding="utf-8")
    hashes = json.loads(Path(args.hashes).read_text(encoding="utf-8"))
    published_dir = Path(args.published)
    published = {
        "predictions": pd.read_csv(
            published_dir / "predicciones_test.csv"
        ),
        "systems": pd.read_csv(
            published_dir / "resultados_semillas.csv"
        ),
        "summary": _read_summary(
            published_dir / "resumen_sistemas.csv"
        ),
        "intervals": pd.read_csv(
            published_dir / "intervalos_confianza.csv"
        ),
    }
    result = run_pipeline(
        reference,
        listing,
        csl,
        test_files,
        hashes,
        published,
        sentence_embedder(),
        load_nlp(),
        n_bootstrap=args.n_bootstrap,
    )
    write_pipeline_outputs(result, Path(args.output))
    print(
        f"Predictions: {len(result.predictions)} · "
        f"Deviations: {len(result.deviations)} · "
        f"Privacy mentions: {result.privacy_mentions}"
    )
    if args.check and (result.deviations or result.privacy_mentions):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


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
