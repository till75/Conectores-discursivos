"""Unit tests for the metric definitions."""

import pytest

from conectores.metrics import NO, compute_metrics


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
