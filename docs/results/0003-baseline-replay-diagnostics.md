# Baseline replay diagnostic report

**Slice:** S3 — baseline replay
**Date:** 2026-11-25
**Status:** pass
**Spec:** [0003-baseline-replay.md](../specs/0003-baseline-replay.md)
**Commits:** `42231a3..f1b410b`, plus the final docs commit
**Report owner:** Till

## Intended goal

Rebuild B0 and B1 from the S2 candidates, the listing and the five frozen test
splits, without reading `predicciones_test.csv` to build them. The rebuilt B0
and B1 columns must match the 439 published test rows, and the ten per-seed
metric rows and the two summary rows must match the published tables to three
decimals.

## Worked examples

**Privacy exception (documentation only).** Till granted an exception on
2026-11-25 to reproduce the six short fragments below so that the B0 and B1
rules can be understood. The exception is limited to this report and extends
the S2 exception. It does not change R5 for the corpus, the application data,
the code, the tests, the commit messages or any other artifact. The fragments
contain no `@name` mention and no `author_hash`. Till will raise the exception
with the team; until the team confirms it, treat it as provisional.

`[[...]]` marks the candidate form in its sentence. Each block quotes the whole
comment when it is short, or the sentence containing the form when the comment
is longer.

### B0 — the listing's first label

B0 does not look at the context or the gold label. It takes the first label
that the listing gives for the form.

1. **A form with one label.**

   > Pero el alza de los pasajes en regiones va, [[ya]] que solo estancarán en la RM

   The listing gives `ya` only `OP:MODAL`, so B0 predicts `OP:MODAL`. The gold
   label here is `NO_DISCURSIVO`: this is a B0 false positive.

2. **A form with five labels.**

   > [[Bueno]], si hubieran dejado dinero quizás esto no estaría pasando

   The listing gives `bueno` five labels in this order:
   `CON:CONTINUATIVO`, `CON:CIERRE`, `CON:INTERACTIVO`,
   `CON:REFORMULATIVOS`, `OP:MODAL`. B0 takes the first,
   `CON:CONTINUATIVO`; the gold label is `CON:INTERACTIVO`.

3. **A form with four labels.**

   > si Boric robó la plata, [[entonces]], quítensela, y así la plata viene de vuelta

   The listing gives `entonces` four labels in this order:
   `CON:CONCLUSIVO`, `CON:CONSECUTIVO`, `CON:CONTINUATIVO`,
   `CON:TEMPORAL`. B0 takes the first, `CON:CONCLUSIVO`; the gold label is
   `CON:CONSECUTIVO`.

### B1 — the training majority per form

B1 counts the gold labels of the form in the training candidates only. The test
form itself is never used to choose its label.

1. **A clear majority, seed 0.**

   > Pero el alza de los pasajes en regiones va, [[ya]] que solo estancarán en la RM

   In seed 0's training, `ya` has 15 `NO_DISCURSIVO` and 1 `OP:MODAL`. B1
   predicts `NO_DISCURSIVO`, which is also the gold label. The same occurrence
   shows the contrast with B0: B0 predicts `OP:MODAL`, B1 predicts
   `NO_DISCURSIVO`.

2. **A tie, seed 2.**

   > [[Bueno]], ahora les toca vivir del alza, esto es sin llorar.

   In seed 2's training, `bueno` has two `CON:INTERACTIVO` and two `OP:MODAL`.
   The tie goes to `CON:INTERACTIVO`, the label that appears first in the
   training rows. B1 predicts `CON:INTERACTIVO`; the gold label is
   `CON:CIERRE`.

3. **An unseen form, seed 1.**

   > Esto [[definitivamente]] es una bomba de tiempo para que reviente. 😡

   `definitivamente` never appears in seed 1's training. B1 falls back to the
   global training majority, `NO_DISCURSIVO` (135 of the training candidates),
   and predicts `NO_DISCURSIVO`. The gold label is `OP:ENUNCIATIVO`; B0 gets
   this one right because the listing's first label for the form is
   `OP:ENUNCIATIVO`.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The listing map has 614 forms, 548 with one label and 66 with two to six | `test_listing_label_branches`, `test_listing_label_map_collapses_and_orders`; real-data count | pass |
| The four label rules and the missing-value boundary are correct | `test_listing_label_branches` | pass |
| B0 takes the first listing label and ignores context and gold | `test_b0_predict_first_label_and_unseen` | pass |
| B0 falls back to `NO_DISCURSIVO` for an unseen form | `test_b0_predict_first_label_and_unseen` | pass |
| B1 takes the training majority; a tie goes to the first occurrence | `test_b1_predict_most_frequent`, `test_b1_predict_tie_uses_first_occurrence` | pass |
| B1 falls back to the global training majority for an unseen form, with the same tie-break | `test_b1_predict_global_tie_uses_first_occurrence` | pass |
| Test rows come from the frozen test threads, training is the complement, unknown IDs are ignored | `test_baseline_predictions_uses_reference_threads` | pass |
| The rebuilt predictions match all 439 published rows, 65/97/92/124/61 per seed | `test_baselines_match_published_predictions` (slow); real-data run has zero left-only, zero right-only and zero value mismatches | pass |
| The ten per-seed rows and the two summary rows match at three decimals | `test_baselines_match_published_metrics` (slow); real-data run reports zero deviations | pass |
| The metrics use the S2 undetected counts 5/3/4/8/4 | The replay passes `count_undetected` totals into `compute_metrics`; changing them moves the rows | pass |
| The prediction frame has no text, context, author hash or name mention | `test_baseline_output_has_no_text`; real-data frame has eight columns and zero `@` | pass |
| S1 and S2 stay green | Full suite and slow suite | pass |
| Real-data tests are slow and skip without the ignored inputs | `pytest -m slow` runs seven tests; the module skip condition covers the four inputs | pass |

