"""Candidate construction for the candidate-replay slice."""

from __future__ import annotations

import re

import pandas as pd

LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"
ETIQ = re.compile(r"\[([^\[\]]+?)::([^\[\]]+)\]")


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
