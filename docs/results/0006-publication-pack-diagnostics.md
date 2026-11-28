# Publication pack diagnostic report

**Slice:** S6 — publication pack
**Date:** 2026-11-27
**Status:** pass
**Spec:** [0006-publication-pack.md](../specs/0006-publication-pack.md)
**Commits:** `a16a6c5..ea803c4`, plus the docs audit and final approval commits
**Report owner:** Till

## Intended goal

One command reads the frozen pilot inputs, rebuilds the published prediction
and metric tables, writes a reproducible pack, and runs the privacy check. The
data card and model card describe the data and the systems, and the README
gives the reproduction commands. S6 composes S1–S5; it does not add a model or
change the protocol.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| One command rebuilds the published pack | `test_pipeline_end_to_end`; real CLI returns 0, writes seven files, 439/30/6/15/5 rows, zero deviations | pass |
| The combined public frame has the 15 published columns and 439 rows | `test_pipeline_end_to_end`; real `predicciones_test.csv` is `(439, 15)` | pass |
| Core predictions, probabilities and flags match the published rows | `run_pipeline` prediction comparison; real run reports zero deviations | pass |
| The systems, summary and intervals match the published tables | `metrics.replay` comparison; real run reports zero deviations | pass |
| The pack carries no `@name`, text, windows, POS internals or `author_hash` | Real scan of all seven files: zero forbidden columns and zero mentions | pass |
| The data card exists with the required sections and counts | `test_data_card_has_required_sections` | pass |
| The model card exists with the required sections and results | `test_model_card_has_required_sections` | pass |
| The README has the reproduction commands and no stale M2 status | `test_readme_has_reproduction_commands` | pass |
| S1–S5 stay green and unchanged | Full default and slow suites | pass |
| The slow tests skip when `doc/`, spaCy, the embeddings extra or the frozen model is absent | Fixture guards in `tests/test_integration.py` | pass |

## What was built

`src/conectores/pipeline.py` holds `PipelineResult`, `PIPELINE_COLUMNS`,
`combine_predictions`, `run_pipeline`, `_compare_predictions`,
`_privacy_mentions`, `_order_like_published`, `write_pipeline_outputs`,
`_format_pipeline_report` and `main`. `metrics.replay` now accepts an explicit
`margins` mapping, so the pipeline uses the rebuilt margins instead of the
published ones.

The tests are `tests/test_pipeline.py` (combined frame, composition, writer,
CLI, prediction/privacy checks), `tests/test_docs.py` (cards and README) and
`tests/test_integration.py` (the real end-to-end pack). The docs are
`docs/data-card.md`, `docs/model-card.md` and the README `## Reproducción`
section.

