"""Unit tests for the M1 feature builder and the frozen embedder."""

import sys
import types

import numpy as np
import pandas as pd
import pytest

from conectores.features import (
    EMBEDDING_MODEL,
    RASGOS,
    FeatureBuilder,
    sentence_embedder,
)


def _frame():
    """Three synthetic candidates with distinct flag patterns."""
    return pd.DataFrame(
        [
            {
                "ventana": "el bus [[ya]] llego",
                "unidad": "ya",
                "coma_antes": False,
                "coma_despues": False,
                "inicio_comentario": False,
                "inicio_oracion": True,
                "fin_enunciado": False,
                "is_reply": False,
            },
            {
                "ventana": "ya, pero no",
                "unidad": "ya",
                "coma_antes": False,
                "coma_despues": True,
                "inicio_comentario": False,
                "inicio_oracion": False,
                "fin_enunciado": False,
                "is_reply": True,
            },
            {
                "ventana": "por lo tanto [[ya]]",
                "unidad": "ya",
                "coma_antes": True,
                "coma_despues": False,
                "inicio_comentario": False,
                "inicio_oracion": False,
                "fin_enunciado": True,
                "is_reply": False,
            },
        ]
    )


def _fake_embedder(texts):
    """Return a 384-column array whose rows are easy to identify."""
    return np.vstack([np.full(384, float(index + 1)) for index in range(len(texts))])


def test_feature_builder_shapes():
    """The matrix has the flags block and the embedding block in that order."""
    train = _frame()
    embeddings = _fake_embedder(train["ventana"].tolist())
    builder = FeatureBuilder().fit(train, _fake_embedder)

    matrix = builder.transform(train)

    assert matrix.shape[0] == len(train)
    assert matrix.shape[1] > 390
    dense = matrix.toarray()
    assert np.allclose(dense[:, -384:], embeddings)
    assert np.array_equal(
        dense[:, -390:-384], train[RASGOS].astype(float).to_numpy()
    )


def test_feature_builder_rejects_wrong_embedding_dimension():
    """An embedder that does not return 384 columns is rejected."""
    train = _frame()
    builder = FeatureBuilder().fit(
        train, lambda texts: np.zeros((len(texts), 383))
    )

    with pytest.raises(ValueError, match="384"):
        builder.transform(train)


def test_feature_builder_fits_on_training_only():
    """An unseen test form adds no vocabulary column."""
    train = _frame()
    unseen = _frame().iloc[[0]].assign(
        ventana="otro contexto [[nueva]]", unidad="nueva"
    )
    builder = FeatureBuilder().fit(train, _fake_embedder)

    train_matrix = builder.transform(train)
    unseen_matrix = builder.transform(unseen)

    assert unseen_matrix.shape[1] == train_matrix.shape[1]


def test_feature_builder_requires_columns():
    """A missing candidate column is named in the error."""
    train = _frame()
    builder = FeatureBuilder().fit(train, _fake_embedder)

    for column in ("ventana", "unidad", *RASGOS):
        with pytest.raises(
            ValueError, match=f"candidates is missing required column: {column}"
        ):
            builder.transform(train.drop(columns=[column]))

    for column in ("ventana", "unidad"):
        with pytest.raises(
            ValueError, match=f"candidates is missing required column: {column}"
        ):
            FeatureBuilder().fit(train.drop(columns=[column]), _fake_embedder)


def _fake_sentence_transformers(created):
    """Build a fake sentence_transformers module for the wrapper tests."""

    class FakeSentenceTransformer:
        def __init__(self, model_name, device=None):
            self.model_name = model_name
            self.device = device
            self.encoded = []
            created.append(self)

        def encode(self, texts, batch_size=64, show_progress_bar=False):
            self.encoded.append(list(texts))
            return np.vstack(
                [np.full(384, float(index + 1)) for index in range(len(texts))]
            )

    return types.SimpleNamespace(SentenceTransformer=FakeSentenceTransformer)


def test_sentence_embedder_caches_and_returns_384(monkeypatch):
    """The wrapper caches by text and returns one 384-column row per input."""
    created = []
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _fake_sentence_transformers(created),
    )

    embedder = sentence_embedder()
    vectors = embedder(["alpha", "beta", "alpha"])

    assert vectors.shape == (3, 384)
    assert created[0].model_name == EMBEDDING_MODEL
    assert created[0].device == "cpu"
    assert created[0].encoded == [["alpha", "beta"]]
    assert np.allclose(vectors[0], vectors[2])
    assert not np.allclose(vectors[0], vectors[1])


def test_sentence_embedder_accepts_a_model_name(monkeypatch):
    """A custom model name is passed to the frozen-model constructor."""
    created = []
    monkeypatch.setitem(
        sys.modules,
        "sentence_transformers",
        _fake_sentence_transformers(created),
    )

    sentence_embedder("fake-model")

    assert created[0].model_name == "fake-model"


@pytest.mark.slow
def test_sentence_embedder_real_model():
    """The real frozen model returns a finite 384-column matrix."""
    pytest.importorskip("sentence_transformers")
    try:
        embedder = sentence_embedder()
    except Exception as exc:
        pytest.skip(f"frozen embedding model unavailable: {exc}")

    vectors = embedder(["un contexto sintético", "otro contexto sintético"])

    assert vectors.shape == (2, 384)
    assert np.isfinite(vectors).all()
