"""Unit tests for the metric definitions."""

import hashlib

import pandas as pd
import pytest

from conectores.metrics import (
    NO,
    ReplayResult,
    bootstrap_difference,
    compare_tables,
    compute_metrics,
    count_undetected,
    main,
    replay,
    replay_intervals,
    replay_systems,
    summary_systems,
    traceability,
    undetected_labels,
)


def test_compute_metrics_hand_checked():
    """One correct label, one false alarm, one missed label, one undetected.

    gold: CON:ADICIÓN, NO, OP:MODAL, NO
    pred: CON:ADICIÓN, NO, NO, OP:MODAL

    True positives: 1 (the CON:ADICIÓN match).
    Predicted positives: 2 (CON:ADICIÓN and OP:MODAL).
    Gold positives: 2 in the sequence plus 1 undetected = 3.
    F1: 2*1/(2+3) = 0.4.
    Precision: 1/2 = 0.5.
    Coverage: 1/3.
    Macro CON/OP: CON 1.0, OP 0.0, mean 0.5.
    """
    gold = ["CON:ADICIÓN", NO, "OP:MODAL", NO]
    pred = ["CON:ADICIÓN", NO, NO, "OP:MODAL"]

    result = compute_metrics(gold, pred, n_undetected=1)

    assert result.f1_label == pytest.approx(0.4)
    assert result.f1_discourse == pytest.approx(0.4)
    assert result.f1_macro == pytest.approx(0.5)
    assert result.precision == pytest.approx(0.5)
    assert result.coverage == pytest.approx(1 / 3)


def test_undetected_labels_excludes_csl():
    """A matched span is not undetected; a CSL span is removed; a non-match is."""
    reference = pd.DataFrame(
        [
            {
                "comment_id": "c1",
                "thread_id": "t1",
                "text_normalized": "",
                "anotacion": "[hasta::NO_DISCURSIVO] [ya::CON:ADICIÓN]",
            },
            {
                "comment_id": "c2",
                "thread_id": "t2",
                "text_normalized": "",
                "anotacion": "[Dale::NO_DISCURSIVO]",
            },
            {
                "comment_id": "c3",
                "thread_id": "t3",
                "text_normalized": "",
                "anotacion": "Sin etiquetas",
            },
        ]
    )
    listing = pd.DataFrame({"unidad": ["hasta", "Dale"]})
    csl = pd.DataFrame({"comment_id": ["c2"], "unidad": ["Dale"]})

    result = undetected_labels(reference, listing, csl)

    assert result.to_dict("records") == [
        {
            "comment_id": "c1",
            "thread_id": "t1",
            "unidad": "ya",
            "oro": "CON:ADICIÓN",
        }
    ]


def test_undetected_labels_boundaries():
    """A list form inside a longer word is not a match."""
    reference = pd.DataFrame(
        [
            {
                "comment_id": "c4",
                "thread_id": "t4",
                "text_normalized": "",
                "anotacion": "[playa::NO_DISCURSIVO]",
            }
        ]
    )
    listing = pd.DataFrame({"unidad": ["ya"]})
    csl = pd.DataFrame({"comment_id": [], "unidad": []})

    result = undetected_labels(reference, listing, csl)

    assert result.to_dict("records") == [
        {
            "comment_id": "c4",
            "thread_id": "t4",
            "unidad": "playa",
            "oro": "NO_DISCURSIVO",
        }
    ]


def test_undetected_labels_excludes_csl_by_position():
    """The published CSL file marks a construction by start and end."""
    reference = pd.DataFrame(
        [
            {
                "comment_id": "c5",
                "thread_id": "t5",
                "text_normalized": "",
                "anotacion": "[Dale::OP:MODAL]",
            }
        ]
    )
    listing = pd.DataFrame({"unidad": ["hasta"]})
    csl = pd.DataFrame(
        [
            {
                "comment_id": "c5",
                "inicio": 0,
                "fin": 22,
                "regla_csl": "[Dale + SN]",
            }
        ]
    )

    result = undetected_labels(reference, listing, csl)

    assert result.to_dict("records") == []


def _bootstrap_fixture():
    """Twenty threads, alternating which system is right."""
    gold, pred_a, pred_b, threads = [], [], [], []
    for index in range(20):
        thread = f"t{index}"
        if index % 2 == 0:
            gold.extend(["CON:ADICIÓN", NO])
            pred_a.extend(["CON:ADICIÓN", NO])
            pred_b.extend([NO, NO])
        else:
            gold.extend(["OP:MODAL", NO])
            pred_a.extend([NO, NO])
            pred_b.extend(["OP:MODAL", NO])
        threads.extend([thread, thread])
    undetected = {f"t{index}": 0 for index in range(20)}
    return gold, pred_a, pred_b, threads, undetected


