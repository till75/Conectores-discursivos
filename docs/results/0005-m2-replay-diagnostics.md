# M2 replay diagnostic report

**Slice:** S5 — M2 replay
**Date:** 2026-11-27
**Status:** pass
**Spec:** [0005-m2-replay.md](../specs/0005-m2-replay.md)
**Design note:** [0005-m2-replay.md](../design/0005-m2-replay.md)
**Commits:** `c76bf79..b3c3620`, plus this report commit
**Report owner:** Till

## Intended goal

Rebuild M2's 439 test labels, probabilities, provenance, rare-category flags,
traceability counts and the M2 and M2-con-abstención metric rows from the S2
candidates, the listing, the five frozen splits, the frozen embedding model and
the frozen rule set, without reading `predicciones_test.csv` to build them. The
margin is learned inside training only. S5 also had to resolve why the published
M2 margins initially differed from the replay.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The 15 frozen rules and their order are recorded | `test_rule_names_are_frozen`, `test_aplicar_reglas_each_rule`, `test_aplicar_reglas_requires_columns` | pass |
| Grammar annotation uses the character offsets and the `INICIO`/`FIN`/`X` fallbacks | `test_anotar_gramatica_offsets`, `test_anotar_gramatica_boundaries`, `test_anotar_gramatica_multiword_uses_first_token`, `test_anotar_gramatica_caches_by_text`, `test_anotar_gramatica_does_not_modify_input`, `test_anotar_gramatica_requires_columns` | pass |
| The M2 matrix appends the rule block and the POS block in order | `test_m2_feature_builder_order`, `test_m2_feature_builder_unseen_pos`, `test_m2_feature_builder_requires_pos_columns` | pass |
| M2 uses the strict listing restriction, never the M1 `vistas` union | `test_m2_list_restriction_single`, `test_m2_list_restriction_multiple`, `test_m2_never_uses_vistas`, `test_m2_unknown_unit_raises` | pass |
| Provenance, the rare-category flag and the abstention branch behave as specified | `test_m2_provenance`, `test_m2_rare_category_flag`, `test_m2_abstention` | pass |
| The margin is learned inside training by grouped CV, with the grid, 20% cap and smaller-margin tie rule | `test_choose_margin_for_uses_training_only`, `test_choose_margin_for_tie_keeps_smaller`; `test_m2_matches_published_metrics` | pass |
| Per-seed predictions select the frozen test threads and ignore unknown IDs | `test_m2_predictions_uses_reference_threads`, `test_m2_predictions_requires_columns`, `test_m2_output_has_no_text` | pass |
| The 439 core M2 labels, `p_M2`, `origen_M2` and `revisar_categoria` match the published rows | `test_m2_matches_published_predictions`; real replay has zero core deviations and `p_M2` within `1e-5` | pass |
| The ten per-seed metric rows and two summary rows match at three decimals | `test_m2_matches_published_metrics`; real replay has zero core and margin deviations | pass |
| Traceability matches `91/58/34/33/20/43` | `test_m2_traceability_matches_published`; real replay returns the six target counts | pass |
| The M2-con-abstención rows match, including the published margins | `test_m2_matches_published_metrics`; margins `0.15/0.10/0.20/0.10/0.20`, `margin_deviations == []` | pass |
| The prediction frame carries no text, windows, POS internals, author hash or name mention | `test_m2_output_has_no_text`; real-data scan finds 0 `@` mentions and no forbidden columns | pass |
| S1–S4 stay green and unchanged | Default and slow suites | pass |
| The real models are exercised by slow tests that skip when unavailable | `test_m2_matches_published_predictions`, `test_m2_matches_published_metrics`, `test_m2_traceability_matches_published` | pass |

## What was built

`src/conectores/rules.py` holds `REGLAS`, `RULE_NAMES`, `aplicar_reglas`,
`anotar_gramatica`, `load_nlp`, `M2FeatureBuilder`, `MIN_EJEMPLOS`,
`POS_COLUMNS`, `Token` and `NLP`. `src/conectores/models.py` holds `M2Model`,
`choose_margin_for`, `_group_kfold_splits`, `m2_predictions`,
`_m2_predictions_and_margins`, `replay_m2`, `M2Result`, `M2_COLUMNS`,
`M2_INPUT_COLUMNS`, `TRACEABILITY_TARGET` and `_compare_m2_predictions`.
`M1Model` exposes a private `_make_builder` hook so M2 reuses the two-step fit.

