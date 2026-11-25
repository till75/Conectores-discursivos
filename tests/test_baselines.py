"""Unit tests for the B0 and B1 baselines."""

import pandas as pd
import pytest

import conectores.baselines as baselines


def _listing(*rows):
    """Build a synthetic listing from ``(unidad, macro, categoria, subcategoria)``."""
    return pd.DataFrame(
        [
            {
                "unidad": unidad,
                "macrofuncion": macro,
                "categoria": categoria,
                "subcategoria": subcategoria,
            }
            for unidad, macro, categoria, subcategoria in rows
        ]
    )


def test_listing_label_branches():
    """The four listing rules and the missing-value boundary."""
    assert baselines.listing_label("Operador", "Modal", "─") == "OP:MODAL"
    assert (
        baselines.listing_label(
            "Conector", "Ordenador de la materia discursiva", "De inicio"
        )
        == "CON:INICIO"
    )
    assert (
        baselines.listing_label(
            "Conector", "Ordenador de la materia discursiva", "Cierre"
        )
        == "CON:CIERRE"
    )
    assert (
        baselines.listing_label("Conector", "Reformulativo", "Explicación")
        == "CON:REFORMULATIVOS"
    )
    assert baselines.listing_label("Conector", "Adición", "─") == "CON:ADICIÓN"
    assert baselines.listing_label("Operador", "Modal", None) == "OP:MODAL"
    assert baselines.listing_label("Conector", None, None) == "CON:"


def test_listing_label_map_collapses_and_orders():
    """Sense numbers, case and duplicates collapse; labels keep listing order."""
    listing = _listing(
        ("Ya", "Conector", "Adición", "─"),
        ("ya 2", "Operador", "Modal", "─"),
        ("ya", "Conector", "Adición", "─"),
        ("bueno", "Conector", "Ordenador de la materia discursiva", "De inicio"),
        ("bueno 3", "Conector", "Ordenador de la materia discursiva", "Cierre"),
    )

    assert baselines.listing_label_map(listing) == {
        "ya": ["CON:ADICIÓN", "OP:MODAL"],
        "bueno": ["CON:INICIO", "CON:CIERRE"],
    }


def test_listing_label_map_requires_columns():
    """Every required listing column is named in the error that its absence raises."""
    listing = _listing(("ya", "Conector", "Adición", "─"))

    for column in ("unidad", "macrofuncion", "categoria", "subcategoria"):
        with pytest.raises(
            ValueError, match=f"listing is missing required column: {column}"
        ):
            baselines.listing_label_map(listing.drop(columns=[column]))
