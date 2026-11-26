# Spec 0004 — M1 replay

**Slice:** S4 — M1 replay
**Status:** approved
**Date:** 2026-11-26
**Approved:** 2026-11-26 by Till
**Design note:** [0004-m1-replay.md](../design/0004-m1-replay.md)
**Requirements source:** `docs/00-brief.md`, `docs/plan.md`,
`doc/equipo11_B0_B1_M1_M2.ipynb`, `doc/resultados_hito2.zip`, `gate.toml`,
`docs/specs/0002-candidate-replay.md`, `docs/specs/0003-baseline-replay.md`

## Outcome

A caller can rebuild M1's 439 test labels, probabilities, five per-seed
margins and the ten per-seed plus two summary metric rows from the S2
candidates, the listing, the five frozen splits and the frozen embedding model,
without reading `predicciones_test.csv` to build them.

## Interface

### Features (`src/conectores/features.py`)

```python
Embedder = Callable[[Sequence[str]], np.ndarray]

EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
EMBEDDING_DIM = 384
RASGOS = [
    "coma_antes",
    "coma_despues",
    "inicio_comentario",
    "inicio_oracion",
    "fin_enunciado",
    "is_reply",
]

def sentence_embedder(model_name: str = EMBEDDING_MODEL) -> Embedder: ...

class FeatureBuilder:
    def fit(
        self, train: pd.DataFrame, embedder: Embedder
    ) -> FeatureBuilder: ...
    def transform(self, df: pd.DataFrame) -> csr_matrix: ...
```

`sentence_embedder` loads the frozen model on CPU and returns a callable that
maps a sequence of window strings to a float array of shape
`(len(texts), 384)`. It may cache by text; the cache lives in memory only.

`FeatureBuilder.fit` fits the three TF-IDF vectorizers on the training rows and
stores the embedder. `transform` returns the feature matrix for any frame with
the same columns. The model calls `fit` on training and `transform` on both
training and test.

### Model and replay (`src/conectores/models.py`)

```python
@dataclass(frozen=True)
class M1Result:
    predictions: pd.DataFrame   # one row per test candidate per seed
    metrics: pd.DataFrame       # 10 rows: M1 and M1 con abstención x 5 seeds
    summary: pd.DataFrame       # 2 rows: mean and std per system
    margins: Mapping[int, float]  # seed -> learned margin
    deviations: list[str]       # empty when the published tables match

class M1Model:
    def __init__(
        self,
        labels: Mapping[str, Sequence[str]],
        embedder: Embedder,
        seed: int = 0,
        C: float = 1.0,
    ): ...
    def fit(self, train: pd.DataFrame) -> M1Model: ...
    def prob(self, df: pd.DataFrame) -> np.ndarray: ...
    def predict(
        self, df: pd.DataFrame, margin: float = 0.0
    ) -> tuple[list[str], np.ndarray, np.ndarray]: ...

def choose_margin(
    train: pd.DataFrame,
    labels: Mapping[str, Sequence[str]],
    embedder: Embedder,
    seed: int = 0,
    max_abstention: float = 0.2,
) -> float: ...

def m1_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> pd.DataFrame: ...

def replay_m1(
    candidate_set: CandidateSet,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    published: Mapping[str, pd.DataFrame],
    embedder: Embedder,
) -> M1Result: ...
```

`M1Model.predict` returns `(labels, probabilities, abstention)`. The labels are
the no-abstention predictions when `margin=0.0`; the probabilities are `p_M1`;
the abstention flags are `abs(p - 0.5) < margin`.

`m1_predictions` returns one row per test candidate per seed with `semilla`,
`comment_id`, `thread_id`, `unidad`, `inicio`, `oro`, `M1`, `p_M1`, `abstiene`
and `M1_con_abstencion`. `M1` is the no-abstention label, `p_M1` is the
probability, `abstiene` is the learned-margin flag, and `M1_con_abstencion` is
`NO_DISCURSIVO` where `abstiene` and `M1` otherwise.

`replay_m1` adds the metric rows, the summary and the deviations from the
published tables. `margins` maps each seed to its learned margin.

### Types and units

- `p_M1` and `margen` are probabilities in `[0, 1]`; `abstencion` is a fraction
  in `[0, 1]`.
- `inicio` is a 0-based character offset into the text used for matching.
- The embedding block has exactly 384 float columns.
- The six flags are booleans in the candidate frame and floats in the feature
  matrix.
