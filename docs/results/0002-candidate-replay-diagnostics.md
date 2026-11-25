# Candidate replay diagnostic report

**Slice:** S2 — candidate replay
**Date:** 2026-11-25
**Status:** pass
**Spec:** [0002-candidate-replay.md](../specs/0002-candidate-replay.md)
**Design note:** [0002-candidate-replay.md](../design/0002-candidate-replay.md)
**Commits:** `335ffab..5eca0ad`, plus the final docs commit
**Report owner:** Till

## Intended goal

Rebuild the 273 candidate occurrences, the 64 positives, the 209 negatives and
the 16 undetected labels from `referencia_piloto.csv`,
`listado_fuentes2009.csv` and `csl_excluidas.csv`, without reading
`predicciones_test.csv`. The rebuilt keys and gold labels must equal the
published predictions per seed, and the counts must match the published
diagnostics exactly. S2 also replaces S1's minimal undetected-label parser with
the full construction while keeping S1's replay and published tables unchanged.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The listing yields 614 forms, lower-cased, sense numbers removed, longest first | `test_listing_forms_normalises_and_deduplicates`, `test_listing_pattern_prefers_longest_form`; integration run gives 614 | pass |
| A form matches standalone, case-insensitively, with letter boundaries; an empty listing never matches | `test_listing_pattern_boundaries`, `test_listing_pattern_empty_listing_never_matches` | pass |
| Annotation parsing removes markup and returns half-open spans with normalised labels | `test_read_annotation_plain_text_and_spans`, `test_read_annotation_normalises_the_span_label`, `test_read_annotation_without_markup`, `test_normalise_label_maps_variants` | pass |
| The builder returns the candidate columns, flags and context | `test_build_candidates_happy_path` | pass |
| A CSL match is excluded, recorded, and its zone is not undetected; one zone may exclude several matches | `test_build_candidates_excludes_csl` | pass |
| A match on an already-claimed span becomes a second piece; the first overlapping span wins | `test_build_candidates_skips_second_piece`, `test_build_candidates_first_span_wins` | pass |
| An empty listing yields no candidates and all non-CSL spans undetected | `test_build_candidates_empty_listing` | pass |
| Missing required columns raise `ValueError` naming the frame and column | `test_build_candidates_requires_columns` | pass |
| The published counts are 614 forms, 284 raw, 8 CSL, 3 second pieces, 273 candidates, 64 positives, 209 negatives and 16 undetected; `284 = 273 + 8 + 3` | `test_candidates_match_published_counts` (slow) | pass |
| Per seed the rebuilt candidates match the published keys and gold labels: 65/97/92/124/61, 439 appearances, 256 unique tested, 17 never tested, 5/3/4/8/4 undetected | `test_candidates_match_published_predictions` (slow) | pass |
| S1 compatibility: the wrapper returns the builder's undetected rows and the S1 replay still has zero deviations | `test_metrics_undetected_labels_uses_builder`; S1 slow tests; replay report `Deviations: 0` | pass |
| Privacy: the public view has no `texto`, `ventana`, `author_hash` or `@name`; the slice writes no candidate file | `test_public_candidates_drops_text`, `test_candidate_output_has_no_text`; real-data check gives 0 `@` mentions | pass |
| Real-data tests are slow and skip without the ignored inputs | `pytest -m slow` runs five tests; the module skip condition covers the four inputs | pass |

## What was built

`src/conectores/candidates.py` now holds the shared annotation parser and label
normaliser, the longest-first listing pattern, the `CandidateSet` builder with
the CSL and second-piece exclusions, the public view and the per-seed counter.
`src/conectores/metrics.py` no longer has its own parser, pattern or normaliser;
`undetected_labels` delegates to `build_candidates(...).undetected`.

`tests/test_candidates.py` covers the unit behaviours with synthetic fixtures.
`tests/test_integration.py` gains two slow tests against the frozen pilot data.
The S1 unit and slow tests remain in the suite and stay green.

Two compatibility details are explicit in the code:

