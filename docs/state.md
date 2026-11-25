# State — 2026-11-23

## Where we are
S2 candidate replay is in progress, not finished. The approved spec and design note are written; only `listing_forms` is implemented and committed. S1 metric replay is complete and passes.

## Done since last handoff
- S1 metric replay: `8ae054f..98fedb2`; `docs/specs/0001-metric-replay.md`, `docs/design/0001-metric-replay.md`, `docs/results/0001-metric-replay-diagnostics.md`. Zero deviations, five hashes verified.
- Brief and plan committed in `9c3b075`: `docs/00-brief.md`, `docs/plan.md`.
- S2 spec approved 2026-11-21 (`docs/specs/0002-candidate-replay.md`); `docs/design/0002-candidate-replay.md` is untracked with it.
- `9d436a9 feat(candidates): normalise the listing forms`; `tests/test_candidates.py` added.
- `pytest -q`: 22 passed, 3 deselected; `ruff check .` clean.

## Next
1. Commit the approved S2 spec, design note and this state note.
2. `/tdd listing_pattern`: case-insensitive, longest-first, letter boundaries, empty listing.
3. `/tdd read_annotation` and `normalise_label`.
4. `/tdd build_candidates`: CSL, second pieces, positives/negatives, undetected.
5. `/tdd public_candidates` and `seed_candidate_counts`.
6. Delegate `metrics.undetected_labels` and keep S1 green.
7. Add slow integration tests for 284/8/3/273/64/209/16/614 and per-seed 65/97/92/124/61.
8. Write `docs/results/0002-candidate-replay-diagnostics.md` and commit final docs.

## Open questions
- None blocking the next behaviour. The 20-candidate implicit-negative audit stays deferred; the 17 candidates never in a test split are covered by the global count only.

## Gotchas
- Use `.\.venv\Scripts\python.exe`; do not rely on global Python.
- `doc/` is read-only evidence and its corpora are gitignored; never copy comment text, context windows or `author_hash` into the repo.
- Slow tests need `doc/resultados_hito2.zip` and are excluded by default.
- S2 target counts are fixed (284/8/3/273/64/209/16/614); a mismatch is a bug, not a tuning problem.
- No `docs/adr/` exists; S2 needs no ADR. Protocol constants live in `gate.toml`.

## Not in an ADR
- S2 keeps the position-based CSL compatibility branch for S1's synthetic test; the published CSL file uses pairs only.
- S2 uses 614 forms; 705 entries and 699 raw strings are recorded counts, not matching units.
- `texto` and `ventana` stay in memory; `public_candidates` is the only outward view.
