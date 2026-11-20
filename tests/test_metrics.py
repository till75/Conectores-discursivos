"""Unit tests for the metric definitions."""

import pandas as pd
import pytest

from conectores.metrics import NO, compute_metrics, undetected_labels


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
