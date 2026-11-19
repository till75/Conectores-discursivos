# AGENTS.md

## Purpose

Conectores-discursivos annotates discourse connectors and operators in Chilean
Spanish YouTube comments, following Fuentes Rodríguez (2009), for Fondecyt
11260185. The same word can be a discourse marker or an ordinary word, so the
system must decide, for each occurrence found in the listing, whether it has a
discourse use and which category it carries.

Two goals:

1. Build a reproducible, CPU-only annotation system that beats the listing
   baselines without inventing data.
2. Learn to co-author a real research tool with opencode.

Correctness, traceability, and honest evaluation matter more than speed. A
missed connector (false negative) is worse than a false alarm: the annotator
sees a false alarm, but a missed connector silently leaves the corpus.

## Environment

- Windows, PowerShell.
- Python lives in the project virtual environment:
  `.venv\Scripts\python.exe` (Python 3.14).
- Run every Python command through that interpreter; do not rely on a globally
  activated `python`.
- The repository root is `C:\dev\Conectores-discursivos`.
- The spaCy Spanish model is `es_core_news_sm`; install it once with
  `.\.venv\Scripts\python.exe -m spacy download es_core_news_sm`.
- The embedding extra (`sentence-transformers`, model
  `paraphrase-multilingual-MiniLM-L12-v2`) is optional and only needed for the
  embedding features; the core environment works without it.

## Commands

```powershell
# Tests
.\.venv\Scripts\python.exe -m pytest

# Lint
.\.venv\Scripts\python.exe -m ruff check .

# Lint and apply safe fixes
.\.venv\Scripts\python.exe -m ruff check . --fix

# Slow or diagnostic runs (excluded by default)
.\.venv\Scripts\python.exe -m pytest -m slow
```

Add dependencies to the virtual environment only when the current slice needs
them, and record them in `pyproject.toml`.

## Data, privacy, and evaluation integrity

These constraints are part of the contract, not preferences:

- **Never commit YouTube comment text.** Raw text, normalised text, context
  windows, and `author_hash` values stay out of git. The repository publishes
  only IDs, labels, counts, and metrics (R5). `doc/` is read-only source
  material; the corpora inside it are gitignored for this reason.
- **No usernames.** The privacy test searches for `@name` mentions and must
  report zero. Do not paste comment text into docs, commit messages, tests, or
  reports; quote at most a short illustrative fragment already published in the
  reference annotation, and only when it is necessary.
- **No leakage across the split.** Split by thread: a comment and its replies
  never land on different sides. Freeze the test before training and record its
  hash.
- **The threshold is learned inside training only.** The abstention margin comes
  from grouped cross-validation in the training split, never from the test.
- **Five seeds, fixed in advance.** Seeds 0–4. Report the mean and the bootstrap
  interval, not the best seed.
- **No rule may be written by looking at the pilot comments.** With five seeds,
  every comment is in some test eventually; a rule tuned on them inflates the
  result. Rules come from the grammar and from Fuentes Rodríguez (2009), and are
  frozen on 25 November. Compare M1 against M2 to show what the knowledge adds.
- **A decision that changes what a result means, or whether runs are
  comparable, needs an ADR** before the code is written. Examples: the split,
  the seeds, the abstention threshold, the frozen rule set, the metrics.

## Diagram conventions

These are author preferences, not optional styling:

- Use Mermaid. Do not switch to PlantUML or another diagram tool without
  explicit approval.
- Never rely on the viewer's theme for text colour. Grey text is a defect.
- Start every Mermaid block with the canonical light base theme:

  ```text
  %%{init: {"theme": "base", "themeVariables": {"darkMode": false, "primaryTextColor": "#000000", "secondaryTextColor": "#000000", "tertiaryTextColor": "#000000", "textColor": "#000000", "lineColor": "#334155", "edgeLabelBackground": "#ffffff", "clusterBkg": "#f8fafc", "clusterBorder": "#94a3b8"}}}%%
  ```

### Two outputs, two rules

Console chat and Markdown documents use different renderers. Do not copy one
rule to the other.

- **Console chat:** use plain labels, no HTML, no inline CSS, and no colour
  fills. Use a narrow `flowchart TB`, a text tree, or a table. The console
  chooses text colour; check the console render. HTML spans are Markdown-only
  and print literally here.
- **Markdown documents:** force black text with the S4 technique: wrap every
  node and edge label in `<span style='color:#000000'>...</span>`. Give edge
  labels a white backing. This is allowed here because the Markdown renderer
  interprets it; check light and dark previews.
- **Markdown backgrounds:** use only white or light-grey fills: `#ffffff`,
  `#f8fafc`, `#f1f5f9`, or `#e2e8f0`. Never use a darker fill. Carry category
  meaning with the stroke colour, not the fill.