- Metrics are fractions in `[0, 1]`; the five names are the S1 names.

### Label vocabulary

`NO_DISCURSIVO`, `CON:<CATEGORÍA>` and `OP:<CATEGORÍA>`. The published
vocabulary is `NO_DISCURSIVO`, `CON:ADICIÓN`, `CON:CIERRE`, `CON:CONCESIVO`,
`CON:CONCLUSIVO`, `CON:CONSECUTIVO`, `CON:CONTINUATIVO`, `CON:INTERACTIVO`,
`CON:REFORMULATIVOS`, `OP:ARGUMENTATIVO`, `OP:ENUNCIATIVO`, `OP:INFORMATIVO` and
`OP:MODAL`. M1 predicts only a label seen in training; the allowed set
(`listing ∪ vistas`) restricts the choice, and the highest-probability training
class is the fallback when no allowed class exists. It does not invent labels.

## Behaviour

### Feature blocks

`FeatureBuilder.transform` concatenates, in this order:

1. word TF-IDF of `ventana`: `ngram_range=(1, 2)`, `min_df=1`,
   `sublinear_tf=True`;
2. character TF-IDF of `ventana`: `analyzer="char_wb"`,
   `ngram_range=(2, 5)`, `min_df=2`, `sublinear_tf=True`;
3. unit TF-IDF of `unidad`: `analyzer=lambda u: [u]`;
4. the six flags in the order of `RASGOS`, cast to float;
5. the embedding block, shape `(n, 384)`.

The three vectorizers are fitted on the training rows only. An unseen form or
an unseen n-gram in test is ignored by the fitted vocabulary; it does not add a
column. The embedding block is wrapped as a sparse matrix and appended last.
The feature order and the vectorizer settings are part of the contract because
they change the fitted model.

### Training

`M1Model.fit`:

- builds the training matrix with `FeatureBuilder.fit(train, embedder)` and
  `transform(train)`;
- fits step 1 with `LogisticRegression(C=C, class_weight="balanced",
  max_iter=2000, random_state=seed)` on `y = oro != NO_DISCURSIVO`;
- records `vistas = train[pos].groupby("unidad")["oro"].apply(set)`, where
  `pos = oro != NO_DISCURSIVO`;
- if there is at least one positive row and more than one positive label, fits
  step 2 with `LogisticRegression(C=C, max_iter=2000, random_state=seed)` on
  the positive rows only; otherwise sets `c2=None` and `unica` to the single
  positive label, or `NO_DISCURSIVO` when there is no positive row.

The default solver is the sklearn default (`lbfgs`); the spec does not override
it. `C=1.0` and `max_iter=2000` are the notebook's settings.

### Prediction and allowed labels

For each test row:

1. `p = c1.predict_proba(X)[:, 1]`.
2. If `abs(p - 0.5) < margin`, predict `NO_DISCURSIVO` and abstain.
3. If `p < 0.5`, predict `NO_DISCURSIVO` without abstaining.
4. Otherwise, build `permitidas = set(labels.get(unidad, [])) |
   vistas.get(unidad, set())`.
5. If `c2 is None`, return `unica`.
6. Otherwise choose the highest-probability class in `permitidas`; if no class
   is permitted, choose the highest-probability class overall. This fallback is
   the notebook's behaviour and must be preserved.

The listing's `labels` map is the S3 `listing_label_map`. The training labels
in `vistas` can add a label that the listing does not allow for the form; the
union is the notebook's rule.

### Margin

`choose_margin` uses `GroupKFold(n_splits=5)` on the training rows, grouped by
`thread_id`. For each fold it fits a fresh `M1Model` on the other folds and
gets the probabilities for the held-out fold. It then scans
`np.arange(0, 0.31, 0.05)`:

- keep the rows with `abs(p - 0.5) >= margin`;
- skip a margin when abstention is above `max_abstention` or no row remains;
- compute F1 on the binary decision `p >= 0.5` versus `y = oro !=
  NO_DISCURSIVO`;
- keep the margin with the highest F1; because the grid is ascending and the
  update is strict, a tie keeps the smaller margin.

The test split is never used. The default `max_abstention=0.2` matches
`gate.toml`; the window is six words each side, also from `gate.toml`.

### Per-seed predictions

