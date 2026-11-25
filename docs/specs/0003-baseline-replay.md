# Spec 0003 — baseline replay

**Slice:** S3 — baseline replay
**Status:** approved
**Date:** 2026-11-25
**Approved:** 2026-11-25 by Till
**Requirements source:** `docs/00-brief.md`, `docs/plan.md`,
`doc/equipo11_B0_B1_M1_M2.ipynb`, `doc/resultados_hito2.zip`,
`docs/specs/0002-candidate-replay.md`

## Outcome

A caller can rebuild the B0 and B1 predictions from the S2 candidates, the
listing and the five frozen test splits, without reading `predicciones_test.csv`
to build them. The rebuilt B0 and B1 columns match the 439 published test rows
exactly, and the ten per-seed metric rows and the two summary rows match the
published tables to three decimals.

## Interface

### Module (`src/conectores/baselines.py`)

```python
NO = "NO_DISCURSIVO"

@dataclass(frozen=True)
class BaselineResult:
    predictions: pd.DataFrame   # 439 rows: one per test candidate per seed
    metrics: pd.DataFrame       # 10 rows: B0 and B1 x 5 seeds
    summary: pd.DataFrame       # 2 rows: mean and std per system
    deviations: list[str]       # empty when the replay matches

def listing_label(
    macro: object, categoria: object, subcategoria: object
) -> str: ...

def listing_label_map(listing: pd.DataFrame) -> dict[str, list[str]]: ...

def b0_predict(
    test: pd.DataFrame, labels: Mapping[str, Sequence[str]]
) -> list[str]: ...

def b1_predict(train: pd.DataFrame, test: pd.DataFrame) -> list[str]: ...

def baseline_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
) -> pd.DataFrame: ...

def replay_baselines(
    candidate_set: CandidateSet,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    published: Mapping[str, pd.DataFrame],
) -> BaselineResult: ...
```

`listing_label` maps one listing row to one project label. `listing_label_map`
maps each normalised form to its distinct labels in listing row order.
`b0_predict` and `b1_predict` return one label per test row. `baseline_predictions`
returns one row per test candidate per seed. `replay_baselines` adds the metric
rows, the summary rows and the deviations from the published tables.

### Listing label map

`listing_label` applies the notebook's `etiqueta_listado`:

- `macro == "Operador"` gives `"OP:" + categoria.upper()`.
- `categoria.startswith("Ordenador")` gives
  `"CON:" + ("INICIO" if subcategoria == "De inicio" else subcategoria.upper())`.
- `categoria.startswith("Reformulativo")` gives `"CON:REFORMULATIVOS"`.
- Otherwise it gives `"CON:" + categoria.upper()`.

`categoria` and `subcategoria` are stripped; a missing value is treated as the
empty string. `macro` is compared as given. The published listing uses
`Operador` and `Conector`, and the placeholder `─` in `subcategoria` for every
category except `Ordenador` and `Reformulativo`; the rule never produces
`CON:─` on the published data.

`listing_label_map` builds the form with the S2 rule (trailing sense number
removed, stripped, lower-cased), computes one label per row, and collapses
duplicates while preserving first occurrence. The published listing yields 614
forms: 548 have one label and 66 have two to six. B0 uses the first label; the
66 ambiguous forms are the cases where the listing alone cannot choose.

### B0

`b0_predict` returns `labels.get(form, [NO])[0]` for each test row. It ignores
the context, the gold label and the training split. Every real candidate form
is in the listing, so the `NO` fallback is a unit-test boundary, not a
real-data path.

### B1

`b1_predict` uses the training candidates only:

- For each form, the most frequent gold label in training.
- Ties are broken by the label's first occurrence in the training frame's row
  order.
- A form absent from training falls back to the most frequent gold label in the
  whole training set, with the same first-occurrence tie-break.

The training frame is the candidate frame filtered to the threads that are not
in the seed's test threads; its row order is the candidate frame's row order.
On the pilot the global fallback is `NO_DISCURSIVO` in all five seeds, but the
rule is the training majority, not a hard-coded `NO`.

The notebook writes the tie-break as `value_counts().index[0]`. The explicit
first-occurrence rule reproduces all five published seeds; it makes the choice
stable if pandas changes its tie order.

### Split and predictions

`baseline_predictions` resolves each test comment ID to its thread through the
reference. The test candidates are the candidates whose `thread_id` is one of
those test threads; the training candidates are the rest. Unknown test IDs are
ignored. This is the same thread filter that S2 uses for `seed_candidate_counts`
and that S1 uses for `count_undetected`; the frozen `test_semillaN.txt` files
are the contract, and `GroupShuffleSplit` is not rerun.

The returned frame has one row per test candidate per seed with `semilla`,
`comment_id`, `thread_id`, `unidad`, `inicio`, `oro`, `B0` and `B1`. The real
inputs give 65, 97, 92, 124 and 61 rows for seeds 0–4, 439 in total.

### Metrics and summary

