---
description: Teach the project from zero and verify understanding
---

Onboard: $ARGUMENTS

Goal: someone who has never seen the pilot can explain the project, the
experiment, and one number, without reading code yet.

Do not write production code. Do not edit anything in `doc/`.

1. **Tell the story in order.** Who the user is, what artefact exists, what the
   team did first, and what the result was. Point at files, not paragraphs.
2. **Name the five ideas.** Occurrence as the unit, feature, logistic
   regression, embedding, evaluation. One concrete example each, taken from the
   project's own words (`ya`, `hasta`, `solo`).
3. **Read one number together.** Use the published table: what F1, coverage,
   precision, and abstention mean here, and what they do not mean. Show where
   the loss actually sits.
4. **Draw the two flows.** Annotation (comment to label) and experiment (labels
   to interval). Narrow, plain labels, no colour fills.
5. **Check understanding.** Ask three questions that need the ideas, not the
   vocabulary: why one comment can be several examples; what missing four of ten
   connectors costs the annotator; why the split is by thread. Stop and re-teach
   if the answers do not hold.
6. **Write the shared vocabulary.** Only after the check, write
   `docs/00-onboarding.md`: the story, the five ideas, a glossary, the number
   reading, and the artefact map. English first, Spanish later for the team.
7. **Propose, do not choose.** Suggest the first slice and finish with
   `Next: /learn <slice>.` The author picks the slice.
