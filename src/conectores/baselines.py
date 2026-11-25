"""B0 and B1 baselines for the baseline-replay slice."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd

from conectores.candidates import NO


def _require(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    """Raise when a required column is absent."""
    for column in columns:
        if column not in frame.columns:
            raise ValueError(f"{name} is missing required column: {column}")


def _text(value: object) -> str:
    """Return a stripped string, treating a missing value as empty."""
    return value.strip() if isinstance(value, str) else ""


def listing_label(macro: object, categoria: object, subcategoria: object) -> str:
    """Map one listing row to one project label."""
    categoria = _text(categoria)
    subcategoria = _text(subcategoria)
    if macro == "Operador":
        return "OP:" + categoria.upper()
    if categoria.startswith("Ordenador"):
        return "CON:" + (
            "INICIO" if subcategoria == "De inicio" else subcategoria.upper()
        )
    if categoria.startswith("Reformulativo"):
        return "CON:REFORMULATIVOS"
    return "CON:" + categoria.upper()


def listing_label_map(listing: pd.DataFrame) -> dict[str, list[str]]:
    """Return each listing form's distinct labels in listing row order."""
    _require(
        listing,
        ["unidad", "macrofuncion", "categoria", "subcategoria"],
        "listing",
    )
    forms = (
        listing["unidad"]
        .astype(str)
        .str.replace(r"\s*\d+$", "", regex=True)
        .str.strip()
        .str.lower()
    )
    labels: dict[str, list[str]] = {}
    for form, macro, categoria, subcategoria in zip(
        forms,
        listing["macrofuncion"],
        listing["categoria"],
        listing["subcategoria"],
        strict=True,
    ):
        bucket = labels.setdefault(form, [])
        label = listing_label(macro, categoria, subcategoria)
        if label not in bucket:
            bucket.append(label)
    return labels


def b0_predict(
    test: pd.DataFrame, labels: Mapping[str, Sequence[str]]
) -> list[str]:
    """Label each test row with the first listing label for its form."""
    _require(test, ["unidad"], "test")
    return [labels.get(form, [NO])[0] for form in test["unidad"]]
