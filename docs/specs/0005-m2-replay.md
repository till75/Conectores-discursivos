# Spec 0005 — M2 replay

**Slice:** S5 — M2 replay
**Status:** approved
**Date:** 2026-11-27
**Approved:** 2026-11-27 by Till
**Design note:** [0005-m2-replay.md](../design/0005-m2-replay.md)
**Requirements source:** `docs/00-brief.md`, `docs/plan.md`,
`doc/equipo11_B0_B1_M1_M2.ipynb`, `doc/resultados_hito2.zip`, `gate.toml`,
`docs/specs/0002-candidate-replay.md`,
`docs/specs/0003-baseline-replay.md`,
`docs/specs/0004-m1-replay.md`,
`docs/learn/04-m2-rules-provenance.md`

## Outcome

A caller can rebuild M2's 439 test labels, probabilities, provenance,
rare-category flags, traceability counts and no-abstention metric rows from the
S2 candidates, the listing, the five frozen splits, the frozen embedding model
and the frozen rule set, without reading `predicciones_test.csv` to build them;
the margin is learned inside training, and any mismatch in the published
abstention rows is reported as a named deviation rather than hidden.

## Interface

### Rules (`src/conectores/rules.py`)

```python
MIN_EJEMPLOS = 5
POS_COLUMNS = ["pos_u", "pos_ant", "pos_sig", "tok_ant", "tok_sig"]
RULE_NAMES = [
    "sig_det_o_num",
    "sig_verbo",
    "ant_verbo",
    "sig_adj_o_adv",
    "ant_det",
    "ant_prep",
    "sig_que",
    "aislada_por_comas",
    "fin_tras_verbo",
    "en_pregunta",
    "hasta_preposicion",
    "ya_temporal",
    "ya_operador",
    "solo_adjetivo",
    "mas_comparativo",
]
REGLAS: Mapping[str, Callable[[Any], bool]]

class Token(Protocol):
    idx: int
    text: str
    pos_: str

NLP = Callable[[str], Sequence[Token]]

def load_nlp(model_name: str = "es_core_news_sm") -> NLP: ...
def anotar_gramatica(cand: pd.DataFrame, nlp: NLP) -> pd.DataFrame: ...
def aplicar_reglas(df: pd.DataFrame) -> pd.DataFrame: ...

class M2FeatureBuilder:
    def fit(
        self, train: pd.DataFrame, embedder: Embedder
    ) -> M2FeatureBuilder: ...
    def transform(self, df: pd.DataFrame) -> csr_matrix: ...
```

`REGLAS` is the frozen rule set, in the order of `RULE_NAMES`. `RULE_NAMES`
is the contract: adding, removing or renaming a rule changes the feature matrix
and needs an ADR. The rule set is recorded verbatim below.

`load_nlp` loads the frozen Spanish spaCy model on CPU. The model is external
and is not trained on the pilot labels. `anotar_gramatica` accepts any callable
that returns a sequence of token-like objects, so unit tests can use a fake.

`anotar_gramatica` requires `texto`, `inicio` and `unidad`; it returns a new
frame with the same row order and a `RangeIndex`, the input columns and the five
`POS_COLUMNS`. The input frame is not modified.

`aplicar_reglas` requires the six candidate flags, `texto`, `inicio`, `unidad`
and the five `POS_COLUMNS`; it returns one boolean column per rule, in
`RULE_NAMES` order, with the same index as the input. `texto` and `inicio` are
needed by `_pregunta` for the `en_pregunta` rule.

`M2FeatureBuilder` composes the S4 `FeatureBuilder` and appends the rule block
and the POS block. It is fitted on training only.

### Model and replay (`src/conectores/models.py`)