`m1_predictions` resolves each test comment ID to its thread through the
reference. The test rows are the candidates whose `thread_id` is one of those
test threads; the training rows are the rest. Unknown test IDs are ignored. An
empty test split contributes no rows. No thread crosses the split.

For each seed it fits one `M1Model` on training, predicts the test rows at
margin `0.0`, learns the margin with `choose_margin`, and derives `abstiene` and
`M1_con_abstencion`. The real inputs give 65, 97, 92, 124 and 61 rows for seeds
0–4, 439 in total.

### Metrics and summary

`replay_m1` computes, for each seed:

- `M1`: `compute_metrics(gold, M1, n_undetected)`; `abstencion` and `margen`
  are `NaN`;
- `M1 con abstención`: `compute_metrics(gold[~abstiene], M1[~abstiene],
  n_undetected)`; `abstencion = mean(abstiene)` and `margen` is the learned
  margin.

`n_undetected` is the seed's total from `metrics.count_undetected` on
`candidate_set.undetected` (5, 3, 4, 8 and 4). The undetected count is not
reduced by abstention, matching the notebook.

`metrics` has ten rows and the columns `sistema`, `semilla`, the five metric
names, `abstencion` and `margen`. `summary` is
`metrics.summary_systems(metrics)` with two rows and the mean and sample
standard deviation of the five metrics.

### Published comparison

`replay_m1` compares three tables when they are present in `published`:

- `predictions`: keys `(semilla, comment_id, unidad, inicio)`, values `oro` and
  `M1` exact, `p_M1` with absolute difference at most `1e-5`. Missing keys on
  either side and any value outside the tolerance are deviations.
- `systems`: keys `(sistema, semilla)`, filtered to `M1` and
  `M1 con abstención`, all non-key columns compared at three decimals.
- `summary`: key `sistema`, filtered to `M1` and `M1 con abstención`, all
  non-key columns compared at three decimals.

A missing or empty table is skipped. `deviations` is empty only when every
present table matches.

### Input requirements and failures

`candidates` must provide `comment_id`, `thread_id`, `unidad`, `inicio`, `oro`,
`ventana`, and the six flags in `RASGOS`. `reference` must provide
`comment_id` and `thread_id`. `listing` must provide `unidad`, `macrofuncion`,
`categoria` and `subcategoria`. A missing column raises `ValueError` naming the
frame and column, for example `candidates is missing required column: ventana`.

The embedder must return a two-dimensional array with shape `(n, 384)`. A wrong
shape raises `ValueError` naming the expected shape. An empty training frame
raises `ValueError("train is empty")`; an empty test frame gives no prediction
rows and no metric rows.

## Target values

The published per-seed values, which the integration test must reproduce:

| Seed | Candidates | Undetected | M1 F1 | M1 + abstention F1 | Margin | Abstention |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 65 | 5 | 0.333 | 0.400 | 0.10 | 16.92% |
| 1 | 97 | 3 | 0.267 | 0.294 | 0.10 | 15.46% |
| 2 | 92 | 4 | 0.261 | 0.308 | 0.10 | 8.70% |
| 3 | 124 | 8 | 0.426 | 0.448 | 0.05 | 4.03% |
| 4 | 61 | 4 | 0.513 | 0.522 | 0.15 | 26.23% |

The published summary means:

| System | F1 label | F1 discourse use | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| M1 | 0.360 | 0.499 | 0.489 | 0.438 | 0.310 |
| M1 con abstención | 0.394 | 0.516 | 0.531 | 0.528 | 0.317 |

The integration test compares all five metrics per seed and both summary
columns (mean and standard deviation), not only `F1_etiqueta`.

## Acceptance criteria

1. **Feature blocks.** The matrix has the three TF-IDF blocks, the six flags and
   the 384-column embedding in the specified order. *Happy:* a three-row
   synthetic frame with a fake embedder yields three rows and the expected block
   widths. *Boundary:* an unseen test form leaves the unit block zero and adds
   no column because the vectorizers are fitted on training only. *Failure:* an
   embedder returning 383 columns raises `ValueError` naming `(n, 384)`.

2. **Training.** Step 1 learns discourse use; step 2 learns the category on
   positive rows only. *Happy:* a positive test row with two allowed labels
   returns one of them. *Boundary:* a form with one allowed label returns that
   label even when step 2 prefers another; a form with no allowed class returns
   the top class. *Failure:* no positive training rows leaves `c2=None` and
   `unica=NO_DISCURSIVO`, so a positive step-1 probability returns
   `NO_DISCURSIVO`, not a category.

