# Onboarding diagnostic report

**Slice:** S0 — onboarding and shared vocabulary
**Date:** 2026-11-20
**Status:** pass
**Spec:** `.opencode/commands/onboard.md` (the command is the contract for this slice)
**Commits:** pending
**Report owner:** Till

## Intended goal

Give a mid-project contributor the vocabulary and the evidence to explain the
project, the experiment, and one published number without reading code. The
observable outcome is the document `docs/00-onboarding.md` plus a demonstrated
understanding of three ideas: the occurrence as the unit, the cost of a false
negative, and the reason the split is by thread.

## Pass/fail criteria

| Criterion | Evidence | Result |
|---|---|---|
| The author can explain why one comment can be several examples | Answer 1: one comment can contain zero to several list forms; each form produces an example. | pass |
| The author can explain what a false negative costs | After correction: a false negative is invisible and leaves the corpus without review; a false alarm costs only review time. | pass |
| The author can explain why the split is by thread | After correction: replies share topic and wording with their parent, so a comment split would leak near-duplicates into test. | pass |
| The shared vocabulary exists | `docs/00-onboarding.md` written against the v4 proposal and the input audit. | pass |
| The document states the published number honestly | Section 3 gives the mean, the per-seed range, the interval caveat, the abstention overrun in seeds 2 and 4, and the 209 implicit negatives. | pass |
| No comment text or `author_hash` is committed | Document quotes only list forms (`ya`, `hasta`, `solo`) and labels. | pass |
| The suite and lint are clean | `pytest` 1 passed; `ruff check .` clean. | pass |

## What was built

`docs/00-onboarding.md`: the story in order, the five ideas, the reading of
0.483, the two flows as Mermaid diagrams, the glossary, the artefact map, the
data discrepancies, and the open questions for the brief. No production code.

## Verification commands

| Command | Result |
|---|---|
| `.\.venv\Scripts\python.exe -m pytest` | 1 passed |
| `.\.venv\Scripts\python.exe -m ruff check .` | All checks passed |
| `git status --short` | `docs/00-onboarding.md` and this report added |

## Diagnostic evidence

- **Reference set:** 150 rows, 65 with a label, 96 spans, 76 distinct units (67
  lowercase), 12 labels, 16 CSL. The reference covers one video.
- **Candidates:** 273, of which 64 positive and 209 implicit negatives; 16
  reference labels are not detected; 8 matches fall inside CSL zones.
- **Published table:** M2 mean F1 0.483 (range 0.432–0.545); B1 0.328;
  M2 − B1 +0.155; the interval excludes zero in 1 of 5 seeds. M2 − M1 +0.123;
  the interval excludes zero in 2 of 5 seeds.
- **Coverage:** 0.407, counting the 16 undetected labels; the hard ceiling is 0.8.
- **Abstention:** mean 15.6%; seeds 2 (30.4%) and 4 (21.3%) exceed the 20% cap.
- **Latency:** p95 0.081 s on CPU.
- **Traceability:** 91 discourse labels; 58 fixed by the list (34 correct), 33
  chosen by the model (20 correct); 43 marked "revisar categoría".
- **Seeds:** 0–4. Each seed has its own frozen test IDs and hash in
  `resultados/publicable/test_congelado/hashes.json`.
- **Application corpus:** 10,505 comments, 6,264 threads, 20 videos; 19,741
  candidates on raw text and 20,097 on normalised text. The v4's 2,000-comment
  sample has 3,655 candidates and 22.5% abstention.

Caveats: the five seeds are repeated splits of the same 150 rows, not
independent samples. The application corpus has no reference labels. The
document's diagrams were inspected in source; the light and dark Markdown
previews still need a visual check.

## Privacy check

The document contains no comment text, no context window, and no `author_hash`.
It quotes only list forms and category labels. The privacy test is not yet
written; this slice adds no code that could leak text.

## Limitations and caveats

- The onboarding check happened in chat; the answers are summarised here, not
  reproduced verbatim.
- The document repeats the proposal's numbers. It does not yet prove they
  reproduce locally; that is the first technical slice's job.
- The v4 proposal's "705 unidades" and the audit's "614 formas" are not
  reconciled. The document records both.
- The "150 comments" wording hides the 65 labelled rows. The document states both.
- The 209 implicit negatives are a serious caveat for precision and recall. The
  document records it; the brief should decide whether to audit them.
- The Mermaid diagrams have not been rendered in the console or in light/dark
  previews. Treat a raw HTML label or a clipped node as a defect.
- The application corpus's 2,000-comment results are not in
  `resultados_hito2.zip`; the document flags the missing artifacts.

## Decision

**Pass.** The author demonstrated the three ideas after two corrections, and the
shared vocabulary exists against the current v4 evidence. The slice is ready to
move on to the brief or to the first technical slice. The author chooses which.

## Follow-up

1. Choose the next step: `/grill` on the v4 proposal to write
   `docs/00-brief.md`, or a technical slice (A metric replay, B candidate replay,
   C baseline replay, D model replay, E embedding ablation, F M3 rules).
2. Run `/plan` to order the slices by risk and record the 21/25/27–28 November
   gates.
3. Run `/learn` on the chosen slice before `/spec`.
