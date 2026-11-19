---
description: Turn an approved brief into vertical slices
---

Read `docs/00-brief.md` and write `docs/plan.md`.

- Slice **vertically**: each slice is test + code + docs + one commit, and
  leaves the project in a working state.
- Order by risk. The slice that could invalidate the design goes first.
- For each slice record: ID, outcome, acceptance criterion, files touched,
  tests added, rough size.
- For each slice, say whether it needs `/learn` (new concepts or unsettled
  approach) before `/spec`; every slice goes through `/spec-review` before
  `/tdd`.
- Flag anything that needs an ADR before implementation. In this project that
  includes the split, the seeds, the abstention threshold, the rule set and its
  freeze date, the metrics, and any change to what may be published under R5.
- Keep the milestone gates from the proposal visible: 20 Nov intermediate
  presentation, 21 Nov benchmark, 25 Nov frozen rules, 27–28 Nov frozen test,
  3–4 Dec repository, data card, model card, and defence.
- Call out what you deliberately deferred.

Do not write production code in this command.
