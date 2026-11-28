"""Unit tests for the publication pipeline."""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

import conectores.pipeline as pipeline
from conectores.candidates import NO
from conectores.pipeline import (
    PIPELINE_COLUMNS,
    PipelineResult,
    combine_predictions,
    main,
    run_pipeline,
    write_pipeline_outputs,
)


def _baselines():
    return pd.DataFrame(
        [
            {
                "semilla": 0,
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 0,
                "oro": "OP:MODAL",
                "B0": "CON:ADICIÓN",
                "B1": "OP:MODAL",
            },
            {
                "semilla": 0,
                "comment_id": "c2",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 3,
                "oro": NO,
                "B0": "CON:ADICIÓN",
                "B1": "CON:ADICIÓN",
            },
        ]
    )


def _m1():
    return pd.DataFrame(
        [
            {
                "semilla": 0,
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 0,
                "oro": "OP:MODAL",
                "M1": "OP:MODAL",
                "p_M1": 0.9,
                "abstiene": False,
                "M1_con_abstencion": "OP:MODAL",
            },
            {
                "semilla": 0,
                "comment_id": "c2",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 3,
                "oro": NO,
                "M1": NO,
                "p_M1": 0.1,
                "abstiene": False,
                "M1_con_abstencion": NO,
            },
        ]
    )


def _m2():
    return pd.DataFrame(
        [
            {
                "semilla": 0,
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 0,
                "oro": "OP:MODAL",
                "M2": "OP:MODAL",
                "p_M2": 0.8,
                "origen_M2": "modelo",
                "revisar_categoria": False,
                "abstiene_M2": False,
            },
            {
                "semilla": 0,
                "comment_id": "c2",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 3,
                "oro": NO,
                "M2": NO,
                "p_M2": 0.2,
                "origen_M2": "modelo",
                "revisar_categoria": False,
                "abstiene_M2": False,
            },
        ]
    )


def test_combine_predictions_builds_public_frame():
    frame = combine_predictions(_baselines(), _m1(), _m2())

    assert list(frame.columns) == PIPELINE_COLUMNS
    assert len(frame) == 2
    assert frame.loc[0, "B0"] == "CON:ADICIÓN"
    assert frame.loc[0, "M1"] == "OP:MODAL"
    assert frame.loc[0, "M2"] == "OP:MODAL"
    assert frame.loc[0, "origen_M2"] == "modelo"
    assert bool(frame.loc[0, "abstiene_M2"]) is False
    assert "abstiene" not in frame.columns
    assert "M1_con_abstencion" not in frame.columns


def test_combine_predictions_rejects_label_disagreement():
    m2 = _m2().assign(oro="CON:ADICIÓN")

    with pytest.raises(ValueError, match="c1"):
        combine_predictions(_baselines(), _m1(), m2)


def test_combine_predictions_rejects_missing_key():
    m2 = _m2().iloc[:1]

    with pytest.raises(ValueError, match="c2"):
        combine_predictions(_baselines(), _m1(), m2)


def _pipeline_reference():
    rows = []
    for thread_index in range(6):
        thread = f"t{thread_index + 1}"
        for kind in ("alpha", "beta", "gamma"):
            comment_id = f"c{len(rows) + 1}"
            text = f"{kind} context ya"
            if kind == "alpha":
                annotation = f"{kind} context [ya::OP:MODAL]"
            elif kind == "beta":
                annotation = f"{kind} context [ya::CON:ADICIÓN]"
            else:
                annotation = text
            rows.append(
                {
                    "comment_id": comment_id,
                    "thread_id": thread,
                    "is_reply": False,
                    "text_normalized": text,
                    "anotacion": annotation,
                }
            )
    return pd.DataFrame(rows)


def _pipeline_listing():
    return pd.DataFrame(
        [
            {
                "unidad": "ya",
                "macrofuncion": "Conector",
                "categoria": "Adición",
                "subcategoria": "─",
            },
            {
                "unidad": "ya 2",
                "macrofuncion": "Operador",
                "categoria": "Modal",
                "subcategoria": "─",
            },
        ]
    )


def _pipeline_csl():
    return pd.DataFrame({"comment_id": [], "unidad": []})


def _pipeline_embedder(texts):
    rows = []
    for text in texts:
        vector = np.zeros(384)
        if "alpha" in text:
            vector[0] = 1.0
        elif "beta" in text:
            vector[1] = 1.0
        elif "gamma" in text:
            vector[2] = 1.0
        rows.append(vector)
    return np.vstack(rows)


class _PipelineToken:
    def __init__(self, idx, text, pos):
        self.idx = idx
        self.text = text
        self.pos_ = pos


def _pipeline_nlp(texto):
    return [_PipelineToken(texto.find("ya"), "ya", "ADV")]


def test_run_pipeline_composes_tables():
    test_text = "c1\n"
    reference = _pipeline_reference()
    listing = _pipeline_listing()
    csl = _pipeline_csl()
    test_files = {0: test_text}
    hashes = {
        "0": hashlib.sha256(test_text.encode("utf-8")).hexdigest()
    }

    result = run_pipeline(
        reference,
        listing,
        csl,
        test_files,
        hashes,
        {},
        _pipeline_embedder,
        _pipeline_nlp,
        n_bootstrap=10,
    )

    assert list(result.predictions.columns) == PIPELINE_COLUMNS
    assert len(result.predictions) == 3
    assert set(result.systems["sistema"]) == {
        "B0",
        "B1",
        "M1",
        "M2",
        "M1 con abstención",
        "M2 con abstención",
    }
    assert len(result.systems) == 6
    assert len(result.summary) == 6
    assert len(result.intervals) == 3
    assert len(result.diagnostics) == 1
    assert set(result.traceability) == {
        "etiquetas_discursivas",
        "fijadas_listado",
        "fijadas_listado_correctas",
        "elegidas_modelo",
        "elegidas_modelo_correctas",
        "revisar_categoria",
    }
    assert result.deviations == []
    assert result.privacy_mentions == 0


