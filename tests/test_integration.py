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

from conectores.candidates import (
    NO,
    build_candidates,
    listing_forms,
    seed_candidate_counts,
)
from conectores.metrics import count_undetected, main

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
