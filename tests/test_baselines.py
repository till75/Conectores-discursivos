"""Unit tests for the B0 and B1 baselines."""

import pandas as pd
import pytest

import conectores.baselines as baselines


def _listing(*rows):
    """Build a synthetic listing from ``(unidad, macro, categoria, subcategoria)``."""
    return pd.DataFrame(
        [
            {
                "unidad": unidad,
                "macrofuncion": macro,
                "categoria": categoria,
                "subcategoria": subcategoria,
            }
            for unidad, macro, categoria, subcategoria in rows
        ]
    )


def test_listing_label_branches():
    """The four listing rules and the missing-value boundary."""
    assert baselines.listing_label("Operador", "Modal", "─") == "OP:MODAL"
    assert (
        baselines.listing_label(
            "Conector", "Ordenador de la materia discursiva", "De inicio"
        )
        == "CON:INICIO"
    )
    assert (
        baselines.listing_label(
            "Conector", "Ordenador de la materia discursiva", "Cierre"
        )
        == "CON:CIERRE"
    )
    assert (
        baselines.listing_label("Conector", "Reformulativo", "Explicación")
        == "CON:REFORMULATIVOS"
    )
    assert baselines.listing_label("Conector", "Adición", "─") == "CON:ADICIÓN"
    assert baselines.listing_label("Operador", "Modal", None) == "OP:MODAL"
    assert baselines.listing_label("Conector", None, None) == "CON:"


def test_listing_label_map_collapses_and_orders():
    """Sense numbers, case and duplicates collapse; labels keep listing order."""
    listing = _listing(
        ("Ya", "Conector", "Adición", "─"),
        ("ya 2", "Operador", "Modal", "─"),
        ("ya", "Conector", "Adición", "─"),
        ("bueno", "Conector", "Ordenador de la materia discursiva", "De inicio"),
        ("bueno 3", "Conector", "Ordenador de la materia discursiva", "Cierre"),
    )

    assert baselines.listing_label_map(listing) == {
        "ya": ["CON:ADICIÓN", "OP:MODAL"],
        "bueno": ["CON:INICIO", "CON:CIERRE"],
    }


def test_listing_label_map_requires_columns():
    """Every required listing column is named in the error that its absence raises."""
    listing = _listing(("ya", "Conector", "Adición", "─"))

    for column in ("unidad", "macrofuncion", "categoria", "subcategoria"):
        with pytest.raises(
            ValueError, match=f"listing is missing required column: {column}"
        ):
            baselines.listing_label_map(listing.drop(columns=[column]))


def test_b0_predict_first_label_and_unseen():
    """B0 takes the first listing label and falls back to NO for an unseen form."""
    test = pd.DataFrame(
        {
            "unidad": ["ya", "bueno", "nuevo"],
            "oro": ["NO_DISCURSIVO", "OP:MODAL", "OP:MODAL"],
            "texto": ["context one", "context two", "context three"],
        }
    )
    labels = {
        "ya": ["OP:MODAL"],
        "bueno": ["CON:CONTINUATIVO", "CON:CIERRE", "OP:MODAL"],
    }

    assert baselines.b0_predict(test, labels) == [
        "OP:MODAL",
        "CON:CONTINUATIVO",
        "NO_DISCURSIVO",
    ]


def test_b0_predict_requires_unidad():
    """B0 names the missing test column."""
    with pytest.raises(ValueError, match="test is missing required column: unidad"):
        baselines.b0_predict(pd.DataFrame({"oro": []}), {})


def _b1_fixture():
    """Training with a clear per-form majority and a global majority."""
    train = pd.DataFrame(
        {
            "unidad": ["ya", "ya", "ya", "bueno", "bueno", "bueno"],
            "oro": [
                "NO_DISCURSIVO",
                "NO_DISCURSIVO",
                "OP:MODAL",
                "OP:MODAL",
                "CON:INTERACTIVO",
                "OP:MODAL",
            ],
        }
    )
    test = pd.DataFrame(
        {
            "unidad": ["ya", "bueno", "nuevo"],
            "oro": ["NO_DISCURSIVO", "CON:INTERACTIVO", "OP:MODAL"],
        }
    )
    return train, test


def test_b1_predict_most_frequent():
    """B1 uses the most frequent training label and the global fallback."""
    train, test = _b1_fixture()

    assert baselines.b1_predict(train, test) == [
        "NO_DISCURSIVO",
        "OP:MODAL",
        "OP:MODAL",
    ]


def test_b1_predict_tie_uses_first_occurrence():
    """A per-form tie goes to the label that appears first in training."""
    train = pd.DataFrame(
        {
            "unidad": ["bueno", "bueno", "bueno", "bueno"],
            "oro": ["OP:MODAL", "CON:INTERACTIVO", "OP:MODAL", "CON:INTERACTIVO"],
        }
    )
    test = pd.DataFrame({"unidad": ["bueno"], "oro": ["CON:CIERRE"]})

    assert baselines.b1_predict(train, test) == ["OP:MODAL"]