The unit behaviours were driven by failing tests. The slow published comparison
was written as a regression guard; its margin assertion then failed and drove
the `GroupKFold` tie-break fix.

The teaching material is in
[`docs/learn/04-m2-rules-provenance.md`](../learn/04-m2-rules-provenance.md).
The [S4 report](0004-m1-replay-diagnostics.md) covers the M1 features; S5 does
not repeat them.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest -q` | 124 passed, 13 deselected (11.61 s) |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m pytest -q -m slow` | 13 passed, 124 deselected (66.06 s) |
| `.\.venv\Scripts\python.exe -m pytest -q tests/test_integration.py -m slow -k "m2"` | 3 passed, 9 deselected (31.78 s) |
| Real-data M2 replay | 439 predictions, 10 metric rows, 2 summary rows, zero core deviations, zero margin deviations |

## Diagnostic evidence

### Split and per-seed results

The replay runs on seeds 0–4. Each seed has its own frozen test split and hash.
The test comments are resolved to threads through the reference; training is
every candidate outside those threads. No thread crosses the split.

| Seed | Test comments | Test threads | Candidates | Undetected | M2 F1 | M2 + abstention F1 | Margin | Abstention | Frozen hash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 31 | 19 | 65 | 5 | 0.432 | 0.452 | 0.15 | 12.31% | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 29 | 19 | 97 | 3 | 0.545 | 0.571 | 0.10 | 5.15% | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 29 | 19 | 92 | 4 | 0.500 | 0.476 | 0.20 | 30.43% | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 37 | 19 | 124 | 8 | 0.452 | 0.449 | 0.10 | 8.87% | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 26 | 19 | 61 | 4 | 0.486 | 0.615 | 0.20 | 21.31% | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The published summary means, reproduced by the replay to three decimals:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| M2 | 0.483 | 0.606 | 0.634 | 0.599 | 0.407 |
| M2 con abstención | 0.513 | 0.639 | 0.689 | 0.715 | 0.401 |

The mean abstention is 15.6%. Seeds 2 (30.43%) and 4 (21.31%) exceed the 20%
cap on the test split. The cap applies while choosing the margin on the
training CV holdout, not to the test outcome, so R3's mean target passes while
two seeds exceed it.

### Margin investigation

The no-abstention M2 matched the published rows from the start. The first
prototype learned margins `0.20/0.15/0.15/0.15/0.20` instead of the published
`0.15/0.10/0.20/0.10/0.20`; 27 of 439 `abstiene_M2` rows differed. No tested
training-only CV variant under scikit-learn 1.9.1 reproduced the published
margins.

The cause was the `GroupKFold` tie-break. Older scikit-learn sorted equal-sized
groups with `np.argsort` (quicksort) before reversing the order; 1.9.1 uses
`kind="stable"`. Equal-sized thread groups therefore land in different folds,
changing the CV probabilities and the learned margin. M1 is robust to the
change; M2 is not.

| Seed | Published | Stable tie-break | Pre-stable tie-break |
|---|---:|---:|---:|
| 0 | 0.15 | 0.20 | **0.15** |
| 1 | 0.10 | 0.15 | **0.10** |
| 2 | 0.20 | 0.15 | **0.20** |
| 3 | 0.10 | 0.15 | **0.10** |
| 4 | 0.20 | 0.20 | **0.20** |

`models._group_kfold_splits` now reproduces the pre-stable tie-break
explicitly. M1 margins stay `0.10/0.10/0.10/0.05/0.15`; M2 margins match the
published values and `margin_deviations` is empty. The grouped-CV protocol,
grid, 20% cap and smaller-margin tie rule are unchanged, so no ADR was needed.
The partial-result fallback approved in the spec was not used.

### Traceability and review

The aggregate traceability counts match the published values:

| Count | Value |
|---|---:|
| Discourse labels | 91 |
| Fixed by the listing | 58 |
| Fixed by the listing and correct | 34 |
| Chosen by the model | 33 |
| Chosen by the model and correct | 20 |
| Flagged for category review | 43 |

The listing fixed 63.7% of the discourse categories and the model chose 36.3%.
The review flag covers 43 of 91 discourse labels (47.3%). The listing-fixed
accuracy is 34/58 (58.6%); the model-chosen accuracy is 20/33 (60.6%).

### Bootstrap intervals

The intervals are reproduced from the published predictions by S1. S5's M2
rows match those predictions, so the intervals are unchanged.