```python
M2_COLUMNS = [
    "semilla",
    "comment_id",
    "thread_id",
    "unidad",
    "inicio",
    "oro",
    "M2",
    "p_M2",
    "origen_M2",
    "revisar_categoria",
    "abstiene_M2",
]

TRACEABILITY_TARGET = {
    "etiquetas_discursivas": 91,
    "fijadas_listado": 58,
    "fijadas_listado_correctas": 34,
    "elegidas_modelo": 33,
    "elegidas_modelo_correctas": 20,
    "revisar_categoria": 43,
}

@dataclass(frozen=True)
class M2Result:
    predictions: pd.DataFrame
    metrics: pd.DataFrame
    summary: pd.DataFrame
    margins: Mapping[int, float]
    traceability: Mapping[str, int]
    deviations: list[str]
    margin_deviations: list[str]

class M2Model(M1Model):
    def __init__(
        self,
        labels: Mapping[str, Sequence[str]],
        embedder: Embedder,
        seed: int = 0,
        C: float = 1.0,
    ): ...
    def fit(self, train: pd.DataFrame) -> M2Model: ...
    def prob(self, df: pd.DataFrame) -> np.ndarray: ...
    def predict(
        self, df: pd.DataFrame, margin: float = 0.0
    ) -> tuple[
        list[str], np.ndarray, np.ndarray, list[str], np.ndarray
    ]: ...

def choose_margin_for(
    model_cls: type[M1Model],
    train: pd.DataFrame,
    labels: Mapping[str, Sequence[str]],
    embedder: Embedder,
    seed: int = 0,
    max_abstention: float = 0.2,
) -> float: ...

def m2_predictions(
    candidates: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    embedder: Embedder,
) -> pd.DataFrame: ...

def replay_m2(
    candidate_set,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    test_ids: Mapping[int, Sequence[str]],
    published: Mapping[str, pd.DataFrame],
    embedder: Embedder,
    nlp: NLP,
) -> M2Result: ...
```

`M2Model.predict` returns `(labels, probabilities, abstention, origin, review)`
in that order. This differs from the notebook's
`(labels, abstention, probabilities, origin, review)`; the repo uses the S4
order so callers do not have to remember two conventions. The values are the
same.

`m2_predictions` requires candidates that already carry the five `POS_COLUMNS`;
the caller runs `anotar_gramatica` once before the seed loop, as the notebook
does. It returns one row per test candidate per seed with `M2_COLUMNS`.

`replay_m2` runs `anotar_gramatica` on `candidate_set.candidates`, calls
`m2_predictions`, records the learned margins from the same per-seed loop,
computes the metrics, the summary and the traceability, and compares them with
the published tables. `m2_predictions` is the public frame-only wrapper; the
margin map belongs to `M2Result`.

`choose_margin_for` is the generic version of S4's `choose_margin`. The S4
function keeps its signature and results; it may delegate to
`choose_margin_for(M1Model, ...)`.

### Types and units

- `p_M2` and `margen` are probabilities in `[0, 1]`; `abstencion` is a fraction
  in `[0, 1]`.
- `inicio` is a 0-based character offset into the text used for matching.
- `origen_M2` is exactly `"listado"` or `"modelo"`.
- `revisar_categoria` and `abstiene_M2` are booleans in the frame and floats in
  the feature matrix.
- Metrics are fractions in `[0, 1]`; the five names are the S1 names.
- `traceability` counts are integers; the six keys are the
  `metrics.traceability` keys.
- `MIN_EJEMPLOS` is 5 and must equal `gate.toml`'s `min_examples`.

### Label vocabulary

`NO_DISCURSIVO`, `CON:<CATEGORÍA>` and `OP:<CATEGORÍA>`. The published
vocabulary is `NO_DISCURSIVO`, `CON:ADICIÓN`, `CON:CIERRE`, `CON:CONCESIVO`,
`CON:CONCLUSIVO`, `CON:CONSECUTIVO`, `CON:CONTINUATIVO`, `CON:INTERACTIVO`,
`CON:REFORMULATIVOS`, `OP:ARGUMENTATIVO`, `OP:ENUNCIATIVO`, `OP:INFORMATIVO` and
`OP:MODAL`. M2 predicts only a category admitted by the listing for the unit. It
does not use the M1 `vistas` union and does not invent labels.

## Behaviour

### Grammar annotation

`anotar_gramatica` parses each distinct `texto` once with `nlp` and caches the
result in memory. For each row it computes `fin = inicio + len(unidad)` and:

- `dentro` is the first token with `token.idx < fin` and
  `token.idx + len(token.text) > inicio`;
- `antes` is the last token with `token.idx + len(token.text) <= inicio`;
- `despues` is the first token with `token.idx >= fin`.

The output columns are:

| Column | Value |
|---|---|
| `pos_u` | `dentro.pos_`, or `"X"` when no token overlaps |
| `pos_ant` | `antes.pos_`, or `"INICIO"` when there is no previous token |
| `pos_sig` | `despues.pos_`, or `"FIN"` when there is no next token |
| `tok_ant` | `antes.text.lower()`, or `""` |
| `tok_sig` | `despues.text.lower()`, or `""` |

The offsets are character offsets, not token indices. A multiword unit is
matched by its first overlapping token, matching the notebook.

### Frozen rule set

