# Conectores discursivos

Anotación automática de conectores y operadores discursivos (Fuentes Rodríguez,
2009) en comentarios de YouTube en español de Chile, para el Fondecyt 11260185.

**Estado:** repositorio recién inicializado. Todavía no hay sistema: el siguiente
paso es `/brainstorm` y `/grill` sobre el problema, no escribir código.

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
