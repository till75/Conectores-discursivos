"""Unit tests for the frozen M2 context rules."""

import numpy as np
import pandas as pd
import pytest

from conectores.features import FeatureBuilder
from conectores.rules import (
    POS_COLUMNS,
    RULE_NAMES,
    M2FeatureBuilder,
    anotar_gramatica,
    aplicar_reglas,
)

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


class _Token:
    def __init__(self, idx, text, pos):
        self.idx = idx
        self.text = text
        self.pos_ = pos


class _NLP:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    def __call__(self, texto):
        self.calls.append(texto)
        return self.docs[texto]


def _grammar_frame(*rows):
    return pd.DataFrame(
        [
            {"texto": texto, "inicio": inicio, "unidad": unidad}
            for texto, inicio, unidad in rows
        ]
    )


def test_anotar_gramatica_offsets():
    nlp = _NLP(
        {
            "el tema nuevo": [
                _Token(0, "el", "DET"),
                _Token(3, "tema", "NOUN"),
                _Token(8, "nuevo", "ADJ"),
            ]
        }
    )
    cand = _grammar_frame(("el tema nuevo", 3, "tema"))

    result = anotar_gramatica(cand, nlp)

    assert list(result.columns) == ["texto", "inicio", "unidad", *POS_COLUMNS]
    assert result.loc[0, "pos_u"] == "NOUN"
    assert result.loc[0, "pos_ant"] == "DET"
    assert result.loc[0, "tok_ant"] == "el"
    assert result.loc[0, "pos_sig"] == "ADJ"
    assert result.loc[0, "tok_sig"] == "nuevo"


def test_anotar_gramatica_boundaries():
    nlp = _NLP(
        {
            "el tema": [
                _Token(0, "el", "DET"),
                _Token(3, "tema", "NOUN"),
            ],
            "el  tema": [
                _Token(0, "el", "DET"),
                _Token(4, "tema", "NOUN"),
            ],
        }
    )
    cand = _grammar_frame(
        ("el tema", 0, "el"),
        ("el tema", 3, "tema"),
        ("el  tema", 2, "zz"),
    )

    result = anotar_gramatica(cand, nlp)

    assert list(result.columns) == ["texto", "inicio", "unidad", *POS_COLUMNS]
    assert result.loc[0, "pos_ant"] == "INICIO"
    assert result.loc[0, "tok_ant"] == ""
    assert result.loc[1, "pos_sig"] == "FIN"
    assert result.loc[1, "tok_sig"] == ""
    assert result.loc[2, "pos_u"] == "X"
    assert result.loc[2, "pos_ant"] == "DET"
    assert result.loc[2, "pos_sig"] == "NOUN"


def test_anotar_gramatica_multiword_uses_first_token():
    nlp = _NLP(
        {
            "por lo tanto, ya": [
                _Token(0, "por", "ADP"),
                _Token(4, "lo", "PRON"),
                _Token(7, "tanto", "NOUN"),
                _Token(12, ",", "PUNCT"),
                _Token(14, "ya", "ADV"),
            ]
        }
    )
    cand = _grammar_frame(("por lo tanto, ya", 0, "por lo tanto"))

    result = anotar_gramatica(cand, nlp)

    assert list(result.columns) == ["texto", "inicio", "unidad", *POS_COLUMNS]
    assert result.loc[0, "pos_u"] == "ADP"
    assert result.loc[0, "pos_sig"] == "PUNCT"


def test_anotar_gramatica_caches_by_text():
    nlp = _NLP(
        {
            "el tema": [
                _Token(0, "el", "DET"),
                _Token(3, "tema", "NOUN"),
            ]
        }
    )
    cand = _grammar_frame(("el tema", 0, "el"), ("el tema", 3, "tema"))

    anotar_gramatica(cand, nlp)

    assert nlp.calls == ["el tema"]


