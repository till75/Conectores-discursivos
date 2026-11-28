# Spec 0006 — Publication pack

**Slice:** S6 — publication pack
**Status:** approved
**Date:** 2026-11-27
**Approved:** 2026-11-27 by Till
**Design note:** none; the plan marks `/learn` as no for S6. The approach is a
composition of the S2–S5 builders and the S1 replay.
**Requirements source:** `docs/00-brief.md`, `docs/plan.md`,
`docs/specs/0001-metric-replay.md`, `docs/specs/0002-candidate-replay.md`,
`docs/specs/0003-baseline-replay.md`, `docs/specs/0004-m1-replay.md`,
`docs/specs/0005-m2-replay.md`, `docs/results/`, `README.md`, `gate.toml`,
`doc/`.

## Outcome

One command reads the frozen pilot inputs, rebuilds the published prediction
and metric tables, writes a reproducible report, and runs the privacy check; the
data card and model card describe the data and the systems, and the README gives
the reproduction commands.

## Interface

### Pipeline (`src/conectores/pipeline.py`)

```python
@dataclass(frozen=True)
class PipelineResult:
    predictions: pd.DataFrame
    systems: pd.DataFrame
    summary: pd.DataFrame
    intervals: pd.DataFrame
    diagnostics: pd.DataFrame
    traceability: Mapping[str, int]
    deviations: list[str]
    privacy_mentions: int

def run_pipeline(
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
    test_files: Mapping[int, str],
    hashes: Mapping[str, str],
    published: Mapping[str, pd.DataFrame],
    embedder: Embedder,
    nlp: NLP,
    n_bootstrap: int = 1000,
) -> PipelineResult: ...

def write_pipeline_outputs(
    result: PipelineResult, output_dir: Path
) -> None: ...

def main(argv: Sequence[str] | None = None) -> int: ...
```

`run_pipeline` builds the candidates, the B0/B1 predictions, the M1 predictions
and the M2 predictions from the inputs. It merges them into one public frame and
uses `metrics.replay` for the systems, summary, intervals, diagnostics,
traceability and hash checks. It compares the merged predictions with
`published["predictions"]` and returns every mismatch as a named deviation.

`write_pipeline_outputs` writes the public tables and the report. `main` is the
CLI wrapper: it reads the CSVs, the frozen test files and the hashes, loads
`sentence_embedder()` and `load_nlp()`, runs the pipeline, writes the outputs,
prints a short summary, and returns `1` when `--check` finds a deviation or a
privacy mention.

### CLI

```text
python -m conectores.pipeline \
  --reference <referencia_piloto.csv> \
  --listing <listado_fuentes2009.csv> \
  --csl <csl_excluidas.csv> \
  --test-ids <test_congelado directory> \
  --hashes <hashes.json> \
  --published <publicable directory> \
  --output <output directory> \
  [--n-bootstrap 1000] \
  [--check]
```

The published directory is the extracted `resultados/publicable` directory from
`doc/resultados_hito2.zip`. It contains `predicciones_test.csv`,
`resultados_semillas.csv`, `resumen_sistemas.csv` and
`intervalos_confianza.csv`. The pipeline reads it only for comparison; it never
uses the published predictions to build the replay.

### Public frame

`PipelineResult.predictions` has the published 15 columns, in this order:

```text
comment_id, thread_id, semilla, unidad, inicio, oro,
B0, B1, M1, M2, p_M1, p_M2, origen_M2,
revisar_categoria, abstiene_M2
```

It has 439 rows on the real inputs and no `texto`, `ventana`, `pos_*`, `tok_*`
or `author_hash`. `B0`, `B1`, `M1` and `M2` are no-abstention labels; `p_M1` and
`p_M2` are probabilities; `abstiene_M2` is the learned-margin flag.

### Types and units

- `p_M1` and `p_M2` are probabilities in `[0, 1]`.
- `inicio` is a 0-based character offset into the text used for matching.
- `origen_M2` is exactly `"listado"` or `"modelo"`.
- `revisar_categoria` and `abstiene_M2` are booleans.
- The metric names are the S1 names; metrics are fractions in `[0, 1]`.
- `traceability` has the six S5 keys; `privacy_mentions` is an integer.
- `n_bootstrap` is the number of thread-bootstrap resamples; default 1000.

### Label vocabulary

`NO_DISCURSIVO`, `CON:<CATEGORÍA>` and `OP:<CATEGORÍA>`. The published
vocabulary is `NO_DISCURSIVO`, `CON:ADICIÓN`, `CON:CIERRE`, `CON:CONCESIVO`,
`CON:CONCLUSIVO`, `CON:CONSECUTIVO`, `CON:CONTINUATIVO`, `CON:INTERACTIVO`,
`CON:REFORMULATIVOS`, `OP:ARGUMENTATIVO`, `OP:ENUNCIATIVO`, `OP:INFORMATIVO` and
`OP:MODAL`. The pipeline does not invent labels.

