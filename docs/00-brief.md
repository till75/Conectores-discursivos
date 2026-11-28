# Project brief — Conectores discursivos

**Status:** approved 20 November 2026
**Slice at approval:** S2 — candidate replay
**Current slice:** S6 — publication pack (complete; see `docs/plan.md` and
`docs/state.md`)
**Sources:** `doc/Equipo11_Propuesta_v4_hito2.docx`, `docs/00-onboarding.md`,
`docs/results/0001-metric-replay-diagnostics.md`, `doc/resultados_hito2.zip`

## Purpose

Reproduce the published discourse-connector pipeline from the same
preconditions, so the team can trust the numbers, inspect every decision, and
extend the system without inventing data. The unit is the occurrence: one
match of a list form in one comment. A comment can contain zero, one, or
several candidates.

The project annotates Chilean Spanish YouTube comments following Fuentes
Rodríguez (2009), for Fondecyt 11260185. The same word can be a discourse
marker or an ordinary word; the system must decide, for each occurrence,
whether it has a discourse use and which category it carries.

## Audience

The team's annotator first. The review queue, abstention, and traceability are
optimised for the person who reviews candidates. Fondecyt researchers are the
second audience; external reuse is a later concern.

## Success criteria

| Criterion | Observable evidence |
|---|---|
| The published metric table is reproduced | S1 replay: 30 system rows, 6 summary rows, 15 intervals, 0 deviations, 5 hashes verified |
| The candidate set is reproduced | 273 candidates from 284 raw matches after 8 CSL matches and 3 second pieces; 64 positive; 209 implicit negatives; 16 undetected labels |
| The baselines and models are reproduced | B0, B1, M1, M2 per seed, with the published means and intervals |
| The protocol is unchanged | Five seeds 0–4, thread split, frozen test IDs and hashes, threshold learned inside training |
| The outputs are private | No comment text, no `author_hash`, no `@name`; IDs, list forms, labels, counts, metrics only |

The primary metric is full-label F1. F2 and coverage are secondary: the false
negative is the expensive error because it is invisible. The headline target is
M2 ≥ B1 + 0.10 F1; the published mean is +0.155, but the 95% interval excludes
zero in only 1 of 5 seeds. The brief does not claim significance.

## Scope

In scope for this repository:

- reproduce the published metric table (done in S1);
- reproduce candidate construction from the reference and the listing;
- reproduce B0 and B1 baselines;
- reproduce M1 and M2, including the list restriction, context rules, POS
  features, rare-category flag, and provenance;
- reproduce the five-seed split, frozen tests, bootstrap intervals, and
  traceability counts;
- produce diagnostics and a slice report for each vertical slice.

## Non-goals

- New annotation: the 150-comment reference is closed.
- Changing the split, seeds, threshold, frozen rules, or metrics without an ADR.
- Tuning rules on pilot comments. Rules come from the grammar and Fuentes
  Rodríguez (2009); with five seeds every comment is in some test.
- Applying the system to the full application corpus in this plan. The
  application run is deferred until the pilot pipeline is validated.
- Replacing the models with an LLM in this plan. The local open LLM annotator
  is future work and needs an ADR.
- Committing raw comment text, context windows, or `author_hash` values.

## Constraints

| Constraint | Detail |
|---|---|
| Environment | Windows, PowerShell; Python 3.14 in `.venv`; CPU-only |
| Cost | $0 per comment; no paid API; local models only |
| Privacy | R5: no comment text, no `author_hash`, no usernames in the repository |
| Evidence | `doc/` is read-only; its corpora are gitignored |
| Reproducibility | Fixed seeds 0–4; frozen test IDs and hashes; deterministic replay |
| Protocol changes | Any change to split, seeds, threshold, rules, or metrics needs an ADR |
| Rules | Frozen on 25 November; no rule written by looking at pilot comments |
| Milestones | 20 Nov presentation; 21 Nov benchmark; 25 Nov M3 rules; 27–28 Nov final evaluation; 3–4 Dec repository, data card, model card, defence |

## Data

| Fact | Value |
|---|---|
| Reference comments reviewed | 150 |
| Reference rows carrying a label | 65 |
| Labels in the reference | 96 in 12 categories |
| Evaluable labels after CSL | 80 |
| Undetected labels (listing cannot see) | 16 |
| CSL constructions | 16 |
| Raw listing matches | 284 |
| CSL matches excluded | 8 |
| Second pieces excluded | 3 |
| Candidates | 273 |
| Positive candidates | 64 |
| Implicit negatives | 209 |
| Listing entries | 705 |
| Distinct raw listing strings | 699 |
| Distinct list forms | 614 |
| Single-category forms | 548 |
| Multi-category forms | 66 |
| Polyfunctional rows | 155 |
| Seeds | 0–4 |
| Test split | 30% by thread; frozen test IDs and hashes |

