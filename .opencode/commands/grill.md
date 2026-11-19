---
description: Interrogate requirements before any code is written
---

Run a requirements grilling session for: $ARGUMENTS

Rules:

- Ask in **rounds**. One theme per round, at most 5 questions, each with
  concrete options so choices are cheap.
- Do **not** scaffold, write code, or create files other than the brief.
- Cover, in this order: purpose and users; success criteria as observable
  behaviour; in scope; explicit non-goals; constraints (OS, offline, Python
  version, performance, CPU-only, $0 per comment, privacy R5, YouTube API
  refresh policy); data and failure modes (false negatives versus false
  positives, abstention, thread leakage, unseen forms); non-functional needs
  (logging, config, reproducibility, packaging, publication of artifacts).
- Treat the proposal in `doc/Equipo11_Propuesta_v3_equipo.docx` as the source of
  requirements R1–R7 and the four restrictions a)–d). Ask before contradicting
  it.
- Stop asking when the remaining unknowns are cheap to reverse later.
- Keep **Decisions**, **Assumptions**, and **Open questions** strictly
  separate. Anything you guessed is an Assumption, never a Decision.

Then write `docs/00-brief.md`. Finish with:

1. The assumptions you need confirmed.
2. `Approve the brief, or correct the assumptions.`
