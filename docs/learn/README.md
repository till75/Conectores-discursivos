# Learn notes

Concept notes from the `/learn` sessions. They explain the ideas behind a
slice before the spec fixes the contract. The spec and the slice report remain
the authority; these pages are the teaching material.

## Start here

| Note | What it explains | Slice |
|---|---|---|
| [01 — Candidate window](01-candidate-window.md) | The ±6-word window, the `[[...]]` marker and the six flags. | S4 |
| [02 — TF-IDF](02-tf-idf.md) | Term frequency, inverse document frequency, n-grams, L2 normalisation and the three TF-IDF blocks. | S4 |
| [03 — Window embeddings](03-window-embeddings.md) | What a 384-dimensional window embedding is and how M1 uses it. | S4 |
| [S3 — B0 versus B1](../results/0003-baseline-replay-diagnostics.md#the-two-rules-at-a-glance) | The baseline flowchart and six worked examples. | S3 |
| [S2 — Candidate categories](../results/0002-candidate-replay-diagnostics.md#worked-examples) | One real example of each candidate count. | S2 |

## How to use these notes

Read the note for the concept you are about to specify or review. The note
explains; the spec states the contract; the report records the evidence. When a
term changes, update the note and `docs/00-onboarding.md` in the same commit.

The notes use the project's markers: `[[...]]` marks the piece under
discussion, and `<<...>>` marks a skipped second piece. Domain labels keep their
Spanish form (`CON:ADICIÓN`, `OP:MODAL`, `NO_DISCURSIVO`).

## Privacy

These pages contain the teaching fragments requested by Till on 2026-11-26.
The exception is limited to `docs/learn/`; it does not change R5 for the
corpus, the application data, the code, the tests, the commit messages or any
other artifact. The fragments contain no `@name` mention and no `author_hash`.
Till will raise the exception with the team; until the team confirms it, treat
it as provisional.