def test_bootstrap_deterministic():
    """Same seed gives the same interval; a different seed moves it."""
    gold, pred_a, pred_b, threads, undetected = _bootstrap_fixture()

    first = bootstrap_difference(
        gold, pred_a, pred_b, threads, undetected, n=200, seed=0
    )
    second = bootstrap_difference(
        gold, pred_a, pred_b, threads, undetected, n=200, seed=0
    )
    other = bootstrap_difference(
        gold, pred_a, pred_b, threads, undetected, n=200, seed=1
    )

    assert first == second
    assert first[0] < first[1]
    assert -1 <= first[0] <= 1
    assert -1 <= first[1] <= 1
    assert first != other


def test_replay_systems_synthetic():
    """Six systems for one seed, with a wrong B1 and no abstention."""
    predictions = pd.DataFrame(
        [
            {
                "semilla": 0,
                "thread_id": "t1",
                "oro": "CON:ADICIÓN",
                "B0": "CON:ADICIÓN",
                "B1": NO,
                "M1": "CON:ADICIÓN",
                "M2": "CON:ADICIÓN",
                "p_M1": 0.9,
                "p_M2": 0.9,
                "abstiene_M2": False,
            },
            {
                "semilla": 0,
                "thread_id": "t2",
                "oro": NO,
                "B0": NO,
                "B1": NO,
                "M1": NO,
                "M2": NO,
                "p_M1": 0.1,
                "p_M2": 0.1,
                "abstiene_M2": False,
            },
        ]
    )
    margins = {(0, "M1 con abstención"): 0.1, (0, "M2 con abstención"): 0.15}

    result = replay_systems(predictions, margins, {0: 0})

    assert len(result) == 6
    by_system = result.set_index("sistema")
    assert list(by_system.index) == [
        "B0",
        "B1",
        "M1",
        "M2",
        "M1 con abstención",
        "M2 con abstención",
    ]
    assert by_system.loc["B0", "F1_etiqueta"] == pytest.approx(1.0)
    assert by_system.loc["B0", "precision_etiqueta"] == pytest.approx(1.0)
    assert by_system.loc["B0", "cobertura_etiqueta"] == pytest.approx(1.0)
    assert by_system.loc["B1", "F1_etiqueta"] == pytest.approx(0.0)
    assert by_system.loc["B1", "precision_etiqueta"] == pytest.approx(0.0)
    assert by_system.loc["B1", "cobertura_etiqueta"] == pytest.approx(0.0)
    assert by_system.loc["M2", "F1_etiqueta"] == pytest.approx(1.0)
    assert by_system.loc["M1 con abstención", "abstencion"] == pytest.approx(0.0)
    assert by_system.loc["M2 con abstención", "margen"] == pytest.approx(0.15)
    assert pd.isna(by_system.loc["B0", "abstencion"])
    assert pd.isna(by_system.loc["B0", "margen"])


def test_summary_systems_synthetic():
    """Mean and sample standard deviation per system, in first-seen order."""
    systems = pd.DataFrame(
        [
            {
                "sistema": "B0",
                "F1_etiqueta": 1.0,
                "F1_uso_discursivo": 1.0,
                "F1_macro_CON_OP": 0.5,
                "precision_etiqueta": 1.0,
                "cobertura_etiqueta": 1.0,
            },
            {
                "sistema": "B0",
                "F1_etiqueta": 0.0,
                "F1_uso_discursivo": 0.0,
                "F1_macro_CON_OP": 0.0,
                "precision_etiqueta": 0.0,
                "cobertura_etiqueta": 0.0,
            },
            {
                "sistema": "B1",
                "F1_etiqueta": 0.5,
                "F1_uso_discursivo": 0.5,
                "F1_macro_CON_OP": 0.5,
                "precision_etiqueta": 0.5,
                "cobertura_etiqueta": 0.5,
            },
            {
                "sistema": "B1",
                "F1_etiqueta": 0.5,
                "F1_uso_discursivo": 0.5,
                "F1_macro_CON_OP": 0.5,
                "precision_etiqueta": 0.5,
                "cobertura_etiqueta": 0.5,
            },
        ]
    )

    summary = summary_systems(systems)

    assert len(summary) == 2
    assert list(summary["sistema"]) == ["B0", "B1"]
    assert summary.loc[0, "F1_etiqueta_mean"] == pytest.approx(0.5)
    assert summary.loc[0, "F1_etiqueta_std"] == pytest.approx(0.70710678, rel=1e-6)
    assert summary.loc[1, "F1_etiqueta_std"] == pytest.approx(0.0)
    assert summary.loc[1, "F1_etiqueta_mean"] == pytest.approx(0.5)


