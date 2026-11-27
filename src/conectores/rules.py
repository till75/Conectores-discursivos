"""Frozen M2 context rules."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import pandas as pd

Rule = Callable[[Any], bool]

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
