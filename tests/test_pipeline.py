"""Unit tests for the publication pipeline."""

import pandas as pd
import pytest

from conectores.candidates import NO
from conectores.pipeline import PIPELINE_COLUMNS, combine_predictions


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