In flowcharts, give each node a short plain label. If a box needs a title and
summary, use two short lines or split the node; do not use inline HTML for bold.
In sequence diagrams, use theme variables for text colour and no inline HTML.
Use one diagram per job. Split a wide diagram rather than letting it overflow.
Use a table for decision lists and classifications. Use colour to carry meaning,
label arrows, and give each box a title and a short summary. Keep the prose or
table as the contract; the diagram explains. Check every diagram in the console
renderer as well as light and dark Markdown previews. Text that renders as raw
HTML, or is clipped, is a defect.

## Language

Code identifiers, commit messages, and agent-facing notes are English.
User-facing prose (README, slice reports, course deliverables) is Spanish, the
language of the team and the assignment. Domain labels (`CON:ADICIÓN`,
`OP:MODAL`, `NO_DISCURSIVO`) keep their Spanish form everywhere.

## Working agreement

- **One vertical slice per turn.** A slice includes its tests, implementation,
  docs, diagnostic report, and commits. Finish it, report, and stop; do not
  start the next slice unless asked.
- **Slice for evaluation.** A slice must have an observable diagnostic report
  and pass/fail evidence. If the slice cannot be evaluated that way, split or
  redefine it before `/spec`.
- **Learn before specifying.** Every slice starts with `/learn` when it
  introduces a new approach or the author has not chosen one. `/learn` ends with
  a one-page design note and an explicit choice. Skip it only when the approach
  is already settled and no new concept is involved.
- **Specify, then review, then approve.** `/spec` writes the contract and ends
  with `/spec-review`. `/spec-review` reviews the contract against the design
  note, resolves concrete decisions, and records approval. `/tdd` starts only
  after that approval.
- **Review questions stand alone.** In `/spec-review` and any approval message,
  restate each decision in full: what changes, the recommended choice, and the
  alternative. Do not refer to "decision 1" or "Round 2" without repeating the
  decision; the author should not have to scroll up. Ask for an explicit yes/no
  per decision.
- **TDD, failing test first.** Show the failing test and its output before
  writing implementation code. The failure must be the missing behaviour, not
  an import or syntax error.
- **Commit each successful TDD cycle.** Treat a cycle as one behaviour-sized
  step, not every edit. A cycle is successful when its new test passes (or, for
  a refactor, the existing tests still pass), the full suite passes, and
  `ruff check .` is clean. Commit the test, implementation, and docs for that
  behaviour together. Never commit a red or partially green tree.
- **A slice may span several commits.** Each commit must be self-contained,
  green, and a coherent Conventional Commit. Do not squash or rewrite history
  unless asked.
- **Docs ship with behaviour.** Update the README, architecture notes, ADRs, or
  docstrings in the same commit as the change they describe. Docs that describe
  the whole slice belong in the slice's final commit.
- **Conventional Commits.** Use `<type>(<scope>): <imperative subject>` and
  explain why in the body when the reason is not obvious.
- **Push only at the end of a slice, after approval.** Do not push mid-slice.
  Wait for explicit approval that the slice is implemented, tested, documented,
  and ready. Approval applies to that slice only; it is not blanket permission
  for later pushes.

## Slice diagnostic reports

Every slice must produce a diagnostic report under `docs/results/` named
`<slice-id>-diagnostics.md`. The report is the artefact that records why the
slice was accepted and why we moved on. It is part of the final TDD cycle, not a
separate afterthought.

A slice is only well-formed if it can be evaluated. Before `/spec`, define the
observable goal, the pass/fail criteria, and the evidence that will go in the
report. If that cannot be done, split or redefine the slice.

The report follows `docs/results/_template-slice-diagnostics.md` and records:

- the slice goal and spec;
- the pass/fail criteria and the evidence for each;
- the commands run and their results;
- the diagnostic data, including caveats and effective sample sizes (number of
  evaluated candidates, number of threads, number of seeds);
- the decision: pass, fail, or partial, and why we move on;
- links to commits, artifacts, and follow-up work.

For any model result, the report must also state: the seed(s), the frozen test
hash, the abstention rate, the coverage (false negatives included), and how many
categories were fixed by the listing versus chosen by the model.

The final TDD step runs the full suite, `ruff check .`, and any slow or
diagnostic commands, then writes or updates the report and commits it with the
slice's final docs. A slice is not ready for approval without it.

When the report shape has stabilized across slices, add a `verify-slice`
command that reads a slice manifest, runs the verification commands, and writes
the report. Until then, the final TDD step writes the report manually. Do not
build `verify-slice` speculatively.

## Definition of done

A slice is ready for approval when:

1. The slice's spec was approved in `/spec-review` before implementation
   started.
2. A failing test was written and shown first for each new behaviour.
3. The new tests pass, and the full test suite passes.
4. `ruff check .` reports no errors.
5. Behaviour is documented where a reader would look for it.
6. A slice diagnostic report exists under `docs/results/` and records the goal,
   pass/fail criteria, evidence, limitations, and decision.
7. No comment text, context window, or `author_hash` entered the repository.
8. Every commit in the slice is green and self-contained, and the final tree is
   clean.
9. The project is left in a working state.
10. Nothing has been pushed before approval.

After approval, push the completed slice. Do not push again until the next
slice is approved.