def test_replay_intervals_synthetic():
    """Two seeds, three comparisons each; flags follow the thread pattern.

    Seed 0: both threads favour M2 and M1 over B1, so the intervals for
    M2-B1 and M1-B1 exclude zero, while M2-M1 stays at zero.
    Seed 1: the threads split between M2 and B1, so every interval includes
    zero. The bootstrap is deterministic, so two calls must agree.
    """
    predictions = pd.DataFrame(
        [
            {
                "semilla": 0,
                "thread_id": "t1",
                "oro": "CON:ADICIÓN",
                "B1": NO,
                "M1": "CON:ADICIÓN",
                "M2": "CON:ADICIÓN",
            },
            {
                "semilla": 0,
                "thread_id": "t2",
                "oro": "OP:MODAL",
                "B1": NO,
                "M1": "OP:MODAL",
                "M2": "OP:MODAL",
            },
            {
                "semilla": 1,
                "thread_id": "t3",
                "oro": "CON:ADICIÓN",
                "B1": NO,
                "M1": NO,
                "M2": "CON:ADICIÓN",
            },
            {
                "semilla": 1,
                "thread_id": "t4",
                "oro": "OP:MODAL",
                "B1": "OP:MODAL",
                "M1": "OP:MODAL",
                "M2": NO,
            },
        ]
    )
    undetected = {0: {"t1": 0, "t2": 0}, 1: {"t3": 0, "t4": 0}}

    intervals = replay_intervals(predictions, undetected, n=1000)

    assert len(intervals) == 6
    assert list(intervals["comparacion"]) == [
        "M2 − B1",
        "M2 − M1",
        "M1 − B1",
        "M2 − B1",
        "M2 − M1",
        "M1 − B1",
    ]
    assert list(intervals["semilla"]) == [0, 0, 0, 1, 1, 1]
    assert intervals["excluye_cero"].tolist() == [
        True,
        False,
        True,
        False,
        False,
        False,
    ]
    assert intervals["IC_inf"].between(-1, 1).all()
    assert intervals["IC_sup"].between(-1, 1).all()
    assert replay_intervals(predictions, undetected, n=1000).equals(intervals)


def _published_systems():
    return pd.DataFrame(
        [
            {
                "sistema": "B0",
                "semilla": 0,
                "F1_etiqueta": 0.315,
                "abstencion": float("nan"),
            },
            {
                "sistema": "B1",
                "semilla": 0,
                "F1_etiqueta": 0.328,
                "abstencion": float("nan"),
            },
        ]
    )


def test_compare_tables_matches():
    """Identical tables produce no deviations, and NaN equals NaN."""
    published = _published_systems()

    assert compare_tables(published.copy(), published, ["sistema", "semilla"]) == []


def test_compare_tables_reports_deviation():
    """One perturbed cell is named with its key and column."""
    published = _published_systems()
    replayed = published.copy()
    replayed.loc[0, "F1_etiqueta"] = 0.316

    deviations = compare_tables(replayed, published, ["sistema", "semilla"])

    assert len(deviations) == 1
    assert "sistema=B0" in deviations[0]
    assert "semilla=0" in deviations[0]
    assert "F1_etiqueta" in deviations[0]


def test_compare_tables_rounds_to_three_decimals():
    """A difference below the third decimal is not a deviation."""
    published = _published_systems()
    replayed = published.copy()
    replayed.loc[0, "F1_etiqueta"] = 0.3154

    assert compare_tables(replayed, published, ["sistema", "semilla"]) == []

    replayed.loc[0, "F1_etiqueta"] = 0.3156
    deviations = compare_tables(replayed, published, ["sistema", "semilla"])
    assert len(deviations) == 1


def test_compare_tables_detects_missing_row():
    """A key absent from the replay is reported as missing."""
    published = _published_systems()
    replayed = published.iloc[:1].copy()

    deviations = compare_tables(replayed, published, ["sistema", "semilla"])

    assert len(deviations) == 1
    assert "sistema=B1" in deviations[0]
    assert "missing" in deviations[0]