## What was built

`src/conectores/baselines.py` holds the listing label map, B0's first-label
rule, B1's training-majority rule with the first-occurrence tie-break and the
global fallback, the per-seed prediction frame, and the replay that adds the
metric rows, the summary and the deviations. `tests/test_baselines.py` covers
the unit behaviours with synthetic fixtures. `tests/test_integration.py` gains
two slow tests against the frozen pilot data. The unit behaviours were driven by
failing tests. The integration tests were written after the replay matched the
real data; they are regression guards for the end-to-end contract, not
failing-first tests. The S1 and S2 tests remain in the suite and stay green.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | 52 passed, 7 deselected |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m pytest -m slow` | 7 passed, 52 deselected |
| Real-data B0/B1 replay | 439 predictions, 10 metric rows, 2 summary rows, zero deviations |

## Diagnostic evidence

The replay runs on seeds 0–4. Each seed uses its own frozen test split and
hash. The test comments are resolved to threads through the reference; the
training rows are every candidate outside those threads. No thread crosses the
split.

| Seed | Test comments | Test threads | Candidates | Undetected | B0 F1 | B1 F1 | Frozen hash |
|---|---:|---:|---:|---:|---:|---:|---|
| 0 | 31 | 19 | 65 | 5 | 0.360 | 0.444 | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 29 | 19 | 97 | 3 | 0.293 | 0.229 | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 29 | 19 | 92 | 4 | 0.305 | 0.278 | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 37 | 19 | 124 | 8 | 0.275 | 0.267 | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 26 | 19 | 61 | 4 | 0.341 | 0.424 | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The published summary means, reproduced by the replay to three decimals:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| B0 | 0.315 | 0.388 | 0.433 | 0.207 | 0.666 |
| B1 | 0.328 | 0.471 | 0.493 | 0.572 | 0.236 |

The prediction comparison covers `(semilla, comment_id, unidad, inicio)` and
the `oro`, `B0` and `B1` values. It reports zero left-only rows, zero right-only
rows and zero value mismatches. The 439 appearances are 256 unique candidates
seen in at least one test split; the 17 candidates that never enter a test split
are outside the B0/B1 evaluation.

B1's fallback path is exercised: the test splits contain 11, 18, 14, 21 and 14
unseen forms for seeds 0–4. The global training majority is `NO_DISCURSIVO` in
all five seeds, so an unseen form predicts `NO_DISCURSIVO`. The tie-break is
also exercised: seed 0 has ties for `entonces` and `igual`, seed 2 for `bueno`,
and seeds 3 and 4 for `igual`; the first-occurrence rule reproduces every
published row.

No model result is produced by this slice, so abstention, the bootstrap
intervals and the listing-versus-model category split are not applicable here.
S1's values for those fields are unchanged and still reproduce.

## Privacy check

The prediction frame has 439 rows and eight columns: seed, IDs, thread, form,
offset, gold label, B0 and B1. It has no `texto`, no `ventana` and no
`author_hash`. A real-data scan of every prediction cell finds zero `@name`
mentions. The slice writes no prediction file: the integration test reads the
ignored `doc/` inputs and writes only to `tmp_path`. Unit fixtures are synthetic
strings.

Apart from the six fragments in the documented exception above, the committed
tree contains no comment text, context window or `author_hash`. The exception is
limited to this report; the code, tests, CLI output and other artifacts still
carry no comment text. The six fragments contain no `@name` mention and no
`author_hash`.

## Limitations and caveats

- B1's tie-break is a choice, not a measured fact. The pilot covers it in four
  tied units across the five seeds, and the first-occurrence rule reproduces
  every published row; an unseen tie is not proven by the pilot.
- The global fallback is `NO_DISCURSIVO` because the negatives are the majority
  in every training split. The rule is the training majority; a future corpus
  with a different majority would change the fallback.
- B0's first-label rule is the baseline's intended weakness: 66 listing forms
  have two to six labels, and B0 always takes the first. The examples above show
  the resulting false positive and two category errors.
- The 17 candidates that never enter a test split are outside the B0/B1
  evaluation. The 209 implicit negatives remain a protocol assumption; the
  20-candidate audit is still deferred.
- The summary comparison uses three decimals, so unrounded differences below
  0.0005 are invisible. The published `resumen_sistemas.csv` has a two-row
  header; the integration test flattens it and does not change the artifact.
- The slice has no CLI or file writer. It exposes functions and this report.
- The six worked examples are real fragments under the documented exception;
  they are not a precedent for other artifacts.

## Decision

**Pass.** B0 and B1 are rebuilt from the S2 candidates, the listing and the
frozen splits, with 439 predictions, ten per-seed metric rows and two summary
rows matching the published tables and zero deviations. The S1 replay and the
S2 candidate counts remain green. The baseline floor is now reproducible.

## Follow-up

1. S4 — M1 replay: build the window, punctuation and position features, fit the
   two-step logistic regression, and learn the abstention margin inside training
   only.
2. Keep B0/B1 as the published floor for the M1 and M2 comparisons.
3. The team should confirm or revoke the two documentation-only privacy
   exceptions for the S2 and S3 reports.
4. The 20-candidate implicit-negative audit remains deferred.