The rules are frozen on 25 November 2026 and recorded here verbatim. The
predicates receive a row with the candidate columns and the five `POS_COLUMNS`
as attributes. `re` is the Python regular-expression module.

```python
REGLAS = {
    # general
    "sig_det_o_num": lambda r: r.pos_sig in ("DET", "NUM")
        or bool(re.match(r"\d", r.tok_sig)),
    "sig_verbo": lambda r: r.pos_sig in ("VERB", "AUX"),
    "ant_verbo": lambda r: r.pos_ant in ("VERB", "AUX"),
    "sig_adj_o_adv": lambda r: r.pos_sig in ("ADJ", "ADV"),
    "ant_det": lambda r: r.pos_ant == "DET",
    "ant_prep": lambda r: r.pos_ant == "ADP",
    "sig_que": lambda r: r.tok_sig == "que",
    "aislada_por_comas": lambda r: r.coma_despues
        and (r.inicio_oracion or r.coma_antes),
    "fin_tras_verbo": lambda r: r.pos_ant in ("VERB", "AUX")
        and r.fin_enunciado,
    "en_pregunta": lambda r: _pregunta(r.texto, r.inicio),
    # unit-specific
    "hasta_preposicion": lambda r: r.unidad == "hasta"
        and (
            r.pos_sig in ("DET", "NUM", "PROPN", "NOUN")
            or bool(re.match(r"\d", r.tok_sig))
        ),
    "ya_temporal": lambda r: r.unidad == "ya"
        and not r.coma_despues
        and r.pos_sig in ("VERB", "AUX", "PRON"),
    "ya_operador": lambda r: r.unidad == "ya"
        and r.inicio_oracion
        and r.coma_despues,
    "solo_adjetivo": lambda r: r.unidad == "solo"
        and r.pos_ant in ("VERB", "AUX", "PRON")
        and r.fin_enunciado,
    "mas_comparativo": lambda r: r.unidad == "más"
        and (
            r.pos_sig in ("ADJ", "ADV", "NOUN", "NUM")
            or r.tok_sig == "que"
        ),
}
```

`_pregunta(texto, inicio)` returns true when the next sentence-ending
punctuation after `inicio` is `?`, or when an opening `¿` appears between the
previous `.` and `inicio`. It treats `\n` as a sentence boundary, like
`inicio_oracion`. The newline rule is frozen; changing it needs an ADR.

### M2 feature matrix

`M2FeatureBuilder.transform` concatenates, in this order:

1. the five S4 blocks: word TF-IDF, character TF-IDF, unit TF-IDF, six flags
   and the 384-column embedding;
2. the 15 rule columns in `RULE_NAMES` order, cast to float;
3. the `DictVectorizer` POS block.

The POS block is one dict per row with these keys, all value `1`:

```text
u=<pos_u>
ant=<pos_ant>
sig=<pos_sig>
<unidad>|sig=<pos_sig>
<unidad>|ant=<pos_ant>
```

The `DictVectorizer` is fitted on the training rows only. An unseen key in test
is ignored by the fitted vectorizer and adds no column. The feature order and the
vectorizer settings are part of the contract because they change the fitted
model.

### Training

`M2Model.fit`:

- requires `oro`, the five `POS_COLUMNS` and the feature columns listed in
  Input requirements;
- raises `ValueError("train is empty")` for an empty frame;
- builds `M2FeatureBuilder` on the training rows;
- fits step 1 with the same settings as M1: `LogisticRegression(C=C,
  class_weight="balanced", max_iter=2000, random_state=seed)` on
  `y = oro != NO_DISCURSIVO`; if step 1 has only one class, sets `c1=None` and
  `c1_constant` to that class, as M1 does;
- fits step 2 with `LogisticRegression(C=C, max_iter=2000, random_state=seed)`
  on the positive rows only when there is at least one positive row and more
  than one positive label; otherwise sets `c2=None`;
- records `n_cat = train[pos].groupby("oro").size().to_dict()`, where
  `pos = oro != NO_DISCURSIVO`.

`vistas` may be recorded for compatibility with `M1Model`, but M2 does not use
it. The strict listing restriction is the only allowed set.

### Prediction and provenance

For each test row:

1. `p = self.prob(df)[i]`.
2. `admitted = self.labels.get(unidad, [])`.
3. If `admitted` is empty, raise `ValueError` naming the unit. The real inputs
   never hit this; R1 says every candidate form is in the listing.
