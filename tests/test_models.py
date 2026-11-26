"""Unit tests for the M1 model."""

import inspect

import numpy as np
import pandas as pd
import pytest

from conectores import models
from conectores.candidates import NO
from conectores.models import M1Model, choose_margin, m1_predictions


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


def _prediction_fixture():
    """Six threads, each with one alpha, one beta and one gamma row."""
    rows = []
    for index in range(18):
        thread = f"t{index % 6 + 1}"
        kind = (index // 6) % 3
        if kind == 0:
            window, gold = "alpha context [[ya]]", "CON:ADICIÓN"
        elif kind == 1:
            window, gold = "beta context [[ya]]", "OP:MODAL"
        else:
            window, gold = "gamma context [[ya]]", NO
        row = _candidate(window, "ya", gold)
        row.update(
            {
                "comment_id": f"c{index + 1}",
                "thread_id": thread,
                "inicio": 0,
            }
        )
        rows.append(row)
    candidates = pd.DataFrame(rows)
    reference = candidates[["comment_id", "thread_id"]].drop_duplicates()
    listing = pd.DataFrame(
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
    return candidates, reference, listing


def test_m1_predictions_uses_reference_threads():
    """Test threads select rows; training is the complement."""
    candidates, reference, listing = _prediction_fixture()

    result = m1_predictions(
        candidates,
        reference,
        listing,
        {0: ["c1"], 1: ["c2"]},
        _fake_embedder,
    )

    assert list(result.columns) == [
        "semilla",
        "comment_id",
        "thread_id",
        "unidad",
        "inicio",
        "oro",
        "M1",
        "p_M1",
        "abstiene",
        "M1_con_abstencion",
    ]
    assert result.groupby("semilla").size().to_dict() == {0: 3, 1: 3}
    expected = {
        (0, "c1"): "CON:ADICIÓN",
        (0, "c7"): "OP:MODAL",
        (0, "c13"): NO,
        (1, "c2"): "CON:ADICIÓN",
        (1, "c8"): "OP:MODAL",
        (1, "c14"): NO,
    }
    records = result[["semilla", "comment_id", "M1"]].to_dict("records")
    assert {
        (record["semilla"], record["comment_id"]): record["M1"]
        for record in records
    } == expected
    assert result["p_M1"].between(0, 1).all()
    assert result["abstiene"].dtype == bool
    abstained = result[result["abstiene"]]
    assert (abstained["M1_con_abstencion"] == NO).all()
    kept = result[~result["abstiene"]]
    assert (kept["M1_con_abstencion"] == kept["M1"]).all()


def test_m1_predictions_ignores_unknown_and_empty():
    """Unknown IDs are ignored; an empty seed contributes no rows."""
    candidates, reference, listing = _prediction_fixture()

    result = m1_predictions(
        candidates,
        reference,
        listing,
        {0: ["c1", "missing"], 1: []},
        _fake_embedder,
    )

    assert result.groupby("semilla").size().to_dict() == {0: 3}
    assert set(result["comment_id"]) == {"c1", "c7", "c13"}


def test_m1_predictions_excludes_test_threads_from_training(monkeypatch):
    """No training frame, including CV folds, contains the test thread."""
    candidates, reference, listing = _prediction_fixture()
    captured = []

    class _CaptureModel(M1Model):
        def fit(self, train):
            captured.append(set(train["thread_id"]))
            return super().fit(train)

    monkeypatch.setattr(models, "M1Model", _CaptureModel)

    m1_predictions(candidates, reference, listing, {0: ["c1"]}, _fake_embedder)

    assert captured
    assert all("t1" not in threads for threads in captured)


def test_m1_predictions_all_empty():
    """No test threads returns an empty frame with the contract columns."""
    candidates, reference, listing = _prediction_fixture()

    result = m1_predictions(
        candidates,
        reference,
        listing,
        {0: ["missing"], 1: []},
        _fake_embedder,
    )

    assert result.empty
    assert list(result.columns) == [
        "semilla",
        "comment_id",
        "thread_id",
        "unidad",
        "inicio",
        "oro",
        "M1",
        "p_M1",
        "abstiene",
        "M1_con_abstencion",
    ]


def test_m1_predictions_requires_columns():
    """Each missing input column names its frame."""
    candidates, reference, listing = _prediction_fixture()

    for column in ("comment_id", "thread_id", "unidad", "inicio", "oro"):
        with pytest.raises(
            ValueError, match=f"candidates is missing required column: {column}"
        ):
            m1_predictions(
                candidates.drop(columns=[column]),
                reference,
                listing,
                {0: ["c1"]},
                _fake_embedder,
            )

    for column in ("comment_id", "thread_id"):
        with pytest.raises(
            ValueError, match=f"reference is missing required column: {column}"
        ):
            m1_predictions(
                candidates,
                reference.drop(columns=[column]),
                listing,
                {0: ["c1"]},
                _fake_embedder,
            )

    for column in ("unidad", "macrofuncion", "categoria", "subcategoria"):
        with pytest.raises(
            ValueError, match=f"listing is missing required column: {column}"
        ):
            m1_predictions(
                candidates,
                reference,
                listing.drop(columns=[column]),
                {0: ["c1"]},
                _fake_embedder,
            )


def test_m1_output_has_no_text():
    """The prediction frame drops the window and any text column."""
    candidates, reference, listing = _prediction_fixture()
    candidates = candidates.assign(texto="hola @name")

    result = m1_predictions(
        candidates, reference, listing, {0: ["c1"]}, _fake_embedder
    )

    assert "texto" not in result.columns
    assert "ventana" not in result.columns
    assert "author_hash" not in result.columns
    assert not any("@" in str(value) for value in result.to_numpy().ravel())
