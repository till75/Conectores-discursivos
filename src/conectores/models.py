"""M1 model for the M1 replay slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

from conectores.candidates import NO
from conectores.features import Embedder, FeatureBuilder


def _require(frame: pd.DataFrame, columns: list[str]) -> None:
    """Raise when a required model column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"train is missing required column: {column}")


class M1Model:
    """Two-step logistic regression for M1."""

    def __init__(
        self,
        labels: Mapping[str, Sequence[str]],
        embedder: Embedder,
        seed: int = 0,
        C: float = 1.0,
    ):
        self.labels = labels
        self.embedder = embedder
        self.seed = seed
        self.C = C

    def fit(self, train: pd.DataFrame) -> M1Model:
        _require(train, ["oro"])
        if train.empty:
            raise ValueError("train is empty")
        self.builder = FeatureBuilder().fit(train, self.embedder)
        X = self.builder.transform(train)
        y1 = (train["oro"] != NO).astype(int).to_numpy()
        classes = np.unique(y1)
        if len(classes) > 1:
            self.c1 = LogisticRegression(
                C=self.C,
                class_weight="balanced",
                max_iter=2000,
                random_state=self.seed,
            ).fit(X, y1)
            self.c1_constant = None
        else:
            self.c1 = None
            self.c1_constant = float(classes[0])
        pos = train["oro"] != NO
        self.vistas = train[pos].groupby("unidad")["oro"].apply(set).to_dict()
        if pos.sum() and train.loc[pos, "oro"].nunique() > 1:
            self.c2 = LogisticRegression(
                C=self.C, max_iter=2000, random_state=self.seed
            ).fit(X[pos.to_numpy()], train.loc[pos, "oro"])
        else:
            self.c2 = None
            self.unica = train.loc[pos, "oro"].iloc[0] if pos.sum() else NO
        return self

    def prob(self, df: pd.DataFrame) -> np.ndarray:
        if self.c1 is None:
            return np.full(len(df), self.c1_constant)
        return self.c1.predict_proba(self.builder.transform(df))[:, 1]

    def predict(
        self, df: pd.DataFrame, margin: float = 0.0
    ) -> tuple[list[str], np.ndarray, np.ndarray]:
        X = self.builder.transform(df)
        if self.c1 is None:
            probabilities = np.full(len(df), self.c1_constant)
        else:
            probabilities = self.c1.predict_proba(X)[:, 1]
        P2 = self.c2.predict_proba(X) if self.c2 is not None else None
        classes = list(self.c2.classes_) if self.c2 is not None else []
        out = []
        abstention = []
        for index, unit in enumerate(df["unidad"]):
            if abs(probabilities[index] - 0.5) < margin:
                out.append(NO)
                abstention.append(True)
                continue
            abstention.append(False)
            if probabilities[index] < 0.5:
                out.append(NO)
                continue
            if P2 is None:
                out.append(self.unica)
                continue
            permitted = set(self.labels.get(unit, [])) | self.vistas.get(
                unit, set()
            )
            order = np.argsort(-P2[index])
            out.append(
                next(
                    (classes[j] for j in order if classes[j] in permitted),
                    classes[order[0]],
                )
            )
        return out, probabilities, np.array(abstention)
