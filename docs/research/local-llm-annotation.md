# Local open LLM annotation — future work

**Status:** proposed future work, not a slice. No code exists yet.
**Date:** 2026-11-20
**Owner:** Till
**Related:** [input audit](../results/data-overview/inputs-audit.md),
[corpus overview](../results/data-overview/corpus-overview.md), the v4 proposal
(`doc/Equipo11_Propuesta_v4_hito2.docx`), R4/R5/R6.

## The observation

The deployed system is deliberately small: a frozen multilingual embedding plus a
logistic regression, trained on 80 positive labels. It reaches F1 0.483, coverage
0.407, precision 0.599. Part of that is a data limit, not a model limit: more
verified examples per category should help. A local open LLM can produce
candidate annotations at scale, and its output can be frozen as a static dataset
that the small model learns from — or the LLM itself can be the annotator.

This note records the design, the constraints it changes, and the measurement
that would have to happen before any of it is trusted.

## What changes

The team accepts a **local GPU**, an RTX 4070 (assume 12 GB; if it is the 8 GB
laptop variant, the model envelope shrinks to 7B at 4-bit). That loosens the
current CPU-only assumption in three ways:

| Requirement | As written | Under this note |
|---|---|---|
| R4, cost | $0 per comment, free Colab CPU | Still $0 marginal cost; hardware is owned, no API, no third party. Inference may use the local GPU. |
| R5, privacy | no comment text leaves the team | Unchanged and stronger: a local model keeps the text on the machine |
| R6, latency | p95 ≤ 1 s per comment on CPU | The current M2 stays CPU-only and compliant; a GPU annotator must be measured separately |

**This is a constraint change, not a settled decision.** R4 and R6 are verified on
CPU in the proposal. If a GPU-based component enters the course deliverable, the
team needs an ADR and, if the verification wording matters for grading,
confirmation from the instructor. If it stays future work beyond the course, no
ADR is needed yet.

## The proposal: a measured teacher, then a student

The dangerous version is "let an LLM label 20,000 candidates and train on them".
It fails because the new labels have no ground truth and because the 150-comment
human reference would be consumed in validating the teacher. The safe version
separates three roles:

```
1. New adjudicated sample        (human, development set)
2. Teacher: frozen open LLM      (measured on the new sample)
3. Student: small model          (trained on teacher labels, tested on the 150)
```

The 150-comment reference stays frozen and untouched as the final benchmark. The
teacher is validated and trained on a **new** human-adjudicated sample drawn from
the application corpus.

### Stage 0 — a new adjudicated sample (the expensive part)

- Draw about 300 candidates from the application corpus, stratified by unit and
  by M2 uncertainty (probability near 0.5) so that hard cases are represented.
- **Adjudicate every candidate in the sampled threads**, not only the connectors.
  This fixes the implicit-negative problem that currently makes 209 of 273
  reference candidates negative by assumption.
- Two annotators plus an adjudicator. Report agreement before adjudication; the
  pilot baseline is 50–59 % exact agreement when both annotate.
- No comment text in the repository; publish IDs, units, and labels only.

This is the only part that needs human time. Without it, the teacher cannot be
measured and the rest is speculation.

### Stage 1 — freeze the teacher exactly

Record and version, in one manifest:

- model name and exact weight hash (GGUF/AWQ artifact, not just the family name);
- quantization (Q4_K_M, Q5_K_M, …), because it changes outputs;
- prompt text, verbatim, with a version number;
- decoding: temperature 0 or a fixed seed, max tokens, stop sequences;
- the listing snapshot, because the allowed categories come from it.

Reproducibility here means "this frozen artifact and prompt produced this file",
not "the model can be re-run and will agree".

### Stage 2 — measure the teacher

Zero-shot, two-step, mirroring the project's own decomposition:

1. is this occurrence a discourse use? yes / no;
2. if yes, choose a category **only among the listing's allowed categories**.