| Seed | M2 − B1 95% interval | Excludes zero | M2 − M1 95% interval | Excludes zero |
|---|---|---|---|---|
| 0 | [−0.274, 0.259] | no | [0.000, 0.201] | no |
| 1 | [−0.025, 0.637] | no | [0.133, 0.436] | yes |
| 2 | [−0.007, 0.742] | no | [0.151, 0.431] | yes |
| 3 | [0.033, 0.343] | yes | [−0.036, 0.113] | no |
| 4 | [−0.255, 0.282] | no | [−0.198, 0.124] | no |

The mean gain M2 − B1 is +0.155, but the interval excludes zero in only seed 3.
The mean gain M2 − M1 is +0.123, with intervals excluding zero in seeds 1 and 2.
The headline is a point estimate, not a significance claim.

### Coverage

Coverage is 0.407 on average. The denominator includes the 5/3/4/8/4 labels the
listing never detects, so the undetected labels are charged as false negatives.
The hard ceiling is 0.8: 16 of the 80 evaluated labels cannot be detected by the
listing.

## Privacy check

The real prediction frame has 439 rows and 11 columns: `semilla`, `comment_id`,
`thread_id`, `unidad`, `inicio`, `oro`, `M2`, `p_M2`, `origen_M2`,
`revisar_categoria` and `abstiene_M2`. It has no `texto`, `ventana`, `pos_*`,
`tok_*`, `author_hash` or `@name` mention. A real-data scan finds 0 `@` mentions
and no forbidden columns.

The spaCy document cache and the embedding cache live in memory and are never
written. The slice writes no prediction file; the integration tests read the
ignored `doc/` inputs and write only to `tmp_path`. This report contains no
comment text. The teaching fragments in `docs/learn/` remain under their
documented exception.

## Limitations and caveats

- The replay is a faithful port of the notebook, including its choices; it is
  not an independent validation of M2 or of the published numbers.
- The margin fix reproduces the pre-stable `GroupKFold` tie-break. It relies on
  numpy's quicksort ordering for equal-sized groups; the slow margin test guards
  against future drift. If scikit-learn or numpy changes again, investigate or
  pin the behaviour; do not silently switch to the stable tie-break.
- The frozen embedding model is external and pretrained. It is not trained on
  the pilot labels, but it may have seen similar text during pretraining.
- The `inicio_oracion` and `_pregunta` newline rule is frozen for reproduction.
  Phrases can span lines; changing the rule would change M1/M2 and needs an ADR.
- The training corpus is small (about 149–212 candidates per seed), so the
  margin, IDF and rare-category estimates are noisy. The published values are
  the target, not a claim that the estimates are stable.
- The 17 candidates that never enter a test split are outside the M2 evaluation.
  The 209 implicit negatives remain a protocol assumption; the 20-candidate
  audit is still deferred.
- The slow tests require the spaCy model, the embeddings extra, the frozen
  embedding model and the `doc/` inputs; they skip when any is absent.
- The slice has no CLI or file writer and does not run the application corpus.
- The partial-result fallback approved in the spec was not used; the result is a
  full pass.
- The mean abstention target passes, but seeds 2 and 4 exceed the 20% cap on the
  test split. This matches the published behaviour and is not hidden.
- The M2 − B1 interval excludes zero in only one seed; the report does not claim
  significance.

## Decision

**Pass.** M2 is rebuilt from the S2 candidates, the listing, the frozen splits,
the frozen embedding model and the frozen rule set. The 439 core labels,
`p_M2`, provenance and review flags match; the ten per-seed rows and two summary
rows match at three decimals; the M2-con-abstención rows and the
`0.15/0.10/0.20/0.10/0.20` margins match; traceability is
`91/58/34/33/20/43`; and the prediction frame is private. S1–S4 remain green.
The published-margin mismatch was resolved by reproducing the pre-stable
`GroupKFold` tie-break, so the slice is a full pass, not partial.

## Follow-up

1. S6 — publication pack: one end-to-end command, data card, model card and the
   privacy check.
2. The group should decide the `inicio_oracion`/`_pregunta` newline question; a
   change needs an ADR before code.
3. The team should confirm or revoke the documentation-only privacy exceptions
   for the S2, S3 and `docs/learn/` material.
4. The 20-candidate implicit-negative audit remains deferred.
5. Keep `_group_kfold_splits` and the slow margin assertion; they are the guard
   against future `GroupKFold`/numpy drift.
6. Push after approval; do not push before it.
