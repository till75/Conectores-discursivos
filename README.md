# Conectores discursivos

Anotación automática de conectores y operadores discursivos (Fuentes Rodríguez,
2009) en comentarios de YouTube en español de Chile, para el Fondecyt 11260185.

**Estado:** el piloto está hecho y sus resultados viven en el notebook de Colab
dentro de `doc/`. El repositorio reproduce la tabla publicada de métricas,
reconstruye las 273 candidatas y reimplementa los baselines B0 y B1, M1 y M2,
incluidos los márgenes, la trazabilidad y la comparación con las tablas
publicadas. La siguiente etapa es el paquete de publicación (S6): un comando
único, la ficha de datos, la ficha de modelo y las instrucciones de
reproducción. Se empieza por entender (`/onboard`) y reproducir, no por escribir
un modelo nuevo.

## El problema

El Fondecyt necesita marcar, en cada comentario, qué palabras funcionan como
conector u operador discursivo y de qué tipo son. Una misma palabra puede
funcionar o no: en «Ya, pero no explican nada» el *ya* es un operador que acepta
lo dicho antes para objetar; en «el bus ya llegó» sólo indica tiempo.

Anotar a mano es lento: en 150 comentarios del piloto, el listado de Fuentes
Rodríguez (2009) arroja 273 coincidencias evaluables y sólo 64 tienen uso
discursivo (en las 150 etiquetas completas hay 96 etiquetas en 12 categorías, 16
de ellas construcciones semilibres). El falso negativo es el error caro: una
falsa alarma la ve el anotador, pero un conector omitido desaparece sin que nadie
lo note. Por eso el sistema se abstiene cuando duda e informa la cobertura.

El sistema propuesto (M2) combina:

- detección de las formas del listado, la más larga primero;
- restricción por el listado: si una forma admite una sola categoría, la fija el
  listado (548 de 614 formas);
- rasgos de contexto: embeddings de la ventana de ±6 palabras
  (`paraphrase-multilingual-MiniLM-L12-v2`), posición, comas, si es respuesta,
  reglas escritas desde la gramática y categorías gramaticales de spaCy;
- regresión logística en dos pasos: uso discursivo; luego categoría, entre las
  que el listado admite;
- abstención por umbral elegido con validación cruzada agrupada por hilo, y
  «revisar categoría» cuando la categoría tiene menos de 5 ejemplos;
- trazabilidad: cada etiqueta registra el origen de la categoría (listado o
  modelo) y las reglas activadas.

## Datos y privacidad

- Corpus piloto: 1.268 comentarios de 6 videos de noticias chilenas; 150 con
  anotación de referencia.
- Corpus de aplicación: 10.505 comentarios, sin etiquetas.
- Por las políticas de la API de YouTube y el requisito R5, el repositorio
  publica **sólo IDs, etiquetas y métricas**. Nunca se versionan texto de
  comentarios, ventanas de contexto ni `author_hash`.
- `doc/` contiene el material de origen (propuesta, guion, notebooks, listado y
  corpus). Los corpus dentro de `doc/` están en `.gitignore`; trátalos como
  material de lectura local, no como parte del repositorio.

## Estructura

```
doc/                     material de origen (propuesta, guion, notebooks, corpus)
src/conectores/          paquete Python
tests/                   pruebas (pytest)
docs/                    brief, plan, ADRs, notas de diseño, specs y resultados
docs/learn/              notas de enseñanza de conceptos (/learn)
docs/results/            informe de diagnóstico de cada slice y artefactos
.opencode/commands/      comandos del flujo de trabajo (/learn, /spec, /tdd, ...)
gate.toml                parámetros congelados del protocolo de evaluación
AGENTS.md                acuerdo de trabajo y definición de terminado
```

## Entorno

Windows y PowerShell, con el entorno virtual en `.venv` (Python 3.14):

```powershell
C:\Python314\python.exe -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m spacy download es_core_news_sm

# Opcional: embeddings de la ventana (instala torch)
.\.venv\Scripts\python.exe -m pip install -e ".[embeddings]"
```

## Desarrollo

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m ruff check .
```

Los tests marcados `slow` no corren por defecto:

```powershell
.\.venv\Scripts\python.exe -m pytest -m slow
```

## Reproducción

Comprobación completa:

```powershell
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m pytest -m slow
.\.venv\Scripts\python.exe -m ruff check .
```

Paquete de publicación. El comando reconstruye las predicciones y las tablas
desde las entradas congeladas, las compara con las tablas publicadas y escribe
el paquete en `resultados_pipeline`:

```powershell
Expand-Archive doc\resultados_hito2.zip -DestinationPath .\resultados_publicados -Force
.\.venv\Scripts\python.exe -m conectores.pipeline `
  --reference doc\referencia_piloto.csv `
  --listing doc\listado_fuentes2009.csv `
  --csl doc\csl_excluidas.csv `
  --test-ids .\resultados_publicados\resultados\publicable\test_congelado `
  --hashes .\resultados_publicados\resultados\publicable\test_congelado\hashes.json `
  --published .\resultados_publicados\resultados\publicable `
  --output .\resultados_pipeline `
  --check
```

`--check` devuelve 1 si hay desviaciones o menciones `@name`. El paquete
contiene `predicciones_test.csv`, `resultados_semillas.csv`,
`resumen_sistemas.csv`, `intervalos_confianza.csv`, `diagnosticos.csv`,
`trazabilidad.json` y `pipeline_report.md`. No contiene texto de comentarios ni
`author_hash`.

Las fichas de datos y de modelo están en
[`docs/data-card.md`](docs/data-card.md) y
[`docs/model-card.md`](docs/model-card.md). La evidencia del piloto está en
[`docs/results/`](docs/results/) y los contratos en [`docs/specs/`](docs/specs/).

## Flujo de trabajo

Cada slice sigue el mismo camino y termina con un informe en `docs/results/`:

1. `/learn` — entender el problema y elegir el enfoque (nota en `docs/design/`).
2. `/spec` — contrato observable con criterios de aceptación.
3. `/spec-review` — aprobación explícita antes de escribir código.
4. `/tdd` — test que falla, implementación mínima, refactor, commit verde.
5. Informe de diagnóstico del slice, luego aprobación y push.

Ver [AGENTS.md](AGENTS.md) para el acuerdo completo, las reglas de privacidad y
las convenciones de diagramas.

## Material de origen

- `doc/Equipo11_Propuesta_v3_equipo.docx` — propuesta del proyecto (problema,
  requisitos, dataset, ruta del sistema, protocolo, riesgos y plan).
- `doc/Guion · Presentación intermedia · Equipo 11.pdf` — guion de la
  presentación intermedia del 20 nov (el nombre real usa un punto medio `·` y
  una tilde combinada).
- `doc/equipo11_B0_B1_M1_M2.ipynb` — notebook con B0, B1, M1, M2 y el detector
  exploratorio de construcciones semilibres.
- `doc/normalizar_comentarios.ipynb` — normalización automática del corpus.
- `doc/listado_fuentes2009.csv` — listado de unidades y categorías.