def _pipeline_result():
    return PipelineResult(
        predictions=pd.DataFrame(columns=PIPELINE_COLUMNS),
        systems=pd.DataFrame({"sistema": ["M2"], "semilla": [0]}),
        summary=pd.DataFrame(
            {"sistema": ["M2"], "F1_etiqueta_mean": [0.5]}
        ),
        intervals=pd.DataFrame(
            {"comparacion": ["M2 − B1"], "semilla": [0]}
        ),
        diagnostics=pd.DataFrame(
            {"semilla": [0], "candidatas": [1], "no_detectadas": [0]}
        ),
        traceability={"etiquetas_discursivas": 1},
        deviations=[],
        privacy_mentions=0,
    )


def test_write_pipeline_outputs(tmp_path):
    result = _pipeline_result()

    write_pipeline_outputs(result, tmp_path)

    assert (tmp_path / "predicciones_test.csv").exists()
    assert (tmp_path / "resultados_semillas.csv").exists()
    assert (tmp_path / "resumen_sistemas.csv").exists()
    assert (tmp_path / "intervalos_confianza.csv").exists()
    assert (tmp_path / "diagnosticos.csv").exists()
    assert (tmp_path / "trazabilidad.json").exists()
    report = (tmp_path / "pipeline_report.md").read_text(encoding="utf-8")
    assert "Deviations: 0" in report
    assert "Privacy mentions: 0" in report


def _write_cli_fixture(tmp_path):
    reference = _pipeline_reference()
    listing = _pipeline_listing()
    csl = _pipeline_csl()
    reference.to_csv(tmp_path / "reference.csv", index=False)
    listing.to_csv(tmp_path / "listing.csv", index=False)
    csl.to_csv(tmp_path / "csl.csv", index=False)
    test_ids = tmp_path / "test_ids"
    test_ids.mkdir()
    (test_ids / "test_semilla0.txt").write_text(
        "c1\n", encoding="utf-8"
    )
    hashes = {"0": hashlib.sha256(b"c1\n").hexdigest()}
    (tmp_path / "hashes.json").write_text(
        json.dumps(hashes), encoding="utf-8"
    )
    published = tmp_path / "published"
    published.mkdir()
    pd.DataFrame(columns=["sistema", "semilla"]).to_csv(
        published / "resultados_semillas.csv", index=False
    )
    pd.DataFrame(
        columns=["sistema", "F1_etiqueta_mean"]
    ).to_csv(published / "resumen_sistemas.csv", index=False)
    pd.DataFrame(columns=["comparacion", "semilla"]).to_csv(
        published / "intervalos_confianza.csv", index=False
    )
    pd.DataFrame(columns=PIPELINE_COLUMNS).to_csv(
        published / "predicciones_test.csv", index=False
    )
    return tmp_path


def _run_pipeline_cli(paths, output):
    return main(
        [
            "--reference",
            str(paths / "reference.csv"),
            "--listing",
            str(paths / "listing.csv"),
            "--csl",
            str(paths / "csl.csv"),
            "--test-ids",
            str(paths / "test_ids"),
            "--hashes",
            str(paths / "hashes.json"),
            "--published",
            str(paths / "published"),
            "--output",
            str(output),
            "--n-bootstrap",
            "10",
            "--check",
        ]
    )


def test_pipeline_cli(tmp_path, monkeypatch):
    paths = _write_cli_fixture(tmp_path)
    monkeypatch.setattr(
        pipeline, "sentence_embedder", lambda: _pipeline_embedder
    )
    monkeypatch.setattr(pipeline, "load_nlp", lambda: _pipeline_nlp)
    output = tmp_path / "output"

    code = _run_pipeline_cli(paths, output)

    assert code == 0
    for name in (
        "predicciones_test.csv",
        "resultados_semillas.csv",
        "resumen_sistemas.csv",
        "intervalos_confianza.csv",
        "diagnosticos.csv",
        "trazabilidad.json",
        "pipeline_report.md",
    ):
        assert (output / name).exists()
    report = (output / "pipeline_report.md").read_text(encoding="utf-8")
    assert "Deviations: 0" in report
    assert "Privacy mentions: 0" in report


def test_pipeline_cli_check_perturbed(tmp_path, monkeypatch):
    paths = _write_cli_fixture(tmp_path)
    pd.DataFrame(
        [{"sistema": "M2", "semilla": 0, "F1_etiqueta": 0.0}]
    ).to_csv(paths / "published" / "resultados_semillas.csv", index=False)
    monkeypatch.setattr(
        pipeline, "sentence_embedder", lambda: _pipeline_embedder
    )
    monkeypatch.setattr(pipeline, "load_nlp", lambda: _pipeline_nlp)

    code = _run_pipeline_cli(paths, tmp_path / "output")

    assert code == 1
