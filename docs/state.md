# State — 2026-11-27

## Where we are
S4 (M1 replay) is finished, approved, and pushed; `origin/main` is `f9ab832` and the tree is clean. S5 (M2 replay) `/learn` is complete and the spec is approved: approach A, the faithful port with the margin learned by grouped CV inside training. No S5 code has been written.

## Done since last handoff
- S4 M1 replay implemented and tested: `1a84fda`, `59a3c13`, `24a1b2c`, `7e6454d`, `01452be`, `cd614f6`.
- S4 spec approved: `e585539`; diagnostics report committed: `f9ab832` (`docs/results/0004-m1-replay-diagnostics.md`).
- S5 prototype evidence collected outside the repo: no-abstention M2 exact, margin path differs.
- S5 `/learn` complete: author chose A; `docs/design/0005-m2-replay.md` and `docs/learn/04-m2-rules-provenance.md` written and linked from the learn index.
- S5 spec approved 2026-11-27: `docs/specs/0005-m2-replay.md`; the partial-result criterion for the 27/439 margin mismatch is accepted.

## Next
1. Start `/tdd` with the frozen rule set.
2. Complete the S5 TDD cycle: rules, grammar, features, model, predictions, metrics and traceability.
3. After the cycle, investigate the published-margin mismatch and fix it before closing S5 if possible; otherwise close S5 as partial with the 27/439 mismatch recorded.
4. Do not use the published margins to choose the margin.

## Open questions
- What causes the published-margin mismatch: library drift or an older margin path? Investigate after the S5 TDD cycle, before closing S5.
- The partial result is a fallback, not the default close.

## Gotchas
- Run Python as `.venv\Scripts\python.exe`; spaCy model is `es_core_news_sm`.
- `doc/` is read-only evidence; its corpora are gitignored.
- S5 prototype is `C:\Users\tills\AppData\Local\Temp\opencode\m2_probe_s5.py`; it is not in the repo.
- No-abstention M2, `p_M2`, `origen_M2`, `revisar_categoria`, and traceability match; margins differ: prototype `0.20/0.15/0.15/0.15/0.20` vs published `0.15/0.10/0.20/0.10/0.20`; 27/439 `abstiene_M2` rows differ.
- S5 margin probe: no tested training-only CV variant (`GroupKFold` 3/4/5/6/10, `GroupShuffleSplit` 5, `KFold` 5) or test-set selection reproduces the published margins; the training row order matches the notebook. Suspect library drift or an older margin path.
- S4 evidence: `pytest -q` 79 passed, 10 deselected; `pytest -m slow` 10 passed; `ruff check .` clean.

## Not in an ADR
- S2/S3/`docs/learn/` have documentation-only privacy exceptions; do not extend them without request.
- S5 `/learn` is complete; the teaching note is documentation, not a spec.
- S5 does not need an ADR for the rule set: recording the frozen rules is not a change. Editing them would need one.
- S4 used the frozen embeddings cache; replay tests must not refit or download it.
