# Spec 0002 — candidate replay

**Slice:** S2 — candidate replay
**Status:** approved
**Date:** 2026-11-21
**Approved:** 2026-11-21 by Till
**Design note:** [0002-candidate-replay.md](../design/0002-candidate-replay.md)
**Requirements source:** `docs/00-brief.md`, `docs/plan.md`,
`doc/Equipo11_Propuesta_v4_hito2.docx`,
`doc/equipo11_B0_B1_M1_M2.ipynb`, `doc/resultados_hito2.zip`

## Outcome

A caller can rebuild the 273 candidate occurrences, the 64 positives, the 209
negatives and the 16 undetected labels from the reference, the listing and the
CSL file, and the result matches the keys, gold labels and per-seed counts of
`predicciones_test.csv` without reading the predictions.

## Interface

### Module (`src/conectores/candidates.py`)

```python
NO = "NO_DISCURSIVO"
LETRA = r"[\wáéíóúñÁÉÍÓÚÑü]"

@dataclass(frozen=True)
class CandidateSet:
    candidates: pd.DataFrame
    undetected: pd.DataFrame
    csl_excluded: pd.DataFrame
    second_pieces: pd.DataFrame
    raw_matches: int

def read_annotation(
    annotation: object,
) -> tuple[str | None, list[tuple[int, int, str, str]]]: ...

def normalise_label(label: str) -> str: ...

def listing_forms(listing: pd.DataFrame) -> list[str]: ...

def listing_pattern(listing: pd.DataFrame) -> re.Pattern[str]: ...

def build_candidates(
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
) -> CandidateSet: ...

def public_candidates(candidates: pd.DataFrame) -> pd.DataFrame: ...

def seed_candidate_counts(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
) -> dict[int, int]: ...
```

`read_annotation` returns `(None, [])` when the value is not a string or does
not contain `::`. Otherwise it returns the plain text with the annotation
markup removed and one span `(start, end, unidad, etiqueta)` per markup. Spans
are half-open character offsets into the plain text; labels are normalised.

`normalise_label` strips and upper-cases the label, maps
`CON:REFORMULATIVO*` to `CON:REFORMULATIVOS`, and maps `CON:ORDENADOR:*` and
`CON:ORDENADORES:*` to `CON:*`. The vocabulary is `NO_DISCURSIVO`,
`CON:ADICIÓN`, `CON:CIERRE`, `CON:CONCESIVO`, `CON:CONCLUSIVO`,
`CON:CONSECUTIVO`, `CON:CONTINUATIVO`, `CON:INTERACTIVO`,
`CON:REFORMULATIVOS`, `OP:ARGUMENTATIVO`, `OP:ENUNCIATIVO`,
`OP:INFORMATIVO` and `OP:MODAL`. The reference's
`CON:REFORMULATIVOS:EXPLICACIÓN` therefore becomes `CON:REFORMULATIVOS`.

`listing_forms` returns the distinct matching forms, longest first. A form is
`unidad`, with a trailing sense number removed (`\s*\d+$`), stripped and
lower-cased. Duplicate forms are collapsed. The published listing has 705 rows
and 614 distinct forms; 705 entries and 699 raw strings are recorded but are not
used as matching units. The 548/66 versus 550/64 category split is irrelevant
here: this slice uses forms, not categories.

`listing_pattern` compiles one case-insensitive pattern from the forms, longest
first, with no letter before or after a match. `LETRA` includes Spanish accented
characters. Multi-word forms are matched with the literal spacing in the form;
flexible spacing and punctuation inside a form are a known limitation, not part
of this slice.

### Candidate frame

`CandidateSet.candidates` has one row per listing match that survives the
exclusions:

