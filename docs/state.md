# State — 2026-11-20

## Where we are
The pilot experiment exists only as a Colab notebook in `doc/`; this repository has
the environment, workflow, and templates, but no system code. No slice has started.

## Done since last handoff
- `0b50b55` scaffold: `.venv` (Python 3.14), `pyproject.toml`, git, privacy-aware
  `.gitignore`, CI workflow.
- `a621359` README filename fix.
- `ef669c7` `/onboard` command, `doc/` marked read-only evidence, status corrected.
- `.venv` has numpy/pandas/scipy/scikit-learn/spaCy + `es_core_news_sm` +
  sentence-transformers (torch 2.15 CPU). `pytest` 1 passed, `ruff check .` clean.

## Next
1. Run `/grill` on `doc/Equipo11_Propuesta_v3_equipo.docx` to write
   `docs/00-brief.md`. R1–R7 and restrictions a)–d) are already fixed there; the
   grilling separates decisions from assumptions, it does not re-invent them.
2. Run `/plan` to write `docs/plan.md` and choose the slice order.
3. Then `/learn` for slice A: metrics from the published predictions in
   `doc/resultados_hito2.zip`, with no model. Optional before that: `/onboard` to
   write `docs/00-onboarding.md` (English now, Spanish later).
4. Only after `/spec-review` approval: `/tdd`.

## Open questions
- Did the 20 Nov intermediate presentation happen? (blocking for planning)
- Git remote: the proposal still says "[pegar enlace de GitHub]". None configured.
- Primary metric: keep F1 and add F2 on the binary decision as secondary?
- Who owns the application-corpus run (due 25 Nov)?
- Were the 150 pilot comments double-annotated (inter-annotator agreement)?

## Gotchas
- `doc/` filenames contain `·` (U+00B7) and a combining acute; enumerate them with
  `Get-ChildItem`, never retype them.
- `doc/` notebooks fail ruff (129 errors); excluded in `pyproject.toml`.
- Comment text and `author_hash` are gitignored (R5). Never paste them into docs,
  commits, tests, or reports.
- Versions differ from Colab (pandas 3.1.1, scikit-learn 1.9.1, spaCy 3.8.18,
  torch 2.15). The published 0.483 may not reproduce; checking that is step one.
- Five seeds over 150 comments means every comment reaches a test eventually:
  repeated grouped holdout, not one frozen test.
- `cobertura_etiqueta` in the notebook is exact-label recall, not detection recall
  (~0.41 vs ~0.51).
- M2 − B1 bootstrap CI includes zero in 4 of 5 seeds; M1 − B1 in 5 of 5.

## Not in an ADR
- README in Spanish; `AGENTS.md` and commands in English.
- `doc/` is read-only evidence.
- `gate.toml` holds the protocol constants.
- Onboarding counts as a slice.
- CI installs `.[dev]` only, not the embeddings extra.