`replay_baselines` computes each B0/B1 row with `metrics.compute_metrics`, using
the seed's undetected count from `metrics.count_undetected` on
`candidate_set.undetected` (5, 3, 4, 8 and 4). The `metrics` frame has
`sistema`, `semilla`, the five metric columns, `abstencion` and `margen`; the
last two are `NaN` for B0 and B1, as in the published table.

`summary` is `metrics.summary_systems(metrics)`: one row per system with the
mean and sample standard deviation of the five metrics.

### Published comparison

`replay_baselines` compares three tables when they are present in `published`:

- `predictions`: keys `(semilla, comment_id, unidad, inicio)`, values `oro`,
  `B0` and `B1`. Missing keys on either side and any value mismatch are
  deviations.
- `systems`: keys `(sistema, semilla)`, filtered to B0 and B1, all non-key
  columns compared at three decimals.
- `summary`: key `sistema`, filtered to B0 and B1, all non-key columns compared
  at three decimals.

A missing or empty table is skipped. `deviations` is empty only when every
present table matches.

### Input requirements and failures

`listing` must provide `unidad`, `macrofuncion`, `categoria` and `subcategoria`.
`candidates` must provide `comment_id`, `thread_id`, `unidad`, `oro` and
`inicio`. `reference` must provide `comment_id` and `thread_id`. `train` and
`test` passed to `b0_predict`/`b1_predict` must provide `unidad` and `oro` (B0
only needs `unidad`). A missing required column raises `ValueError` naming the
frame and column, for example `listing is missing required column: categoria`.

An empty listing gives an empty map and B0 predicts `NO` for every row. An empty
test split gives no prediction rows and no metric rows. Unknown test IDs are
ignored.

## Behaviour

### Target values

The published per-seed `F1_etiqueta` values, which the integration test must
reproduce at three decimals:

| Seed | B0 | B1 |
|---|---:|---:|
| 0 | 0.360 | 0.444 |
| 1 | 0.293 | 0.229 |
| 2 | 0.305 | 0.278 |
| 3 | 0.275 | 0.267 |
| 4 | 0.341 | 0.424 |

The published summary means:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| B0 | 0.315 | 0.388 | 0.433 | 0.207 | 0.666 |
| B1 | 0.328 | 0.471 | 0.493 | 0.572 | 0.236 |

The integration test compares all five metrics per seed and both summary
columns (mean and standard deviation), not only `F1_etiqueta`.

### Candidate and metric provenance

The builder reads `candidate_set.candidates` and `candidate_set.undetected`
from S2. It does not read `predicciones_test.csv` to build B0/B1; the published
predictions are used only for comparison. It does not change the candidate set,
the split, the seeds, the threshold or the metrics.

## Acceptance criteria

1. **Listing label map.** `listing_label` returns the four branch outputs;
   `listing_label_map` returns 614 forms, 548 with one label and 66 with two to
   six, in listing row order with duplicates collapsed. *Happy:* `Operador` +
   `Modal` gives `OP:MODAL`. *Boundary:* `Ordenador` + `De inicio` gives
   `CON:INICIO`; `Reformulativo` + `Explicación` gives `CON:REFORMULATIVOS`.
   *Failure:* a missing required column raises `ValueError` naming it.

2. **B0.** The first listing label is used, context and gold are ignored, and an
   unseen form falls back to `NO`. *Happy:* a form with one label gives it.
   *Boundary:* a form with several labels gives the first. *Failure:* a form
   absent from the map gives `NO`, not a training label.

3. **B1.** The most frequent training label is used. *Happy:* a form with a
   clear majority. *Boundary:* a tie chooses the label that appears first in
   training. *Failure:* an unseen form uses the global training majority, with
   the same tie-break, not `NO` by default.

4. **Split.** Test candidates are the candidates in the frozen test threads;
   training candidates are the rest. No thread crosses the split. Unknown test
   IDs are ignored. *Happy:* one test thread selects its candidates. *Boundary:*
   an empty test split gives no rows. *Failure:* a candidate from a test thread
   never enters training.

5. **Predictions.** The rebuilt frame has 65/97/92/124/61 rows per seed and 439
   in total. It matches `predicciones_test.csv` on
   `(semilla, comment_id, unidad, inicio)` with zero left-only, zero right-only
   and zero `oro`/`B0`/`B1` value mismatches.

6. **Metrics.** The ten B0/B1 per-seed rows match `resultados_semillas.csv` at
   three decimals, and the two summary rows match `resumen_sistemas.csv` at
   three decimals, for all five metrics and both summary columns.

7. **Undetected labels.** The metrics use the S2 undetected counts 5/3/4/8/4;
   removing or changing them moves the metric rows and fails criterion 6.

8. **Privacy.** The prediction frame contains IDs, forms, offsets, gold labels
   and B0/B1; it contains no `texto`, `ventana`, `author_hash` or `@name`
   mention. The slice writes no prediction file. Unit fixtures are synthetic;
   the integration test reads the ignored `doc/` data and writes only to
   `tmp_path`.

9. **Compatibility.** S1's replay and S2's candidate counts stay green and
   unchanged. `baselines.py` does not modify `candidates.py` or `metrics.py`.