def test_count_undetected_uses_test_threads():
    """Only undetected labels in the seed's frozen test threads count.

    ``c2`` is in seed 0's test set but has no prediction row for seed 0, so
    resolving test IDs through the predictions would miss its label. The
    reference resolves every test comment to its thread.
    """
    reference = pd.DataFrame(
        [
            {"comment_id": "c1", "thread_id": "t1", "semilla": 0},
            {"comment_id": "c2", "thread_id": "t2", "semilla": 1},
            {"comment_id": "c3", "thread_id": "t3", "semilla": 1},
        ]
    )
    undetected = pd.DataFrame(
        [
            {
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "oro": "CON:ADICIÓN",
            },
            {
                "comment_id": "c2",
                "thread_id": "t2",
                "unidad": "igual",
                "oro": "CON:CONSECUTIVO",
            },
            {
                "comment_id": "c3",
                "thread_id": "t3",
                "unidad": "pues",
                "oro": "CON:CONSECUTIVO",
            },
        ]
    )
    test_ids = {0: ["c1", "c2"], 1: ["c3"]}

    totals, per_thread = count_undetected(undetected, reference, test_ids)

    assert totals == {0: 2, 1: 1}
    assert per_thread == {0: {"t1": 1, "t2": 1}, 1: {"t3": 1}}


def test_traceability_counts():
    """Only M2 discourse predictions count; origin and correctness follow."""
    predictions = pd.DataFrame(
        [
            {
                "M2": "CON:ADICIÓN",
                "oro": "CON:ADICIÓN",
                "origen_M2": "listado",
                "revisar_categoria": False,
            },
            {
                "M2": "OP:MODAL",
                "oro": "OP:MODAL",
                "origen_M2": "modelo",
                "revisar_categoria": True,
            },
            {
                "M2": NO,
                "oro": "CON:ADICIÓN",
                "origen_M2": "modelo",
                "revisar_categoria": False,
            },
        ]
    )

    counts = traceability(predictions)

    assert counts == {
        "etiquetas_discursivas": 2,
        "fijadas_listado": 1,
        "fijadas_listado_correctas": 1,
        "elegidas_modelo": 1,
        "elegidas_modelo_correctas": 1,
        "revisar_categoria": 1,
    }


def _replay_fixture():
    """Two seeds, four candidates and two undetected labels."""
    predictions = pd.DataFrame(
        [
            {
                "semilla": 0,
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "oro": "CON:ADICIÓN",
                "B0": "CON:ADICIÓN",
                "B1": NO,
                "M1": "CON:ADICIÓN",
                "M2": "CON:ADICIÓN",
                "p_M1": 0.9,
                "p_M2": 0.9,
                "abstiene_M2": False,
                "origen_M2": "listado",
                "revisar_categoria": False,
            },
            {
                "semilla": 0,
                "comment_id": "c2",
                "thread_id": "t2",
                "unidad": "no",
                "oro": "OP:MODAL",
                "B0": "OP:MODAL",
                "B1": NO,
                "M1": "OP:MODAL",
                "M2": "OP:MODAL",
                "p_M1": 0.9,
                "p_M2": 0.9,
                "abstiene_M2": False,
                "origen_M2": "modelo",
                "revisar_categoria": False,
            },
            {
                "semilla": 1,
                "comment_id": "c4",
                "thread_id": "t4",
                "unidad": "ya",
                "oro": "CON:ADICIÓN",
                "B0": "CON:ADICIÓN",
                "B1": NO,
                "M1": "CON:ADICIÓN",
                "M2": "CON:ADICIÓN",
                "p_M1": 0.9,
                "p_M2": 0.9,
                "abstiene_M2": False,
                "origen_M2": "listado",
                "revisar_categoria": False,
            },
            {
                "semilla": 1,
                "comment_id": "c5",
                "thread_id": "t5",
                "unidad": "no",
                "oro": NO,
                "B0": NO,
                "B1": NO,
                "M1": NO,
                "M2": NO,
                "p_M1": 0.1,
                "p_M2": 0.1,
                "abstiene_M2": False,
                "origen_M2": "modelo",
                "revisar_categoria": False,
            },
        ]
    )
    reference = pd.DataFrame(
        [
            {
                "comment_id": "c1",
                "thread_id": "t1",
                "anotacion": "[ya::CON:ADICIÓN]",
            },
            {
                "comment_id": "c2",
                "thread_id": "t2",
                "anotacion": "[no::OP:MODAL]",
            },
            {
                "comment_id": "c3",
                "thread_id": "t3",
                "anotacion": "[pues::OP:MODAL]",
            },
            {
                "comment_id": "c4",
                "thread_id": "t4",
                "anotacion": "[ya::CON:ADICIÓN]",
            },
            {
                "comment_id": "c5",
                "thread_id": "t5",
                "anotacion": "[no::NO_DISCURSIVO]",
            },
            {
                "comment_id": "c6",
                "thread_id": "t6",
                "anotacion": "[pues::OP:MODAL]",
            },
        ]
    )
    listing = pd.DataFrame({"unidad": ["ya", "no"]})
    csl = pd.DataFrame({"comment_id": [], "unidad": []})
    published_systems = pd.DataFrame(
        [
            {"sistema": "M1 con abstención", "semilla": 0, "margen": 0.1},
            {"sistema": "M2 con abstención", "semilla": 0, "margen": 0.15},
            {"sistema": "M1 con abstención", "semilla": 1, "margen": 0.1},
            {"sistema": "M2 con abstención", "semilla": 1, "margen": 0.15},
        ]
    )
    test_files = {0: "c1\nc2\nc3\n", 1: "c4\nc5\nc6\n"}
    hashes = {
        str(seed): hashlib.sha256(text.encode("utf-8")).hexdigest()
        for seed, text in test_files.items()
    }
    return {
        "predictions": predictions,
        "reference": reference,
        "listing": listing,
        "csl": csl,
        "published": {
            "systems": published_systems,
            "summary": pd.DataFrame(),
            "intervals": pd.DataFrame(),
        },
        "hashes": hashes,
        "test_files": test_files,
    }


