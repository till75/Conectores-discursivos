"""Unit tests for the M1 model."""

import inspect

import numpy as np
import pandas as pd
import pytest

from conectores import models
from conectores.candidates import NO
from conectores.models import M1Model, choose_margin


def _candidate(window, unit, gold):
    """One synthetic candidate row."""
    return {
        "ventana": window,
        "unidad": unit,
        "oro": gold,
        "coma_antes": False,
        "coma_despues": False,
        "inicio_comentario": False,
        "inicio_oracion": False,
        "fin_enunciado": False,
        "is_reply": False,
    }


def _train():
    """Five examples of each class, with a linearly separable embedding."""
    rows = []
    rows.extend(
        _candidate("alpha context [[ya]]", "ya", "CON:ADICIÓN") for _ in range(5)
    )
    rows.extend(
        _candidate("beta context [[ya]]", "ya", "OP:MODAL") for _ in range(5)
    )
    rows.extend(_candidate("gamma context [[ya]]", "ya", NO) for _ in range(5))
    return pd.DataFrame(rows)


def _test(window, unit="ya", gold="OP:MODAL"):
    """One synthetic test row."""
    return pd.DataFrame([_candidate(window, unit, gold)])


def _fake_embedder(texts):
    """Encode alpha, beta and gamma in separate coordinates."""
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


LABELS = {"ya": ["CON:ADICIÓN", "OP:MODAL"]}


def test_m1_predicts_permitted_category():
    """A positive row returns a category allowed for its form."""
    model = M1Model(LABELS, _fake_embedder).fit(_train())
    test = _test("beta context [[ya]]")

    labels, probabilities, abstention = model.predict(test, 0.0)

    assert labels == ["OP:MODAL"]
    assert probabilities.shape == (1,)
    assert probabilities[0] > 0.5
    assert bool(abstention[0]) is False
    assert np.allclose(model.prob(test), probabilities)


def test_m1_single_allowed_label():
    """The listing can restrict a form to one label."""
    model = M1Model({"nueva": ["CON:ADICIÓN"]}, _fake_embedder).fit(_train())

    labels, _, _ = model.predict(
        _test("beta context [[nueva]]", unit="nueva"), 0.0
    )

    assert labels == ["CON:ADICIÓN"]


def test_m1_training_labels_extend_the_listing():
    """A label seen in training is allowed even when the listing omits it."""
    model = M1Model({"ya": ["CON:ADICIÓN"]}, _fake_embedder).fit(_train())

    labels, _, _ = model.predict(_test("beta context [[ya]]"), 0.0)

    assert labels == ["OP:MODAL"]


def test_m1_falls_back_to_top_class():
    """With no allowed class, the highest-probability class wins."""
    model = M1Model({"nueva": []}, _fake_embedder).fit(_train())

    labels, _, _ = model.predict(
        _test("beta context [[nueva]]", unit="nueva"), 0.0
    )

    assert labels == ["OP:MODAL"]


def test_m1_single_positive_label():
    """One positive label means step 2 cannot fit; the label is returned."""
    rows = []
    rows.extend(
        _candidate("alpha context [[ya]]", "ya", "CON:ADICIÓN") for _ in range(5)
    )
    rows.extend(_candidate("gamma context [[ya]]", "ya", NO) for _ in range(5))
    model = M1Model({"ya": ["CON:ADICIÓN"]}, _fake_embedder).fit(
        pd.DataFrame(rows)
    )

    labels, _, _ = model.predict(
        _test("alpha context [[ya]]", gold="CON:ADICIÓN"), 0.0
    )

    assert model.c2 is None
    assert model.unica == "CON:ADICIÓN"
    assert labels == ["CON:ADICIÓN"]


def test_m1_no_positive_training():
    """No positive rows leaves NO as the fallback."""
    train = pd.DataFrame(
        [_candidate("gamma context [[ya]]", "ya", NO) for _ in range(5)]
    )
    model = M1Model({"ya": ["OP:MODAL"]}, _fake_embedder).fit(train)

    labels, _, _ = model.predict(_test("gamma context [[ya]]", gold=NO), 0.0)

    assert model.c2 is None
    assert model.unica == NO
    assert labels == [NO]


def test_m1_abstains_near_half():
    """A wide margin returns NO_DISCURSIVO and flags the abstention."""
    model = M1Model(LABELS, _fake_embedder).fit(_train())

    labels, probabilities, abstention = model.predict(
        _test("beta context [[ya]]"), 0.6
    )

    assert labels == [NO]
    assert bool(abstention[0]) is True
    assert probabilities[0] > 0.5


def test_m1_negative_without_abstention():
    """A clear negative returns NO_DISCURSIVO without abstaining."""
    model = M1Model(LABELS, _fake_embedder).fit(_train())

    labels, probabilities, abstention = model.predict(
        _test("gamma context [[ya]]", gold=NO), 0.0
    )

    assert labels == [NO]
    assert bool(abstention[0]) is False
    assert probabilities[0] < 0.5


def test_m1_requires_gold_label():
    """The model names the missing oro column."""
    with pytest.raises(
        ValueError, match="train is missing required column: oro"
    ):
        M1Model(LABELS, _fake_embedder).fit(_train().drop(columns=["oro"]))


def test_m1_requires_non_empty_training():
    """An empty training frame is rejected with a clear message."""
    with pytest.raises(ValueError, match="train is empty"):
        M1Model(LABELS, _fake_embedder).fit(_train().iloc[0:0])


class _ProbModel:
    """A model whose probability is the row's ``p`` column."""

    def __init__(self, labels, embedder, seed=0):
        self.labels = labels

    def fit(self, train):
        return self

    def prob(self, df):
        return df["p"].to_numpy()


def _margin_train():
    """Eleven rows where 0.05 and 0.10 tie, and 0.05 must win."""
    rows = []
    for index in range(11):
        if index < 5:
            gold, probability = "CON:ADICIÓN", 0.9
        elif index < 9:
            gold, probability = NO, 0.1
        elif index == 9:
            gold, probability = NO, 0.51
        else:
            gold, probability = NO, 0.45
        rows.append(
            {
                "thread_id": f"t{index % 5}",
                "oro": gold,
                "p": probability,
            }
        )
    return pd.DataFrame(rows)


def test_choose_margin_uses_training_only():
    """The margin function has no test input."""
    assert "test" not in inspect.signature(choose_margin).parameters


def test_choose_margin_tie_keeps_smaller(monkeypatch):
    """A tie between 0.05 and 0.10 keeps the smaller margin."""
    monkeypatch.setattr(models, "M1Model", _ProbModel)

    margin = choose_margin(_margin_train(), LABELS, _fake_embedder)

    assert margin == 0.05
