"""Candidate construction for the candidate-replay slice."""

from __future__ import annotations

import re
from dataclasses import dataclass

import pandas as pd

NO = "NO_DISCURSIVO"
LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"
ETIQ = re.compile(r"\[([^\[\]]+?)::([^\[\]]+)\]")

CANDIDATE_COLUMNS = [
    "comment_id",
    "thread_id",
    "is_reply",
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
]


@dataclass(frozen=True)
class CandidateSet:
    """The candidate rows and the exclusions that explain them."""

    candidates: pd.DataFrame
    undetected: pd.DataFrame
    csl_excluded: pd.DataFrame
    second_pieces: pd.DataFrame
    raw_matches: int


def normalise_label(label: str) -> str:
    """Apply the project's label normalisation."""
    label = label.strip().upper()
    if label.startswith("CON:REFORMULATIVO"):
        return "CON:REFORMULATIVOS"
    return label.replace("CON:ORDENADOR:", "CON:").replace("CON:ORDENADORES:", "CON:")


def read_annotation(
    annotation: object,
) -> tuple[str | None, list[tuple[int, int, str, str]]]:
    """Return the plain text and the ``[unidad::ETIQUETA]`` spans."""
    if not isinstance(annotation, str) or "::" not in annotation:
        return None, []
    plain, spans, pos = "", [], 0
    for match in ETIQ.finditer(annotation):
        plain += annotation[pos : match.start()]
        start = len(plain)
        plain += match.group(1)
        spans.append(
            (start, len(plain), match.group(1), normalise_label(match.group(2)))
        )
        pos = match.end()
    plain += annotation[pos:]
    return plain, spans


def listing_forms(listing: pd.DataFrame) -> list[str]:
    """Return the distinct matching forms, longest first."""
    forms = (
        listing["unidad"]
        .astype(str)
        .str.replace(r"\s*\d+$", "", regex=True)
        .str.strip()
        .str.lower()
    )
    return sorted(set(forms), key=lambda form: (-len(form), form))


def listing_pattern(listing: pd.DataFrame) -> re.Pattern[str]:
    """Build the case-insensitive, longest-first listing pattern."""
    forms = listing_forms(listing)
    if not forms:
        return re.compile(r"(?!)")
    alternatives = "|".join(re.escape(form) for form in forms)
    return re.compile(rf"(?<!{LETRA})({alternatives})(?!{LETRA})", re.I)


def _require(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    """Raise when a required column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"{name} is missing required column: {column}")


def _csl_zone_test(csl: pd.DataFrame):
    """Return a predicate for the reference spans excluded as CSL zones."""
    pairs = set(zip(csl["comment_id"], csl["unidad"], strict=True))
    ranges = []
    if {"inicio", "fin"} <= set(csl.columns):
        ranges = list(zip(csl["comment_id"], csl["inicio"], csl["fin"], strict=True))

    def is_zone(comment_id: str, start: int, end: int, unit: str) -> bool:
        if (comment_id, unit) in pairs:
            return True
        return any(
            zone_comment == comment_id and zone_start <= start and end <= zone_end
            for zone_comment, zone_start, zone_end in ranges
        )

    return is_zone


def build_candidates(
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
) -> CandidateSet:
    """Build one candidate per listing match that survives the exclusions."""
    _require(
        reference,
        ["comment_id", "thread_id", "is_reply", "text_normalized", "anotacion"],
        "reference",
    )
    _require(listing, ["unidad"], "listing")
    _require(csl, ["comment_id", "unidad"], "csl")

    pattern = listing_pattern(listing)
    is_zone = _csl_zone_test(csl)
    candidate_rows: list[dict[str, object]] = []
    undetected_rows: list[dict[str, object]] = []
    csl_rows: list[dict[str, object]] = []
    second_rows: list[dict[str, object]] = []
    raw_matches = 0

    for row in reference.itertuples():
        text = row.text_normalized if isinstance(row.text_normalized, str) else ""
        plain, spans = read_annotation(row.anotacion)
        if plain is not None:
            text = plain
        zones = [
            (start, end, unit)
            for start, end, unit, _ in spans
            if is_zone(row.comment_id, start, end, unit)
        ]
        spans = [
            span
            for span in spans
            if not is_zone(row.comment_id, span[0], span[1], span[2])
        ]
        used: set[int] = set()
        for match in pattern.finditer(text):
            raw_matches += 1
            start, end = match.span()
            zone = next(
                (
                    unit
                    for zone_start, zone_end, unit in zones
                    if zone_start < end and start < zone_end
                ),
                None,
            )
            if zone is not None:
                csl_rows.append(
                    {
                        "comment_id": row.comment_id,
                        "thread_id": row.thread_id,
                        "unidad": match.group(0),
                        "inicio": start,
                        "csl": zone,
                    }
                )
                continue
            gold = NO
            second_unit = None
            for index, (span_start, span_end, unit, label) in enumerate(spans):
                if span_start < end and start < span_end:
                    if index in used:
                        second_unit = unit
                    else:
                        gold = label
                        used.add(index)
                    break
            if second_unit is not None:
                second_rows.append(
                    {
                        "comment_id": row.comment_id,
                        "thread_id": row.thread_id,
                        "unidad": match.group(0),
                        "inicio": start,
                        "unidad_referencia": second_unit,
                    }
                )
                continue
            left, right = text[:start], text[end:]
            candidate_rows.append(
                {
                    "comment_id": row.comment_id,
                    "thread_id": row.thread_id,
                    "is_reply": bool(row.is_reply),
                    "unidad": match.group(0).lower(),
                    "inicio": start,
                    "oro": gold,
                    "texto": text,
                    "ventana": " ".join(left.split()[-6:])
                    + " [["
                    + match.group(0)
                    + "]] "
                    + " ".join(right.split()[:6]),
                    "coma_antes": bool(re.search(r"[,;:]\s*$", left)),
                    "coma_despues": bool(re.match(r"\s*[,;:]", right)),
                    "inicio_comentario": left.strip() == "",
                    "inicio_oracion": bool(
                        re.search(r"(^|[.!?…¿¡\n]\s*)$", left)
                    ),
                    "fin_enunciado": bool(re.match(r"\s*([.!?…]|$)", right)),
                }
            )
        for index, (_, _, unit, label) in enumerate(spans):
            if index not in used:
                undetected_rows.append(
                    {
                        "comment_id": row.comment_id,
                        "thread_id": row.thread_id,
                        "unidad": unit,
                        "oro": label,
                    }
                )

    return CandidateSet(
        candidates=pd.DataFrame(candidate_rows, columns=CANDIDATE_COLUMNS),
        undetected=pd.DataFrame(
            undetected_rows, columns=["comment_id", "thread_id", "unidad", "oro"]
        ),
        csl_excluded=pd.DataFrame(
            csl_rows,
            columns=["comment_id", "thread_id", "unidad", "inicio", "csl"],
        ),
        second_pieces=pd.DataFrame(
            second_rows,
            columns=[
                "comment_id",
                "thread_id",
                "unidad",
                "inicio",
                "unidad_referencia",
            ],
        ),
        raw_matches=raw_matches,
    )