10. **Test split.** Unit tests run by default with synthetic fixtures. The
    real-data tests are marked `slow` and skip when `doc/resultados_hito2.zip`
    is absent.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_listing_label_branches` | unit | The four label rules and the missing-value handling. |
| `test_listing_label_map_collapses_and_orders` | unit | Sense numbers, case, duplicates and label order. |
| `test_b0_predict_first_label_and_unseen` | unit | First label; `NO` fallback. |
| `test_b1_predict_most_frequent` | unit | Majority label per form. |
| `test_b1_predict_tie_uses_first_occurrence` | unit | Tie-break by training order. |
| `test_b1_predict_unseen_uses_global_fallback` | unit | Unseen form uses the training majority. |
| `test_b1_predict_global_tie_uses_first_occurrence` | unit | Global fallback tie-break. |
| `test_baseline_predictions_uses_reference_threads` | unit | Test threads, training complement, unknown IDs ignored. |
| `test_baseline_predictions_requires_columns` | unit | Each missing column names its frame. |
| `test_baseline_output_has_no_text` | unit | No `texto`, `ventana`, `author_hash` or `@` mention. |
| `test_replay_baselines_reports_deviations` | unit | A perturbed prediction and a perturbed metric are named. |
| `test_baselines_match_published_predictions` | integration, slow | 439 rows; B0/B1 keys and values match. |
| `test_baselines_match_published_metrics` | integration, slow | Ten per-seed rows and two summary rows at three decimals. |

The existing S1 and S2 slow tests remain in the suite and must stay green.

## Out of scope

- Training or refitting M1 or M2.
- Features, embeddings, the frozen rules, POS, the rare-category flag,
  abstention and provenance.
- The candidate construction and its counts (S2).
- The metric definitions, the bootstrap intervals and the traceability counts
  (S1).
- The application corpus and its candidate counts.
- A CLI or a file writer. S3 exposes functions and a diagnostic report only.
- Changing the split, seeds, threshold, rules or metrics.

## Privacy impact

The B0/B1 predictions hold only IDs, forms, offsets, gold labels and the two
predictions. The rules read `unidad` and `oro`; they never read `texto` or
`ventana`. The slice writes no file. The integration test reads the ignored
`doc/` inputs and writes only to `tmp_path`. Unit fixtures use synthetic
strings. No `author_hash` is read or written. The report contains IDs, list
forms, labels, counts and metrics, with zero `@name` mentions.

## Evaluation protocol impact

None. B0 and B1 are the published baselines; the slice rebuilds them with the
same split, seeds, candidate set and metrics. It does not choose a threshold,
write a rule or change a metric. No ADR is needed.

## Contradictions and open points

- The notebook's B1 tie-break is implicit in `value_counts().index[0]`. This
  spec fixes it as first occurrence in training order. That reproduces all five
  seeds, but the pilot does not prove the rule for an unseen tie.
- B0 uses the full listing's first label, not the training labels. That is the
  definition of the listing baseline, not a bug.
- The 548/66 split describes label ambiguity in the listing, not the 273
  candidates. The 66 ambiguous forms are the ones a later model can choose
  between.
- The global fallback is `NO_DISCURSIVO` on the pilot because the negatives are
  the majority. The rule is the training majority; a future corpus with a
  different majority would change the fallback.
- The split is reconstructed from the frozen test files by thread, not by
  rerunning `GroupShuffleSplit`. The frozen files are the contract.
- `resumen_sistemas.csv` has a two-row header; the caller passes a flat frame
  with `sistema` and `metric_stat` columns, as S1 does.

## Rough size

One module (`baselines.py`), one unit test file, additions to
`tests/test_integration.py`, and the diagnostic report. About 450 lines.

## Approval

**Approved:** 2026-11-25 by Till.

**Approved decisions:**

1. The interface above: `listing_label`, `listing_label_map`, `b0_predict`,
   `b1_predict`, `baseline_predictions`, `replay_baselines` and
   `BaselineResult` with predictions, metrics, summary and deviations.
2. B1 tie-break: the label that appears first in the training frame's row
   order, for both the per-form majority and the global fallback.
3. The comparison targets: exact B0/B1 predictions (439 rows, zero
   mismatches) and three-decimal metrics and summary (ten and two rows).
4. The split: test threads from the frozen `test_semillaN.txt` files, training
   is the complement, unknown IDs ignored, `GroupShuffleSplit` not rerun.
5. No CLI and no changes to `candidates.py` or `metrics.py`; S1 and S2 stay
   green.

The S3 diagnostic report contains three B0 and three B1 worked examples under
a documentation-only privacy exception granted by Till on 2026-11-25. The
exception is limited to that report and does not change R5 for any other
artifact.

**Assumptions:**

- The notebook's `b0` and `b1` are the reference implementation.
- The frozen test files define the split.
- The listing has 548 single-label and 66 multi-label forms.
- The published B0/B1 columns and metric rows are the target.
- Missing `categoria`/`subcategoria` values are empty strings; the published
  listing has none.

**Deferred:**

- M1 and M2.
- Features, embeddings, rules, POS, rare-category flag and abstention.
- A baseline CLI or file writer.
- The application corpus.
- The 20-candidate implicit-negative audit.
