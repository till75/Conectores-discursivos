"""Slow integration tests against the published pilot data.

The published data lives in ``doc/`` and is gitignored. These tests skip when
it is absent, so a clean checkout still runs the unit suite. Run them with
``pytest -m slow``.
"""

import shutil
import zipfile
from pathlib import Path

import pandas as pd
import pytest

from conectores.baselines import replay_baselines
from conectores.candidates import (
    NO,
    build_candidates,
    listing_forms,
    seed_candidate_counts,
)
from conectores.features import sentence_embedder
from conectores.metrics import count_undetected, main
from conectores.models import replay_m1, replay_m2
from conectores.pipeline import PIPELINE_COLUMNS
from conectores.pipeline import main as pipeline_main
from conectores.rules import load_nlp

DOC = Path(__file__).resolve().parents[1] / "doc"
ZIP = DOC / "resultados_hito2.zip"
REFERENCE = DOC / "referencia_piloto.csv"
LISTING = DOC / "listado_fuentes2009.csv"
CSL = DOC / "csl_excluidas.csv"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not all(path.exists() for path in (ZIP, REFERENCE, LISTING, CSL)),
        reason="published pilot data is not present",
    ),
]


def _extract_publicable(tmp_path: Path) -> Path:
    """Extract the published results and return the publicable directory."""
    with zipfile.ZipFile(ZIP) as archive:
        archive.extractall(tmp_path)
    return tmp_path / "resultados" / "publicable"


def _run_cli(
    publicable: Path,
    output: Path,
    *,
    published: Path | None = None,
    test_ids: Path | None = None,
    hashes: Path | None = None,
) -> int:
    """Run the replay CLI against the extracted published data."""
    return main(
        [
            "replay",
            "--predictions",
            str(publicable / "predicciones_test.csv"),
            "--reference",
            str(REFERENCE),
            "--listing",
            str(LISTING),
            "--csl",
            str(CSL),
            "--published",
            str(published or publicable),
            "--hashes",
            str(hashes or publicable / "test_congelado" / "hashes.json"),
            "--test-ids",
            str(test_ids or publicable / "test_congelado"),
            "--output",
            str(output),
            "--check",
        ]
    )


def test_replay_matches_published(tmp_path):
    """The replay reproduces the published tables with zero deviations."""
    publicable = _extract_publicable(tmp_path)
    output = tmp_path / "output"

    code = _run_cli(publicable, output)

    assert code == 0
    assert len(pd.read_csv(output / "replay_systems.csv")) == 30
    assert len(pd.read_csv(output / "replay_summary.csv")) == 6
    assert len(pd.read_csv(output / "replay_intervals.csv")) == 15
    assert len(pd.read_csv(output / "replay_diagnostics.csv")) == 5
    report = (output / "replay_report.md").read_text(encoding="utf-8")
    assert "Deviations: 0" in report


def test_candidates_match_published_counts(tmp_path):
    """The builder reproduces the published inventory and exclusions."""
    publicable = _extract_publicable(tmp_path)
    reference = pd.read_csv(REFERENCE)
    listing = pd.read_csv(LISTING)
    csl = pd.read_csv(CSL)

    result = build_candidates(reference, listing, csl)

    assert len(listing_forms(listing)) == 614
    assert result.raw_matches == 284
    assert len(result.csl_excluded) == 8
    assert len(result.second_pieces) == 3
    assert len(result.candidates) == 273
    assert int((result.candidates["oro"] != NO).sum()) == 64
    assert int((result.candidates["oro"] == NO).sum()) == 209
    assert len(result.undetected) == 16
    assert result.raw_matches == (
        len(result.candidates) + len(result.csl_excluded) + len(result.second_pieces)
    )

    published_csl = pd.read_csv(publicable / "excluidas_dentro_de_csl.csv")
    assert set(
        zip(result.csl_excluded["comment_id"], result.csl_excluded["unidad"])
    ) == set(zip(published_csl["comment_id"], published_csl["unidad"]))
    assert set(result.csl_excluded["csl"]) == set(published_csl["csl"])


