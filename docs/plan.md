# Plan — vertical slices

**Status:** active
**Source:** `docs/00-brief.md` (approved 20 November 2026)
**Current state:** S0–S6 are implemented. S1–S6 reproduce the published metric
table, the candidates, the baselines, M1, M2 and the publication pack; the S6
pack is ready for approval. S1 verifies the five frozen hashes.

## Ordering principle

The slice that could invalidate the design goes first. Candidate construction
is the foundation: if the 273 candidates cannot be rebuilt from the reference
and the listing, the S1 undetected-label parser is wrong and every downstream
count shifts. Baselines come next because they are cheap and they exercise the
split and the metrics with real labels. The models follow, cheapest first.

Every slice is vertical: tests, code, docs, and one commit. Every slice leaves
the project in a working state. Every slice goes through `/spec-review` before
`/tdd`. Slices marked `/learn` introduce a new approach and start with a design
note and an explicit choice.

## Slices

| ID | Slice | Outcome | Acceptance criterion | Files touched | Tests added | Size | `/learn` | ADR |
|---|---|---|---|---|---|---|---|---|
| S2 | Candidate replay | Rebuild the 273 candidates from the reference and the listing | 284 raw matches → 8 CSL matches and 3 second pieces excluded → 273 candidates; 64 positive; 209 implicit negatives; 16 undetected labels; per-seed candidate counts match the published diagnostics | `src/conectores/candidates.py`, `tests/test_candidates.py`, `tests/test_integration.py` | Unit: form matching, CSL exclusion, second-piece exclusion, positive/negative classification. Slow: match the published 273/64/209/16/8/3 | M | yes | no |
| S3 | Baseline replay | Rebuild B0 and B1 from the reference and the listing | B0 and B1 predictions and metrics match the published per-seed rows and the summary at three decimals | `src/conectores/baselines.py`, `tests/test_baselines.py`, `tests/test_integration.py` | Unit: B0 first-category rule, B1 most-frequent label, unseen form fallback. Slow: published B0/B1 rows | S | no | no |
| S4 | M1 replay | Rebuild M1: two-step logistic regression on context features | M1 predictions and metrics match the published per-seed rows and the summary at three decimals; the margin is learned inside training by grouped CV | `src/conectores/features.py`, `src/conectores/models.py`, `tests/test_features.py`, `tests/test_models.py`, `tests/test_integration.py` | Unit: window features, punctuation, position, embedding shape, two-step fit. Slow: published M1 rows | L | yes | no |
| S5 | M2 replay | Rebuild M2: M1 plus the list restriction, the frozen rules, POS, rare-category flag, and provenance | M2 predictions and metrics match the published per-seed rows, the summary, and the traceability counts (91/58/34/33/20/43) at three decimals | `src/conectores/rules.py`, `src/conectores/models.py`, `tests/test_rules.py`, `tests/test_integration.py` | Unit: each frozen rule, list restriction, POS rule, rare-category flag, provenance. Slow: published M2 rows and traceability | L | yes | yes, if the rule set changes |
| S6 | Publication pack | End-to-end run, data card, model card, reproduction commands | One command rebuilds the published table from the raw inputs; the data card and model card describe the data and the systems; the privacy check reports zero `@name` | `src/conectores/pipeline.py`, `src/conectores/metrics.py`, `docs/data-card.md`, `docs/model-card.md`, `README.md`, `tests/test_pipeline.py`, `tests/test_docs.py`, `tests/test_integration.py` | Unit: frame, composition, writer, CLI, prediction/privacy, docs. Slow: seven-file end-to-end pack. Privacy: zero `@name` | M | no | no |

## Slice detail

### S2 — candidate replay

**Why first:** the candidate set is the unit every later metric depends on.
The S1 replay reconstructed the 16 undetected labels with a minimal parser; S2
replaces that parser with the full candidate construction. If the counts
disagree, S1's coverage and F1 are wrong and the brief's data table needs
correcting.

**Approach:** read the reference annotation, extract the spans, match the 614
listing forms, remove the 8 matches inside CSL zones and the 3 second pieces,
and classify each candidate as positive or implicit negative. Compare the
per-seed candidate counts and the undetected totals against the published
diagnostics.

**Open question:** the implicit negatives are assumed reviewed and rejected.
S2 records the assumption; it does not resolve it.

### S3 — baseline replay

**Why next:** B0 and B1 are simple and they validate the split end to end.
They also give the floor the models must beat.

**Approach:** B0 labels every list match with the list's first category and
ignores context. B1 labels each form with its most frequent label in training.
Unseen forms fall back to the listing's first category. Compare against the
published B0 and B1 rows.

### S4 — M1 replay

**Design note:** [0004 — M1 replay](design/0004-m1-replay.md).

**Why:** M1 is the trained model behind both M1 and M2. Reproducing it proves
the features and the training protocol before the rules are added.

**Approach:** build the ±6-word window, punctuation, position, and embedding
features; fit the two-step logistic regression; choose the abstention margin by
grouped cross-validation inside training only. Compare against the published M1
rows. The embedding model is frozen; the seed set is 0–4.

### S5 — M2 replay

**Why:** M2 is the headline system. Its extra pieces are the list restriction,
the hand-written rules, POS features, the rare-category flag, and provenance.

**Approach:** layer the restriction and the rules on M1. Record the rule set
verbatim with its freeze date. Compare against the published M2 rows and the
traceability counts. Any change to the rule set needs an ADR before code.

**ADR flag:** the frozen rule set and its freeze date are protocol. Recording
them is not a change; editing them is. If the notebook's rules cannot be
reproduced exactly, stop and write an ADR.

### S6 — publication pack

**Why last:** it depends on S2–S5. It turns the pipeline into one reproducible
command and writes the data card and the model card for the 3–4 December
deliverables.

**Approach:** one command reads the raw inputs, runs candidates, baselines, M1,
and M2, and writes the tables and the report. The data card states the corpus,
the split, the reference, and the privacy controls. The model card states the
systems, the features, the metrics, and the limitations. The privacy check
reports zero `@name`.

## Milestone gates

| Gate | Date | What it needs | Status |
|---|---|---|---|
| Intermediate presentation | 20 Nov | Project framing and first results | S1 evidence is available |
| Benchmark | 21 Nov | The published comparison table | S1 reproduces it with zero deviations |
| Frozen rules | 25 Nov | The M2 rule set recorded and frozen | S5 records it; no edit without an ADR |
| Frozen test | 27–28 Nov | The five test IDs and hashes unchanged | S1 verifies all five hashes |
| Repository, data card, model card, defence | 3–4 Dec | S2–S6 complete and documented | S6 implemented; pending approval |

The benchmark gate is already covered by S1: the published table is
reproduced from the raw predictions. S2–S5 extend the evidence from the
predictions to the full pipeline.

## Deliberately deferred

- **Application corpus run.** The 2,000-comment sample and the 19,741/20,097
  candidates are deferred until the pilot pipeline is validated. The brief
  records both counts; the application slice will choose.
- **Implicit-negative audit.** The 20-candidate check is deferred; the caveat
  stays in every report.
- **Local open LLM annotator.** Future work; needs an ADR before it enters the
  plan.
- **548-vs-550 reconciliation.** The brief records both; the team confirms the
  split.
- **F2 and coverage-at-budget.** Secondary metrics; no slice yet.
- **The 2,000-comment sample's missing artifacts.** Flagged; not reproduced.

## Approval

Approve the plan, or correct the slice order and the scope.
