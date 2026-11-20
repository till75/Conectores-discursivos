# Metric replay diagnostic report

**Slice:** S1 — metric replay
**Date:** 2026-11-20
**Status:** pass
**Spec:** [0001-metric-replay.md](../specs/0001-metric-replay.md)
**Design note:** [0001-metric-replay.md](../design/0001-metric-replay.md)
**Commits:** `8ae054f..98fedb2`, plus the final docs commit
**Report owner:** Till

## Intended goal

Recompute the published metric table from the published predictions and the
reference, without training a model. The replay must reproduce the per-seed
table, the summary table, the 15 bootstrap intervals, the five frozen hashes and
the v4 traceability counts, and it must exit non-zero when a cell deviates by
more than three decimals. The slice establishes the yardstick for later
reimplementations: if a fresh candidate construction or model lands at a
different F1, the replay shows whether the difference is the code, the local
package versions or the protocol.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The replay reproduces the 30 per-seed rows to three decimals | `test_replay_matches_published` (slow) runs the CLI with `--check` and exits 0; the replay reports zero deviations | pass |
| The replay reproduces the six summary rows to three decimals | Same integration run; `replay_summary.csv` has six rows and matches `resumen_sistemas.csv` | pass |
| The replay reproduces the 15 interval rows to three decimals | Same integration run; `replay_intervals.csv` has 15 rows and matches `intervalos_confianza.csv` | pass |
| The replay verifies the five frozen hashes | `test_replay_frozen_hashes` (slow) changes one test file and the replay names the hash; the unmodified run reports zero deviations | pass |
| The diagnostics reproduce the published counts | `replay_diagnostics.csv` gives 65/97/92/124/61 candidates and 5/3/4/8/4 undetected labels; the report gives 91/58/34/33/20/43 traceability counts | pass |
| One perturbed cell makes `--check` exit 1 and name the cell | `test_replay_perturbed_cell_fails` (slow) perturbs a published cell and asserts exit 1 and the named cell | pass |
| The output contains no comment text or `author_hash` | `test_output_has_no_text` checks the output columns and the report; the integration run writes only IDs, labels and metrics | pass |
| The integration tests are slow and skip without the ignored data | `pytest -m slow` runs three tests; the module skips when `doc/resultados_hito2.zip` is absent | pass |

## What was built

`src/conectores/metrics.py` holds the five metric definitions, the
undetected-label parser, the thread bootstrap, the per-seed table, the summary
table, the interval table, the table comparison, the undetected-count bridge,
the traceability counts, the `replay` result object and the CLI. The CLI reads
the predictions, reference, listing, CSL, published tables, hashes and frozen
test files, writes four replay tables and a Markdown report, and returns 1 on a
deviation when `--check` is set.

`tests/test_metrics.py` covers the unit behaviours with synthetic fixtures.
`tests/test_integration.py` covers the real published data and is marked
`slow`. The design note and the spec are part of this slice's final docs commit.