4. If `abs(p - 0.5) < margin`, label `NO_DISCURSIVO`, abstain, set
   `origen_M2="modelo"` and `revisar_categoria=False`.
5. If `p < 0.5`, label `NO_DISCURSIVO`, do not abstain, set
   `origen_M2="modelo"` and `revisar_categoria=False`.
6. If `len(admitted) == 1`, label `admitted[0]`, set
   `origen_M2="listado"`.
7. Otherwise, if `c2` is not `None`, order the step-2 classes by descending
   probability and keep only the classes in `admitted`. If the filtered order is
   non-empty, label its first class and set `origen_M2="modelo"`. If it is
   empty, label `admitted[0]` and set `origen_M2="listado"`.
8. If `c2` is `None`, label `admitted[0]` and set `origen_M2="listado"`.
9. For a positive label, set
   `revisar_categoria = n_cat.get(label, 0) < MIN_EJEMPLOS`.

The fallback in step 7 is the notebook's strict behaviour: it never falls back
to a class outside the listing, and it never uses the M1 `vistas` union. A
category admitted by the listing but never seen in training cannot be chosen by
the model; it is used only as the `admitted[0]` fallback and is marked
`"listado"`.

### Margin

`choose_margin_for` uses `GroupKFold(n_splits=5)` on the training rows, grouped
by `thread_id`. For each fold it fits a fresh `model_cls(labels, embedder,
seed=seed)` on the other folds and gets `prob` for the held-out fold. It then
scans `np.arange(0, 0.31, 0.05)`:

- keep the rows with `abs(p - 0.5) >= margin`;
- skip a margin when abstention is above `max_abstention` or no row remains;
- compute F1 on the binary decision `p >= 0.5` versus
  `y = oro != NO_DISCURSIVO`;
- keep the margin with the highest F1; because the grid is ascending and the
  update is strict, a tie keeps the smaller margin.

The test split is never used. The default `max_abstention=0.2` matches
`gate.toml`. The margin is the same protocol for M1 and M2; only the model class
changes.

The published M2 margins are `0.15/0.10/0.20/0.10/0.20`. The current prototype
learns `0.20/0.15/0.15/0.15/0.20` from the same training rows. No tested
training-only CV variant reproduces the published margins. The spec does not
copy the published margins; it records the mismatch and leaves the
investigation in S5.

### Per-seed predictions

`m2_predictions` resolves each test comment ID to its thread through the
reference. The test rows are the candidates whose `thread_id` is one of those
test threads; the training rows are the rest. Unknown test IDs are ignored. An
empty test split contributes no rows. No thread crosses the split.

For each seed it fits one `M2Model` on training, predicts the test rows at
margin `0.0`, learns the margin with `choose_margin_for(M2Model, ...)`, and
derives `abstiene_M2`. The real inputs give 65, 97, 92, 124 and 61 rows for seeds
0–4, 439 in total.

### Metrics and summary

`replay_m2` computes, for each seed:

- `M2`: `compute_metrics(gold, M2, n_undetected)`; `abstencion` and `margen`
  are `NaN`;
- `M2 con abstención`: `compute_metrics(gold[~abstiene], M2[~abstiene],
  n_undetected)`; `abstencion = mean(abstiene)` and `margen` is the learned
  margin.

`n_undetected` is the seed's total from `metrics.count_undetected` on
`candidate_set.undetected` (5, 3, 4, 8 and 4). The undetected count is not
reduced by abstention, matching the notebook.

`metrics` has ten rows and the columns `sistema`, `semilla`, the five metric
names, `abstencion` and `margen`. `summary` is
`metrics.summary_systems(metrics)` with two rows and the mean and sample
standard deviation of the five metrics. The published comparison uses both the
mean and the standard deviation, and all five metrics per row, not only
`F1_etiqueta`.

### Traceability

`replay_m2` computes `metrics.traceability` on the concatenated predictions.
The six counts are compared with `TRACEABILITY_TARGET`. An abstention is not a
discourse label and is not counted in `etiquetas_discursivas`; a `NO_DISCURSIVO`
row is not counted either. `origen_M2` and `revisar_categoria` are the only
inputs to the counts.

### Published comparison

`replay_m2` compares three tables when they are present in `published`:

- `predictions`: keys `(semilla, comment_id, unidad, inicio)`. Core values:
  `oro`, `M2`, `origen_M2` and `revisar_categoria` exact; `p_M2` with absolute
  difference at most `1e-5`. Margin value: `abstiene_M2` exact.
