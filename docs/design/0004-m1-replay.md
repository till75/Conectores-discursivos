# Design note 0004 — M1 replay

- **Status:** chosen
- **Date:** 2026-11-26
- **Slice:** S4 — M1 replay
- **Related:** [brief](../00-brief.md), [plan](../plan.md),
  [S2 spec](../specs/0002-candidate-replay.md),
  [S3 report](../results/0003-baseline-replay-diagnostics.md),
  [candidate window](../learn/01-candidate-window.md),
  [TF-IDF](../learn/02-tf-idf.md),
  [window embeddings](../learn/03-window-embeddings.md)

## Problem

M1 is the trained model behind both M1 and M2. S4 rebuilds it from the S2
candidates and the five frozen splits: the ±6-word window, the six flags, the
three TF-IDF blocks, the frozen embedding block, the two-step logistic
regression and the margin learned by grouped cross-validation inside training.
The caller gets M1 labels, probabilities, margins and metrics without reading
`predicciones_test.csv`. Reproducing M1 proves the features and the training
protocol before S5 adds M2's rules.

## Terms

- **Candidate window.** The six words before the match, the `[[...]]`-marked
  match and the six words after it, plus six flags for punctuation, position
  and reply. Example: a `mientras` occurrence after `dólares,` and a newline;
  the full example is in [01 — Candidate window](../learn/01-candidate-window.md).
- **Two-step model.** Step 1 decides discourse use versus `NO_DISCURSIVO`;
  step 2 chooses the category among the labels the listing allows and the
  labels seen in training. Example: step 1 says discourse, step 2 chooses
  `OP:MODAL`.
- **Abstention margin.** A band around probability 0.5: if `|p − 0.5| < margin`,
  predict `NO_DISCURSIVO` and count an abstention. The margin is chosen by
  five-fold grouped cross-validation inside training only, with at most 20%
  abstention. Example: margin 0.10 abstains on probabilities between 0.40 and
  0.60.

## Approaches

| Approach | What it makes easy | What it makes hard | Evidence |
|---|---|---|---|
| **A — faithful port with the frozen embeddings** | Exact reproduction; supports S5; no protocol change. | Needs the embedding extra and the frozen model; CPU time; exact feature order, row order and hyperparameters. | Scratch prototype: 0/439 label mismatches, max probability difference 3.6e-7, exact F1, exact margins 0.10/0.10/0.10/0.05/0.15, exact abstention and M1-with-abstention rows. |
| **B — no embeddings** | No torch or model download; faster; simpler. | Does not reproduce the published M1; changes what the result means; S5 inherits the difference; needs an ADR and a new acceptance. | Scratch prototype: 62/439 label mismatches; seed 0 F1 0.462 instead of 0.333; margins differ for seeds 3 and 4. |
| **C — replay the published probabilities** | Exact metrics with little work. | It is S1 again, not a model replay; it proves nothing about the features or training and cannot support S5 or the application corpus. | S1 already reproduces the metric rows this way. |

## Recommendation

**A.** The prototype reproduces every published M1 label, every margin and every
metric; the remaining probability difference is floating-point noise. B would
change the published result, and C duplicates S1 without proving the model.

## Chosen approach

**A — faithful port with the frozen embeddings.** The author chose it because
the feature extractor is part of the original design: it takes the window's
words and the brackets marking the match, and turns that string into a
384-element vector that represents the meaning and makes the window comparable
to other windows semantically. Without embeddings, that part of the original
project would not be reproduced faithfully.

## What would change the decision

- If the frozen embedding model cannot be loaded or the exact predictions cannot
  be reproduced, stop and investigate versions before changing the acceptance.
  Dropping the embeddings changes what the result means and needs an ADR.
- If the `inicio_oracion` newline rule is changed, M1 and M2 change and the
  published numbers are no longer comparable; that needs an ADR. The question
  is recorded in `docs/state.md` and
  [01 — Candidate window](../learn/01-candidate-window.md).
- If the local library versions drift from the published environment, pin them
  or re-freeze the comparison before claiming reproduction.

## Sources

`doc/equipo11_B0_B1_M1_M2.ipynb` (`M1`, `elegir_margen_m`, `embedder`);
`doc/resultados_hito2.zip`; the S2 candidate contract and the S3 baseline
report; Fuentes Rodríguez (2009); `doc/Equipo11_Propuesta_v4_hito2.docx`.
