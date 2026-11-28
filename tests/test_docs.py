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
        "## Esquema de las tablas",
        "## Normalización",
        "## Candidatas",
        "## Partición",
        "## Referencia",
        "## Recolección y procedencia",
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
        "284 − 8 − 3 = 273",
        "author_hash",
        "anotacion_final",
        "comment_text_raw",
        "polifuncional",
        "6.984",
        "2023-03-21",
        "2026-11-14",
        "2026-11-20",
        "API de",
        "model-card.md",
    ):
        assert value in text


def test_model_card_has_required_sections():
    assert MODEL_CARD.exists()
    text = MODEL_CARD.read_text(encoding="utf-8")

    for heading in (
        "## Detalles del modelo",
        "### Sistemas",
        "### Rasgos y salida del pipeline",
        "## Uso previsto",
        "## Factores",
        "## Métricas y umbrales",
        "## Datos de entrenamiento",
        "## Datos de evaluación",
        "## Análisis cuantitativos",
        "## Riesgos, ética y recomendaciones",
        "## Limitaciones",
        "## Especificaciones técnicas",
        "## Impacto ambiental",
        "## Privacidad",
        "## Cita, licencia y contacto",
        "## Reproducción",
    ):
        assert heading in text
    for value in (
        "0.483",
        "0.513",
        "0.328",
        "91/58/34/33/20/43",
        "2026-11-27",
        "0.1.0",
        "Fondecyt 11260185",
        "Proyecto marco",
        "Proyecto de capstone",
        "19 hilos",
        "15,6 %",
        "pendiente",
        "origen_M2",
        "abstiene_M2",
        "15 reglas",
        "[[...]]",
        "Paso 1",
        "Paso 2",
        "construcciones semilibres",
        "Versión del paquete",
        "Versión de la ficha",
    ):
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
