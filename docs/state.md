# State — 2026-11-25

## Where we are
S2 candidate replay is complete and passes. The repository can rebuild the 273 candidates, the 64 positives, the 209 negatives and the 16 undetected labels from the reference, the listing and the CSL file without reading the predictions. S1 metric replay remains complete and green. S3 baseline replay is next and has not started.

## Done since last handoff
- S2 candidate replay: `335ffab..5eca0ad`; `docs/specs/0002-candidate-replay.md`, `docs/design/0002-candidate-replay.md`, `docs/results/0002-candidate-replay-diagnostics.md`.
- `candidates.py` now holds the shared annotation parser, label normaliser, listing pattern, candidate builder, public view and per-seed counter.
- `metrics.undetected_labels` delegates to the builder; S1's replay, tables and hashes are unchanged.
- Published counts reproduced exactly: 614 forms, 284 raw, 8 CSL, 3 second pieces, 273 candidates, 64/209, 16 undetected. Per-seed 65/97/92/124/61 and 5/3/4/8/4 undetected; 439 appearances match the published keys and gold labels.
- `pytest -q`: 39 passed, 5 deselected; `pytest -m slow`: 5 passed, 39 deselected; `ruff check .` clean.

## Next
1. `/learn` S3 baseline replay if needed (the plan marks `/learn` as no).
2. `/spec` and `/spec-review` for S3: B0's first-category rule and B1's most-frequent-label rule, with the listing's label map.
3. Replay B0 and B1 per seed and match the published rows and summary at three decimals.
4. Write `docs/results/0003-baseline-replay-diagnostics.md` and commit final docs.

## Open questions
- None blocking S3. The 20-candidate implicit-negative audit stays deferred; the 17 candidates never in a test split are covered by the global count only.

## Gotchas
- Use `.\.venv\Scripts\python.exe`; do not rely on global Python.
- `doc/` is read-only evidence and its corpora are gitignored. Do not copy comment text, context windows or `author_hash` into the repo, with one documented exception: the eight short fragments in `docs/results/0002-candidate-replay-diagnostics.md`, granted by Till on 2026-11-25 and pending team review. The exception does not extend to any other artifact.
- Slow tests need `doc/resultados_hito2.zip` and are excluded by default.
- S2 target counts are fixed (284/8/3/273/64/209/16/614); a mismatch is a bug, not a tuning problem.
- `public_candidates` is the only outward candidate view; `texto` and `ventana` stay in memory.
- No `docs/adr/` exists; S2 needed no ADR. Protocol constants live in `gate.toml`.

## Not in an ADR
- S2 keeps the position-based CSL compatibility branch for S1's synthetic test; the published CSL file uses pairs only.
- S2 uses 614 forms; 705 entries and 699 raw strings are recorded counts, not matching units.
- `undetected_labels` supplies neutral `is_reply`/`text_normalized` values for S1 fixtures that predate those columns; the undetected rows depend on neither.
