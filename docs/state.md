# State — 2026-11-26

## Where we are
S3 baseline replay is complete and passes. The repository can rebuild the 273 candidates (S2) and the B0/B1 baselines (S3) from the reference, the listing and the frozen splits without reading the published predictions. S1 metric replay and S2 remain green. S4 M1 replay has completed `/learn`: the concept notes are in `docs/learn/`, the prototype reproduces the published M1, and the author chose approach A (faithful port with the frozen embeddings). The design note is written; `/spec` is next.

## Done since last handoff
- S2 candidate replay: `335ffab..5eca0ad`; `docs/specs/0002-candidate-replay.md`, `docs/design/0002-candidate-replay.md`, `docs/results/0002-candidate-replay-diagnostics.md`.
- `candidates.py` now holds the shared annotation parser, label normaliser, listing pattern, candidate builder, public view and per-seed counter.
- `metrics.undetected_labels` delegates to the builder; S1's replay, tables and hashes are unchanged.
- Published counts reproduced exactly: 614 forms, 284 raw, 8 CSL, 3 second pieces, 273 candidates, 64/209, 16 undetected. Per-seed 65/97/92/124/61 and 5/3/4/8/4 undetected; 439 appearances match the published keys and gold labels.
- `pytest -q`: 39 passed, 5 deselected; `pytest -m slow`: 5 passed, 39 deselected; `ruff check .` clean.
- S3 baseline replay: `42231a3..f1b410b`; `docs/specs/0003-baseline-replay.md`, `docs/results/0003-baseline-replay-diagnostics.md`.
- `baselines.py` builds the listing label map (614 forms, 548/66), B0's first-label rule, B1's training-majority rule with first-occurrence ties and the global fallback, the per-seed predictions, the metrics and the summary.
- Published B0/B1 reproduced exactly: 439 predictions (65/97/92/124/61), ten per-seed rows and two summary rows with zero deviations. Summary F1 label: B0 0.315, B1 0.328.
- `pytest -q`: 52 passed, 7 deselected; `pytest -m slow`: 7 passed, 52 deselected; `ruff check .` clean.
- S4 `/learn` notes extracted to `docs/learn/` with an index: candidate window and six flags, TF-IDF, 384-dimensional window embeddings, plus links to the S2/S3 worked examples. The S4 prototype reproduces the published M1 exactly with embeddings (0/439 label mismatches, max probability difference 3.6e-7) and fails without them (62/439 mismatches).
- S4 design note `docs/design/0004-m1-replay.md`: approach A, faithful port with the frozen embeddings; linked from the plan and the learn index.

## Next
1. `/spec` and `/spec-review` for S4: window features, punctuation, position, embeddings, the two-step logistic regression and the margin learned by grouped CV inside training.
2. Replay M1 per seed and match the published rows and summary at three decimals.
3. Write `docs/results/0004-m1-replay-diagnostics.md` and commit final docs.

## Open questions
- S4: `inicio_oracion` treats a newline as a sentence boundary. Phrases can span lines; the group should decide whether to keep the frozen rule or change it. A change alters M1/M2 and needs an ADR.
- The 20-candidate implicit-negative audit stays deferred; the 17 candidates never in a test split are covered by the global count only.

## Gotchas
- Use `.\.venv\Scripts\python.exe`; do not rely on global Python.
- `doc/` is read-only evidence and its corpora are gitignored. Do not copy comment text, context windows or `author_hash` into the repo, with three documented exceptions requested by Till on 2026-11-25/26 and pending team review: the eight short fragments in `docs/results/0002-candidate-replay-diagnostics.md`, the six short fragments in `docs/results/0003-baseline-replay-diagnostics.md`, and the teaching fragments in `docs/learn/`. The exceptions do not extend to any other artifact.
- Slow tests need `doc/resultados_hito2.zip` and are excluded by default.
- S2 target counts are fixed (284/8/3/273/64/209/16/614); a mismatch is a bug, not a tuning problem.
- S3 targets are fixed (439 predictions, 65/97/92/124/61, ten per-seed rows and two summary rows, zero deviations); a mismatch is a bug, not a tuning problem.
- `public_candidates` is the only outward candidate view; `texto` and `ventana` stay in memory.
- B1 ties go to the label that appears first in the training row order; the global fallback uses the same rule.
- No `docs/adr/` exists; S2 and S3 needed no ADR. Protocol constants live in `gate.toml`.

## Not in an ADR
- S2 keeps the position-based CSL compatibility branch for S1's synthetic test; the published CSL file uses pairs only.
- S2 uses 614 forms; 705 entries and 699 raw strings are recorded counts, not matching units.
- `undetected_labels` supplies neutral `is_reply`/`text_normalized` values for S1 fixtures that predate those columns; the undetected rows depend on neither.
- S3 reads the frozen `test_semillaN.txt` files by thread instead of rerunning `GroupShuffleSplit`; the frozen files are the split contract.
- S3's B1 tie-break is first occurrence in training order, not pandas' implicit `value_counts` order; the explicit rule reproduces all five seeds.
- S4 chooses the faithful port with the frozen embeddings; dropping them would change the published M1 and needs an ADR.
