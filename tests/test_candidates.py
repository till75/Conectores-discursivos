"""Unit tests for candidate construction."""

import pandas as pd
import pytest

import conectores.candidates as candidates
from conectores.candidates import listing_forms


def _reference(*rows):
    """Build a synthetic reference frame from ``(comment_id, thread_id, anotacion)``."""
    return pd.DataFrame(
        [
            {
                "comment_id": comment_id,
                "thread_id": thread_id,
                "is_reply": False,
                "text_normalized": "",
                "anotacion": annotation,
            }
            for comment_id, thread_id, annotation in rows
        ]
    )


def _listing(*units):
    """Build a synthetic listing frame."""
    return pd.DataFrame({"unidad": list(units)})


def _empty_csl():
    """Build an empty CSL frame with the published columns."""
    return pd.DataFrame({"comment_id": [], "unidad": []})


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


def test_build_candidates_happy_path():
    """A positive, an explicit negative, an implicit negative and an undetected span."""
    reference = _reference(
        (
            "c1",
            "t1",
            "[ya::CON:ADICIÓN], además. [no::NO_DISCURSIVO] "
            "[por lo tanto::CON:CONCLUSIVO]",
        )
    )
    listing = _listing("ya", "además", "no")

    result = candidates.build_candidates(reference, listing, _empty_csl())

    assert list(result.candidates["unidad"]) == ["ya", "además", "no"]
    assert list(result.candidates["oro"]) == [
        "CON:ADICIÓN",
        "NO_DISCURSIVO",
        "NO_DISCURSIVO",
    ]
    assert list(result.undetected["unidad"]) == ["por lo tanto"]
    assert list(result.undetected["oro"]) == ["CON:CONCLUSIVO"]
    assert result.raw_matches == 3
    assert result.csl_excluded.empty
    assert result.second_pieces.empty

    first = result.candidates.iloc[0]
    assert first["comment_id"] == "c1"
    assert first["thread_id"] == "t1"
    assert first["inicio"] == 0
    assert first["texto"] == "ya, además. no por lo tanto"
    assert first["ventana"].strip().startswith("[[ya]]")
    assert bool(first["coma_antes"]) is False
    assert bool(first["coma_despues"]) is True
    assert bool(first["inicio_comentario"]) is True
    assert bool(first["inicio_oracion"]) is True
    assert bool(first["fin_enunciado"]) is False

    second = result.candidates.iloc[1]
    assert bool(second["coma_antes"]) is True
    assert bool(second["coma_despues"]) is False
    assert bool(second["inicio_oracion"]) is False
    assert bool(second["fin_enunciado"]) is True


def test_build_candidates_excludes_csl():
    """A CSL zone drops every match inside it and is never undetected."""
    reference = _reference(
        ("c1", "t1", "[Dale::OP:MODAL]"),
        ("c2", "t2", "[ya es mucho::CON:ADICIÓN]"),
        ("c3", "t3", "[ya::CON:ADICIÓN] fuera"),
    )
    listing = _listing("dale", "ya", "mucho")
    csl = pd.DataFrame(
        {"comment_id": ["c1", "c2"], "unidad": ["Dale", "ya es mucho"]}
    )

    result = candidates.build_candidates(reference, listing, csl)

    assert len(result.candidates) == 1
    assert result.candidates.iloc[0]["comment_id"] == "c3"
    assert result.candidates.iloc[0]["oro"] == "CON:ADICIÓN"
    assert list(result.csl_excluded["unidad"]) == ["Dale", "ya", "mucho"]
    assert list(result.csl_excluded["csl"]) == ["Dale", "ya es mucho", "ya es mucho"]
    assert list(result.csl_excluded["thread_id"]) == ["t1", "t2", "t2"]
    assert result.undetected.empty
    assert result.raw_matches == 4


def test_build_candidates_skips_second_piece():
    """Two listing forms inside one unit give one candidate and one second piece."""
    reference = _reference(("c1", "t1", "[más encima::CON:ADICIÓN]"))
    listing = _listing("más", "encima")

    result = candidates.build_candidates(reference, listing, _empty_csl())

    assert list(result.candidates["unidad"]) == ["más"]
    assert list(result.candidates["oro"]) == ["CON:ADICIÓN"]
    assert len(result.second_pieces) == 1
    second = result.second_pieces.iloc[0]
    assert second["unidad"] == "encima"
    assert second["inicio"] == 4
    assert second["unidad_referencia"] == "más encima"
    assert result.undetected.empty
    assert result.raw_matches == 2


def test_build_candidates_first_span_wins():
    """The first overlapping span supplies the label and can claim the match."""
    reference = _reference(
        ("c1", "t1", "[a::CON:ADICIÓN][b::OP:MODAL]"),
        ("c2", "t2", "[a bc::CON:ADICIÓN][d::OP:MODAL]"),
    )
    listing = _listing("ab", "bcd", "a")

    result = candidates.build_candidates(reference, listing, _empty_csl())

    assert list(result.candidates["comment_id"]) == ["c1", "c2"]
    assert list(result.candidates["oro"]) == ["CON:ADICIÓN", "CON:ADICIÓN"]
    assert list(result.second_pieces["comment_id"]) == ["c2"]
    assert list(result.second_pieces["unidad"]) == ["bcd"]
    assert list(result.second_pieces["unidad_referencia"]) == ["a bc"]
    assert list(result.undetected["oro"]) == ["OP:MODAL", "OP:MODAL"]
    assert result.raw_matches == 3


def test_build_candidates_empty_listing():
    """No forms means no candidates and every non-CSL span is undetected."""
    reference = _reference(("c1", "t1", "[ya::CON:ADICIÓN] [no::NO_DISCURSIVO]"))

    result = candidates.build_candidates(reference, _listing(), _empty_csl())

    assert result.candidates.empty
    assert result.raw_matches == 0
    assert list(result.undetected["unidad"]) == ["ya", "no"]
    assert list(result.undetected["oro"]) == ["CON:ADICIÓN", "NO_DISCURSIVO"]


def test_build_candidates_requires_columns():
    """Every required column is named in the error that its absence raises."""
    reference = _reference(("c1", "t1", "[ya::CON:ADICIÓN]"))
    listing = _listing("ya")
    csl = _empty_csl()

    reference_columns = (
        "comment_id",
        "thread_id",
        "is_reply",
        "text_normalized",
        "anotacion",
    )
    for column in reference_columns:
        with pytest.raises(
            ValueError, match=f"reference is missing required column: {column}"
        ):
            candidates.build_candidates(
                reference.drop(columns=[column]), listing, csl
            )

    with pytest.raises(ValueError, match="listing is missing required column: unidad"):
        candidates.build_candidates(reference, _listing().drop(columns=["unidad"]), csl)

    for column in ("comment_id", "unidad"):
        message = f"csl is missing required column: {column}"
        with pytest.raises(ValueError, match=message):
            candidates.build_candidates(
                reference, listing, csl.drop(columns=[column])
            )
