# Design note 0005 — M2 replay

- **Status:** chosen
- **Date:** 2026-11-27
- **Slice:** S5 — M2 replay
- **Related:** [brief](../00-brief.md), [plan](../plan.md),
  [S4 design](0004-m1-replay.md), [S4 spec](../specs/0004-m1-replay.md),
  [S4 report](../results/0004-m1-replay-diagnostics.md),
  [M2 rules and provenance](../learn/04-m2-rules-provenance.md)

## Problem

M2 is the headline system. It layers five things on M1: the strict listing
restriction, the 15 frozen context rules, spaCy part-of-speech features, the
rare-category flag and provenance. S5 rebuilds M2 from the S2 candidates, the
listing, the five frozen splits and the frozen embedding model without reading
`predicciones_test.csv`.

The prototype already reproduces the linguistic layer exactly: the
no-abstention labels, `p_M2`, `origen_M2`, `revisar_categoria` and the
traceability counts match the published values. The only mismatch is the
abstention margin. S5 must therefore decide what a faithful replay means when
the notebook's margin path and the published margins disagree.

## Terms

- **Strict listing restriction.** If the listing admits exactly one category for
  the unit, the listing fixes it (`origen_M2 = "listado"`). If it admits more
  than one, the model chooses among the admitted categories
  (`origen_M2 = "modelo"`). Example: a unit with two admitted categories is
  model-chosen; a unit with one admitted category is list-fixed.
- **Frozen rule set.** The 15 context rules in the notebook's `REGLAS`, frozen on
  25 November 2026. They are binary features; S5 records them verbatim and does
  not edit them. Example: `sig_verbo` fires when the next token is a verb or an
  auxiliary.
- **Provenance.** `origen_M2` records whether the listing or the model fixed the
  category, and `revisar_categoria` flags categories with fewer than five
  training examples. The published traceability counts are
  91/58/34/33/20/43: 91 discourse labels, 58 list-fixed, 34 list-fixed correct,
  33 model-chosen, 20 model-chosen correct and 43 review flags.

## Approaches

| Approach | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|
| **A — faithful port, investigate the margin** | Keeps S5 an independent replay; the linguistic layer already matches; turns the margin mismatch into evidence rather than hiding it. | The published margins are not reproduced by the current notebook path; needs a version and fold investigation; the slice may end partial or fail. | No-abstention M2, `p_M2`, `origen_M2`, `revisar_categoria` and traceability are exact. Margins differ: prototype `0.20/0.15/0.15/0.15/0.20` vs published `0.15/0.10/0.20/0.10/0.20`; 27/439 `abstiene_M2` rows differ. |
| **B — use the published margins** | The abstention rows match by construction. | It is not a replay: it reads the answer from the published table and hides the margin bug. It changes what the result means and needs an ADR. | The published margins are 0.15/0.10/0.20/0.10/0.20. |
| **C — rule-first/M3** | The rules become the system, which is easier to explain. | It is a different system with no published M2 comparison; it does not satisfy S5's acceptance criterion. | No prototype; would need a new slice and a new baseline. |

## Recommendation

**A.** The linguistic layer is reproduced exactly; the only open piece is the
margin. A keeps the replay honest and makes the mismatch a finding. B copies the
published answer, and C replaces the slice instead of completing it.

## Chosen approach

**A — faithful port, with the margin learned by grouped cross-validation inside
training only.** The author chose A because it is the only option that tests
whether M2 can be rebuilt from the inputs. Using the published margins would
make the abstention rows true by construction and would not be a replay.

The margin rule stays as the notebook states it:

- `GroupKFold(n_splits=5)` on the training rows, grouped by `thread_id`;
- grid `0.00, 0.05, …, 0.30`;
- at most 20% abstention on the CV holdout;
- highest CV F1, with the smaller margin on a tie.

The test split is never used to choose the margin. Choosing it on test would use
the test labels to set the operating point, inflating the reported F1 and
coverage. Grouping by thread keeps a comment and its replies on one side, which
matches the thread-level split and prevents near-duplicate replies from leaking
into the holdout.

The 20% cap applies to the CV holdout, not to the test. The published seed 2
test abstention is 30.4%, which is an outcome of the fixed margin, not a
violation of the cap.

## What would change the decision

- If no training-only CV path reproduces the published margins, S5 reports the
  result as partial or fail with the evidence. The group may then accept the
  difference or change the protocol; a protocol change needs an ADR.
- If the rule set or its freeze date changes, stop and write an ADR. Recording
  the frozen rules is not a change; editing them is.
- If the frozen embedding model or the library versions cannot be reproduced,
  investigate or pin them before changing the acceptance. The local environment
  uses scikit-learn 1.9.1; the published notebook may have used an earlier
  `GroupKFold`.
- If the team wants a rule-first M3, that is a new slice, not S5.

## Sources

`doc/equipo11_B0_B1_M1_M2.ipynb` (M2 class, `REGLAS`, `anotar_gramatica`,
`elegir_margen_m`, cells 6, 14, 22 and 27); `doc/resultados_hito2.zip`;
[design note 0004](0004-m1-replay.md) and
[S4 report](../results/0004-m1-replay-diagnostics.md); Fuentes Rodríguez (2009);
`doc/Equipo11_Propuesta_v4_hito2.docx`.