def test_anotar_gramatica_does_not_modify_input():
    nlp = _NLP(
        {
            "el tema": [
                _Token(0, "el", "DET"),
                _Token(3, "tema", "NOUN"),
            ]
        }
    )
    cand = _grammar_frame(("el tema", 3, "tema"))

    anotar_gramatica(cand, nlp)

    assert list(cand.columns) == ["texto", "inicio", "unidad"]


@pytest.mark.parametrize("column", ["texto", "inicio", "unidad"])
def test_anotar_gramatica_requires_columns(column):
    nlp = _NLP({})
    cand = _grammar_frame(("el tema", 3, "tema")).drop(columns=[column])

    with pytest.raises(ValueError, match=column):
        anotar_gramatica(cand, nlp)


def _fake_embedder(texts):
    return np.ones((len(texts), 384))


def _m2_frame(**overrides):
    row = {
        "unidad": "ya",
        "inicio": 0,
        "texto": "ya, pero",
        "ventana": "[[ya]] , pero",
        "coma_antes": False,
        "coma_despues": True,
        "inicio_comentario": True,
        "inicio_oracion": False,
        "fin_enunciado": False,
        "is_reply": False,
        "pos_u": "ADV",
        "pos_ant": "INICIO",
        "pos_sig": "PUNCT",
        "tok_ant": "",
        "tok_sig": ",",
    }
    return pd.DataFrame([{**row, **overrides}])


def _m2_train():
    return pd.concat(
        [
            _m2_frame(),
            _m2_frame(
                unidad="pero",
                inicio=4,
                ventana="ya , [[pero]]",
                pos_u="CCONJ",
                pos_ant="PUNCT",
                pos_sig="FIN",
                tok_ant=",",
                tok_sig="",
            ),
        ],
        ignore_index=True,
    )


def test_m2_feature_builder_order():
    train = _m2_train()
    builder = M2FeatureBuilder()
    assert builder.fit(train, _fake_embedder) is builder

    base = FeatureBuilder().fit(train, _fake_embedder)
    matrix = builder.transform(train).toarray()
    base_matrix = base.transform(train).toarray()
    rules = aplicar_reglas(train).astype(float).to_numpy()
    base_width = base_matrix.shape[1]
    rule_width = len(RULE_NAMES)

    assert matrix.shape[0] == len(train)
    assert matrix.shape[1] > base_width + rule_width
    assert np.array_equal(matrix[:, :base_width], base_matrix)
    assert np.array_equal(
        matrix[:, base_width : base_width + rule_width],
        rules,
    )

    names = list(builder.dv.get_feature_names_out())
    assert "u=ADV" in names
    assert "ant=INICIO" in names
    assert "sig=PUNCT" in names
    assert "ya|sig=PUNCT" in names
    assert "ya|ant=INICIO" in names


def test_m2_feature_builder_unseen_pos():
    train = _m2_train()
    builder = M2FeatureBuilder().fit(train, _fake_embedder)
    seen = builder.transform(train.iloc[[0]]).toarray()
    unseen = builder.transform(_m2_frame(pos_sig="NOUN")).toarray()
    base_width = FeatureBuilder().fit(
        train, _fake_embedder
    ).transform(train).shape[1]
    pos_start = base_width + len(RULE_NAMES)

    assert seen.shape[1] > pos_start
    assert unseen.shape[1] == seen.shape[1]

    names = list(builder.dv.get_feature_names_out())
    assert "sig=NOUN" not in names
    assert "ya|sig=NOUN" not in names
    for name in ("sig=PUNCT", "ya|sig=PUNCT"):
        assert unseen[0, pos_start + names.index(name)] == 0
    for name in ("u=ADV", "ant=INICIO", "ya|ant=INICIO"):
        assert unseen[0, pos_start + names.index(name)] == 1


def test_m2_feature_builder_requires_pos_columns():
    train = _m2_frame().drop(columns=["pos_sig"])

    with pytest.raises(ValueError, match="pos_sig"):
        M2FeatureBuilder().fit(train, _fake_embedder)
