# Design note 0002 — candidate replay

- **Status:** chosen
- **Date:** 2026-11-21
- **Slice:** S2 — candidate replay
- **Related:** `docs/00-brief.md`, `docs/plan.md`,
  `docs/specs/0001-metric-replay.md`,
  `docs/results/0001-metric-replay-diagnostics.md`,
  `doc/equipo11_B0_B1_M1_M2.ipynb`

## Problem

S1 recomputed the published metrics from `predicciones_test.csv`, but it never
rebuilt the candidate occurrences those predictions sit on. S2 builds the 273
candidates from `referencia_piloto.csv`, `listado_fuentes2009.csv` and
`csl_excluidas.csv`: 64 positive, 209 implicit negatives, 16 undetected labels,
8 matches inside CSL zones and 3 second pieces. After S2 the repository can go
from the raw annotation to candidate rows without reading the predictions. That
is the precondition for replaying B0, B1, M1 and M2. S1's minimal
undetected-label parser is replaced by this builder.

## Terms

- **Candidate:** one listing match in one comment, with its context and gold
  label. The 150 reference comments produce 273 candidates; 64 carry a gold
  label and 209 are implicit negatives.
- **Second piece:** a listing match that overlaps a reference unit already
  claimed by an earlier match. If the listing matches `más` and then `encima`
  against the single reference unit `[más encima::…]`, the second match is
  skipped so the unit counts once. There are 3 in the pilot.
- **CSL zone:** a reference span whose semi-free construction is excluded from
  evaluation. A listing match that overlaps it is dropped before candidate
  creation. Eight listing matches fall inside the 16 CSL occurrences.

## Approaches

| Approach | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|
| **A — faithful port** | Exact counts by construction: port `construir_candidatos`; the CSL and second-piece rules are already written. | Carries the regex's brittleness (single-space multi-word forms, lookbehind boundaries); duplicates S1's annotation parser unless it is extracted into a shared module. | 273/64/209/16/8/3 and the per-seed 65/97/92/124/61. |
| **B — annotation-first** | Anchors on the reference spans, so the gold label is the anchor and second pieces fall out naturally. | Must still reproduce the same 284 raw matches and 8 CSL exclusions; partial overlaps need an explicit rule. | The same counts; any difference is a bug to investigate. |
| **C — token-based spaCy matching** | Robust to spacing and punctuation in multi-word forms. | Changes the match set, so it will not reproduce 273 without tuning; the acceptance is exact counts. | The counts would have to match; if they do not, the slice fails. |

## Recommendation

A. The slice's job is to reproduce the notebook's numbers from the same
preconditions; the notebook is the reference implementation behind the
published table. B is cleaner but risks changing the set. C is better
engineering but changes the numbers, which belongs to a later slice with an
ADR.

## Chosen approach

**A — faithful port.** The author chose it after the learn session and
explained both exclusions: CSL matches are dropped before candidate creation,
and a match that overlaps an already-claimed reference unit is skipped because
that unit is already represented. The port keeps the notebook's
longest-form-first, case-insensitive, letter-boundary matching and its
order-dependent handling of overlapping reference spans. Annotation parsing and
listing matching are extracted into shared helpers so S1's replay and S2's
builder use one implementation; S1's published counts must stay unchanged.

No ADR is needed: the port reproduces the frozen protocol and changes no split,
seed, threshold, rule or metric.

## What would change the decision

- If the port cannot reproduce 273/64/209/16/8/3 on the frozen inputs, stop and
  investigate. A mismatch is a port bug or a data-version difference; do not
  adjust the target counts.
- If the notebook's regex is shown to miss multi-word forms because of spacing
  or punctuation, fixing it is a separate slice with an ADR, because it changes
  the candidate set and therefore every downstream metric.
- If the team resolves the implicit-negative assumption with the 20-candidate
  audit, the classification changes and needs an ADR.
- If the 284 raw matches cannot be reconciled with 273 candidates and 11
  exclusions, stop before specifying the rest of the slice.

## Sources

Fuentes Rodríguez (2009); `doc/Equipo11_Propuesta_v4_hito2.docx`; the notebook's
`cargar_listado` and `construir_candidatos`; `docs/00-brief.md`; `docs/plan.md`;
`docs/results/0001-metric-replay-diagnostics.md`.