- `systems`: keys `(sistema, semilla)`, filtered to `M2` and
  `M2 con abstención`, all non-key columns compared at three decimals.
- `summary`: key `sistema`, filtered to `M2` and `M2 con abstención`, all
  non-key columns compared at three decimals.

A missing or empty table is skipped. Missing keys on either side are deviations.

`M2Result.deviations` contains the core deviations: missing or extra rows;
`oro`, `M2`, `origen_M2` or `revisar_categoria` mismatch; `p_M2` beyond the
tolerance; traceability mismatch; `M2` metric or summary mismatch.

`M2Result.margin_deviations` contains the margin-dependent deviations:
`abstiene_M2` mismatch; learned margin mismatch; `M2 con abstención` metric or
summary mismatch.

A **full pass** has `deviations == []` and `margin_deviations == []`. A
**partial** result has `deviations == []` and `margin_deviations != []`. A
**fail** has `deviations != []`.

### Input requirements and failures

`candidates` must provide `comment_id`, `thread_id`, `unidad`, `inicio`, `oro`,
`texto`, `ventana`, the six flags in `RASGOS` and the five `POS_COLUMNS`.
`reference` must provide `comment_id` and `thread_id`. `listing` must provide
`unidad`, `macrofuncion`, `categoria` and `subcategoria`.

A missing column raises `ValueError` naming the frame and column, for example
`candidates is missing required column: pos_sig`. An empty training frame raises
`ValueError("train is empty")`. A unit with no admitted category raises
`ValueError` naming the unit. The embedder must return a two-dimensional array
with shape `(n, 384)`; a wrong shape raises `ValueError` naming the expected
shape. An empty test frame gives no prediction rows and no metric rows.

## Target values

The published M2 no-abstention per-seed values, which the integration test must
reproduce at three decimals:

| Seed | Candidates | Undetected | F1 label | F1 discourse | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|---:|---:|
| 0 | 65 | 5 | 0.432 | 0.595 | 0.527 | 0.615 | 0.333 |
| 1 | 97 | 3 | 0.545 | 0.591 | 0.648 | 0.667 | 0.462 |
| 2 | 92 | 4 | 0.500 | 0.636 | 0.665 | 0.611 | 0.423 |
| 3 | 124 | 8 | 0.452 | 0.613 | 0.639 | 0.538 | 0.389 |
| 4 | 61 | 4 | 0.486 | 0.595 | 0.692 | 0.562 | 0.429 |

The published M2 summary:

| System | F1 label | F1 discourse | Macro CON/OP | Precision | Coverage |
|---|---:|---:|---:|---:|---:|
| M2 | 0.483 | 0.606 | 0.634 | 0.599 | 0.407 |

The published M2-with-abstention rows are the comparison target, not a pass
condition if the margins differ:

| Seed | F1 label | Abstention | Margin |
|---|---:|---:|---:|
| 0 | 0.452 | 12.31% | 0.15 |
| 1 | 0.571 | 5.15% | 0.10 |
| 2 | 0.476 | 30.43% | 0.20 |
| 3 | 0.449 | 8.87% | 0.10 |
| 4 | 0.615 | 21.31% | 0.20 |

The prototype margins are `0.20/0.15/0.15/0.15/0.20`; 27 of 439
`abstiene_M2` rows differ. The traceability target is
`91/58/34/33/20/43`.

## Acceptance criteria

1. **Frozen rule set.** `RULE_NAMES` has exactly the 15 frozen names in order;
   `aplicar_reglas` returns one boolean column per name. *Happy:* a synthetic
   row with `pos_sig="VERB"` activates `sig_verbo`. *Boundary:* a row with
   `pos_ant="INICIO"` does not activate `ant_verbo`, `ant_det` or `ant_prep`.
   *Failure:* a 14-rule or 16-rule set, or a renamed rule, fails the frozen-set
   test.

2. **Grammar annotation.** `anotar_gramatica` adds the five POS columns from
   the character offsets. *Happy:* a synthetic doc yields the expected `pos_u`,
   `pos_ant`, `pos_sig`, `tok_ant` and `tok_sig`. *Boundary:* a candidate at the
   start gets `pos_ant="INICIO"` and `tok_ant=""`; at the end it gets
   `pos_sig="FIN"` and `tok_sig=""`. *Failure:* a missing `texto`, `inicio` or
   `unidad` raises `ValueError` naming the column.