def test_candidates_match_published_predictions(tmp_path):
    """Per seed, the rebuilt candidates match the published keys and gold labels."""
    publicable = _extract_publicable(tmp_path)
    predictions = pd.read_csv(publicable / "predicciones_test.csv")
    reference = pd.read_csv(REFERENCE)
    result = build_candidates(reference, pd.read_csv(LISTING), pd.read_csv(CSL))
    test_ids = {}
    for path in sorted((publicable / "test_congelado").glob("test_semilla*.txt")):
        seed = int(path.stem.split("_")[-1].replace("semilla", ""))
        test_ids[seed] = path.read_text(encoding="utf-8").split()

    counts = seed_candidate_counts(result.candidates, reference, test_ids)

    assert counts == {0: 65, 1: 97, 2: 92, 3: 124, 4: 61}
    comment_to_thread = dict(
        zip(reference["comment_id"], reference["thread_id"], strict=True)
    )
    appearances = 0
    tested = set()
    for seed, ids in test_ids.items():
        threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        built = result.candidates[result.candidates["thread_id"].isin(threads)]
        published = predictions[predictions["semilla"] == seed]
        built_keys = set(
            zip(built["comment_id"], built["unidad"], built["inicio"], built["oro"])
        )
        published_keys = set(
            zip(
                published["comment_id"],
                published["unidad"],
                published["inicio"],
                published["oro"],
            )
        )
        assert built_keys == published_keys
        appearances += len(built_keys)
        tested |= set(zip(built["comment_id"], built["unidad"], built["inicio"]))

    assert appearances == 439
    assert len(tested) == 256
    assert len(
        set(
            zip(
                result.candidates["comment_id"],
                result.candidates["unidad"],
                result.candidates["inicio"],
            )
        )
    ) == 273

    totals, _ = count_undetected(result.undetected, reference, test_ids)
    assert totals == {0: 5, 1: 3, 2: 4, 3: 8, 4: 4}


def _read_summary(path: Path) -> pd.DataFrame:
    """Read the published summary with its two-row header."""
    frame = pd.read_csv(path, header=[0, 1])
    frame.columns = [
        "sistema" if str(first).startswith("Unnamed") else f"{first}_{second}"
        for first, second in frame.columns
    ]
    return frame[frame["sistema"] != "sistema"].reset_index(drop=True)


def _baseline_inputs(tmp_path: Path):
    """Load the frozen inputs and the five test splits."""
    publicable = _extract_publicable(tmp_path)
    reference = pd.read_csv(REFERENCE)
    listing = pd.read_csv(LISTING)
    csl = pd.read_csv(CSL)
    candidate_set = build_candidates(reference, listing, csl)
    test_ids = {}
    for path in sorted((publicable / "test_congelado").glob("test_semilla*.txt")):
        seed = int(path.stem.split("_")[-1].replace("semilla", ""))
        test_ids[seed] = path.read_text(encoding="utf-8").split()
    return publicable, reference, listing, candidate_set, test_ids


def test_baselines_match_published_predictions(tmp_path):
    """The rebuilt B0/B1 columns match all 439 published test rows."""
    publicable, reference, listing, candidate_set, test_ids = _baseline_inputs(
        tmp_path
    )
    predictions = pd.read_csv(publicable / "predicciones_test.csv")

    result = replay_baselines(
        candidate_set,
        reference,
        listing,
        test_ids,
        {"predictions": predictions},
    )

    assert result.deviations == []
    assert len(result.predictions) == 439
    assert result.predictions.groupby("semilla").size().to_dict() == {
        0: 65,
        1: 97,
        2: 92,
        3: 124,
        4: 61,
    }


def test_baselines_match_published_metrics(tmp_path):
    """The ten per-seed rows and the two summary rows match to three decimals."""
    publicable, reference, listing, candidate_set, test_ids = _baseline_inputs(
        tmp_path
    )
    systems = pd.read_csv(publicable / "resultados_semillas.csv")
    summary = _read_summary(publicable / "resumen_sistemas.csv")

    result = replay_baselines(
        candidate_set,
        reference,
        listing,
        test_ids,
        {"systems": systems, "summary": summary},
    )

    assert result.deviations == []
    assert len(result.metrics) == 10
    assert len(result.summary) == 2
    b0 = result.summary[result.summary["sistema"] == "B0"].iloc[0]
    b1 = result.summary[result.summary["sistema"] == "B1"].iloc[0]
    assert round(b0["F1_etiqueta_mean"], 3) == 0.315
    assert round(b1["F1_etiqueta_mean"], 3) == 0.328
    assert round(b0["cobertura_etiqueta_mean"], 3) == 0.666
    assert round(b1["precision_etiqueta_mean"], 3) == 0.572