The unit behaviours were driven by failing tests. The integration and privacy
tests were written after the replay matched the real data; they are regression
guards for the end-to-end contract, not failing-first tests.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | 21 passed, 3 deselected |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m pytest -m slow` | 3 passed, 21 deselected |
| Real-data replay with `--check` (integration test) | exit 0; zero deviations |

## Diagnostic evidence

The replay runs on seeds 0–4. Each seed has its own frozen test split and hash.
The candidate count is the number of prediction rows for that seed; the
undetected count is the number of reference labels in the seed's test threads
that the listing never matches.

| Seed | Test comments | Test threads | Candidates | Undetected | Frozen hash |
|---|---:|---:|---:|---:|---|
| 0 | 31 | 19 | 65 | 5 | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 29 | 19 | 97 | 3 | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 29 | 19 | 92 | 4 | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 37 | 19 | 124 | 8 | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 26 | 19 | 61 | 4 | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The published summary means, reproduced by the replay to three decimals:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| B0 | 0.315 | 0.388 | 0.433 | 0.207 | 0.666 |
| B1 | 0.328 | 0.471 | 0.493 | 0.572 | 0.236 |
| M1 | 0.360 | 0.499 | 0.489 | 0.438 | 0.310 |
| **M2** | **0.483** | **0.606** | **0.634** | **0.599** | **0.407** |
| M1 + abstention | 0.394 | 0.516 | 0.531 | 0.528 | 0.317 |
| M2 + abstention | 0.513 | 0.639 | 0.689 | 0.715 | 0.401 |

The primary metric is F1 label. M2's per-seed values are 0.432, 0.545, 0.500,
0.452 and 0.486. The mean 0.483 is a point estimate over five repeated splits,
not five independent samples.

M2's abstention rate averages 15.6%; seeds 2 (30.4%) and 4 (21.3%) exceed the
20% cap. The M2 + abstention row's per-seed abstention is 12.3%, 5.2%, 30.4%,
8.9% and 21.3%.

The traceability counts are 91 discourse labels, 58 fixed by the listing (34
correct), 33 chosen by the model (20 correct) and 43 marked "revisar
categoría". The last figure is 47.3% of the 91 discourse predictions.

The bootstrap intervals for M2 − B1, by seed:

| Seed | 95% interval | Excludes zero |
|---|---|---|
| 0 | [−0.274, 0.259] | no |
| 1 | [−0.025, 0.637] | no |
| 2 | [−0.007, 0.742] | no |
| 3 | [0.033, 0.343] | yes |
| 4 | [−0.255, 0.282] | no |

The mean difference is +0.155. The interval excludes zero in 1 of 5 seeds. For
M2 − M1 the mean difference is +0.123 and the interval excludes zero in seeds 1
and 2. For M1 − B1 the mean difference is +0.032 and every interval includes
zero.

The replay's comparison rounds both sides to three decimals and treats NaN as
equal. The real-data run reports zero deviations; the replay's systems,
summary and intervals tables match the published CSVs.

Caveats: the five seeds are repeated splits of the same 150 rows, not
independent samples. The 16 undetected labels are reconstructed from the
reference and the listing; the replay's parser is a minimal version of the
candidate logic. The 209 implicit negatives are candidates the protocol assumes
were reviewed and rejected. The application corpus has no reference labels.

## Privacy check

The replay output contains no comment text and no `author_hash`. The output
columns are IDs, list forms, labels, probabilities, flags and metrics. The unit
test `test_output_has_no_text` checks the four replay CSVs and the Markdown
report for `texto`, `text`, `author_hash`, `anotacion`, `comentario` and `@`
mentions. The output and the report contain zero `@name` mentions. The
integration test reads the ignored local data but writes only counts, IDs and
metrics. The report itself contains no comment text. The committed tree
contains no comment text, context window or `author_hash`.

## Limitations and caveats

- The replay reproduces the notebook's metric choices, including its mistakes.
  It does not validate the model, the candidate construction or the split.
- The 16 undetected labels are reconstructed from the reference and the
  listing. The replay's parser is a minimal version of the candidate logic; a
  full candidate construction may find different spans.
- The 209 implicit negatives are a protocol assumption. The input audit
  suggests checking 20 unmarked candidates to settle whether they were really
  reviewed and rejected.
- The published `705 unidades` and the audit's `614 formas` are not
  reconciled. The replay uses the listing's forms and does not choose between
  the two counts.
- The bootstrap is deterministic given the seed and `n`, but it depends on
  numpy's RNG. A different numpy version could move the intervals.
- The summary's published CSV has a two-row header; the replay reads it with
  `header=[0, 1]` and flattens the metric names. The comparison skips the
  second header row.
- The integration tests skip when `doc/resultados_hito2.zip` is absent. The
  unit suite runs without the ignored data.
- The five seeds are repeated splits of the same 150 rows. The intervals
  measure split variability, not sampling variability across new comments.

## Decision

**Pass.** The replay reproduces the three published tables to three decimals
with zero deviations, verifies the five frozen hashes, reproduces the v4
diagnostics and traceability counts, and names a perturbed cell or hash. The
yardstick is established. The slice is ready to move on.

## Follow-up

1. Slice B — candidate construction: rebuild the 273 candidates from the
   reference and the listing, including the 16 undetected labels and the 8 CSL
   matches. The replay's undetected-label parser is the starting point.
2. Write `docs/00-brief.md` and `docs/plan.md`; they are still missing. The
   brief should choose the 705-versus-614 count and confirm the three-decimal
   tolerance.
3. Audit 20 unmarked candidates to settle the 209 implicit negatives.
4. Reconcile the published `705 unidades` with the audit's `614 formas`.
5. The F2 question remains open; it needs the candidate construction and the
   reference labels.
