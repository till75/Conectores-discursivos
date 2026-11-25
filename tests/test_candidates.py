"""Unit tests for candidate construction."""

import pandas as pd

import conectores.candidates as candidates
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


def test_listing_pattern_boundaries():
    """A form matches standalone and case-insensitively, never inside a word."""
    listing = pd.DataFrame({"unidad": ["Ya", "más"]})
    pattern = candidates.listing_pattern(listing)

    assert pattern.findall("ya, pero no en playa") == ["ya"]
    assert pattern.findall("YA") == ["YA"]
    assert pattern.findall("más encima") == ["más"]


def test_listing_pattern_prefers_longest_form():
    """The longest form wins when a shorter form is its suffix."""
    listing = pd.DataFrame({"unidad": ["tanto", "por lo tanto"]})
    pattern = candidates.listing_pattern(listing)

    assert pattern.findall("por lo tanto, tanto") == ["por lo tanto", "tanto"]


def test_listing_pattern_empty_listing_never_matches():
    """An empty listing compiles to a pattern that never matches."""
    pattern = candidates.listing_pattern(pd.DataFrame({"unidad": []}))

    assert pattern.findall("ya, por lo tanto") == []
