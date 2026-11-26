# 01 — The candidate window and the six flags

**Slice:** S4 — M1 replay
**Related:** [02 — TF-IDF](02-tf-idf.md),
[03 — Window embeddings](03-window-embeddings.md),
[S2 — Candidate report](../results/0002-candidate-replay-diagnostics.md)

**Privacy exception (documentation only).** This page contains one short
fragment requested by Till on 2026-11-26; the exception is limited to
`docs/learn/`. See the [index](README.md#privacy).

## What the window is

A candidate is one listing match in one comment. M1 does not read the whole
comment; it reads a **window** around the match:

- the six words before the match,
- the match itself, marked with `[[...]]`,
- the six words after the match.

The window is built with `left.split()[-6:]`, the marker, and
`right.split()[:6]`. Whitespace is collapsed to single spaces. The window is
therefore about a dozen words (more when the match is multi-word), far below
the embedding model's 128-token limit.

The six **flags** are separate booleans computed on the raw left and right
text, before whitespace is collapsed. They tell the model what the normalised
window can no longer show: punctuation, position in the comment, position in
the sentence, and whether the comment is a reply.

## A real example

The full comment, for context:

```text
Vender Enap, que tuvo ganancias de 850 millones de dólares,
mientras tenemos uno de los combustibles más caros del mundo
```

The window:

```text
ganancias de 850 millones de dólares, [[mientras]] tenemos uno de los combustibles más
```

Broken down:

- left six: `ganancias` / `de` / `850` / `millones` / `de` / `dólares,`
- match: `[[mientras]]`
- right six: `tenemos` / `uno` / `de` / `los` / `combustibles` / `más`

The full comment has 20 words; the window drops `Vender Enap, que tuvo` on the
left and `caros del mundo` on the right.

## The six flags for this occurrence

| Flag | Value | What it checks | Why it has this value here |
|---|---|---|---|
| `coma_antes` | **True** | `[,;:]\s*$` on the left text | the left ends with `dólares,` plus a newline |
| `coma_despues` | **False** | `\s*[,;:]` at the start of the right text | the right starts with `tenemos` |
| `inicio_comentario` | **False** | the left text is blank | there is text before the match |
| `inicio_oracion` | **True** | a sentence boundary at the end of the left text | the newline after the comma counts as a boundary |
| `fin_enunciado` | **False** | punctuation or end-of-text at the start of the right text | the right continues with `tenemos` |
| `is_reply` | **True** | the reference's reply flag | this comment is a reply |

There is an important subtlety in this example. The window string collapses
whitespace, so the newline after `dólares,` disappears from `ventana`; but
`inicio_oracion` is computed on the raw left text, where the newline is still
present. That is why the window looks mid-sentence while the flag says it
starts a sentence: the flags preserve information the normalised window loses.

## The newline question

`inicio_oracion` currently treats `\n` as a sentence boundary. A phrase can
span lines, so this may be wrong: a line break is not necessarily the start of
a new sentence.

S4 keeps the frozen rule so the published M1 and M2 numbers stay comparable.
Changing it would change the flag, the M1/M2 predictions and the published
tables, so it needs an ADR and a decision by the group. The question is
recorded in `docs/state.md`.

## How M1 uses the window

The window becomes five feature blocks:

- word TF-IDF (1–2 grams) of `ventana`;
- character TF-IDF (`char_wb`, 2–5 grams);
- unit TF-IDF of `unidad`;
- the six flags as six binary features;
- the 384-dimensional embedding of `ventana`.

See [02 — TF-IDF](02-tf-idf.md) for the first three blocks and
[03 — Window embeddings](03-window-embeddings.md) for the last one.
