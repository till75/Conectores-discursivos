# M1 replay diagnostic report

**Slice:** S4 — M1 replay
**Date:** 2026-11-26
**Status:** pass
**Spec:** [0004-m1-replay.md](../specs/0004-m1-replay.md)
**Design note:** [0004-m1-replay.md](../design/0004-m1-replay.md)
**Commits:** `15709a6..a503d67`, plus the final docs commit
**Report owner:** Till

## Intended goal

Rebuild M1's 439 test labels, probabilities, five margins and ten per-seed plus
two summary metric rows from the S2 candidates, the listing, the five frozen
splits and the frozen embedding model, without reading `predicciones_test.csv`
to build them. Reproducing M1 proves the window, punctuation, position and
embedding features and the two-step training protocol before S5 adds M2's
rules.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The feature matrix has the three TF-IDF blocks, six flags and 384-column embedding in the specified order | `test_feature_builder_shapes` | pass |
| The vectorizers are fitted on training only; an unseen test form adds no column | `test_feature_builder_fits_on_training_only` | pass |
| A wrong embedding dimension and a missing candidate column are named | `test_feature_builder_rejects_wrong_embedding_dimension`, `test_feature_builder_requires_columns` | pass |
| Step 1 learns discourse use and step 2 learns the category on positive rows only | `test_m1_predicts_permitted_category`, `test_m1_single_allowed_label` | pass |
| The listing and training labels restrict the category; the top class is the fallback | `test_m1_training_labels_extend_the_listing`, `test_m1_falls_back_to_top_class` | pass |
| One-class training falls back to `unica` or `NO_DISCURSIVO` | `test_m1_single_positive_label`, `test_m1_no_positive_training` | pass |
| The margin is learned by five-fold grouped CV on training, with the grid, the 20% cap and the smallest-margin tie rule | `test_choose_margin_uses_training_only`, `test_choose_margin_tie_keeps_smaller` | pass |
| The test threads select rows, training is the complement, unknown IDs are ignored and an empty split returns no rows | `test_m1_predictions_uses_reference_threads`, `test_m1_predictions_ignores_unknown_and_empty`, `test_m1_predictions_excludes_test_threads_from_training`, `test_m1_predictions_all_empty` | pass |
| The rebuilt predictions match the 439 published rows, 65/97/92/124/61 per seed, with labels exact and `p_M1` within `1e-5` | `test_m1_matches_published_predictions` (slow); real-data run reports zero deviations | pass |
| The ten per-seed rows and the two summary rows match at three decimals, including margins and abstention | `test_m1_matches_published_metrics` (slow); real-data run reports zero deviations | pass |
| The metric rows use the S2 undetected counts 5/3/4/8/4 | `test_replay_m1_uses_undetected_counts` | pass |
| The prediction frame has no text, window, author hash or name mention | `test_m1_output_has_no_text`; real-data frame has ten columns and zero `@` | pass |
| S1, S2 and S3 stay green and unchanged | Full default and slow suites | pass |
| Unit tests use a fake embedder; the real model is exercised by a slow test that skips when unavailable | `test_sentence_embedder_caches_and_returns_384`, `test_sentence_embedder_accepts_a_model_name`, `test_sentence_embedder_real_model` | pass |

## What was built

`src/conectores/features.py` holds `FeatureBuilder`, `sentence_embedder`,
`RASGOS`, `EMBEDDING_MODEL` and `EMBEDDING_DIM`. `src/conectores/models.py`
holds `M1Model`, `choose_margin`, `m1_predictions`, `replay_m1` and
`M1Result`; `m1_predictions` and `replay_m1` share one prediction loop so the
learned margins are available without refitting. `tests/test_features.py`,
`tests/test_models.py` and `tests/test_integration.py` cover the unit
behaviours, the replay and the published tables.

The unit behaviours were driven by failing tests. The integration and
real-model tests were written after the replay matched the real data; they are
regression guards for the end-to-end contract, not failing-first tests.