3. **Strict listing restriction.** M2 uses only `labels`, not `vistas`. *Happy:*
   a unit with two admitted labels returns the model's top admitted label and
   `origen_M2="modelo"`. *Boundary:* a unit with one admitted label returns it
   even when the model prefers another, with `origen_M2="listado"`. *Failure:* a
   category not in the listing is never returned; a unit with no admitted label
   raises `ValueError` naming the unit.

4. **Provenance and rare flag.** `origen_M2` is `"listado"` or `"modelo"`;
   `revisar_categoria` is true when the chosen category has fewer than five
   training positives. *Happy:* a category with four positives is flagged.
   *Boundary:* exactly five is not flagged; an abstention is
   `NO_DISCURSIVO`, `origen_M2="modelo"`, `revisar_categoria=False`.
   *Failure:* a category with no training example is flagged; a
   `NO_DISCURSIVO` row is never flagged.

5. **Margin.** The margin is learned inside training by five-fold grouped CV,
   with the grid, the 20% cap and the smallest-margin tie rule. *Happy:* a
   synthetic training set with a clear separation returns a margin from the
   grid. *Boundary:* a tie between two margins keeps the smaller one.
   *Failure:* changing the test labels does not change the learned margin; the
   test split is not passed to `choose_margin_for`.

6. **Core M2 predictions.** The 439 `M2` labels, `origen_M2` and
   `revisar_categoria` match exactly; `p_M2` matches within `1e-5`. *Happy:* the
   real inputs report `deviations == []`. *Boundary:* a key present on only one
   side is a deviation; an empty published table is skipped. *Failure:* a
   perturbed label, probability, origin or review flag is named.

7. **Core metrics and summary.** The five `M2` per-seed rows and the one `M2`
   summary row match at three decimals. *Happy:* the real inputs report zero
   core deviations. *Boundary:* the `M2` row has `NaN` for `abstencion` and
   `margen`. *Failure:* a perturbed metric cell is named.

8. **Traceability.** The six counts match `91/58/34/33/20/43`. *Happy:* the real
   inputs match. *Boundary:* an abstention and a `NO_DISCURSIVO` row are not
   counted as discourse labels. *Failure:* a changed origin or review flag
   changes the counts and is named.

9. **Abstention rows and partial outcome.** The `M2 con abstención` rows are
   produced from the learned margins and compared with the published rows.
   *Happy:* if the learned margins match, `margin_deviations == []`. *Boundary:*
   if they differ, the rows are still produced, the `abstiene_M2` mismatches are
   named, and the slice is partial, not fail. *Failure:* choosing the margin on
   the test labels changes the margin and fails the leakage test; using the
   published margins without an ADR fails the independence check.

10. **Privacy.** The prediction frame has no `texto`, `ventana`, `pos_*`,
    `tok_*`, `author_hash` or `@name` mention. *Happy:* the public frame has
    only `M2_COLUMNS`. *Boundary:* `anotar_gramatica` reads `texto` in memory,
    but the public frame drops it and the spaCy cache is never written.
    *Failure:* a prediction frame containing `texto` or `ventana`, or a written
    file with text, fails.

11. **Compatibility.** S1, S2, S3 and S4 stay green and unchanged.
    `M1Model`, `choose_margin`, `FeatureBuilder`, `candidates.py`, `metrics.py`
    and `baselines.py` keep their results. *Happy:* the full suite passes.
    *Boundary:* `M2Model` subclasses `M1Model` without changing the M1 feature
    order. *Failure:* a change that moves an S1–S4 result fails.