3. **Margin.** The margin is learned inside training by five-fold grouped CV,
   with the grid, the 20% cap and the smallest-margin tie rule. *Happy:* a
   synthetic training set with a clear separation returns a margin from the
   grid. *Boundary:* a tie between two margins keeps the smaller one.
   *Failure:* changing the test labels does not change the learned margin.

4. **Split and predictions.** Test rows come from the frozen test threads;
   training is the complement; unknown IDs are ignored. *Happy:* the five seeds
   give 65/97/92/124/61 rows and 439 in total. *Boundary:* an empty test split
   contributes no rows. *Failure:* a candidate from a test thread never enters
   training.

5. **Published labels and probabilities.** The 439 `M1` labels match exactly and
   `p_M1` matches within `1e-5`. *Happy:* the real inputs report zero
   deviations. *Boundary:* a key present on only one side is a deviation.
   *Failure:* a perturbed label or a probability beyond the tolerance is named.

6. **Metrics and summary.** The ten per-seed rows and the two summary rows match
   at three decimals, including the margins and abstention rates. *Happy:* the
   real inputs report zero deviations. *Boundary:* the `M1` row has `NaN` for
   `abstencion` and `margen`; the `M1 con abstención` row has the learned
   values. *Failure:* a perturbed metric cell is named.

7. **Undetected labels.** The metrics use 5/3/4/8/4 undetected labels; removing
   or changing them moves the metric rows and fails criterion 6.

8. **Privacy.** The prediction frame has no `texto`, `ventana`, `author_hash` or
   `@name` mention. The embedding cache holds text in memory only. The slice
   writes no prediction file; the integration test writes only to `tmp_path`.

9. **Compatibility.** S1, S2 and S3 stay green and unchanged. `features.py` and
   `models.py` do not modify `candidates.py`, `metrics.py` or `baselines.py`.