The window is the same ±6 words, with the occurrence marked. The prompt carries
the Fuentes definitions, not pilot examples — with 5 seeds every pilot comment is
in some test eventually. Report precision, coverage, F1, abstention, and the
category distribution against the adjudicated sample, with a bootstrap interval
by thread.

**Gate A:** the teacher beats M2 on the adjudicated sample by a margin whose
interval excludes zero. If it does not, stop. Do not distil a teacher that is no
better than the student.

### Stage 3 — distil, or deploy the teacher

Two legitimate outcomes:

- **Distil.** Train the small model on teacher labels (optionally mixed with the
  human labels) and keep the CPU-deployable student. This preserves R4/R6 and
  keeps the frozen system small.
- **Deploy the teacher.** If the LLM is accurate and fast enough under batching,
  it becomes the system. This changes the architecture and needs an ADR.

**Gate B:** the student beats M2 on the frozen 150 without losing the rare
categories. **Gate C:** the chosen system meets p95 ≤ 1 s per comment on the
target hardware, measured, not assumed.

## Hardware and model envelope

12 GB of VRAM constrains the teacher:

| Size | 4-bit weights | Fits 12 GB? | Comment |
|---|---:|---|---|
| 7–8B | ~4–6 GB | comfortably | fastest; start here |
| 12–14B | ~7–9 GB | yes, tight with context | likely the best quality/speed point |
| 32B | ~18–20 GB | no | would need offloading and becomes slow |

Instruction-tuned, Spanish-capable open models in the 7–14B range are the
candidates to compare (for example Qwen3-8B, Llama-3.1-8B, Mistral-Nemo-12B,
Salamandra-7B; verify availability, licence, and Spanish quality when the
experiment starts). Do not assume one is best for Chilean Spanish and Fuentes'
categories; the adjudicated sample decides.

Throughput, as an order of magnitude: 19,741 candidates at ~50 output tokens is
about one million generated tokens. On a 4070 that is hours, not weeks, if the
prompt is batched; prompt processing is the larger cost but batches well. This is
what makes the idea practical now and was not true on CPU.

## What this would and would not fix

Would fix:

- the variance from 64 positive labels, if the teacher finds more examples;
- some rare-category starvation, if the teacher can recognise those categories;
- the implicit-negative assumption, through Stage 0's full adjudication.

Would not fix:

- **the 0.8 recall ceiling.** 16 of the 80 human labels are forms the listing
  never detects. No teacher can label what the detector never sees. That needs a
  separate open-set track: ask the LLM to propose candidate forms outside the
  listing, then have humans review them.
- the taxonomy's ambiguity. A teacher cannot be more consistent than the
  annotators it imitates.

## Risks

| Risk | Mitigation |
|---|---|
| Teacher is confidently wrong on Fuentes categories | Gate A on a human-adjudicated sample, before any training |
| Category collapse to frequent labels | Report per-category results; stratify the sample by unit |
| Prompt sensitivity | Freeze the prompt, version it, and report it verbatim |
| Quantization drift | Freeze the artifact hash; never mix quantizations in one result |
| Distillation amplifies teacher errors | Keep human labels in the mix; evaluate on human data only |
| GPU changes the verified constraints | ADR before it enters the deliverable; keep M2 as the CPU baseline |
| Annotation time | Stage 0 is the bottleneck; 300 candidates is days, not hours |

## Open questions

- Which model and quantization? Decide on the adjudicated sample, not by
  reputation.
- Is the RTX 4070 the 12 GB or the 8 GB variant? It changes the table above.
- Does the instructor accept a GPU-based component under R4/R6, or must the
  deliverable stay CPU-only with the LLM as an offline development tool?
- Who annotates and adjudicates Stage 0, and when? It is the only stage that
  cannot be automated.
- Does the new adjudicated sample replace the 150 as the evaluation set, or
  complement it? Replacing it would break comparability with the published
  results; complementing it is the safer default.

## References

- Fuentes Rodríguez (2009), the source of the category inventory.
- The project's v4 proposal and the input audit for the counts above.
- llama.cpp/Ollama and vLLM documentation for the serving and quantization
  details; pin versions when the experiment starts.