def test_b1_predict_global_tie_uses_first_occurrence():
    """An unseen form uses the global majority with the same tie-break."""
    train = pd.DataFrame(
        {
            "unidad": ["ya", "ya", "ya", "ya"],
            "oro": ["OP:MODAL", "NO_DISCURSIVO", "OP:MODAL", "NO_DISCURSIVO"],
        }
    )
    test = pd.DataFrame({"unidad": ["nuevo"], "oro": ["NO_DISCURSIVO"]})

    assert baselines.b1_predict(train, test) == ["OP:MODAL"]


def test_b1_predict_requires_columns():
    """B1 names the missing train or test column."""
    train, test = _b1_fixture()

    for column in ("unidad", "oro"):
        with pytest.raises(
            ValueError, match=f"train is missing required column: {column}"
        ):
            baselines.b1_predict(train.drop(columns=[column]), test)
        with pytest.raises(
            ValueError, match=f"test is missing required column: {column}"
        ):
            baselines.b1_predict(train, test.drop(columns=[column]))


def _candidates_fixture():
    """Four candidates in three threads, with a listing and a reference."""
    candidates = pd.DataFrame(
        [
            {
                "comment_id": "c1",
                "thread_id": "t1",
                "unidad": "ya",
                "inicio": 0,
                "oro": "NO_DISCURSIVO",
            },
            {
                "comment_id": "c2",
                "thread_id": "t1",
                "unidad": "bueno",
                "inicio": 5,
                "oro": "CON:INTERACTIVO",
            },
            {
                "comment_id": "c3",
                "thread_id": "t2",
                "unidad": "ya",
                "inicio": 0,
                "oro": "OP:MODAL",
            },
            {
                "comment_id": "c4",
                "thread_id": "t3",
                "unidad": "nuevo",
                "inicio": 0,
                "oro": "NO_DISCURSIVO",
            },
        ]
    )
    reference = pd.DataFrame(
        [
            {"comment_id": "c1", "thread_id": "t1"},
            {"comment_id": "c2", "thread_id": "t1"},
            {"comment_id": "c3", "thread_id": "t2"},
            {"comment_id": "c4", "thread_id": "t3"},
        ]
    )
    listing = _listing(
        ("ya", "Operador", "Modal", "─"),
        ("bueno", "Conector", "Continuativo", "─"),
        ("bueno 2", "Conector", "Interactivo", "─"),
    )
    return candidates, reference, listing


def test_baseline_predictions_uses_reference_threads():
    """Test threads select rows; training is the complement; unknown IDs vanish."""
    candidates, reference, listing = _candidates_fixture()

    result = baselines.baseline_predictions(
        candidates, reference, listing, {0: ["c1"], 1: ["c3", "missing"], 2: []}
    )

    assert list(result.columns) == [
        "semilla",
        "comment_id",
        "thread_id",
        "unidad",
        "inicio",
        "oro",
        "B0",
        "B1",
    ]
    assert result.to_dict("records") == [
        {
            "semilla": 0,
            "comment_id": "c1",
            "thread_id": "t1",
            "unidad": "ya",
            "inicio": 0,
            "oro": "NO_DISCURSIVO",
            "B0": "OP:MODAL",
            "B1": "OP:MODAL",
        },
        {
            "semilla": 0,
            "comment_id": "c2",
            "thread_id": "t1",
            "unidad": "bueno",
            "inicio": 5,
            "oro": "CON:INTERACTIVO",
            "B0": "CON:CONTINUATIVO",
            "B1": "OP:MODAL",
        },
        {
            "semilla": 1,
            "comment_id": "c3",
            "thread_id": "t2",
            "unidad": "ya",
            "inicio": 0,
            "oro": "OP:MODAL",
            "B0": "OP:MODAL",
            "B1": "NO_DISCURSIVO",
        },
    ]


def test_baseline_predictions_requires_columns():
    """Each missing input column names its frame."""
    candidates, reference, listing = _candidates_fixture()

    for column in ("comment_id", "thread_id", "unidad", "oro", "inicio"):
        with pytest.raises(
            ValueError, match=f"candidates is missing required column: {column}"
        ):
            baselines.baseline_predictions(
                candidates.drop(columns=[column]), reference, listing, {0: ["c1"]}
            )

    for column in ("comment_id", "thread_id"):
        with pytest.raises(
            ValueError, match=f"reference is missing required column: {column}"
        ):
            baselines.baseline_predictions(
                candidates, reference.drop(columns=[column]), listing, {0: ["c1"]}
            )

    for column in ("unidad", "macrofuncion", "categoria", "subcategoria"):
        with pytest.raises(
            ValueError, match=f"listing is missing required column: {column}"
        ):
            baselines.baseline_predictions(
                candidates, reference, listing.drop(columns=[column]), {0: ["c1"]}
            )