The unit behaviours were driven by failing tests. The slow end-to-end test was
written after the pipeline was composed; its first run found 29 interval
deviations, which drove the frozen bootstrap-order fix. The slow test is now a
regression guard for the whole pack.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | 139 passed, 14 deselected (14.81 s) |
| `.\.venv\Scripts\python.exe -m pytest -q -m slow` | 14 passed, 139 deselected (89.78 s) |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_integration.py -m slow -k "pipeline_end_to_end"` | 1 passed (40.23 s) |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| Real CLI with `--check` | exit 0; seven files; zero deviations; zero privacy mentions |

## Diagnostic evidence

### The pack

| File | Shape |
|---|---|
| `predicciones_test.csv` | 439 × 15 |
| `resultados_semillas.csv` | 30 × 9 |
| `resumen_sistemas.csv` | 6 × 11 |
| `intervalos_confianza.csv` | 15 × 5 |
| `diagnosticos.csv` | 5 × 3 |
| `trazabilidad.json` | six counts |
| `pipeline_report.md` | counts, traceability, deviations, privacy |

The prediction columns are `comment_id`, `thread_id`, `semilla`, `unidad`,
`inicio`, `oro`, `B0`, `B1`, `M1`, `M2`, `p_M1`, `p_M2`, `origen_M2`,
`revisar_categoria` and `abstiene_M2`.

The real run reports:

```text
Predictions: 439 · Deviations: 0 · Privacy mentions: 0
```

### Split and frozen tests

The pack runs on seeds 0–4. Each seed has 19 frozen test threads; the frozen
hashes match the published files.

| Seed | Candidates | Undetected | Frozen hash |
|---|---:|---:|---|
| 0 | 65 | 5 | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 97 | 3 | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 92 | 4 | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 124 | 8 | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 61 | 4 | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The five seeds produce 439 appearances, 256 unique candidates seen in at least
one test split and 17 candidates that never enter a test.

### Metrics and abstention

| System | F1 label | F1 discourse | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| M2 | 0.483 | 0.606 | 0.634 | 0.599 | 0.407 |
| M2 con abstención | 0.513 | 0.639 | 0.689 | 0.715 | 0.401 |

B1 obtains 0.328; the mean gain M2 − B1 is +0.155.

| Seed | M2 con abstención F1 | Abstention | Margin |
|---|---:|---:|---:|
| 0 | 0.452 | 12.31% | 0.15 |
| 1 | 0.571 | 5.15% | 0.10 |
| 2 | 0.476 | 30.43% | 0.20 |
| 3 | 0.449 | 8.87% | 0.10 |
| 4 | 0.615 | 21.31% | 0.20 |

The mean abstention is 15.6%. Seeds 2 and 4 exceed the 20% cap on test; the cap
applies to the training CV holdout, not to the test outcome.

### Traceability and review

| Count | Value |
|---|---:|
| Discourse labels | 91 |
| Fixed by the listing | 58 |
| Fixed by the listing and correct | 34 |
| Chosen by the model | 33 |
| Chosen by the model and correct | 20 |
| Flagged for category review | 43 |

The listing fixed 63.7% of the discourse categories and the model chose 36.3%.
The review flag covers 43 of 91 discourse labels (47.3%).

### Bootstrap intervals

The pack's `intervalos_confianza.csv` has the 15 published rows. The first
end-to-end run exposed 29 interval deviations because the combined frame was
sorted by key, changing the thread order used by the bootstrap RNG. The fix
reorders the rebuilt frame to the frozen published key order before the
interval calculation; no published label or probability is read. The intervals
now match.

| Seed | M2 − B1 95% interval | Excludes zero | M2 − M1 95% interval | Excludes zero |
|---|---|---|---|---|
| 0 | [−0.274, 0.259] | no | [0.000, 0.201] | no |
| 1 | [−0.025, 0.637] | no | [0.133, 0.436] | yes |
| 2 | [−0.007, 0.742] | no | [0.151, 0.431] | yes |
| 3 | [0.033, 0.343] | yes | [−0.036, 0.113] | no |
| 4 | [−0.255, 0.282] | no | [−0.198, 0.124] | no |

The mean gain M2 − B1 is +0.155, but the interval excludes zero in only seed 3.
The mean gain M2 − M1 is +0.123, with intervals excluding zero in seeds 1 and 2.
The pack does not claim significance.

### Privacy scan

The real prediction frame is 439 × 15 and contains no `texto`, `ventana`,
`pos_*`, `tok_*` or `author_hash`. All seven output files were scanned:

- zero forbidden columns in every CSV;
- zero `@name` mentions; `@USER` is allowed;
- zero mentions in `pipeline_report.md` and `trazabilidad.json`.

The pipeline reads comment text in memory for candidates, embeddings and spaCy,
but writes only IDs, forms, labels, probabilities, flags, counts and metrics.
The cards are in Spanish and contain no comment text. `doc/` remains read-only
and gitignored.

## Privacy check

R5 passes. The public frame and all seven outputs contain no comment text, no
context window, no POS/token internals and no `author_hash`. The privacy scan
reports zero `@name` mentions. The output directory is local; the integration
test writes only to `tmp_path`. The data card, model card and this report
contain no comment text.

## Limitations and caveats

- The pack is the pilot pack. The application corpus run remains deferred; its
  unlabeled data cannot be scored against the pilot reference.
- The bootstrap intervals depend on the frozen published row order. The order is
  used only for the RNG sequence; no published value builds a prediction. If the
  published order changes, the intervals must be rechecked.
- The published tables are inside `doc/resultados_hito2.zip`; the CLI takes an
  extracted `resultados/publicable` directory and the README shows the
  extraction.
- The summary output is flat; the comparison reads the published two-row header
  through the S1 helper.
- The pilot is one video and a small sample. The partition is by thread, not by
  video; generalisation to a new video is untested.
- The 209 implicit negatives remain a protocol assumption; the 20-candidate
  audit is deferred.
- The 16 labels the listing cannot detect remain false negatives in coverage.
- The 17 candidates that never enter a test remain outside the evaluation.
- The pre-stable `GroupKFold` tie-break is reproduced deliberately; a future
  scikit-learn or numpy change will fail the slow margin test and must be
  investigated, not silently relaxed.
- The `inicio_oracion`/`_pregunta` newline rule is frozen; changing it needs an
  ADR.
- The mean abstention target passes, but seeds 2 and 4 exceed the 20% cap on
  test.
- The M2 − B1 interval excludes zero in only one seed; the report does not claim
  significance.
- The 548/550 reconciliation and F2/coverage-at-budget remain deferred.

## Decision

**Pass.** One command rebuilds the publication pack from the frozen inputs: 439
predictions, 30 system rows, 6 summary rows, 15 intervals and 5 diagnostics,
with zero deviations and zero privacy mentions. The prediction, systems,
summary and interval comparisons match the published tables; the data card,
model card and README are present and tested; S1–S5 remain green. The pack is
ready for approval.

## Follow-up

1. The application corpus run is the next slice; it needs its own design/spec
   and a privacy review.
2. The group should decide the `inicio_oracion`/`_pregunta` newline question; a
   change needs an ADR.
3. The team should confirm or revoke the documentation-only privacy exceptions
   for the S2, S3 and `docs/learn/` material.
4. The 20-candidate implicit-negative audit remains deferred.
5. The 548/550 reconciliation and F2/coverage-at-budget remain deferred.
6. Keep the published-key bootstrap order and the slow end-to-end test as the
   guard for the interval reproduction.
7. Push after approval; do not push before it.