## Behaviour

### End-to-end replay

1. `build_candidates(reference, listing, csl)` returns the candidate set.
2. `baseline_predictions` returns B0/B1 for each test candidate and seed.
3. `m1_predictions` returns M1, `p_M1`, `abstiene` and
   `M1_con_abstencion`; the pipeline keeps the public M1 columns.
4. `anotar_gramatica` adds the POS columns; `m2_predictions` returns M2,
   `p_M2`, `origen_M2`, `revisar_categoria` and `abstiene_M2`.
5. The three frames are merged on `(semilla, comment_id, unidad, inicio)`.
   `oro` and `thread_id` must agree; a disagreement is a deviation.
6. `metrics.replay` computes the systems, summary, intervals, diagnostics,
   traceability and the published-table and hash comparisons.
7. The merged frame is compared with `published["predictions"]`: keys
   `(semilla, comment_id, unidad, inicio)`; `oro`, `B0`, `B1`, `M1` and `M2`
   exact; `p_M1` and `p_M2` within `1e-5`; `origen_M2`,
   `revisar_categoria` and `abstiene_M2` exact.
8. The privacy check scans every cell of the public frame for `@` mentions.
   `@USER` is the anonymised placeholder and is not a mention. Any other
   `@name` increments `privacy_mentions` and adds a deviation.

The test split is the frozen one from S1–S5. The pipeline does not rerun
`GroupShuffleSplit`, change the seeds or choose the margin on test.

### Outputs

`write_pipeline_outputs` creates the output directory and writes:

| File | Content |
|---|---|
| `predicciones_test.csv` | the 15 public columns, 439 rows |
| `resultados_semillas.csv` | 30 system rows, the S1 columns |
| `resumen_sistemas.csv` | 6 summary rows, flat columns `sistema`, `*_mean`, `*_std` |
| `intervalos_confianza.csv` | 15 interval rows |
| `diagnosticos.csv` | 5 per-seed candidate and undetected rows |
| `trazabilidad.json` | the six traceability counts |
| `pipeline_report.md` | counts, deviations, traceability, privacy and commands |

The report contains no comment text. A `--check` run returns `1` when
`deviations` is non-empty or `privacy_mentions > 0`.

### Data card (`docs/data-card.md`)

The data card is written in Spanish and contains:

- the pilot corpus: 1,268 comments, 6 videos, 798 threads; 150 reference
  comments, 65 with at least one label, 96 label spans, 12 categories, one
  video; 273 candidates from 284 raw matches after 8 CSL and 3 second-piece
  exclusions; 64 positive, 209 implicit negatives, 16 undetected;
- the application corpus: 10,505 comments, 20 videos, 6,264 threads, no labels;
  it shares zero comment IDs with the pilot; the application run is deferred;
- the listing: 705 rows, 614 forms, 548 single-category, 66 multi-category, 16
  CSL constructions;
- the split: 30% of threads, seeds 0–4, frozen test IDs and hashes, 19 test
  threads per seed, 439 appearances, 256 unique candidates, 17 never tested;
- the reference: adjudicated/selected, not a measured agreement; 48
  `anotacion_final` rows; the agreement caveat;
- privacy: R5, no comment text, no `author_hash`, no `@name`; only IDs, forms,
  labels, counts and metrics; `doc/` is read-only and gitignored;
- limitations: one pilot video, topic shift to the application corpus, small
  sample, implicit negatives, undetected labels, no application labels.

### Model card (`docs/model-card.md`)

The model card is written in Spanish and contains:

- the systems: B0, B1, M1, M2, M1 con abstención and M2 con abstención;
- the features: the ±6-word window, word/character/unit TF-IDF, six flags, the
  384-column frozen embedding, the 15 frozen rules, spaCy POS and the
  rare-category flag;
- the training: two-step logistic regression, `C=1.0`, `max_iter=2000`,
  balanced step 1, seeds 0–4; the margin by five-fold grouped CV on training,
  grid `0.00–0.30`, 20% cap and smaller-margin tie; the pre-stable
  `GroupKFold` tie-break used for the published margins;
- the metrics: full-label F1 primary, discourse F1, macro CON/OP, precision and
  coverage; thread-bootstrap intervals;
- the published results: M2 0.483, M2 con abstención 0.513, B1 0.328, mean gain
  +0.155; the interval caveat; mean abstention 15.6%; traceability
  `91/58/34/33/20/43`;
- intended use: assist the annotator, not autonomous annotation; the review
  queue and provenance;
