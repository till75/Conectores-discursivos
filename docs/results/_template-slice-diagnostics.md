# <Slice> diagnostic report

**Slice:** <ID> — <name>
**Date:** YYYY-MM-DD
**Status:** pass / fail / partial
**Spec:** [<spec>](<path>)
**Commits:** <hashes>
**Report owner:** <author>

## Intended goal

State the observable outcome the slice was meant to achieve. Link the spec and
the design note or ADR that fixed the approach.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| <criterion from the spec> | <test, command, artifact, or measurement> | pass / fail / partial |

## What was built

Summarise the behaviour, interfaces, and files that changed. Keep this short;
the spec and architecture notes remain the contract.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | <counts and result> |
| `.\.venv\Scripts\python.exe -m ruff check .` | <result> |
| <slow or diagnostic command> | <result> |

## Diagnostic evidence

Record the measurements that justify the decision. Always include:

- seeds used and how many runs;
- the frozen test hash and the number of test threads and candidates;
- the abstention rate and the «revisar categoría» rate;
- F1 of the full label (primary), F1 of discourse use, and macro CON/OP F1;
- coverage, counting the reference labels the listing never detects;
- how many categories were fixed by the listing versus chosen by the model;
- the bootstrap interval by thread when comparing two systems.

Caveats: small samples per category (7 of 12 categories have three or fewer
examples in the pilot), and no reference labels for the application corpus.

## Privacy check

State the result of the R5 check: zero `@name` mentions, no comment text, no
`author_hash` values in the committed tree or artifacts.

## Limitations and caveats

List what the evidence does not prove, known weak baselines, deterministic
repetition, single-seed results, and any deferred work.

## Decision

State pass, fail, or partial. Explain why the slice is ready to move on, or what
blocks it. If partial, name the follow-up slice or condition.

## Follow-up

List the next slice, open questions, and any artifacts that should be revisited.