| Column | Type | Meaning |
|---|---|---|
| `comment_id` | string | Reference comment ID. |
| `thread_id` | string | Reference thread ID. |
| `is_reply` | bool | Reference reply flag. |
| `unidad` | string | Matched text, lower-cased. |
| `inicio` | int | 0-based start offset of the match in the text used. |
| `oro` | string | Gold label, or `NO_DISCURSIVO` when no reference span overlaps. |
| `texto` | string | Text used for matching; private, in memory only. |
| `ventana` | string | Six words each side around the match; private, in memory only. |
| `coma_antes` | bool | A `,`, `;` or `:` immediately precedes the match. |
| `coma_despues` | bool | A `,`, `;` or `:` immediately follows the match. |
| `inicio_comentario` | bool | The match starts the comment. |
| `inicio_oracion` | bool | The match starts a sentence. |
| `fin_enunciado` | bool | The match ends a sentence or the comment. |

The text used for matching is the plain text reconstructed from `anotacion`
when the annotation contains `::`; otherwise it is `text_normalized`, or the
empty string when that value is missing. This reproduces the notebook: rows
marked `Sin etiquetas` are still searched in `text_normalized` for implicit
negatives.

`CandidateSet.undetected` has `comment_id`, `thread_id`, `unidad` and `oro`: one
row per reference span that no candidate claimed and that is not a CSL zone.

`CandidateSet.csl_excluded` has `comment_id`, `thread_id`, `unidad`, `inicio`
and `csl`: one row per listing match dropped because it overlaps a CSL zone.
`csl` is the reference unit of the zone.

`CandidateSet.second_pieces` has `comment_id`, `thread_id`, `unidad`, `inicio`
and `unidad_referencia`: one row per match dropped because its overlapping
reference span was already claimed by an earlier match.
`unidad_referencia` is that already-claimed reference unit.

`CandidateSet.raw_matches` is the number of regex matches before CSL and
second-piece filtering. The invariant is
`raw_matches == len(candidates) + len(csl_excluded) + len(second_pieces)`.

`public_candidates` returns a copy of the candidate frame without `texto` and
`ventana`. It is the only candidate view that may be written to a report or
test artifact.

`seed_candidate_counts` maps each test comment ID to its thread through the
reference, then counts candidates whose `thread_id` is in that seed's test
threads. Unknown test IDs are ignored. It returns `{seed: count}`.

The builder never reads `predicciones_test.csv`. The published predictions are
used only by the integration test, to compare the rebuilt candidate keys and
gold labels.

### Existing replay compatibility

`metrics.undetected_labels` keeps its four output columns and is reimplemented
as `build_candidates(...).undetected`. `metrics` imports `NO`,
`read_annotation`, `normalise_label` and `listing_pattern` from
`candidates.py`. The S1 replay, its CLI, its published tables and its frozen
hashes do not change.

## Behaviour

### CSL zones

A reference span is a CSL zone when either

- its `(comment_id, unidad)` pair appears in the CSL file, or
- the CSL file has `inicio` and `fin` and the span is fully contained in that
  range for the same comment.

The published `csl_excluidas.csv` has only `comment_id` and `unidad`; the
position branch exists to preserve S1's existing synthetic contract. CSL zones
are removed from the span list before matching. A listing match is excluded
when it overlaps a CSL zone (`match_start < zone_end and zone_start <
match_end`). Excluded matches are recorded, not turned into candidates, and
their zones are never reported as undetected.

### Matching and gold assignment

For each reference row, matches are visited left to right in the order the
pattern returns them. Each match is handled once:

1. If it overlaps a CSL zone, record a CSL exclusion and continue.
2. Find the first reference span in annotation order that overlaps the match.
3. If there is no overlapping span, create a candidate with
   `oro = NO_DISCURSIVO`.
4. If the span has not been used, create a candidate with the span's label and
   mark the span used.
5. If the span has already been used, record a second piece and skip the match.

If a match overlaps several spans, only the first is considered. If that first
span is already used, the match is a second piece even when a later overlapping
span is unused. After all matches, every non-CSL span that was never used
becomes an undetected label.