The 705/699/614 relationship is settled: 705 entries, 699 distinct raw strings,
614 distinct forms after normalising sense numbers. The 6 repeated raw strings
account for 705 → 699. The 548/66 split is the team's count; the CSV's category
grouping gives 550 single-category forms. The 2-form difference is an
assumption to confirm, not a blocker.

## Failure modes

| Failure | Cost | Control |
|---|---|---|
| False negative | Invisible connector leaves the corpus | Coverage metric; report false negatives; abstain only near 0.5 |
| False positive | Annotator loses time | Precision metric; review queue; provenance |
| Thread leakage | Test measures memorised context | Split by thread; bootstrap by thread |
| Implicit negatives | Precision/recall depend on unreviewed candidates | Record the caveat; defer the 20-candidate audit |
| CSL confusion | Semi-free constructions inflate errors | Exclude 16 CSL constructions and their 8 list matches; report them separately |
| Unseen forms | Listing cannot propose 16 labels | Count them as missed; coverage denominator includes them |
| Small categories | Per-category F1 is unstable | Report macro CON/OP; flag categories with <5 examples |
| 705/614 confusion | Wrong denominator in reports | Use 614 forms; record 705/699 as entry counts |
| 548/550 confusion | Wrong single-category count | Confirm the 2-form difference; do not hide it |

## Requirements

| ID | Requirement | Target |
|---|---|---|
| R1 | Detect candidates | All 614 forms in a test text; occurrence-level candidates |
| R2 | Classify | Full-label F1 ≥ B1 + 0.10 on the frozen test |
| R3 | Abstain | Mean abstention ≤ 20%; threshold learned inside training |
| R4 | Operate cheaply | $0 per comment; CPU-only; no paid API |
| R5 | Protect privacy | Zero `@name`, no comment text, no `author_hash` |
| R6 | Respond | p95 latency ≤ 1 s per comment |
| R7 | Trace decisions | 100% of predictions carry origin and review flags |

## Decisions

| Decision | Choice |
|---|---|
| Primary metric | Full-label F1; F2 and coverage secondary |
| Canonical listing count | 614 forms; 705 entries and 699 raw strings recorded |
| Implicit negatives | Defer the 20-candidate audit; record the caveat |
| Application corpus | Defer until the pilot pipeline is validated |
| Milestones | Keep all proposal gates visible |
| Audience | Team annotator first; Fondecyt researchers second |
| Success | Reproduce the published numbers from the same preconditions |
| Reference | Closed at 150 comments; no expansion |
| Next slice at approval | Candidate replay (S2) |
| Application candidate count | Decide later; 19,741 vs 20,097; 2,000 sample is exploratory |

## Assumptions to confirm

1. The 548/66 split is correct; the CSV's 550/64 category grouping differs by
   two forms. The brief records both until the team confirms.
2. The 2,000-comment application sample (3,655 candidates, 22.5% abstention,
   54 CSL) is exploratory; its artifacts are not in `resultados_hito2.zip`.
3. The reference's `anotacion` is an adjudicated or selected label, not a
   measured agreement: `anotacion_final` covers 48 of 65 labelled rows; the
   reference matches Vannia in 58 of 65; Hernán's role is unclear.
4. The 209 implicit negatives are 84 rows marked "Sin etiquetas" plus 125
   candidates inside annotated comments; precision and recall depend on the
   assumption that they were reviewed and rejected.
5. The proposal's R1 wording "705 unidades" means 705 entries; the matching
   inventory is 614 forms.
6. The headline 0.483 is M2 without abstention; the abstention variant is
   0.513 at 15.6% mean, with seeds 2 and 4 above 20%.
7. The 21 November benchmark and the 40-case M3 review have named owners; the
   brief does not assign them.
8. The local open LLM annotator remains future work and needs an ADR before it
   enters the plan.

## Open questions

- Which application candidate count will the 25 November run use: 19,741 or
  20,097?
- What exactly does F2 add beyond coverage for the binary discourse decision?
- Who owns the 21 November benchmark and the 40-case M3 review?
- How should the 2,000-comment sample be reported if its artifacts are missing?
- Does the 548/66 split or the 550/64 category grouping match the published
  restriction (a)?

## Approval

**Approved:** 20 November 2026. The open questions remain as recorded; the
current slice and status live in `docs/plan.md` and `docs/state.md`.