@pytest.fixture(scope="module")
def m1_replay(tmp_path_factory):
    """Rebuild M1 once with the real frozen model and the published tables."""
    tmp_path = tmp_path_factory.mktemp("m1")
    publicable, reference, listing, candidate_set, test_ids = _baseline_inputs(
        tmp_path
    )
    published = {
        "predictions": pd.read_csv(publicable / "predicciones_test.csv"),
        "systems": pd.read_csv(publicable / "resultados_semillas.csv"),
        "summary": _read_summary(publicable / "resumen_sistemas.csv"),
    }
    try:
        embedder = sentence_embedder()
    except Exception as exc:
        pytest.skip(f"frozen embedding model unavailable: {exc}")
    return replay_m1(
        candidate_set, reference, listing, test_ids, published, embedder
    )


def test_m1_matches_published_predictions(m1_replay):
    """The rebuilt M1 labels and probabilities match the 439 published rows."""
    result = m1_replay

    assert result.deviations == []
    assert len(result.predictions) == 439
    assert result.predictions.groupby("semilla").size().to_dict() == {
        0: 65,
        1: 97,
        2: 92,
        3: 124,
        4: 61,
    }
    assert set(result.margins) == {0, 1, 2, 3, 4}
    for seed, expected in {0: 0.10, 1: 0.10, 2: 0.10, 3: 0.05, 4: 0.15}.items():
        assert result.margins[seed] == pytest.approx(expected)
    assert not any("p_M1" in deviation for deviation in result.deviations)


def test_m1_matches_published_metrics(m1_replay):
    """The ten per-seed rows and two summary rows match to three decimals."""
    result = m1_replay

    assert result.deviations == []
    assert len(result.metrics) == 10
    assert len(result.summary) == 2
    m1_rows = result.metrics[result.metrics["sistema"] == "M1"].reset_index(
        drop=True
    )
    abstention_rows = result.metrics[
        result.metrics["sistema"] == "M1 con abstención"
    ].reset_index(drop=True)
    assert list(m1_rows["F1_etiqueta"].round(3)) == [
        0.333,
        0.267,
        0.261,
        0.426,
        0.513,
    ]
    assert list(abstention_rows["F1_etiqueta"].round(3)) == [
        0.400,
        0.294,
        0.308,
        0.448,
        0.522,
    ]
    expected_abstention = [0.169231, 0.154639, 0.086957, 0.040323, 0.262295]
    for row, expected in zip(
        abstention_rows.itertuples(), expected_abstention, strict=True
    ):
        assert row.margen == pytest.approx(
            {0: 0.10, 1: 0.10, 2: 0.10, 3: 0.05, 4: 0.15}[row.semilla]
        )
        assert row.abstencion == pytest.approx(expected, abs=1e-5)
    m1_summary = result.summary[result.summary["sistema"] == "M1"].iloc[0]
    abstention_summary = result.summary[
        result.summary["sistema"] == "M1 con abstención"
    ].iloc[0]
    assert round(m1_summary["F1_etiqueta_mean"], 3) == 0.360
    assert round(abstention_summary["F1_etiqueta_mean"], 3) == 0.394


@pytest.fixture(scope="module")
def m2_replay(tmp_path_factory):
    """Rebuild M2 once with the real models and the published tables."""
    tmp_path = tmp_path_factory.mktemp("m2")
    publicable, reference, listing, candidate_set, test_ids = _baseline_inputs(
        tmp_path
    )
    published = {
        "predictions": pd.read_csv(publicable / "predicciones_test.csv"),
        "systems": pd.read_csv(publicable / "resultados_semillas.csv"),
        "summary": _read_summary(publicable / "resumen_sistemas.csv"),
    }
    try:
        embedder = sentence_embedder()
    except Exception as exc:
        pytest.skip(f"frozen embedding model unavailable: {exc}")
    try:
        nlp = load_nlp()
    except Exception as exc:
        pytest.skip(f"spaCy model unavailable: {exc}")
    return replay_m2(
        candidate_set,
        reference,
        listing,
        test_ids,
        published,
        embedder,
        nlp,
    )


def test_m2_matches_published_predictions(m2_replay):
    """The rebuilt M2 core values match the 439 published rows."""
    result = m2_replay

    assert result.deviations == []
    assert len(result.predictions) == 439
    assert result.predictions.groupby("semilla").size().to_dict() == {
        0: 65,
        1: 97,
        2: 92,
        3: 124,
        4: 61,
    }
    assert set(result.margins) == {0, 1, 2, 3, 4}
    assert not any("p_M2" in deviation for deviation in result.deviations)