Positive means `oro != NO_DISCURSIVO`; negative means `oro == NO_DISCURSIVO`.
A match that overlaps an explicit `NO_DISCURSIVO` span is negative but marks the
span used, so the span is not also reported as undetected. The 209 negatives
include explicit negatives and candidates with no overlapping span; the
assumption that the unmarked ones were reviewed and rejected is recorded in the
report and is not resolved by this slice.

### Input requirements and failures

`reference` must provide `comment_id`, `thread_id`, `is_reply`,
`text_normalized` and `anotacion`. `listing` must provide `unidad`. `csl` must
provide `comment_id` and `unidad`; `inicio` and `fin` are optional. A missing
required column raises `ValueError` naming the frame and column, for example
`reference is missing required column: anotacion`.

An empty listing is valid: `listing_forms` returns `[]`, the pattern never
matches, there are no candidates, and every non-CSL reference span is
undetected. An empty CSL frame excludes nothing.

## Acceptance criteria

1. **Listing inventory.** The published listing yields 614 forms. Trailing
   sense numbers are removed, forms are lower-cased and duplicates collapse.
   *Happy:* `["Ya", "ya 2"]` yields `["ya"]`. *Boundary:* `["por lo tanto"]`
   stays one multi-word form. *Failure:* an empty listing yields no forms and a
   never-matching pattern.

2. **Annotation parsing.** `[ya::CON:ADICIÓN]` yields plain text `ya` and span
   `(0, 2, "ya", "CON:ADICIÓN")`. `[Dale::OP:MODAL]` yields
   `OP:MODAL`. *Boundary:* `[x::CON:REFORMULATIVOS:EXPLICACIÓN]` normalises to
   `CON:REFORMULATIVOS`. *Failure:* an annotation without `::` returns
   `(None, [])`; a missing `anotacion` column raises `ValueError`.

3. **Candidate construction.** One row per surviving match, with the columns in
   the table above. *Happy:* a matching span creates one positive candidate.
   *Boundary:* an unmatched reference span creates one undetected row. *Failure:*
   a match with no overlapping span creates a negative candidate, not an
   undetected row.

4. **CSL exclusion.** A match overlapping a CSL zone is recorded in
   `csl_excluded`, never in `candidates`, and its zone is not undetected.
   *Happy:* one CSL match gives one exclusion, zero candidates, zero
   undetected. *Boundary:* one CSL zone can exclude more than one match; each
   match is counted. *Failure:* a match outside the zone is unaffected.

5. **Second pieces.** A match overlapping an already-claimed span is recorded in
   `second_pieces` and skipped. *Happy:* two listing forms inside one
   multi-word reference unit give one candidate and one second piece.
   *Boundary:* the first overlapping span wins even if another overlapping span
   is unused. *Failure:* without a used span, the same match becomes a normal
   candidate.

6. **Published counts.** On the frozen pilot inputs, the builder returns
   284 raw matches, 8 CSL exclusions, 3 second pieces, 273 candidates, 64
   positives, 209 negatives, 16 undetected labels and 614 forms. The global
   invariant `284 = 273 + 8 + 3` holds.

7. **Per-seed replay.** Restricting candidates to each seed's frozen test
   threads gives 65, 97, 92, 124 and 61 candidates for seeds 0–4. For every
   seed, the restricted candidates match `predicciones_test.csv` on
   `(comment_id, unidad, inicio, oro)` with zero left-only and zero right-only
   rows: 439 per-seed appearances in total. The 273 candidates are unique; 256
   appear in at least one seed's test set and 17 never do. The global count
   covers all 273; the key-and-gold comparison covers the 439 published
   appearances. Per-seed undetected counts are 5, 3, 4, 8 and 4.

8. **S1 compatibility.** `build_candidates(...).undetected` equals
   `metrics.undetected_labels(...)` on the real inputs (16 rows), and the
   existing S1 replay still reproduces its published tables with zero
   deviations.

