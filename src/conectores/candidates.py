"""Candidate construction for the candidate-replay slice."""

from __future__ import annotations

import pandas as pd


def listing_forms(listing: pd.DataFrame) -> list[str]:
    """Return the distinct matching forms, longest first."""
    forms = (
        listing["unidad"]
        .astype(str)
        .str.replace(r"\s*\d+$", "", regex=True)
        .str.strip()
        .str.lower()
    )
    return sorted(set(forms), key=len, reverse=True)