- limitations: one-video pilot, topic shift, implicit negatives, 16 undetected
  labels, no significance claim, external frozen embeddings, the newline-rule
  question and the deferred application corpus;
- privacy: R5 and the human-review requirement.

### README

The README is updated in Spanish:

- the status says S2–S6 are reproduced and M2 is no longer notebook-only;
- a “Reproducción” section gives the install, test, slow-test, lint and
  pipeline commands;
- the pipeline example shows how to extract `doc/resultados_hito2.zip` and pass
  the publicable directory;
- the data card and model card are linked;
- the privacy statement remains visible.

## Acceptance criteria

1. **One-command reproduction.** The real inputs produce 439 predictions, 30
   system rows, 6 summary rows, 15 interval rows and 5 diagnostic rows with zero
   deviations and exit code 0. *Happy:* the real command writes all seven
   outputs. *Boundary:* `--check` with a perturbed published cell returns 1 and
   names the cell. *Failure:* a missing input column raises `ValueError` naming
   the frame and column; a changed test hash is a named deviation.

2. **Combined predictions.** The public frame has the 15 columns and 439 rows;
   `oro`, B0/B1/M1/M2, `p_M1`/`p_M2`, `origen_M2`, `revisar_categoria` and
   `abstiene_M2` match the published rows. *Happy:* zero prediction deviations.
   *Boundary:* a key present on one side is a deviation. *Failure:* a text,
   window or author-hash column in the output fails the privacy gate.

3. **Privacy.** The real frame has zero `@name` mentions and no text, window,
   POS or author-hash columns. *Happy:* `privacy_mentions == 0` and
   `deviations` has no privacy entry. *Boundary:* `@USER` is allowed; a
   synthetic `@name` increments the count and adds a deviation. *Failure:* a
   written output containing comment text fails.

4. **Data card.** `docs/data-card.md` exists and contains the corpus, listing,
   candidate, split, reference, privacy and limitation sections with the counts
   above. *Happy:* all sections are present. *Boundary:* the application corpus
   is described as unlabeled and deferred. *Failure:* a missing section or a
   comment fragment fails the docs check.

5. **Model card.** `docs/model-card.md` exists and contains the systems,
   features, training, metrics, results, intended use, limitations and privacy
   sections. *Happy:* all sections are present. *Boundary:* the abstention and
   interval caveats are stated. *Failure:* a missing section or a claim of
   significance fails the docs check.

6. **README.** The README has the updated status and the reproduction commands,
   including the pipeline command and the slow-test command. *Happy:* a reader
   can follow the commands. *Boundary:* the zip extraction step is shown.
   *Failure:* the stale “M2 only in the notebook” status remains.

7. **Compatibility.** S1–S5 stay green and unchanged. The pipeline composes the
   existing builders and replay; it does not change the split, seeds, test
   hashes, threshold, metrics or frozen rules.

