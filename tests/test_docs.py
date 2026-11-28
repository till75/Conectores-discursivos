"""Documentation tests for the publication cards and README."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_CARD = ROOT / "docs" / "data-card.md"
MODEL_CARD = ROOT / "docs" / "model-card.md"
README = ROOT / "README.md"


def test_data_card_has_required_sections():
    assert DATA_CARD.exists()
    text = DATA_CARD.read_text(encoding="utf-8")

    for heading in (
        "## Corpus piloto",
        "## Corpus de aplicación",
        "## Listado",
        "## Candidatas",
        "## Partición",
        "## Referencia",
        "## Privacidad",
        "## Limitaciones",
    ):
        assert heading in text
    for value in (
        "1.268",
        "150",
        "65",
        "273",
        "64",
        "209",
        "614",
        "10.505",
        "439",
    ):
        assert value in text


def test_model_card_has_required_sections():
    assert MODEL_CARD.exists()
    text = MODEL_CARD.read_text(encoding="utf-8")

    for heading in (
        "## Sistemas",
        "## Rasgos",
        "## Entrenamiento",
        "## Métricas",
        "## Resultados",
        "## Uso previsto",
        "## Limitaciones",
        "## Privacidad",
    ):
        assert heading in text
    for value in ("0.483", "0.513", "0.328", "91/58/34/33/20/43"):
        assert value in text


def test_readme_has_reproduction_commands():
    text = README.read_text(encoding="utf-8")

    assert "## Reproducción" in text
    assert "conectores.pipeline" in text
    assert "Expand-Archive" in text
    assert "pytest -m slow" in text
    assert "docs/data-card.md" in text
    assert "docs/model-card.md" in text
    assert "M2 todavía vive sólo en el notebook" not in text
