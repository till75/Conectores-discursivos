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


def test_normalise_label_maps_variants():
    """Labels are trimmed, upper-cased and collapsed onto the project vocabulary."""
    assert candidates.normalise_label(" con:adición ") == "CON:ADICIÓN"
    assert (
        candidates.normalise_label("CON:REFORMULATIVOS:EXPLICACIÓN")
        == "CON:REFORMULATIVOS"
    )
    assert candidates.normalise_label("CON:ORDENADOR:CIERRE") == "CON:CIERRE"
    assert (
        candidates.normalise_label("CON:ORDENADORES:CONTINUATIVO")
        == "CON:CONTINUATIVO"
    )


def test_read_annotation_plain_text_and_spans():
    """Markup is removed and each span carries half-open offsets and its label."""
    plain, spans = candidates.read_annotation("[ya::CON:ADICIÓN] [Dale::OP:MODAL]")

    assert plain == "ya Dale"
    assert spans == [
        (0, 2, "ya", "CON:ADICIÓN"),
        (3, 7, "Dale", "OP:MODAL"),
    ]


def test_read_annotation_normalises_the_span_label():
    """A nested reference label is normalised before it leaves the parser."""
    _, spans = candidates.read_annotation("[x::CON:REFORMULATIVOS:EXPLICACIÓN]")

    assert spans == [(0, 1, "x", "CON:REFORMULATIVOS")]


def test_read_annotation_without_markup():
    """A value that is not a string or has no ``::`` carries no annotation."""
    for value in ("Sin etiquetas", "", None, 5):
        assert candidates.read_annotation(value) == (None, [])