9. **Privacy.** `public_candidates` contains neither `texto` nor `ventana` and
   no `author_hash`; it contains no `@name` mention. The slice writes no
   candidate file. Unit fixtures are synthetic; the integration test reads the
   ignored `doc/` data and writes only to `tmp_path`.

10. **Test split.** Unit tests run by default with synthetic fixtures. The
    real-data tests are marked `slow` and skip when
    `doc/resultados_hito2.zip` is absent.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_listing_forms_normalises_and_deduplicates` | unit | Trailing sense numbers, case and duplicates collapse to the expected forms, longest first. |
| `test_listing_pattern_boundaries` | unit | `ya` matches standalone but not inside `playa`; case-insensitive matching works. |
| `test_read_annotation_plain_text_and_spans` | unit | Markup is removed, offsets and normalised labels are correct. |
| `test_read_annotation_without_markup` | unit | No `::` returns `(None, [])`. |
| `test_build_candidates_happy_path` | unit | One positive, one explicit negative, one implicit negative and one undetected row from a synthetic reference. |
| `test_build_candidates_excludes_csl` | unit | A match inside a CSL zone is excluded and the zone is not undetected. |
| `test_build_candidates_skips_second_piece` | unit | Two matches inside one multi-word unit give one candidate and one second piece. |
| `test_build_candidates_first_span_wins` | unit | The first overlapping span supplies the gold label; a used first span makes the match a second piece. |
| `test_build_candidates_empty_listing` | unit | No candidates; every non-CSL span is undetected. |
| `test_build_candidates_requires_columns` | unit | Each missing required column raises `ValueError` with its name. |
| `test_public_candidates_drops_text` | unit | `texto` and `ventana` are absent; IDs, forms, labels and flags remain. |
| `test_seed_candidate_counts_uses_reference_threads` | unit | Test IDs resolve through the reference; unknown IDs are ignored. |
| `test_metrics_undetected_labels_uses_builder` | unit | The compatibility wrapper returns the builder's undetected rows. |
| `test_candidates_match_published_counts` | integration, slow | 614 forms, 284 raw, 8 CSL, 3 second pieces, 273 candidates, 64 positive, 209 negative, 16 undetected. |
| `test_candidates_match_published_predictions` | integration, slow | Per-seed 65/97/92/124/61; 439 appearances match the published keys and gold labels; 273 unique candidates, 17 never in a test split; per-seed undetected 5/3/4/8/4. |
| `test_candidate_output_has_no_text` | unit | `public_candidates` has no `texto`, `ventana`, `author_hash` or `@` mention. |

The existing S1 slow tests remain in the suite and must stay green.

## Out of scope

- Training or refitting B0, B1, M1 or M2.
- Building the listing's label map, B0's first-category rule or B1's frequency
  rule. Those belong to S3.
- The train/test split, seeds, margins, bootstrap and metrics.
- POS features, embeddings, the rare-category flag, the frozen rules and
  provenance.
- The application corpus and its 19,741/20,097 candidate counts.
- The 20-candidate implicit-negative audit and the 548/66 versus 550/64
  reconciliation.
- Fixing the regex's handling of flexible spacing or punctuation inside
  multi-word forms. That changes the candidate set and needs an ADR.
- A candidate CLI or a file writer. S2 exposes a function and a diagnostic
  report only.
- F2 and coverage-at-budget.

## Privacy impact

The candidate frame holds `texto` and `ventana` in memory because later slices
need the context. They are never written to the repository, the diagnostic
report, the test artifacts or a CSV. `public_candidates` is the only view that
may leave the process, and it drops both columns. The integration test reads
the ignored `doc/` inputs and writes only to `tmp_path`. Unit fixtures use
synthetic strings. No `author_hash` is read or written. The report contains
IDs, list forms, labels, flags and counts, with zero `@name` mentions.

## Evaluation protocol impact

None. The builder does not read the test IDs, does not train and does not change
the split, seeds, abstention threshold, rules or metrics. It rebuilds the
candidate set that the published predictions already assume. The per-seed check
uses the frozen `test_semillaN.txt` files only to filter the built candidates;
the builder itself is independent of the split. No ADR is needed.

If the builder's counts differ from 273/64/209/16/8/3, stop and investigate.
Do not adjust the target counts or the matching rules to fit them. Changing the
candidate construction in a way that changes the set is a later decision with an
ADR.

## Contradictions and open points

- The notebook's CSL matching uses `(comment_id, unidad)` only. S1 also has a
  synthetic position-based CSL test. This spec keeps that position branch in
  the shared builder so S1's contract and published outputs are unchanged; the
  published CSL file never exercises it.
- The plan says S2 replaces S1's minimal parser. The implementation delegates
  `metrics.undetected_labels` to the builder, so the full construction is the
  authoritative one while the S1 replay stays green.
- The brief records 705 entries, 699 raw strings and 614 forms. This slice uses
  the 614 forms; the other two are recorded counts, not matching units.
- The 209 negatives are a protocol assumption, not a measured audit. The report
  must repeat the caveat and the 20-candidate check remains deferred.
- The empty-listing and position-based CSL cases are compatibility boundaries;
  they are not present in the published inputs.

## Rough size

One module (`candidates.py`), one unit test file, additions to
`tests/test_integration.py`, and the diagnostic report. About 350 lines.

## Approval

**Approved:** 2026-11-21 by Till.

**Approved decisions:**

1. Keep the position-based CSL compatibility branch. A reference span is a CSL
   zone when its `(comment_id, unidad)` pair is listed, or when a CSL row with
   `inicio`/`fin` fully contains it. The published `csl_excluidas.csv` has only
   the pair columns, so the branch never fires on real data; it preserves S1's
   synthetic position test and allows `metrics.undetected_labels` to delegate
   to the builder.
2. Fix the candidate targets at 284 raw matches, 8 CSL exclusions, 3 second
   pieces, 273 candidates, 64 positives, 209 negatives, 16 undetected labels
   and 614 forms. Do not adjust the targets to fit an implementation.
3. Keep `metrics.undetected_labels` as the S1 compatibility entry point,
   delegating to `build_candidates(...).undetected`; S1's published tables,
   hashes and slow tests must stay unchanged.

**Assumptions:**

- The notebook's `construir_candidatos` is the reference implementation.
- The 273 candidates are unique. The 439 published rows are per-seed
  appearances; 256 candidates appear in at least one test split and 17 never
  do, so those 17 are covered by the global count rather than a published row.
- The 209 negatives include explicit `NO_DISCURSIVO` spans and unmarked
  candidates; the 20-candidate audit remains deferred.
- `texto` and `ventana` stay in memory; `public_candidates` is the only outward
  candidate view.
- Missing required columns raise `ValueError` naming the frame and column.
- An empty listing yields no forms, a never-matching pattern, zero candidates
  and all non-CSL spans undetected.
- `csl_excluded` and `second_pieces` columns are diagnostics; their extra
  columns do not change the candidate set.
- No ADR is needed: split, seeds, threshold, rules and metrics are unchanged.

**Deferred:**

- Training or refitting B0, B1, M1 or M2.
- The listing's label map, B0's first-category rule and B1's frequency rule.
- POS features, embeddings, the rare-category flag, the frozen rules and
  provenance.
- The application corpus and the 19,741/20,097 candidate counts.
- The 20-candidate implicit-negative audit and the 548/66 versus 550/64
  reconciliation.
- Flexible spacing or punctuation inside multi-word forms; that changes the
  candidate set and needs an ADR.
- A candidate CLI or file writer.
- F2 and coverage-at-budget.
