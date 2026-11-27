"""Frozen M2 context rules."""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from typing import Any, Protocol

import pandas as pd
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction import DictVectorizer

from conectores.features import Embedder, FeatureBuilder

Rule = Callable[[Any], bool]

POS_COLUMNS = ["pos_u", "pos_ant", "pos_sig", "tok_ant", "tok_sig"]

REQUIRED_COLUMNS = [
    "unidad",
    "inicio",
    "texto",
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


class Token(Protocol):
    idx: int
    text: str
    pos_: str


NLP = Callable[[str], Sequence[Token]]


def anotar_gramatica(cand: pd.DataFrame, nlp: NLP) -> pd.DataFrame:
    """Add the five POS columns to the candidate frame."""
    for column in ("texto", "inicio", "unidad"):
        if column not in cand.columns:
            raise ValueError(
                f"candidates is missing required column: {column}"
            )
    cache: dict[str, Sequence[Token]] = {}
    rows = []
    for texto, inicio, unidad in zip(
        cand["texto"], cand["inicio"], cand["unidad"], strict=True
    ):
        if texto not in cache:
            cache[texto] = nlp(texto)
        doc = cache[texto]
        fin = inicio + len(unidad)
        dentro = next(
            (
                token
                for token in doc
                if token.idx < fin and token.idx + len(token.text) > inicio
            ),
            None,
        )
        antes = [
            token
            for token in doc
            if token.idx + len(token.text) <= inicio
        ]
        despues = next(
            (token for token in doc if token.idx >= fin),
            None,
        )
        rows.append(
            {
                "pos_u": dentro.pos_ if dentro is not None else "X",
                "pos_ant": antes[-1].pos_ if antes else "INICIO",
                "pos_sig": despues.pos_ if despues is not None else "FIN",
                "tok_ant": antes[-1].text.lower() if antes else "",
                "tok_sig": despues.text.lower()
                if despues is not None
                else "",
            }
        )
    return pd.concat(
        [
            cand.reset_index(drop=True),
            pd.DataFrame(rows, columns=POS_COLUMNS),
        ],
        axis=1,
    )


def _require_pos(df: pd.DataFrame) -> None:
    for column in ("unidad", "pos_u", "pos_ant", "pos_sig"):
        if column not in df.columns:
            raise ValueError(
                f"candidates is missing required column: {column}"
            )


class M2FeatureBuilder:
    """Build the M2 feature matrix: M1 blocks, rules and POS."""

    def fit(
        self, train: pd.DataFrame, embedder: Embedder
    ) -> M2FeatureBuilder:
        _require_pos(train)
        self.base = FeatureBuilder().fit(train, embedder)
        self.dv = DictVectorizer().fit(self._pos_dicts(train))
        return self

    def transform(self, df: pd.DataFrame) -> csr_matrix:
        base = self.base.transform(df)
        rules = csr_matrix(aplicar_reglas(df).astype(float).to_numpy())
        pos = self.dv.transform(self._pos_dicts(df))
        return hstack([base, rules, pos]).tocsr()

    @staticmethod
    def _pos_dicts(df: pd.DataFrame) -> list[dict[str, int]]:
        return [
            {
                f"u={pos_u}": 1,
                f"ant={pos_ant}": 1,
                f"sig={pos_sig}": 1,
                f"{unidad}|sig={pos_sig}": 1,
                f"{unidad}|ant={pos_ant}": 1,
            }
            for unidad, pos_u, pos_ant, pos_sig in zip(
                df["unidad"],
                df["pos_u"],
                df["pos_ant"],
                df["pos_sig"],
                strict=True,
            )
        ]


def _pregunta(texto: str, inicio: int) -> bool:
    """Return whether the unit sits inside an interrogative sentence."""
    resto = texto[inicio:]
    match = re.search(r"[.!?…\n]", resto)
    previous_dot = max(0, texto.rfind(".", 0, inicio))
    return bool(match and match.group(0) == "?") or "¿" in texto[
        previous_dot:inicio
    ]


REGLAS: dict[str, Rule] = {
    # general
    "sig_det_o_num": lambda r: r.pos_sig in ("DET", "NUM")
    or bool(re.match(r"\d", r.tok_sig)),
    "sig_verbo": lambda r: r.pos_sig in ("VERB", "AUX"),
    "ant_verbo": lambda r: r.pos_ant in ("VERB", "AUX"),
    "sig_adj_o_adv": lambda r: r.pos_sig in ("ADJ", "ADV"),
    "ant_det": lambda r: r.pos_ant == "DET",
    "ant_prep": lambda r: r.pos_ant == "ADP",
    "sig_que": lambda r: r.tok_sig == "que",
    "aislada_por_comas": lambda r: r.coma_despues
    and (r.inicio_oracion or r.coma_antes),
    "fin_tras_verbo": lambda r: r.pos_ant in ("VERB", "AUX")
    and r.fin_enunciado,
    "en_pregunta": lambda r: _pregunta(r.texto, r.inicio),
    # unit-specific
    "hasta_preposicion": lambda r: r.unidad == "hasta"
    and (
        r.pos_sig in ("DET", "NUM", "PROPN", "NOUN")
        or bool(re.match(r"\d", r.tok_sig))
    ),
    "ya_temporal": lambda r: r.unidad == "ya"
    and not r.coma_despues
    and r.pos_sig in ("VERB", "AUX", "PRON"),
    "ya_operador": lambda r: r.unidad == "ya"
    and r.inicio_oracion
    and r.coma_despues,
    "solo_adjetivo": lambda r: r.unidad == "solo"
    and r.pos_ant in ("VERB", "AUX", "PRON")
    and r.fin_enunciado,
    "mas_comparativo": lambda r: r.unidad == "más"
    and (
        r.pos_sig in ("ADJ", "ADV", "NOUN", "NUM") or r.tok_sig == "que"
    ),
}

RULE_NAMES = list(REGLAS)


def aplicar_reglas(df: pd.DataFrame) -> pd.DataFrame:
    """Return one boolean column per frozen rule."""
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            raise ValueError(
                f"candidates is missing required column: {column}"
            )
    return pd.DataFrame(
        {
            name: [bool(rule(row)) for row in df.itertuples()]
            for name, rule in REGLAS.items()
        },
        index=df.index,
    )
