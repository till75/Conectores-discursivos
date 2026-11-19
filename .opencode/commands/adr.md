---
description: Record an architecture decision and its trade-offs
---

Record an architecture decision: $ARGUMENTS

- Read the existing `docs/adr/` files first and take the next number. Do not
  reopen a settled decision without naming the ADR it supersedes.
- Confirm the decision has actually been made. If it is still open, record the
  options and stop; never mark a proposal as accepted.
- Write `docs/adr/NNNN-<slug>.md`:
  - **Status**: proposed, accepted, or superseded by NNNN.
  - **Context**: the forces, constraints, and trigger for deciding now.
  - **Decision**: one paragraph in the active voice.
  - **Consequences**: what gets easier, what gets harder, and the debt accepted.
  - **Alternatives rejected**: each option and why it lost.
- ADRs are immutable. Supersede an old one with a new ADR; do not rewrite
  history.
- Link the ADR from `docs/architecture.md` if that file exists.

Any decision that changes what a result means, or whether two runs are
comparable, requires an ADR. In this project that includes: the train/test
split, the seed set, the abstention threshold, the rule set and its freeze date,
the metrics, the embedding model, and what may be published under R5.

Do not write production code. If the decision changes the plan, say which
slices are affected.