12. **Slow tests.** The real-data tests are `slow`, require the spaCy model, the
    embeddings extra and the frozen embedding model, and skip with a reason when
    an input is absent. *Happy:* `pytest -m slow` runs the M2 integration test.
    *Boundary:* the test skips with a reason when spaCy or the embeddings extra
    is missing. *Failure:* a missing required input fails with a clear message,
    not a silent skip.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_rule_names_are_frozen` | unit | Exactly the 15 names in `RULE_NAMES` order. |
| `test_aplicar_reglas_each_rule` | unit | Each frozen predicate fires on a crafted row and stays false otherwise. |
| `test_aplicar_reglas_requires_columns` | unit | A missing POS or candidate column names it. |
| `test_anotar_gramatica_offsets` | unit | `pos_u`, `pos_ant`, `pos_sig`, `tok_ant` and `tok_sig` from known offsets. |
| `test_anotar_gramatica_boundaries` | unit | `INICIO`/`FIN` and empty tokens at the edges. |
| `test_anotar_gramatica_requires_columns` | unit | Missing `texto`, `inicio` or `unidad` names it. |
| `test_m2_feature_builder_order` | unit | Base blocks, 15 rule columns and the POS block in order. |
| `test_m2_feature_builder_unseen_pos` | unit | An unseen POS key adds no column. |
| `test_m2_fit_empty_training` | unit | `M2Model.fit` raises `ValueError("train is empty")`. |
| `test_m2_fit_requires_columns` | unit | Missing `oro` or a POS column names it. |
| `test_m2_list_restriction_single` | unit | One admitted label wins over the model preference. |
| `test_m2_list_restriction_multiple` | unit | The model picks among admitted labels only. |
| `test_m2_never_uses_vistas` | unit | A training-only label outside the listing is never predicted. |
| `test_m2_unknown_unit_raises` | unit | A unit with no admitted label raises `ValueError`. |
| `test_m2_provenance` | unit | `"listado"` and `"modelo"` in the expected branches. |
| `test_m2_rare_category_flag` | unit | Four positives flag; five do not; abstention is not flagged. |
| `test_m2_abstention` | unit | `abs(p - 0.5) < margin` gives `NO_DISCURSIVO`, abstention and `"modelo"`. |
| `test_choose_margin_for_uses_training_only` | unit | Changing test labels leaves the margin unchanged. |
| `test_choose_margin_for_tie_keeps_smaller` | unit | A tie keeps the smaller margin. |
| `test_m2_predictions_uses_reference_threads` | unit | Test threads, training complement, unknown IDs ignored. |
| `test_m2_predictions_requires_columns` | unit | Each missing candidate, reference or listing column names its frame. |
| `test_m2_output_has_no_text` | unit | No `texto`, `ventana`, `pos_*`, `tok_*`, `author_hash` or `@` mention. |
| `test_replay_m2_reports_core_and_margin_deviations` | unit | A perturbed core cell and a perturbed abstention cell land in the right list. |
| `test_traceability_target` | unit | The six target counts are the published values. |
| `test_m2_matches_published_predictions` | integration, slow | 439 rows; core values exact; `p_M2` within `1e-5`; `deviations == []`. |
| `test_m2_matches_published_metrics` | integration, slow | Five `M2` rows and the `M2` summary row at three decimals; the abstention rows are produced and any margin deviation is named. |
| `test_m2_traceability_matches_published` | integration, slow | `91/58/34/33/20/43`. |

The existing S1, S2, S3 and S4 slow tests remain in the suite and must stay
green.

## Out of scope

- Changing the frozen rule set, its order or its freeze date.
- Changing `inicio_oracion` or `_pregunta` to stop treating a newline as a
  sentence boundary.
- The CSL detector, the application corpus and its predictions.
- A CLI or a file writer. S5 exposes functions and a diagnostic report only.
- Changing the split, seeds, abstention cap, metrics or test hashes.
- The 20-candidate implicit-negative audit, the 548/550 reconciliation, F2 and
  coverage-at-budget.
- A rule-first M3 or any LLM annotator.
- Changing the S4 M1 feature order, margin protocol or results.

## Privacy impact

`anotar_gramatica` reads `texto` to run spaCy, and `M2FeatureBuilder` reads
`texto` only through the candidate frame. The public prediction frame contains
only `M2_COLUMNS`: IDs, form, offset, gold label, `M2`, `p_M2`, `origen_M2`,
`revisar_categoria` and `abstiene_M2`. It contains no `texto`, `ventana`,
`pos_*`, `tok_*`, `author_hash` or `@name` mention.

The spaCy document cache and the embedding cache live in memory and are never
written. The slice writes no prediction file; the integration test reads the
ignored `doc/` inputs and writes only to `tmp_path`. The spec and the report
contain no comment text. The separate `docs/learn/` teaching fragments remain
under their documented exception.

## Evaluation protocol impact

The split, seeds, frozen test IDs, test hashes, metrics and abstention cap are
unchanged. The margin is learned inside training only, as R3 requires; the test
split is never used. The rule set is recorded, not changed. Recording the frozen
rules does not need an ADR; editing them would.

The one protocol-adjacent change is the acceptance of a partial result as a
fallback when the published M2 margins cannot be reproduced after the S5 TDD
cycle. That changes what the slice's result means, so `/spec-review` approved it
explicitly. If the group wants to treat the partial result as a pass, or to use
the published margins, an ADR comes first. The newline rule remains frozen;
changing it needs an ADR.

## Contradictions and open points

- **Plan versus prototype.** `docs/plan.md` says M2 predictions and metrics
  match the published per-seed rows and summary at three decimals. The prototype
  reproduces the no-abstention M2 exactly but not the published margins, so the
  `M2 con abstención` rows differ on 27/439 rows. The spec defines a partial
  outcome instead of silently relaxing the plan. `/spec-review` must approve
  this or require an ADR.
- **Margin cause.** The published margins are not reproduced by the current
  notebook path or by the tested CV variants. The likely causes are library
  drift (local scikit-learn 1.9.1) or an older margin path. S5 investigates;
  the spec does not choose the published margins.
- **API order.** The notebook returns `(labels, abstention, probabilities,
  origin, review)`; the repo returns `(labels, probabilities, abstention,
  origin, review)` for consistency with S4. The values are unchanged.
- **Unknown unit.** The notebook would raise `IndexError`; the spec raises
  `ValueError` naming the unit. The real inputs never hit it.
- **`M2` row values.** The `M2` row has `NaN` for `abstencion` and `margen`; the
  `M2 con abstención` row carries the learned values. This mirrors the published
  table.
- **`p_M2` tolerance.** The published `p_M2` is not a metric column; the spec
  uses a `1e-5` probability tolerance as a fidelity guard, as S4 does.
- **Traceability scope.** The published 91/58/34/33/20/43 counts are aggregated
  over the five test splits; the spec compares the aggregate, not a per-seed
  split.
- **Small corpus.** The training set has about 149–212 candidates per seed, so
  the margin and the rare-category flag are estimated from few rows. The
  published values are the target, not a claim that the estimates are stable.
- **Newline rule.** `inicio_oracion` and `_pregunta` both treat `\n` as a
  sentence boundary. S5 keeps the frozen behaviour; changing it would change
  M1/M2 and needs an ADR.
- **Deferred audit.** The 209 implicit negatives remain a protocol assumption;
  the 20-candidate audit is still deferred.

## Approved decisions

**Decision 1 — partial result accepted as a fallback (2026-11-27).** When
`deviations == []` and `margin_deviations != []`, S5 is **partial**: the
no-abstention M2 is reproduced, but the published abstention rows are not. The
partial result is a fallback, not the default close. After the S5 TDD cycle,
investigate the published-margin mismatch and fix it before closing S5 if
possible. If the cause cannot be found or fixed, close S5 as partial with the
27/439 `abstiene_M2` mismatch and a follow-up. Treating partial as a pass, or
using the published margins, needs an ADR.

**Decision 2 — S4 prediction return order (2026-11-27).** `M2Model.predict`
returns `(labels, probabilities, abstention, origin, review)`, not the
notebook's `(labels, abstention, probabilities, origin, review)`.

**Decision 3 — `ValueError` for an unknown unit (2026-11-27).** A unit with no
admitted category raises `ValueError` naming the unit, not the notebook's
`IndexError`.

## Rough size

`src/conectores/rules.py` (~220 lines), additions to
`src/conectores/models.py` (~180 lines), `tests/test_rules.py` (~280 lines),
additions to `tests/test_models.py` (~180 lines), additions to
`tests/test_integration.py` (~120 lines) and the diagnostic report. About 1,000
lines.

## Approval

**Approved:** 2026-11-27 by Till.

**Approved decisions:** partial result accepted as a fallback when the core
matches and the margins differ; S4 prediction return order; `ValueError` for an
unknown unit.

**Assumptions:**

- The notebook's `M2`, `REGLAS`, `anotar_gramatica` and `elegir_margen_m` are
  the reference implementation.
- The frozen spaCy model is `es_core_news_sm`; the frozen embedding model is
  `paraphrase-multilingual-MiniLM-L12-v2`; the frozen test files define the
  split.
- The published no-abstention M2 rows and the traceability counts are the
  target.
- The `1e-5` `p_M2` tolerance is a fidelity guard, not a metric change.
- The margin mismatch is a finding to investigate, not a reason to use test
  labels or published margins.
- `M2FeatureBuilder` lives in `rules.py`; `TRACEABILITY_TARGET` is a constant in
  `models.py`.

**Deferred (after the S5 TDD cycle, before closing S5):**

- The published-margin investigation: find the cause and fix it if possible.
- If it cannot be fixed, the partial-outcome report and follow-up.

**Deferred (beyond S5):**

- The 20-candidate implicit-negative audit.
- The application corpus and its predictions.
- The newline-rule change.
- The 548/550 reconciliation, F2 and coverage-at-budget.
- A rule-first M3 or any LLM annotator.

Next: /tdd frozen rule set.