The teaching material is in [`docs/learn/`](../learn/README.md): the candidate
window and six flags, TF-IDF, and the 384-dimensional embedding. The
[S3 report](0003-baseline-replay-diagnostics.md) has the B0/B1 flowchart and
examples; the [S2 report](0002-candidate-replay-diagnostics.md) has the
candidate categories. The S4 report does not repeat those fragments.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | 79 passed, 10 deselected |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m pytest -m slow` | 10 passed, 79 deselected (38.75 s) |
| M1 slow tests only | 2 passed (21.43 s) |
| Real-data M1 replay | 439 predictions, 10 metric rows, 2 summary rows, zero deviations |

## Diagnostic evidence

The replay runs on seeds 0–4. Each seed has its own frozen test split and
hash. The test comments are resolved to threads through the reference; the
training rows are every candidate outside those threads. No thread crosses the
split.

| Seed | Test comments | Test threads | Candidates | Undetected | M1 F1 | M1 + abstention F1 | Margin | Abstention | Frozen hash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 31 | 19 | 65 | 5 | 0.333 | 0.400 | 0.10 | 16.92% | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 29 | 19 | 97 | 3 | 0.267 | 0.294 | 0.10 | 15.46% | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 29 | 19 | 92 | 4 | 0.261 | 0.308 | 0.10 | 8.70% | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 37 | 19 | 124 | 8 | 0.426 | 0.448 | 0.05 | 4.03% | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 26 | 19 | 61 | 4 | 0.513 | 0.522 | 0.15 | 26.23% | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The published summary means, reproduced by the replay to three decimals:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| M1 | 0.360 | 0.499 | 0.489 | 0.438 | 0.310 |
| M1 con abstención | 0.394 | 0.516 | 0.531 | 0.528 | 0.317 |

The prediction comparison covers `(semilla, comment_id, unidad, inicio)` and
the `oro`, `M1` and `p_M1` values. It reports zero left-only rows, zero
right-only rows, zero label mismatches and zero probabilities outside the
`1e-5` gate. The design-note prototype observed a maximum probability
difference of `3.6e-7`; the integration gate is `1e-5`.

The 439 appearances are 256 unique candidates seen in at least one test split;
the 17 candidates that never enter a test split are outside the M1 evaluation.
M1's coverage includes the 5/3/4/8/4 undetected labels as false negatives.

The margins are learned inside each training split by five-fold `GroupKFold`
on the threads, with the `0.00–0.30` grid, the 20% abstention cap and the
smallest-margin tie rule. The test split is never used. The embedding model is
`paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensions, CPU, frozen; it is not
trained on the pilot labels.

M1 does not record listing-versus-model category provenance; that is M2's
traceability field in S5. The listing restricts the allowed set, but the
category is chosen by the model. The bootstrap intervals are not recomputed by
S4; S1 already reproduces them from the published predictions, and S4's
predictions match those rows.

## Privacy check

The prediction frame has 439 rows and ten columns: seed, IDs, thread, form,
offset, gold label, `M1`, `p_M1`, `abstiene` and `M1_con_abstencion`. It has no
`texto`, no `ventana` and no `author_hash`. A real-data scan of every
prediction cell finds zero `@name` mentions. The embedding cache holds window
text in memory only and is never written. The slice writes no prediction file;
the integration test reads the ignored `doc/` inputs and writes only to
`tmp_path`.

This report contains no comment text. The teaching fragments in `docs/learn/`
remain under their documented exception; they are not repeated here. The code,
tests, CLI output and other artifacts still carry no comment text.

## Limitations and caveats

- The replay is a faithful port of the notebook, including its choices; it is
  not an independent validation of M1 or of the published numbers.
- The frozen embedding model is external and pretrained. It is not trained on
  the pilot labels, but it may have seen similar text during pretraining.
- The `inicio_oracion` newline rule is frozen for reproduction. The author
  flagged that phrases can span lines; changing it would alter M1/M2 and needs
  an ADR. It remains an open question for the group.
- The `1e-5` probability gate is a fidelity guard. The observed prototype
  difference is `3.6e-7`; a future library drift could exceed the gate and must
  be investigated or pinned, not silently relaxed.
- The training corpus is small (about 149–212 candidates per seed), so the IDF
  and margin estimates are noisy. The published values are the target, not a
  claim that the estimates are stable.
- The 17 candidates that never enter a test split are outside the M1
  evaluation. The 209 implicit negatives remain a protocol assumption; the
  20-candidate audit is still deferred.
- The slow tests require the `embeddings` extra and the frozen model; they skip
  when either is unavailable. The unit tests use a fake embedder, so they do
  not exercise the real 384-dimensional model.
- M1 has no listing-versus-model provenance; that belongs to M2.
- The slice has no CLI or file writer and does not run the application corpus.

## Decision

**Pass.** M1 is rebuilt from the S2 candidates, the listing, the frozen splits
and the frozen embedding model. The 439 labels match exactly, `p_M1` is within
`1e-5`, the ten per-seed rows and two summary rows match at three decimals, and
the margins and abstention rates are reproduced. S1, S2 and S3 remain green.

## Follow-up

1. S5 — M2 replay: add the listing restriction, the frozen rules, spaCy POS,
   the rare-category flag and provenance; compare the published M2 rows and
   the traceability counts. Any change to the rule set needs an ADR.
2. The group should decide the `inicio_oracion` newline question; a change
   needs an ADR before code.
3. The team should confirm or revoke the documentation-only privacy exceptions
   for the S2, S3 and `docs/learn/` material.
4. The 20-candidate implicit-negative audit remains deferred.
5. Push after approval; do not push before it.
