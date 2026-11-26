"""M1 model for the M1 replay slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from conectores.baselines import listing_label_map
from conectores.candidates import NO
from conectores.features import Embedder, FeatureBuilder

M1_COLUMNS = [
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


def _require(
    frame: pd.DataFrame, columns: list[str], name: str = "train"
) -> None:
    """Raise when a required model column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"{name} is missing required column: {column}")


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


def choose_margin(
    train: pd.DataFrame,
    labels: Mapping[str, Sequence[str]],
    embedder: Embedder,
    seed: int = 0,
    max_abstention: float = 0.2,
) -> float:
    """Return the margin chosen by grouped cross-validation on training."""
    folds = GroupKFold(n_splits=5)
    probabilities = np.zeros(len(train))
    for fit_index, hold_index in folds.split(
        train, groups=train["thread_id"]
    ):
        model = M1Model(labels, embedder, seed=seed).fit(train.iloc[fit_index])
        probabilities[hold_index] = model.prob(train.iloc[hold_index])

    truth = (train["oro"] != NO).to_numpy()
    best_margin, best_f1 = 0.0, -1.0
    for margin in np.arange(0, 0.31, 0.05):
        keep = np.abs(probabilities - 0.5) >= margin
        if 1 - keep.mean() > max_abstention or keep.sum() == 0:
            continue
        predicted = probabilities[keep] >= 0.5
        kept_truth = truth[keep]
        true_positives = int((predicted & kept_truth).sum())
        f1 = (
            0.0
            if true_positives == 0
            else 2 * true_positives / (predicted.sum() + kept_truth.sum())
        )
        if f1 > best_f1 + 1e-9:
            best_margin, best_f1 = round(float(margin), 2), f1
    return best_margin


def m1_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> pd.DataFrame:
    """Return one M1 row per test candidate per frozen split."""
    _require(
        candidates,
        ["comment_id", "thread_id", "unidad", "inicio", "oro"],
        "candidates",
    )
    _require(reference, ["comment_id", "thread_id"], "reference")
    labels = listing_label_map(listing)
    comment_to_thread = dict(
        zip(reference["comment_id"], reference["thread_id"], strict=True)
    )
    frames = []
    for seed, ids in test_ids.items():
        threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        test = candidates[candidates["thread_id"].isin(threads)]
        train = candidates[~candidates["thread_id"].isin(threads)]
        if test.empty:
            continue
        model = M1Model(labels, embedder, seed=int(seed)).fit(train)
        predicted, probabilities, _ = model.predict(test, 0.0)
        margin = choose_margin(train, labels, embedder, seed=int(seed))
        abstiene = np.abs(probabilities - 0.5) < margin
        abstained_labels = [
            NO if flag else label
            for label, flag in zip(predicted, abstiene, strict=True)
        ]
        frames.append(
            test.assign(
                semilla=int(seed),
                M1=predicted,
                p_M1=probabilities,
                abstiene=abstiene,
                M1_con_abstencion=abstained_labels,
            )
        )
    if not frames:
        return pd.DataFrame(columns=M1_COLUMNS)
    return pd.concat(frames, ignore_index=True)[M1_COLUMNS]
