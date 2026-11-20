# Design note 0001 — metric replay

- **Status:** chosen
- **Date:** 2026-11-20
- **Slice:** S1 — metric replay
- **Related:** `docs/00-onboarding.md`, `docs/state.md`,
  `doc/Equipo11_Propuesta_v4_hito2.docx`, `doc/resultados_hito2.zip`

## Problem

The published table in `doc/resultados_hito2.zip` reports F1, coverage,
precision, abstention and bootstrap intervals for five seeds. This repository has
no code that recomputes them. Before reimplementing the pipeline, the team needs
a trusted yardstick: a program that reads the published predictions and the
reference and reproduces the table. Without it, a later mismatch cannot be
attributed to the new code, the local package versions, or the protocol.

## Terms

- **Metric replay:** recompute the published metrics from the published
  predictions and the reference, not from a new model.
- **Undetected label:** a reference label whose form the Fuentes list never
  matches. There are 16 in the 80 evaluated labels. They are not candidates, so
  they are absent from `predicciones_test.csv`.
- **Frozen test hash:** the SHA-256 of each `test_semillaN.txt` file in
  `hashes.json`, used to prove the test IDs did not change.

## Approaches

| Approach | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|
| A1 — predictions + reference | A true replay: recomputes F1, coverage, precision, abstention, macro F1 and the 1,000-repetition bootstrap, including the 16 undetected labels. | Needs a minimal undetected-label parser; overlaps with the candidate construction in a later slice. | The notebook's `metricas` takes `n_no_detectadas`; the predictions CSV does not carry it. |
| A2 — predictions only | Simplest code. | Coverage and F1 come out too high because the denominator misses the 16 undetected labels. It replays a different metric. | `gp = positives + n_no_detectadas` in `metricas`. |
| A3 — summary only | Cheapest: checks means, standard deviations and interval arithmetic. | Does not validate the metric code; a bug in `metricas` would pass. | The summary CSVs are derived, not raw. |

## Recommendation

A1. It is the only approach that reproduces the published metric. A2 changes the
denominator and would not be a yardstick. A3 checks the summary, not the metric.

## Chosen approach

**A1 — predictions + reference.** The slice reads `predicciones_test.csv`,
`referencia_piloto.csv`, `csl_excluidas.csv`, the three published summary CSVs,
`test_semillaN.txt` and `hashes.json`. It reconstructs the undetected labels per
test thread, recomputes the per-seed and mean metrics, recomputes the bootstrap
with `n=1000` and the seed as the RNG seed, and verifies the frozen hashes.

Acceptance: per-seed and mean values match the published table to three decimals;
a deviation fails the slice and is investigated. The bootstrap is deterministic
given the seed and `n=1000`, so the intervals should match. The integration test
reads the ignored local data and is marked `slow`; unit tests use synthetic
fixtures with no comment text.

No ADR is needed: the slice reproduces the frozen protocol in `gate.toml` and the
v4 proposal. It does not change the split, seeds, threshold, rules or metrics.

## What would change the decision

- If the local package versions make the published values unreproducible, the
  slice documents the deviation and the yardstick becomes "reproduce within a
  stated tolerance" rather than "match to three decimals".
- If the reference's 16 undetected labels cannot be reconstructed without the
  full candidate logic, the slice imports a minimal parser and Slice B later
  replaces it.
- If the team decides the published metric definitions are wrong, that is a
  protocol change and needs an ADR before the replay.

## Sources

Fuentes Rodríguez (2009); the v4 proposal; `docs/00-onboarding.md`; the notebook's
`metricas` and `bootstrap_dif`; the input audit.