- S1's undetected fixtures predate `is_reply` and `text_normalized`. The
  undetected rows depend on neither, so the wrapper supplies `False` and `""`
  when the columns are absent; `build_candidates` itself still requires them.
- S1's position-based CSL fixture carries `comment_id`, `inicio` and `fin` but
  no `unidad`. The builder therefore requires `comment_id` plus either `unidad`
  or both `inicio` and `fin`. The published CSL file uses the pair columns and
  never exercises the position branch.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | 39 passed, 5 deselected |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `.\.venv\Scripts\python.exe -m pytest -m slow` | 5 passed, 39 deselected |
| S1 replay with `--check` (inside the slow suite) | exit 0; zero deviations |
| Real-data candidate build (read-only) | 614 forms, 284 raw, 8 CSL, 3 second pieces, 273 candidates, 64/209, 16 undetected |

## Diagnostic evidence

The builder runs on the frozen pilot inputs only. It does not read the test
IDs, train a model or change the split, so the seeds and the abstention
threshold are not inputs to this slice. The per-seed check uses the five frozen
test files solely to filter the built candidates.

| Seed | Test comments | Test threads | Candidates | Undetected | Frozen hash |
|---|---:|---:|---:|---:|---|
| 0 | 31 | 19 | 65 | 5 | `009f6a053441d892ac8e5ecc752245db5d75b1e83596302f00ae00c2af5842de` |
| 1 | 29 | 19 | 97 | 3 | `dbfa9e5b70c79cc22560af49ce191bde88ac0d7bf077556fe420fa58a13a001a` |
| 2 | 29 | 19 | 92 | 4 | `fe6a51c6f6625b97e20899be09e841a8427db6fddc13846dc884ee4e46c35ecc` |
| 3 | 37 | 19 | 124 | 8 | `c72d5e4a14172e81d11417163f047e5c3adbe124d977f71ec240c0cc1776922a` |
| 4 | 26 | 19 | 61 | 4 | `e479487d20b218e88226ebc5ae09b848031ebbf60cdf7c9da351c2ae17181d63` |

The 273 candidates are unique. The five test splits contain 439 candidate
appearances in total; 256 candidates appear in at least one split and 17 never
do. The global count covers all 273; the key-and-gold comparison covers the 439
published appearances.

The eight CSL exclusions match `excluidas_dentro_de_csl.csv` on
`(comment_id, unidad, csl)`. The three second pieces and the 16 undetected
labels are new diagnostics; their counts match the spec's targets.

No model result is produced by this slice, so abstention, coverage, the
bootstrap intervals and the listing-versus-model category split are not
applicable here. S1's values for those fields are unchanged and still reproduce.

## Worked examples

**Privacy exception (documentation only).** Till granted an exception on
2026-11-25 to reproduce the eight short fragments below so that the candidate
categories can be understood. The exception is limited to this report. It does
not change R5 for the corpus, the application data, the code, the tests, the
commit messages or any other artifact. The fragments contain no `@name` mention
and no `author_hash`. Till will raise the exception with the team; until the
team confirms it, treat it as provisional.

`[[...]]` marks the piece under discussion; `<<...>>` marks a skipped second
piece. Each block quotes the whole comment when it is short, or the sentence
containing the unit when the comment is longer.

1. **614 forms — one form from the listing inventory, shown in use.**

   > [[Bueno]], si hubieran dejado dinero quizás esto no estaría pasando

   The listing rows `bueno 4`, `bueno 2`, `bueno 1`, `bueno 3` and `bueno 5`
   all collapse to the single normalised form `bueno`. The 614 are distinct
   forms, not occurrences.

2. **284 raw matches — a regex match before any exclusion.**

   > Estoy [[de acuerdo]]... los pago.

   This match survives as a candidate. The 284 also include the matches that
   become the 8 CSL exclusions and the 3 second pieces.

3. **8 CSL exclusions — a match dropped inside a semi-free construction.**

   > [[No]], si boric lo hizo perfecto 😂😂😂😂

   The match `No` is inside the CSL zone `No, si`, so it is recorded as an
   exclusion and never becomes a candidate.

