# Spec 0001 — metric replay

**Slice:** S1 — metric replay
**Status:** approved
**Approved:** 2026-11-20
**Design note:** [0001-metric-replay.md](../design/0001-metric-replay.md)
**Requirements source:** `doc/Equipo11_Propuesta_v4_hito2.docx`,
`docs/00-onboarding.md`, `doc/resultados_hito2.zip`

## Outcome

`python -m conectores.metrics replay --check` reads the published predictions and
the reference, recomputes the published table, and exits 0 only when every
published value matches to three decimals. A single deviation exits 1 and names
the cell.

## Interface

### Pure functions (`src/conectores/metrics.py`)

```python
NO = "NO_DISCURSIVO"

@dataclass(frozen=True)
class Metrics:
    f1_label: float
    f1_discourse: float
    f1_macro: float
    precision: float
    coverage: float

def compute_metrics(
    gold: Sequence[str], pred: Sequence[str], n_undetected: int
) -> Metrics: ...

def undetected_labels(
    reference: pd.DataFrame, listing: pd.DataFrame, csl: pd.DataFrame
) -> pd.DataFrame: ...

def bootstrap_difference(
    gold: Sequence[str],
    pred_a: Sequence[str],
    pred_b: Sequence[str],
    thread_id: Sequence[str],
    n_undetected_by_thread: Mapping[str, int],
    n: int = 1000,
    seed: int = 0,
) -> tuple[float, float]: ...
```

### Replay (`src/conectores/metrics.py`)

```python
@dataclass(frozen=True)
class ReplayResult:
    systems: pd.DataFrame       # 30 rows: 6 systems x 5 seeds
    summary: pd.DataFrame       # 6 rows: mean and std per system
    intervals: pd.DataFrame     # 15 rows: 3 comparisons x 5 seeds
    diagnostics: pd.DataFrame   # candidate and undetected counts per seed
    traceability: Mapping[str, int]  # the v4 traceability counts
    deviations: list[str]       # empty when the replay matches

def replay(
    predictions: pd.DataFrame,
    reference: pd.DataFrame,
    listing: pd.DataFrame,
    csl: pd.DataFrame,
    published: Mapping[str, pd.DataFrame],
    hashes: Mapping[str, str],
    test_files: Mapping[int, str],
    n: int = 1000,
) -> ReplayResult: ...
```

### CLI

```text
python -m conectores.metrics replay \
  --predictions PATH --reference PATH --listing PATH --csl PATH \
  --published PATH --hashes PATH --test-ids PATH \
  --output DIR [--check]
```

`--published` points at the directory holding `resultados_semillas.csv`,
`resumen_sistemas.csv` and `intervalos_confianza.csv`; the CLI reads the three
files. `--hashes` points at `hashes.json`; `--test-ids` points at the directory
holding `test_semillaN.txt`. The CLI writes `replay_systems.csv`,
`replay_summary.csv`, `replay_intervals.csv`, `replay_diagnostics.csv` and
`replay_report.md` to `--output`. With `--check`, it compares to the published
files and exits 1 on any deviation.

## Metric definitions

Let `NO = "NO_DISCURSIVO"`, `tp = sum(g == p != NO)`, `pp = sum(p != NO)`,
`gp = sum(g != NO) + n_undetected`, and `f1 = 2*tp/(pp+gp)` when `tp > 0`, else
0.

- `f1_label = f1(tp, pp, gp)`.
- `f1_discourse = f1(tpd, pp, gp)` where `tpd = sum(g != NO and p != NO)`.
- `precision = tp/pp` when `pp > 0`, else 0.
- `coverage = tp/gp` when `gp > 0`, else 0.
- `f1_macro`: for `M` in `CON`, `OP`, let `t = sum(macro(g) == macro(p) == M)`,
  `a = sum(macro(p) == M)`, `b = sum(macro(g) == M)`, `f1(M) = 2*t/(a+b)` when
  `t > 0`, else 0; `f1_macro` is the mean of the two. `macro(label)` is
  `label.split(":")[0]` for a labelled string and `NO` for `NO`.

`undetected_labels` returns one row per reference span the listing does not
match, with `comment_id`, `thread_id`, `unidad` and `oro`. It parses the
`[unidad::ETIQUETA]` annotation, removes spans whose `(comment_id, unidad)` is in
`csl`, and excludes spans that overlap a listing match. The listing match uses
the same boundary and case rules as the notebook: longest form first, no letter
before or after, case-insensitive. It does not need to build the candidate rows.

## Published-row semantics

The replay reproduces the notebook's choices, including its mistakes:

- `B0`, `B1`, `M1`, `M2` use the full test and no abstention. `abstencion` and
  `margen` are `NaN`.
- `M1 con abstención` and `M2 con abstención` use the published margin. The
  abstention flag is `abs(prob - 0.5) < margen`. For M2 the published
  `abstiene_M2` column must equal the derived flag; for M1 the flag is derived
  from `p_M1` and the published margin.
- The abstention rows compute metrics on the kept rows only, but keep the full
  test's undetected count in the denominator. This is the notebook's choice and
  the replay must reproduce it.
- `abstencion` is the mean of the flags over the full test. `margen` is the
  published margin.
