"""Unit tests for the frozen M2 context rules."""

import pandas as pd
import pytest

from conectores.rules import RULE_NAMES, aplicar_reglas

FROZEN_RULES = [
    "sig_det_o_num",
    "sig_verbo",
    "ant_verbo",
    "sig_adj_o_adv",
    "ant_det",
    "ant_prep",
    "sig_que",
    "aislada_por_comas",
    "fin_tras_verbo",
    "en_pregunta",
    "hasta_preposicion",
    "ya_temporal",
    "ya_operador",
    "solo_adjetivo",
    "mas_comparativo",
]

BASE_ROW = {
    "unidad": "x",
    "inicio": 0,
    "texto": "x",
    "coma_antes": False,
    "coma_despues": False,
    "inicio_comentario": True,
    "inicio_oracion": False,
    "fin_enunciado": False,
    "is_reply": False,
    "pos_u": "X",
    "pos_ant": "INICIO",
    "pos_sig": "FIN",
    "tok_ant": "",
    "tok_sig": "",
}


def _frame(**overrides):
    """Build a one-row candidate frame with the synthetic defaults."""
    return pd.DataFrame([{**BASE_ROW, **overrides}])


def test_rule_names_are_frozen():
    assert RULE_NAMES == FROZEN_RULES


def test_aplicar_reglas_neutral_row_is_false():
    result = aplicar_reglas(_frame())
    assert list(result.columns) == FROZEN_RULES
    assert not result.loc[0].any()


@pytest.mark.parametrize(
    ("rule", "overrides"),
    [
        ("sig_det_o_num", {"pos_sig": "DET"}),
        ("sig_verbo", {"pos_sig": "VERB"}),
        ("ant_verbo", {"pos_ant": "AUX"}),
        ("sig_adj_o_adv", {"pos_sig": "ADV"}),
        ("ant_det", {"pos_ant": "DET"}),
        ("ant_prep", {"pos_ant": "ADP"}),
        ("sig_que", {"tok_sig": "que"}),
        (
            "aislada_por_comas",
            {"coma_despues": True, "inicio_oracion": True},
        ),
        ("fin_tras_verbo", {"pos_ant": "VERB", "fin_enunciado": True}),
        (
            "en_pregunta",
            {"unidad": "ya", "inicio": 1, "texto": "¿ya?"},
        ),
        ("hasta_preposicion", {"unidad": "hasta", "pos_sig": "NOUN"}),
        ("ya_temporal", {"unidad": "ya", "pos_sig": "VERB"}),
        (
            "ya_operador",
            {
                "unidad": "ya",
                "inicio_oracion": True,
                "coma_despues": True,
            },
        ),
        (
            "solo_adjetivo",
            {
                "unidad": "solo",
                "pos_ant": "VERB",
                "fin_enunciado": True,
            },
        ),
        ("mas_comparativo", {"unidad": "más", "pos_sig": "ADJ"}),
    ],
)
def test_aplicar_reglas_each_rule(rule, overrides):
    result = aplicar_reglas(_frame(**overrides))
    assert rule in result.columns
    assert bool(result.loc[0, rule]) is True


def test_aplicar_reglas_requires_columns():
    frame = _frame().drop(columns=["pos_sig"])
    with pytest.raises(ValueError, match="pos_sig"):
        aplicar_reglas(frame)