def test_m2_matches_published_metrics(m2_replay):
    """The five M2 rows and the M2 summary row match to three decimals."""
    result = m2_replay

    assert result.deviations == []
    assert len(result.metrics) == 10
    assert len(result.summary) == 2
    m2_rows = result.metrics[result.metrics["sistema"] == "M2"].reset_index(
        drop=True
    )
    abstention_rows = result.metrics[
        result.metrics["sistema"] == "M2 con abstención"
    ].reset_index(drop=True)
    assert list(m2_rows["F1_etiqueta"].round(3)) == [
        0.432,
        0.545,
        0.500,
        0.452,
        0.486,
    ]
    assert len(abstention_rows) == 5
    assert dict(result.margins) == {
        0: 0.15,
        1: 0.10,
        2: 0.20,
        3: 0.10,
        4: 0.20,
    }
    assert result.margin_deviations == []
    m2_summary = result.summary[result.summary["sistema"] == "M2"].iloc[0]
    assert round(m2_summary["F1_etiqueta_mean"], 3) == 0.483


def test_m2_traceability_matches_published(m2_replay):
    """The aggregate traceability counts match the published values."""
    assert m2_replay.traceability == {
        "etiquetas_discursivas": 91,
        "fijadas_listado": 58,
        "fijadas_listado_correctas": 34,
        "elegidas_modelo": 33,
        "elegidas_modelo_correctas": 20,
        "revisar_categoria": 43,
    }


def test_pipeline_end_to_end(tmp_path):
    """The publication pipeline writes the full pack with zero deviations."""
    publicable = _extract_publicable(tmp_path)
    output = tmp_path / "output"

    code = pipeline_main(
        [
            "--reference",
            str(REFERENCE),
            "--listing",
            str(LISTING),
            "--csl",
            str(CSL),
            "--test-ids",
            str(publicable / "test_congelado"),
            "--hashes",
            str(publicable / "test_congelado" / "hashes.json"),
            "--published",
            str(publicable),
            "--output",
            str(output),
            "--check",
        ]
    )

    assert code == 0
    predictions = pd.read_csv(output / "predicciones_test.csv")
    assert list(predictions.columns) == PIPELINE_COLUMNS
    assert len(predictions) == 439
    assert len(pd.read_csv(output / "resultados_semillas.csv")) == 30
    assert len(pd.read_csv(output / "resumen_sistemas.csv")) == 6
    assert len(pd.read_csv(output / "intervalos_confianza.csv")) == 15
    assert len(pd.read_csv(output / "diagnosticos.csv")) == 5
    report = (output / "pipeline_report.md").read_text(encoding="utf-8")
    assert "Deviations: 0" in report
    assert "Privacy mentions: 0" in report


def test_replay_perturbed_cell_fails(tmp_path):
    """One perturbed published cell makes the check exit 1 and name it."""
    publicable = _extract_publicable(tmp_path)
    perturbed = tmp_path / "perturbed"
    shutil.copytree(publicable, perturbed)
    systems = pd.read_csv(perturbed / "resultados_semillas.csv")
    systems.loc[0, "F1_etiqueta"] = systems.loc[0, "F1_etiqueta"] + 0.01
    systems.to_csv(perturbed / "resultados_semillas.csv", index=False)
    output = tmp_path / "output"

    code = _run_cli(publicable, output, published=perturbed)

    assert code == 1
    report = (output / "replay_report.md").read_text(encoding="utf-8")
    assert "sistema=B0" in report
    assert "F1_etiqueta" in report


def test_replay_frozen_hashes(tmp_path):
    """A changed frozen test file makes the check exit 1 and name the hash."""
    publicable = _extract_publicable(tmp_path)
    modified = tmp_path / "test_congelado"
    shutil.copytree(publicable / "test_congelado", modified)
    path = modified / "test_semilla0.txt"
    path.write_bytes(path.read_bytes() + b"\n")
    output = tmp_path / "output"

    code = _run_cli(
        publicable,
        output,
        test_ids=modified,
        hashes=publicable / "test_congelado" / "hashes.json",
    )

    assert code == 1
    report = (output / "replay_report.md").read_text(encoding="utf-8")
    assert "hash semilla 0" in report
