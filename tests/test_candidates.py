"""Unit tests for candidate construction."""

import pandas as pd

from conectores.candidates import listing_forms


def test_listing_forms_normalises_and_deduplicates():
    """Sense numbers, case and duplicates collapse; forms stay longest-first."""
    listing = pd.DataFrame(
        {
            "unidad": [
                "Ya",
                "ya 2",
                "por lo tanto",
                "POR LO TANTO 12",
                "sin embargo",
                "sin embargo 3",
            ]
        }
    )

    assert listing_forms(listing) == ["por lo tanto", "sin embargo", "ya"]