4. **3 second pieces — a match skipped because its unit was already claimed.**

   > Es lo [[más]] <<lógico>>, ya que las alzas deben ser graduales.

   The reference unit is `lo más lógico`. `[[más]]` became the candidate with
   gold label `OP:MODAL`; `<<lógico>>` is the second piece and was skipped.

5. **273 candidates — a surviving match.**

   > Esto [[definitivamente]] es una bomba de tiempo para que reviente. 😡

   Gold label: `OP:ENUNCIATIVO`.

6. **64 positives — a candidate whose gold label is a discourse label.**

   > A andar en bicicleta [[nomás]]

   Gold label: `OP:ARGUMENTATIVO`.

7. **209 negatives — a candidate labelled `NO_DISCURSIVO`.**

   > Kast, [[ya]] estás hundido!

   Gold label: `NO_DISCURSIVO`. Here no reference span overlaps the match, so
   it is one of the implicit negatives that the protocol assumes were reviewed
   and rejected.

8. **16 undetected labels — a reference span the listing never matches.**

   > [[Wataca]], devuelve la plata

   Gold label: `CON:INTERACTIVO`. Because the listing has no form that matches
   it, it never becomes a candidate; it is reported only as an undetected
   label.

The arithmetic behind the examples:

- `284 = 273 + 8 + 3`: raw matches split into candidates, CSL exclusions and
  second pieces.
- `273 = 64 + 209`: candidates split into positives and negatives.
- The 16 undetected labels sit outside the 273: they are reference spans, not
  matches.

## Privacy check

`public_candidates` returns 273 rows and 11 columns: IDs, thread, reply flag,
form, offset, gold label and the five position flags. It has no `texto`, no
`ventana` and no `author_hash`. A real-data scan of every public cell finds zero
`@name` mentions. The slice writes no candidate file: the integration test
reads the ignored `doc/` inputs and writes only to `tmp_path`. Unit fixtures are
synthetic strings.

Apart from the eight fragments in the documented exception above, the committed
tree contains no comment text, context window or `author_hash`. The exception is
limited to this report: the public view, the tests, the CLI output and the other
artifacts still carry no comment text. The eight fragments contain no `@name`
mention and no `author_hash`.

## Limitations and caveats

- The port is faithful to the notebook, including its regex limits: multi-word
  forms use their literal spacing, and flexible spacing or punctuation inside a
  form is not matched. Fixing that changes the candidate set and needs an ADR.
- The 209 negatives include explicit `NO_DISCURSIVO` spans and unmarked
  occurrences. The assumption that the unmarked ones were reviewed and rejected
  remains a protocol assumption; the 20-candidate audit is still deferred.
- The 17 candidates that never enter a test split are covered only by the
  global count, not by a published per-seed row.
- The position-based CSL branch is a compatibility boundary; the published CSL
  file only uses `(comment_id, unidad)` pairs.
- The listing has 705 entries and 699 raw strings; this slice uses the 614
  distinct forms and does not reconcile the three counts.
- The builder uses the reference's `text_normalized` only when `anotacion` has
  no `::`. That reproduces the notebook, but it means rows marked
  `Sin etiquetas` are searched for implicit negatives.
- The slice does not train or refit B0, B1, M1 or M2, and it does not build the
  listing's label map or the baselines' category rules.

## Decision

**Pass.** The builder reproduces every published count and every published
candidate key and gold label, the raw-match invariant holds, the S1 replay
still has zero deviations, and the privacy contract holds. The repository can
now go from the raw annotation to candidate rows without reading the
predictions, which is the precondition for replaying B0, B1, M1 and M2.

## Follow-up

1. S3 — baseline replay: build the listing's label map, B0's first-category
   rule and B1's frequency rule, then replay both baselines from the candidates.
2. Audit 20 unmarked candidates to settle the 209 implicit negatives.
3. Reconcile the 705 entries, 699 raw strings and 614 forms if a later slice
   needs the listing's category inventory.
4. Revisit flexible spacing and punctuation inside multi-word forms only with an
   ADR, because it changes the candidate set and every downstream metric.