10. **Test split.** Unit tests use a fake embedder and run by default. The
    real-data tests are `slow`, require the `embeddings` extra and the frozen
    model, and skip with a reason when the data or the model is absent.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_feature_builder_shapes` | unit | Three rows, the three TF-IDF blocks, six flags and 384 embedding columns. |
| `test_feature_builder_fits_on_training_only` | unit | An unseen test form adds no vocabulary column. |
| `test_feature_builder_rejects_wrong_embedding_dimension` | unit | A 383-column embedder raises `ValueError`. |
| `test_feature_builder_requires_columns` | unit | Missing `ventana`, a flag or another required column names it. |
| `test_m1_predicts_permitted_category` | unit | A positive row returns a label from `admitidas ∪ vistas`. |
| `test_m1_single_allowed_label` | unit | One allowed label wins over the step-2 preference. |
| `test_m1_no_positive_training` | unit | `c2=None`, `unica=NO_DISCURSIVO`; a positive probability returns `NO_DISCURSIVO`. |
| `test_m1_falls_back_to_top_class` | unit | No allowed class returns the top class. |
| `test_choose_margin_uses_training_only` | unit | Changing test labels leaves the margin unchanged. |
| `test_choose_margin_tie_keeps_smaller` | unit | A tie keeps the smaller margin. |
| `test_m1_predictions_uses_reference_threads` | unit | Test threads, training complement, unknown IDs ignored. |
| `test_m1_predictions_requires_columns` | unit | Each missing candidate, reference or listing column names its frame. |
| `test_m1_output_has_no_text` | unit | No `texto`, `ventana`, `author_hash` or `@` mention. |
| `test_replay_m1_reports_deviations` | unit | A perturbed label, probability and metric are named. |
| `test_m1_matches_published_predictions` | integration, slow | 439 rows; labels exact; probabilities within `1e-5`. |
| `test_m1_matches_published_metrics` | integration, slow | Ten per-seed rows and two summary rows at three decimals; margins and abstention. |

The existing S1, S2 and S3 slow tests remain in the suite and must stay green.

## Out of scope

- M2, the frozen rules, spaCy POS, the rare-category flag and provenance.
- The candidate construction, the baselines, the metric definitions and the
  bootstrap intervals.
- The application corpus and its predictions.
- A CLI or a file writer. S4 exposes functions and a diagnostic report only.
- Changing the split, seeds, the abstention cap, the metrics or the frozen rule
  set.
- Changing `inicio_oracion` to stop treating a newline as a sentence boundary.
  That is an open question and needs an ADR before any change.
- The 20-candidate implicit-negative audit.

## Privacy impact

The feature builder reads `ventana`, but the prediction frame contains only IDs,
forms, offsets, gold labels, `M1`, `p_M1`, `abstiene` and
`M1_con_abstencion`. It contains no `texto`, `ventana`, `author_hash` or
`@name` mention. The embedding cache lives in memory and is never written. The
slice writes no prediction file; the integration test reads the ignored `doc/`
inputs and writes only to `tmp_path`. The spec and the report contain no comment
text. The separate `docs/learn/` teaching fragments remain under their
documented exception.

## Evaluation protocol impact

None. The split, seeds, test files, abstention cap and metrics are unchanged.
The margin is learned inside training only, as R3 requires; the test split is
never used. The embedding model is frozen and is not trained on the pilot
labels. The only protocol-adjacent open question is the newline rule in
`inicio_oracion`; S4 keeps the frozen behaviour so the published M1/M2 numbers
stay comparable. Changing it needs an ADR. No ADR is needed for the chosen
approach.

## Contradictions and open points

- The notebook's `inicio_oracion` treats `\n` as a sentence boundary. The author
  flagged that phrases can span lines. S4 keeps the frozen rule to reproduce the
  published M1; changing it would change M1/M2 and needs an ADR. The question is
  recorded in `docs/state.md` and
  [01 — Candidate window](../learn/01-candidate-window.md).
- The published `p_M1` is not a metric column; the spec adds a `1e-5`
  probability tolerance as a fidelity check. The observed prototype difference
  is at most `3.6e-7`.
- The `M1` row has `NaN` for `abstencion` and `margen`; the
  `M1 con abstención` row carries the learned values. This mirrors the
  published table.
- `resumen_sistemas.csv` has a two-row header; the caller passes a flat frame
  with `sistema` and `metric_stat` columns, as in S3.
- The notebook passes `ventana` with the `[[...]]` markers to the embedding
  model. This is the frozen design, not a bug; the unit block separately
  identifies the form.
- The training corpus is small (about 149–212 candidates per seed), so the IDF
  and the margin are estimated from few rows. The published values are the
  target, not a claim that the estimates are stable.

## Rough size

`src/conectores/features.py` (~120 lines), `src/conectores/models.py`
(~250 lines), `tests/test_features.py` (~150 lines), `tests/test_models.py`
(~250 lines), additions to `tests/test_integration.py` (~100 lines) and the
diagnostic report. About 900 lines.

## Approval

**Approved:** 2026-11-26 by Till.

**Approved decisions (A, B, C as specified):**

1. **Feature/model split and exact feature order (A).** `features.py` holds
   `FeatureBuilder` with the three TF-IDF blocks, the six flags and the
   384-column embedding, fitted on training only; `models.py` holds `M1Model`,
   `choose_margin`, `m1_predictions`, `replay_m1` and `M1Result`. The feature
   order and settings are as specified: word, character, unit, six flags,
   embedding; step 1 balanced, step 2 unweighted; `C=1.0`, `max_iter=2000`.
2. **Margin protocol (B).** Five-fold `GroupKFold` by thread on training, grid
   `0.00..0.30` by `0.05`, a 20% cap, and the smallest margin on ties. The test
   split is never used.
3. **Comparison gate (C).** All 439 labels exact, `p_M1` within `1e-5`, and all
   five metrics per seed plus both summary columns at three decimals.

The frozen `inicio_oracion` newline rule is kept; changing it is an open
question and needs an ADR. There is no CLI and no change to `candidates.py`,
`metrics.py` or `baselines.py`.

**Assumptions:**

- The notebook's `M1`, `elegir_margen_m` and `embedder` are the reference
  implementation.
- The frozen model is `paraphrase-multilingual-MiniLM-L12-v2` with 384
  dimensions and CPU inference.
- The frozen test files define the split; `GroupShuffleSplit` is not rerun.
- The published `M1` and `M1 con abstención` rows are the target.
- The `1e-5` probability tolerance is a fidelity guard, not a metric change.

**Deferred:**

- M2 and its rules, POS, the rare-category flag and provenance.
- The application corpus.
- A CLI or file writer.
- The newline-rule change and the 20-candidate audit.

Next: /tdd FeatureBuilder.