8. **Test split.** The real-data tests are `slow`, require `doc/`, spaCy, the
   embeddings extra and the frozen model, and skip with a reason when an input
   is absent. The unit tests use synthetic frames and a fake embedder.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_pipeline_matches_published` | integration, slow | 439 predictions, 30 systems rows, 6 summary rows, 15 intervals, 5 diagnostics, zero deviations, zero privacy mentions. |
| `test_pipeline_cli` | integration, slow | The CLI writes the seven outputs and returns 0; a perturbed published cell returns 1. |
| `test_pipeline_requires_columns` | unit | A missing reference, listing, candidate or test input column names the frame and column. |
| `test_pipeline_perturbed_prediction` | unit | A perturbed `M2`, `p_M2` or `abstiene_M2` cell is named. |
| `test_pipeline_privacy_mentions` | unit | `@USER` is ignored; a synthetic `@name` increments the count and adds a deviation. |
| `test_pipeline_output_has_no_text` | integration, slow | The output CSVs and report contain no text, window, POS, author hash or `@name`. |
| `test_data_card_sections` | unit | The data card exists and contains the required headings and counts. |
| `test_model_card_sections` | unit | The model card exists and contains the required headings and caveats. |
| `test_readme_reproduction` | unit | The README has the updated status and the pipeline/slow commands. |

The existing S1–S5 slow tests remain in the suite and must stay green.

## Out of scope

- Running the application corpus or publishing its predictions.
- New annotation, new models, M3 or an LLM annotator.
- Changing the split, seeds, test hashes, abstention threshold, metrics or
  frozen rule set.
- Publishing comment text, windows or `author_hash`.
- A web UI or a hosted service.
- The 548/550 reconciliation, the 20-candidate implicit-negative audit, F2 and
  coverage-at-budget.
- The `inicio_oracion`/`_pregunta` newline-rule change.
- A data card or model card for the unlabeled application corpus.

## Privacy impact

R5 is unchanged. The pipeline reads comment text in memory to build candidates,
compute embeddings and run spaCy, but it writes only the public 15-column frame
and aggregate tables. The output has no `texto`, `ventana`, `pos_*`, `tok_*`,
`author_hash` or `@name`; `@USER` is the anonymised placeholder. The report and
the cards contain no comment text. `doc/` stays read-only and gitignored; the
output directory is local and contains no text. The privacy check reports zero
mentions on the real inputs.

## Evaluation protocol impact

None. The split, seeds, frozen test IDs and hashes, abstention cap, metrics and
frozen rule set are unchanged. The pipeline composes S1–S5; it does not choose
the margin on test. The pre-stable `GroupKFold` tie-break is part of the
reproduction of the published margins and is documented in the model card; it
does not change the protocol. Any protocol change needs an ADR before code.

## Contradictions and open points

- The README currently says M2 lives only in the notebook. S6 updates that
  status; the change is documentation, not a result change.
- The published tables are inside `doc/resultados_hito2.zip`. The README must
  show the extraction step, or the caller must pass an extracted publicable
  directory.
- The published summary has a two-row header; the pipeline writes a flat
  `sistema`, `*_mean`, `*_std` table. The comparison reads the published header
  through the S1 helper. The values, not the header shape, are the contract.
- The data card and model card are new documents; they must not copy comment
  text. The counts come from the audit and the S2–S5 reports.
- The application corpus counts 19,741/20,097 and the 2,000-comment sample stay
  deferred; S6 does not resolve them.
- The 548/550 reconciliation, the 20-candidate audit and the newline-rule
  question remain open.
- The pipeline's `--check` compares published tables; a future library change
  that moves a result will fail the check and must be investigated, not
  silently relaxed.
- **Bootstrap order (resolved 2026-11-27).** The published prediction table
  defines the frozen row/thread order used by the bootstrap RNG. The rebuilt
  frame is reordered to that key order before the interval calculation, without
  reading any published label or probability. Point predictions, systems and
  summary are order-independent; the intervals now match the published rows.

## Rough size

`src/conectores/pipeline.py` (~250 lines), additions to
`tests/test_integration.py` (~150 lines), `docs/data-card.md` (~150 lines),
`docs/model-card.md` (~180 lines), `README.md` (~40 lines) and the S6
diagnostic report. About 900 lines.

## Approval

**Approved:** 2026-11-27 by Till.

**Approved decisions:**

1. **Seven-file publication pack.** The pipeline writes
   `predicciones_test.csv`, `resultados_semillas.csv`,
   `resumen_sistemas.csv` with flat `*_mean`/`*_std` columns,
   `intervalos_confianza.csv`, `diagnosticos.csv`, `trazabilidad.json` and
   `pipeline_report.md`. The published comparison stays separate and reads the
   published two-row summary header through the S1 helper.
2. **Spanish static cards.** `docs/data-card.md` and `docs/model-card.md` are
   written in Spanish and are not generated by the pipeline.
3. **Extracted publicable directory.** The CLI takes an extracted
   `resultados/publicable` directory; the README shows the zip extraction.
4. **Injected models.** `run_pipeline` takes `embedder` and `nlp`; the CLI
   loads the frozen embedding model and `es_core_news_sm`.
5. **Privacy rule.** `@USER` is the anonymised placeholder and is allowed; any
   other `@name` increments `privacy_mentions` and fails `--check`.
6. **No protocol change.** The split, seeds, frozen test hashes, abstention
   threshold, metrics and frozen rules are unchanged. The pre-stable
   `GroupKFold` tie-break is documented in the model card and is part of the
   reproduction, not a protocol change.

**Assumptions:**

- The S2–S5 builders and the S1 replay are the reference implementation; S6
  composes them and does not add a model.
- The published prediction values are comparison targets only; the frozen
  published row order is used to reproduce the thread-bootstrap RNG order. No
  published label or probability is used to build a prediction.
- The summary output is flat; the comparison reads the published header shape.
- The data card and model card contain no comment text.
- `doc/` is read-only and gitignored; the output directory is local.
- The slow tests skip with a reason when `doc/`, spaCy, the embeddings extra or
  the frozen model is absent.

**Deferred:**

- The application corpus run and its predictions.
- New annotation, M3 or an LLM annotator.
- Publishing comment text, windows or `author_hash`.
- A web UI or hosted service.
- The 548/550 reconciliation, the 20-candidate implicit-negative audit, F2 and
  coverage-at-budget.
- The `inicio_oracion`/`_pregunta` newline-rule change.
- A data card or model card for the unlabeled application corpus.

Next: /tdd combined public frame.
