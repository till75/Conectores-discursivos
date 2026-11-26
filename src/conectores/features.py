"""Feature construction for the M1 replay slice."""

from __future__ import annotations

from collections.abc import Callable, Sequence

import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer

Embedder = Callable[[Sequence[str]], np.ndarray]

RASGOS = [
    "coma_antes",
    "coma_despues",
    "inicio_comentario",
    "inicio_oracion",
    "fin_enunciado",
    "is_reply",
]
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384


def sentence_embedder(model_name: str = EMBEDDING_MODEL) -> Embedder:
    """Return a callable that encodes windows with the frozen model."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name, device="cpu")
    cache: dict[str, np.ndarray] = {}

    def embed(texts: Sequence[str]) -> np.ndarray:
        new_texts = [
            text for text in dict.fromkeys(texts) if text not in cache
        ]
        if new_texts:
            vectors = model.encode(
                new_texts, batch_size=64, show_progress_bar=False
            )
            for text, vector in zip(new_texts, vectors, strict=True):
                cache[text] = vector
        return np.vstack([cache[text] for text in texts])

    return embed


def _require(frame: pd.DataFrame, columns: list[str]) -> None:
    """Raise when a required candidate column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"candidates is missing required column: {column}")


class FeatureBuilder:
    """Build the M1 feature matrix."""

    def fit(self, train: pd.DataFrame, embedder: Embedder) -> FeatureBuilder:
        _require(train, ["ventana", "unidad"])
        self.embedder = embedder
        self.word = TfidfVectorizer(
            ngram_range=(1, 2), min_df=1, sublinear_tf=True
        )
        self.char = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True
        )
        self.unit = TfidfVectorizer(analyzer=lambda unit: [unit])
        self.word.fit(train["ventana"])
        self.char.fit(train["ventana"])
        self.unit.fit(train["unidad"])
        return self

    def transform(self, df: pd.DataFrame) -> csr_matrix:
        _require(df, ["ventana", "unidad", *RASGOS])
        embedding = np.asarray(self.embedder(df["ventana"].tolist()))
        if embedding.shape != (len(df), EMBEDDING_DIM):
            raise ValueError(
                f"embedder returned shape {embedding.shape}; "
                f"expected ({len(df)}, {EMBEDDING_DIM})"
            )
        blocks = [
            self.word.transform(df["ventana"]),
            self.char.transform(df["ventana"]),
            self.unit.transform(df["unidad"]),
            csr_matrix(df[RASGOS].astype(float).to_numpy()),
            csr_matrix(embedding),
        ]
        return hstack(blocks).tocsr()
