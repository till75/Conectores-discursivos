"""Candidate construction for the candidate-replay slice."""

from __future__ import annotations

import re

import pandas as pd

LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"


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
