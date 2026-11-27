"""Models for the M1 and M2 replay slices."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

from conectores.baselines import listing_label_map
from conectores.candidates import NO
from conectores.features import Embedder, FeatureBuilder
from conectores.metrics import (
    compare_tables,
    compute_metrics,
    count_undetected,
    summary_systems,
)
from conectores.rules import MIN_EJEMPLOS, POS_COLUMNS, M2FeatureBuilder

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

M2_COLUMNS = [
    "semilla",
    "comment_id",
    "thread_id",
    "unidad",
    "inicio",
    "oro",
    "M2",
    "p_M2",
    "origen_M2",
    "revisar_categoria",
    "abstiene_M2",
]

M2_INPUT_COLUMNS = [
    "comment_id",
    "thread_id",
    "unidad",
    "inicio",
    "oro",
    "texto",
    "ventana",
    "coma_antes",
    "coma_despues",
    "inicio_comentario",
    "inicio_oracion",
    "fin_enunciado",
    "is_reply",
    "pos_u",
    "pos_ant",
    "pos_sig",
    "tok_ant",
    "tok_sig",
]

METRIC_COLUMNS = [
    "F1_etiqueta",
    "F1_uso_discursivo",
    "F1_macro_CON_OP",
    "precision_etiqueta",
    "cobertura_etiqueta",
]


@dataclass(frozen=True)
class M1Result:
    """The rebuilt M1 tables and their deviations from the published ones."""

    predictions: pd.DataFrame
    metrics: pd.DataFrame
    summary: pd.DataFrame
    margins: Mapping[int, float]
    deviations: list[str]


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

    def _make_builder(self, train: pd.DataFrame) -> FeatureBuilder:
        return FeatureBuilder().fit(train, self.embedder)

    def fit(self, train: pd.DataFrame) -> M1Model:
        _require(train, ["oro"])
        if train.empty:
            raise ValueError("train is empty")
        self.builder = self._make_builder(train)
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


class M2Model(M1Model):
    """M2: M1 plus the strict listing, rules, POS and provenance."""

    def _make_builder(self, train: pd.DataFrame) -> M2FeatureBuilder:
        return M2FeatureBuilder().fit(train, self.embedder)

    def fit(self, train: pd.DataFrame) -> M2Model:
        _require(train, ["oro", *POS_COLUMNS])
        if train.empty:
            raise ValueError("train is empty")
        super().fit(train)
        positive = train["oro"] != NO
        self.n_cat = train.loc[positive, "oro"].value_counts().to_dict()
        return self

    def predict(
        self, df: pd.DataFrame, margin: float = 0.0
    ) -> tuple[list[str], np.ndarray, np.ndarray, list[str], np.ndarray]:
        X = self.builder.transform(df)
        if self.c1 is None:
            probabilities = np.full(len(df), self.c1_constant)
        else:
            probabilities = self.c1.predict_proba(X)[:, 1]
        P2 = self.c2.predict_proba(X) if self.c2 is not None else None
        classes = list(self.c2.classes_) if self.c2 is not None else []
        out = []
        abstention = []
        origin = []
        review = []
        for index, unit in enumerate(df["unidad"]):
            admitted = self.labels.get(unit, [])
            if not admitted:
                raise ValueError(
                    f"unit has no admitted category: {unit}"
                )
            if abs(probabilities[index] - 0.5) < margin:
                out.append(NO)
                abstention.append(True)
                origin.append("modelo")
                review.append(False)
                continue
            abstention.append(False)
            if probabilities[index] < 0.5:
                out.append(NO)
                origin.append("modelo")
                review.append(False)
                continue
            if len(admitted) == 1:
                label = admitted[0]
                source = "listado"
            elif P2 is not None:
                order = [
                    classes[j]
                    for j in np.argsort(-P2[index])
                    if classes[j] in admitted
                ]
                if order:
                    label = order[0]
                    source = "modelo"
                else:
                    label = admitted[0]
                    source = "listado"
            else:
                label = admitted[0]
                source = "listado"
            out.append(label)
            origin.append(source)
            review.append(self.n_cat.get(label, 0) < MIN_EJEMPLOS)
        return (
            out,
            probabilities,
            np.array(abstention),
            origin,
            np.array(review),
        )


def choose_margin_for(
    model_cls: type[M1Model],
    train: pd.DataFrame,
    labels: Mapping[str, Sequence[str]],
    embedder: Embedder,
    seed: int = 0,
    max_abstention: float = 0.2,
) -> float:
    """Return the margin chosen by grouped CV on training."""
    folds = GroupKFold(n_splits=5)
    probabilities = np.zeros(len(train))
    for fit_index, hold_index in folds.split(
        train, groups=train["thread_id"]
    ):
        model = model_cls(labels, embedder, seed=seed).fit(
            train.iloc[fit_index]
        )
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


def choose_margin(
    train: pd.DataFrame,
    labels: Mapping[str, Sequence[str]],
    embedder: Embedder,
    seed: int = 0,
    max_abstention: float = 0.2,
) -> float:
    """Return the margin chosen by grouped cross-validation on training."""
    return choose_margin_for(
        M1Model, train, labels, embedder, seed, max_abstention
    )


def _m1_predictions_and_margins(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> tuple[pd.DataFrame, dict[int, float]]:
    """Return the M1 rows and the learned margin for each seed."""
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
    margins = {}
    for seed, ids in test_ids.items():
        seed = int(seed)
        threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        test = candidates[candidates["thread_id"].isin(threads)]
        train = candidates[~candidates["thread_id"].isin(threads)]
        if test.empty:
            continue
        model = M1Model(labels, embedder, seed=seed).fit(train)
        predicted, probabilities, _ = model.predict(test, 0.0)
        margin = choose_margin(train, labels, embedder, seed=seed)
        margins[seed] = margin
        abstiene = np.abs(probabilities - 0.5) < margin
        abstained_labels = [
            NO if flag else label
            for label, flag in zip(predicted, abstiene, strict=True)
        ]
        frames.append(
            test.assign(
                semilla=seed,
                M1=predicted,
                p_M1=probabilities,
                abstiene=abstiene,
                M1_con_abstencion=abstained_labels,
            )
        )
    if not frames:
        return pd.DataFrame(columns=M1_COLUMNS), margins
    return pd.concat(frames, ignore_index=True)[M1_COLUMNS], margins


def m1_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> pd.DataFrame:
    """Return one M1 row per test candidate per frozen split."""
    predictions, _ = _m1_predictions_and_margins(
        candidates, reference, listing, test_ids, embedder
    )
    return predictions


def m2_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> pd.DataFrame:
    """Return one M2 row per test candidate per frozen split."""
    _require(candidates, M2_INPUT_COLUMNS, "candidates")
    _require(reference, ["comment_id", "thread_id"], "reference")
    _require(
        listing,
        ["unidad", "macrofuncion", "categoria", "subcategoria"],
        "listing",
    )
    labels = listing_label_map(listing)
    comment_to_thread = dict(
        zip(reference["comment_id"], reference["thread_id"], strict=True)
    )
    frames = []
    for seed, ids in test_ids.items():
        seed = int(seed)
        threads = {
            comment_to_thread[comment_id]
            for comment_id in ids
            if comment_id in comment_to_thread
        }
        test = candidates[candidates["thread_id"].isin(threads)]
        train = candidates[~candidates["thread_id"].isin(threads)]
        if test.empty:
            continue
        model = M2Model(labels, embedder, seed=seed).fit(train)
        predicted, probabilities, _, origin, review = model.predict(
            test, 0.0
        )
        margin = choose_margin_for(
            M2Model, train, labels, embedder, seed=seed
        )
        abstiene = np.abs(probabilities - 0.5) < margin
        frames.append(
            test.assign(
                semilla=seed,
                M2=predicted,
                p_M2=probabilities,
                origen_M2=origin,
                revisar_categoria=review,
                abstiene_M2=abstiene,
            )
        )
    if not frames:
        return pd.DataFrame(columns=M2_COLUMNS)
    return pd.concat(frames, ignore_index=True)[M2_COLUMNS]


def _format_key(keys: Sequence[str], key: Sequence[object]) -> str:
    """Format a row key as ``semilla=0, comment_id=c1``."""
    return ", ".join(
        f"{name}={value}" for name, value in zip(keys, key, strict=True)
    )


def _compare_m1_predictions(
    rebuilt: pd.DataFrame, published: pd.DataFrame
) -> list[str]:
    """Return one named deviation per missing row or changed prediction."""
    keys = ["semilla", "comment_id", "unidad", "inicio"]
    merged = rebuilt.merge(
        published,
        on=keys,
        how="outer",
        suffixes=("_replay", "_published"),
        indicator=True,
    )
    deviations = []
    for _, row in merged.iterrows():
        key = _format_key(keys, tuple(row[column] for column in keys))
        if row["_merge"] == "left_only":
            deviations.append(f"{key}: missing from published")
            continue
        if row["_merge"] == "right_only":
            deviations.append(f"{key}: missing from replay")
            continue
        for column in ("oro", "M1"):
            actual = row[f"{column}_replay"]
            expected = row[f"{column}_published"]
            if actual != expected:
                deviations.append(
                    f"{key}, {column}: replay {actual!r} != published {expected!r}"
                )
        difference = abs(
            float(row["p_M1_replay"]) - float(row["p_M1_published"])
        )
        if difference > 1e-5:
            deviations.append(
                f"{key}, p_M1: replay {row['p_M1_replay']!r} "
                f"!= published {row['p_M1_published']!r}"
            )
    return deviations


def replay_m1(
    candidate_set,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    published: Mapping[str, pd.DataFrame],
    embedder: Embedder,
) -> M1Result:
    """Rebuild M1 and compare it with the published tables."""
    predictions, margins = _m1_predictions_and_margins(
        candidate_set.candidates, reference, listing, test_ids, embedder
    )
    totals, _ = count_undetected(candidate_set.undetected, reference, test_ids)
    rows = []
    for seed, group in predictions.groupby("semilla", sort=True):
        seed = int(seed)
        n_undetected = totals.get(seed, 0)
        m1 = compute_metrics(group["oro"], group["M1"], n_undetected)
        rows.append(
            {
                "sistema": "M1",
                "semilla": seed,
                "F1_etiqueta": m1.f1_label,
                "F1_uso_discursivo": m1.f1_discourse,
                "F1_macro_CON_OP": m1.f1_macro,
                "precision_etiqueta": m1.precision,
                "cobertura_etiqueta": m1.coverage,
                "abstencion": np.nan,
                "margen": np.nan,
            }
        )
        kept = ~group["abstiene"].to_numpy()
        m1a = compute_metrics(
            group["oro"][kept], group["M1"][kept], n_undetected
        )
        rows.append(
            {
                "sistema": "M1 con abstención",
                "semilla": seed,
                "F1_etiqueta": m1a.f1_label,
                "F1_uso_discursivo": m1a.f1_discourse,
                "F1_macro_CON_OP": m1a.f1_macro,
                "precision_etiqueta": m1a.precision,
                "cobertura_etiqueta": m1a.coverage,
                "abstencion": float(group["abstiene"].mean()),
                "margen": margins[seed],
            }
        )
    metrics = pd.DataFrame(
        rows,
        columns=[
            "sistema",
            "semilla",
            *METRIC_COLUMNS,
            "abstencion",
            "margen",
        ],
    )
    summary = summary_systems(metrics)

    deviations = []
    published_predictions = published.get("predictions")
    if published_predictions is not None and not published_predictions.empty:
        deviations.extend(
            _compare_m1_predictions(predictions, published_predictions)
        )
    published_systems = published.get("systems")
    if published_systems is not None and not published_systems.empty:
        filtered = published_systems[
            published_systems["sistema"].isin(["M1", "M1 con abstención"])
        ]
        deviations.extend(
            compare_tables(metrics, filtered, ["sistema", "semilla"])
        )
    published_summary = published.get("summary")
    if published_summary is not None and not published_summary.empty:
        filtered = published_summary[
            published_summary["sistema"].isin(["M1", "M1 con abstención"])
        ]
        deviations.extend(compare_tables(summary, filtered, ["sistema"]))
    return M1Result(
        predictions=predictions,
        metrics=metrics,
        summary=summary,
        margins=margins,
        deviations=deviations,
    )
