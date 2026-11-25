# Baseline replay diagnostic report

**Slice:** S3 — baseline replay
**Date:** 2026-11-25
**Status:** in progress — worked examples added at spec approval; pass/fail evidence and decision pending
**Spec:** [0003-baseline-replay.md](../specs/0003-baseline-replay.md)
**Commits:** pending
**Report owner:** Till

## Intended goal

Rebuild B0 and B1 from the S2 candidates, the listing and the five frozen test
splits, without reading `predicciones_test.csv` to build them. The rebuilt B0
and B1 columns must match the 439 published test rows, and the ten per-seed
metric rows and the two summary rows must match the published tables to three
decimals.

## Worked examples

**Privacy exception (documentation only).** Till granted an exception on
2026-11-25 to reproduce the six short fragments below so that the B0 and B1
rules can be understood. The exception is limited to this report and extends
the S2 exception. It does not change R5 for the corpus, the application data,
the code, the tests, the commit messages or any other artifact. The fragments
contain no `@name` mention and no `author_hash`. Till will raise the exception
with the team; until the team confirms it, treat it as provisional.

`[[...]]` marks the candidate form in its sentence. Each block quotes the whole
comment when it is short, or the sentence containing the form when the comment
is longer.

### B0 — the listing's first label

B0 does not look at the context or the gold label. It takes the first label
that the listing gives for the form.

1. **A form with one label.**

   > Pero el alza de los pasajes en regiones va, [[ya]] que solo estancarán en la RM

   The listing gives `ya` only `OP:MODAL`, so B0 predicts `OP:MODAL`. The gold
   label here is `NO_DISCURSIVO`: this is a B0 false positive.

2. **A form with five labels.**

   > [[Bueno]], si hubieran dejado dinero quizás esto no estaría pasando

   The listing gives `bueno` five labels in this order:
   `CON:CONTINUATIVO`, `CON:CIERRE`, `CON:INTERACTIVO`,
   `CON:REFORMULATIVOS`, `OP:MODAL`. B0 takes the first,
   `CON:CONTINUATIVO`; the gold label is `CON:INTERACTIVO`.

3. **A form with four labels.**

   > si Boric robó la plata, [[entonces]], quítensela, y así la plata viene de vuelta

   The listing gives `entonces` four labels in this order:
   `CON:CONCLUSIVO`, `CON:CONSECUTIVO`, `CON:CONTINUATIVO`,
   `CON:TEMPORAL`. B0 takes the first, `CON:CONCLUSIVO`; the gold label is
   `CON:CONSECUTIVO`.

### B1 — the training majority per form

B1 counts the gold labels of the form in the training candidates only. The test
form itself is never used to choose its label.

1. **A clear majority, seed 0.**

   > Pero el alza de los pasajes en regiones va, [[ya]] que solo estancarán en la RM

   In seed 0's training, `ya` has 15 `NO_DISCURSIVO` and 1 `OP:MODAL`. B1
   predicts `NO_DISCURSIVO`, which is also the gold label. The same occurrence
   shows the contrast with B0: B0 predicts `OP:MODAL`, B1 predicts
   `NO_DISCURSIVO`.

2. **A tie, seed 2.**

   > [[Bueno]], ahora les toca vivir del alza, esto es sin llorar.

   In seed 2's training, `bueno` has two `CON:INTERACTIVO` and two `OP:MODAL`.
   The tie goes to `CON:INTERACTIVO`, the label that appears first in the
   training rows. B1 predicts `CON:INTERACTIVO`; the gold label is
   `CON:CIERRE`.

3. **An unseen form, seed 1.**

   > Esto [[definitivamente]] es una bomba de tiempo para que reviente. 😡

   `definitivamente` never appears in seed 1's training. B1 falls back to the
   global training majority, `NO_DISCURSIVO` (135 of the training candidates),
   and predicts `NO_DISCURSIVO`. The gold label is `OP:ENUNCIATIVO`; B0 gets
   this one right because the listing's first label for the form is
   `OP:ENUNCIATIVO`.

## Pass/fail criteria

To be completed after the TDD cycles.

## Verification commands

To be completed after the TDD cycles.

## Diagnostic evidence

To be completed after the TDD cycles.

## Privacy check

Apart from the six fragments in the documented exception above, this slice
writes no comment text. The prediction frame carries IDs, forms, offsets, gold
labels and B0/B1; it carries no `texto`, `ventana`, `author_hash` or `@name`.
The integration test reads the ignored `doc/` inputs and writes only to
`tmp_path`.

## Limitations and caveats

To be completed after the TDD cycles.

## Decision

To be completed after the TDD cycles.

## Follow-up

To be completed after the TDD cycles.
