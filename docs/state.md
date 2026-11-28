# State — 2026-11-27

## Where we are
S4 (M1 replay) is finished, approved, and pushed; `origin/main` is `f9ab832`. S5 (M2 replay) is approved and pushed; `origin/main` is `0060709`. S6 (publication pack) is implemented, the slow end-to-end test is green and the diagnostic report is written. S6 is ready for approval.

## Done since last handoff
- S4 M1 replay implemented and tested: `1a84fda`, `59a3c13`, `24a1b2c`, `7e6454d`, `01452be`, `cd614f6`.
- S4 spec approved: `e585539`; diagnostics report committed: `f9ab832` (`docs/results/0004-m1-replay-diagnostics.md`).
- S5 prototype evidence collected outside the repo: no-abstention M2 exact, margin path differs.
- S5 `/learn` complete: author chose A; `docs/design/0005-m2-replay.md` and `docs/learn/04-m2-rules-provenance.md` written and linked from the learn index.
- S5 spec approved 2026-11-27: `docs/specs/0005-m2-replay.md`; the partial-result criterion for the 27/439 margin mismatch is accepted as a fallback.
- S5 frozen rule set: `src/conectores/rules.py` and `tests/test_rules.py`; 15 rules, `aplicar_reglas` returns the boolean columns.
- S5 grammar annotation: `anotar_gramatica` adds the five POS columns from character offsets, with a text cache and `INICIO`/`FIN`/`X` fallbacks.
- S5 feature builder: `M2FeatureBuilder` appends the 15 rule columns and the POS `DictVectorizer` block to the S4 matrix; the POS vocabulary is fitted on training only.
- S5 model: `M2Model` adds the strict listing restriction, provenance, the rare-category flag and the abstention branch; `M1Model` now exposes a private `_make_builder` hook.
- S5 margin: `choose_margin_for` is the generic grouped-CV margin; `choose_margin` delegates to it and keeps the S4 behaviour.
- S5 predictions: `m2_predictions` resolves test threads, fits M2 per seed, learns the margin inside training and returns `M2_COLUMNS` without text.
- S5 replay: `replay_m2` returns predictions, metrics, summary, margins, traceability and the split core/margin deviations; the prediction, systems and summary comparisons are implemented.
- S5 slow comparison: the three M2 integration tests pass on the real inputs; core deviations are empty, the M2 rows and summary match, and traceability is 91/58/34/33/20/43. `load_nlp` was added to load `es_core_news_sm`.
- S5 margin cause found and fixed: scikit-learn's `GroupKFold` changed the tie-break for equal-sized groups from unstable `np.argsort` to `kind="stable"`. `_group_kfold_splits` reproduces the pre-stable behaviour; M1 margins stay `0.10/0.10/0.10/0.05/0.15`, M2 margins now match `0.15/0.10/0.20/0.10/0.20`, and `margin_deviations` is empty on the real inputs.
- S5 full pass: 13 slow tests and 124 default tests pass; `ruff check .` clean.
- S5 diagnostic report written: `docs/results/0005-m2-replay-diagnostics.md`, including the margin investigation, the fix, the per-seed table, the intervals and the privacy check.
- S5 approved and pushed: `0060709`; `origin/main` is at `0060709`.
- S6 spec approved 2026-11-27: `docs/specs/0006-publication-pack.md`; seven-file pack, flat summary, Spanish static cards, extracted publicable directory and the `@USER` privacy rule are approved.
- S6 combined public frame: `src/conectores/pipeline.py` and `tests/test_pipeline.py`; the helper merges B0/B1, M1 and M2 into the 15-column public frame, checks key/label/thread agreement and drops the M1 abstention internals.
- S6 pipeline composition: `run_pipeline` builds candidates, B0/B1, M1 and M2, combines the frame, passes the rebuilt margins to `metrics.replay`, and returns the tables, traceability and privacy count. `replay` now accepts explicit `margins`.
- S6 output writer and CLI: `write_pipeline_outputs` writes the seven public files and the report; `main` reads the inputs, loads the frozen models, runs the pipeline, writes the outputs and returns 1 on deviations or privacy mentions. The tests use synthetic files and monkeypatched models.
- S6 prediction and privacy checks: `_compare_predictions` names missing or changed core cells and probabilities; `_privacy_mentions` counts `@name` but allows `@USER`; `run_pipeline` adds a privacy deviation when the count is non-zero.
- S6 documentation: `docs/data-card.md`, `docs/model-card.md` and the README `## Reproducción` section; `tests/test_docs.py` checks the sections, counts and commands.
- S6 slow end-to-end: `test_pipeline_end_to_end` runs the real CLI and writes the full pack with zero deviations and zero privacy mentions. The rebuilt frame is ordered by the frozen published keys before the bootstrap; that reproduces the 15 published intervals without reading published values.
- S6 evidence: 139 default tests and 14 slow tests pass; `ruff check .` clean.
- S6 diagnostic report written: `docs/results/0006-publication-pack-diagnostics.md`, including the pack shapes, split/hashes, metrics, abstention, traceability, intervals, privacy scan and the bootstrap-order fix.

## Next
1. Commit the final S6 docs.
2. Stop for approval; do not push before it.

## Open questions
- The `inicio_oracion` newline rule, the 20-candidate audit and the documentation privacy exceptions remain open.
- The application corpus run remains deferred.

## Gotchas
- Run Python as `.venv\Scripts\python.exe`; spaCy model is `es_core_news_sm`.
- `doc/` is read-only evidence; its corpora are gitignored.
- S5 prototype is `C:\Users\tills\AppData\Local\Temp\opencode\m2_probe_s5.py`; it is not in the repo.
- M2 margins match `0.15/0.10/0.20/0.10/0.20`; no-abstention M2, `p_M2`, `origen_M2`, `revisar_categoria` and traceability match, and `margin_deviations` is empty.
- Margin cause: `GroupKFold` tie-break drift. The old sklearn used unstable `np.argsort` on equal-sized groups; 1.9.1 uses `kind="stable"`. `_group_kfold_splits` reproduces the old behaviour. Do not replace it with `GroupKFold` without rechecking the published M2 margins.
- S4 evidence: `pytest -q` 79 passed, 10 deselected; `pytest -m slow` 10 passed; `ruff check .` clean.

## Not in an ADR
- S2/S3/`docs/learn/` have documentation-only privacy exceptions; do not extend them without request.
- S5 `/learn` is complete; the teaching note is documentation, not a spec.
- S5 does not need an ADR for the rule set: recording the frozen rules is not a change. Editing them would need one.
- S4 used the frozen embeddings cache; replay tests must not refit or download it.