def test_replay_tables_synthetic():
    """The replay combines the tables and the diagnostics for two seeds."""
    fixture = _replay_fixture()

    result = replay(**fixture, n=200)

    assert isinstance(result, ReplayResult)
    assert len(result.systems) == 12
    assert len(result.summary) == 6
    assert len(result.intervals) == 6
    assert result.diagnostics.to_dict("records") == [
        {"semilla": 0, "candidatas": 2, "no_detectadas": 1},
        {"semilla": 1, "candidatas": 2, "no_detectadas": 1},
    ]
    assert result.traceability == {
        "etiquetas_discursivas": 3,
        "fijadas_listado": 2,
        "fijadas_listado_correctas": 2,
        "elegidas_modelo": 1,
        "elegidas_modelo_correctas": 1,
        "revisar_categoria": 0,
    }
    assert result.deviations == []
    systems = result.systems.set_index(["semilla", "sistema"])
    assert systems.loc[(0, "B0"), "F1_etiqueta"] == pytest.approx(0.8)
    assert systems.loc[(0, "B1"), "F1_etiqueta"] == pytest.approx(0.0)
    assert systems.loc[(0, "M2"), "F1_etiqueta"] == pytest.approx(0.8)
    assert systems.loc[(1, "B0"), "F1_etiqueta"] == pytest.approx(2 / 3)
    assert systems.loc[(1, "B1"), "F1_etiqueta"] == pytest.approx(0.0)
    assert systems.loc[(1, "M2"), "F1_etiqueta"] == pytest.approx(2 / 3)
    assert result.intervals["excluye_cero"].tolist() == [
        True,
        False,
        True,
        False,
        False,
        False,
    ]


def test_replay_reports_deviations_and_hashes():
    """A perturbed cell and a wrong hash are both named."""
    fixture = _replay_fixture()
    first = replay(**fixture, n=200)
    published = {
        "systems": first.systems.copy(),
        "summary": first.summary.copy(),
        "intervals": first.intervals.copy(),
    }
    published["systems"].loc[0, "F1_etiqueta"] = 0.123
    hashes = dict(fixture["hashes"])
    hashes["0"] = "0" * 64

    result = replay(
        **{**fixture, "published": published, "hashes": hashes}, n=200
    )

    assert any("F1_etiqueta" in deviation for deviation in result.deviations)
    assert any("hash" in deviation.lower() for deviation in result.deviations)


def test_cli_help(capsys):
    """The replay command exposes its options."""
    with pytest.raises(SystemExit) as excinfo:
        main(["replay", "--help"])

    assert excinfo.value.code == 0
    captured = capsys.readouterr()
    assert "--predictions" in captured.out
    assert "--reference" in captured.out
    assert "--listing" in captured.out
    assert "--csl" in captured.out
    assert "--published" in captured.out
    assert "--hashes" in captured.out
    assert "--test-ids" in captured.out
    assert "--output" in captured.out
    assert "--check" in captured.out