- The summary uses the sample standard deviation (`ddof=1`) and the same row
  order as the published table.

## Acceptance criteria

1. **Per-seed table.** The replay reproduces all 30 rows of
   `resultados_semillas.csv` to three decimals for `F1_etiqueta`,
   `F1_uso_discursivo`, `F1_macro_CON_OP`, `precision_etiqueta`,
   `cobertura_etiqueta`, `abstencion` and `margen`.
2. **Summary table.** The replay reproduces the six rows of
   `resumen_sistemas.csv` means and standard deviations to three decimals.
3. **Intervals.** The replay reproduces the 15 rows of
   `intervalos_confianza.csv` to three decimals, including `excluye_cero`.
4. **Frozen hashes.** The replay verifies the five `test_semillaN.txt` SHA-256
   values against `hashes.json`.
5. **Diagnostics.** The replay reports 65, 97, 92, 124 and 61 candidates for
   seeds 0–4 and 5, 3, 4, 8 and 4 undetected labels for the same seeds. It also
   reports the v4 traceability counts: 91 discourse labels, 58 list-fixed
   (34 correct), 33 model-chosen (20 correct) and 43 "revisar categoría".
6. **Deviation detection.** A single perturbed cell makes `--check` exit 1 and
   name the cell in `replay_report.md`.
7. **Privacy.** The output contains no comment text and no `author_hash`. The
   output columns are IDs, list forms, labels, probabilities, flags and metrics.
8. **Test split.** The integration test is marked `slow` and skips when the
   ignored local data is absent. Unit tests run by default with synthetic
   fixtures.

## Tests to add

| Test | Type | Asserts |
|---|---|---|
| `test_compute_metrics_hand_checked` | unit | Four rows with two TP, one FP and one FN, plus one undetected label, produce the expected F1, precision and coverage. |
| `test_compute_metrics_no_positive` | unit | All-negative input returns zeros without dividing by zero. |
| `test_undetected_labels_excludes_csl` | unit | A synthetic annotation with one list match, one non-match and one CSL span returns only the non-match. |
| `test_undetected_labels_boundaries` | unit | A list form inside a longer word is not a match. |
| `test_bootstrap_deterministic` | unit | The same seed returns the same interval; a different seed changes it. |
| `test_replay_matches_published` | integration, slow | Every row of the three published tables matches to three decimals. |
| `test_replay_perturbed_cell_fails` | integration, slow | One perturbed cell makes `--check` exit 1 and names the cell. |
| `test_replay_frozen_hashes` | integration, slow | The five hashes match `hashes.json`. |
| `test_output_has_no_text` | unit | The output columns contain no `texto` or `author_hash`. |
| `test_cli_help` | unit | The CLI exposes `replay` and its options. |

## Out of scope

- Building the full candidate table; only the undetected-label parser is in this
  slice. Slice B builds the candidates.
- Training or refitting B0, B1, M1 or M2. The predictions and margins are
  published inputs.
- Recomputing the margins by cross-validation. The replay reads the published
  margins.
- The application corpus and its predictions.
- The F2 question, the brief and the plan. The brief should confirm the replay is
  Slice A and the three-decimal tolerance.

## Privacy impact

The replay reads `doc/referencia_piloto.csv`, which is ignored and contains
comment text. It writes only IDs, list forms, labels, probabilities, flags and
metrics. The integration test reads the ignored data; unit tests use synthetic
fixtures. No comment text or `author_hash` enters the repository.

## Evaluation protocol impact

None. The replay reproduces the frozen protocol in `gate.toml` and the v4
proposal. It does not change the split, seeds, threshold, rules or metrics. No
ADR is needed.

## Contradictions and open points

- `docs/00-brief.md` and `docs/plan.md` are not written. This spec uses the v4
  proposal and the onboarding doc as the requirements source. The brief should
  confirm the slice order and the tolerance.
- The v4 proposal's "705 unidades" and the listing's 614 forms remain
  unreconciled. This slice does not use the 705/614 distinction; it uses the
  listing's matching rules.
- The published `resultados_semillas.csv` has six-decimal values; the comparison
  rounds both sides to three decimals. The `resumen_sistemas.csv` has a
  two-row header; the comparison skips the second header row.

## Rough size

Two modules (`metrics.py`, `__main__.py`), two test files, about 400 lines.

## Approval

**Approved:** 2026-11-20 by Till.

**Approved decisions:**

1. Include the v4 traceability counts (91 discourse labels, 58 list-fixed/34
   correct, 33 model-chosen/20 correct, 43 "revisar categoría") as Slice A
   diagnostics.
2. Use the published margins as inputs; do not re-run the grouped
   cross-validation.
3. Reproduce the notebook's abstention denominator: kept rows for the metrics,
   the full test's undetected count in the denominator.

**Assumptions:**

- `docs/00-brief.md` and `docs/plan.md` are missing; the v4 proposal and the
  onboarding doc are the requirements source.
- Both sides of each comparison are rounded to three decimals.
- The integration test is marked `slow` and skips without the ignored data.
- Output uses IDs and list forms, never comment text.
- The comparison skips the second header row of `resumen_sistemas.csv`.

**Deferred:**

- Candidate construction, model training, the application corpus, the F2
  question, the brief and the plan.
