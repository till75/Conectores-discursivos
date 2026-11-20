# State — 2026-11-20

## Where we are
The pilot experiment exists only as a Colab notebook in `doc/`; this repository has
the environment, workflow, and templates, but no system code. The hito 2 results and
their limitations are recorded in `doc/Equipo11_Propuesta_v4_hito2.docx` and
`doc/Justificación de parámetros y requisitos · Equipo 11.docx`.

## Done since last handoff
- `0b50b55` scaffold: `.venv` (Python 3.14), `pyproject.toml`, git,
  privacy-aware `.gitignore`, CI workflow.
- `a621359` README filename fix.
- `ef669c7` `/onboard`, `doc/` marked read-only evidence, README status corrected.
- `2866a29` proposal v4, parameter justification, slides v2; private audio ignored.
- `docs/results/data-overview/` describes the corpus: 20 videos, 10,505 comments,
  binary depth, 83.5 % single-comment threads, and a 150-row reference that covers
  one video with 65 labelled rows.
- `.venv` has numpy/pandas/scipy/scikit-learn/spaCy + `es_core_news_sm` +
  sentence-transformers (torch 2.15 CPU). `pytest` 1 passed, `ruff check .` clean.

## Next
1. Run `/grill` on `doc/Equipo11_Propuesta_v4_hito2.docx` to write
   `docs/00-brief.md`. R1–R7 are already fixed there; the grilling separates
   decisions from assumptions, it does not re-invent them.
2. Run `/plan`. Candidate slices: reproduce the published table; recompute the
   metrics from `predicciones_test.csv` with no model; the embedding ablation
   (team benchmark, 21 Nov); M3 rules (team plan, 25 Nov).
3. Then `/learn` for slice A and `/spec` + `/spec-review` before any `/tdd`.

## Open questions
- Git remote: the proposal still says "[pegar enlace de GitHub]". None configured.
- Primary metric: keep F1 and add F2 / coverage-at-budget as secondary?
- Who owns the 21 Nov benchmark and the 40-case M3 validation?
- Were the 150 pilot comments double-annotated (inter-annotator agreement)?
- The 150 reference rows all carry the same video title (fuel prices), while the
  proposal says the pilot has 6 videos. Confirm whether the reference annotation
  covers one video or six.
- Where are the application-corpus artifacts? v4 reports 3,655 candidates and
  22.5 % abstention, but `resultados_hito2.zip` has no `aplicacion_*.csv`.

## Gotchas
- `doc/` filenames contain `·` (U+00B7) and a combining acute; enumerate with
  `Get-ChildItem`, never retype them.
- `doc/` notebooks fail ruff (129 errors); excluded in `pyproject.toml`.
- Comment text and `author_hash` are gitignored (R5); private audio too. Never
  paste them into docs, commits, tests, or reports.
- Versions differ from Colab (pandas 3.1.1, scikit-learn 1.9.1, spaCy 3.8.18,
  torch 2.15). The published 0.483 may not reproduce; checking that is step one.
- Five seeds over 150 comments means every comment reaches a test eventually:
  repeated grouped holdout, not one frozen test.
- The v4 proposal already declares the CI failure (1 of 5 seeds) and the abstention
  overrun (seeds 2 and 4). Do not present these as new findings.
- Only OP:ARGUMENTATIVO and OP:MODAL reach 5 test examples; 10 of 12 categories
  do not, so per-category F1 is not estimable for them.
- The team reports two independent runs with identical hashes and results; that is
  their claim, not something this repository has verified.
- `cobertura_etiqueta` in the notebook is exact-label recall, not detection recall
  (~0.41 vs ~0.51).
- YouTube threads are two levels only: all 4,241 replies attach to the thread root,
  so depth adds nothing beyond `is_reply`. 83.5 % of the 6,264 threads contain a
  single comment; 49.8 % of comments sit in those threads.
- Only 65 of the 150 reference rows contain a label: 96 spans over 76 units and
  12 labels. "150 annotated comments" means reviewed, not labelled.

## Not in an ADR
- README in Spanish; `AGENTS.md` and commands in English.
- `doc/` is read-only evidence; voice notes are never committed.
- `gate.toml` holds the protocol constants.
- Onboarding counts as a slice.
- CI installs `.[dev]` only, not the embeddings extra.
