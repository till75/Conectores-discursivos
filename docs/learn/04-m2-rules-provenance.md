# 04 — M2 rules and provenance

**Slice:** S5 — M2 replay
**Related:** [design note 0005](../design/0005-m2-replay.md),
[01 — Candidate window](01-candidate-window.md),
[S4 report](../results/0004-m1-replay-diagnostics.md)

**Privacy exception (documentation only).** This page uses the already-published
`mientras` fragment by reference and constructed examples. It adds no comment
text, no `@name` mention and no `author_hash`. See the
[index](README.md#privacy).

## What M2 adds to M1

M1 is a two-step model: step 1 decides discourse use versus `NO_DISCURSIVO`;
step 2 chooses the category. M2 keeps that model and adds five pieces:

| Piece | What it does | Where it lives |
|---|---|---|
| Strict listing restriction | The category must come from the listing, not from labels seen in training. | `M2.predict` |
| 15 frozen context rules | Adds binary linguistic features to the model. | `REGLAS`, `M2._X` |
| spaCy POS features | Adds the part of speech of the unit and its neighbours. | `anotar_gramatica`, `M2._X` |
| Rare-category flag | Marks categories with fewer than five training examples for review. | `M2.predict`, `n_cat` |
| Provenance | Records whether the listing or the model fixed the category. | `origen_M2` |

The order matters. The listing restriction decides *which categories are
allowed*. The model and the rules help decide *which allowed category to pick*.
Provenance records the result.

## 1. Strict listing restriction and provenance

M1 allows a category if it is in the listing **or** if it was seen in training
for that unit. M2 removes the second half: only the listing is allowed.

```text
M1: permitted = listing[unit] ∪ seen_in_training[unit]
M2: permitted = listing[unit]
```

Then M2 applies a simple rule:

- if the listing admits **exactly one** category, the listing fixes it and
  `origen_M2 = "listado"`;
- if the listing admits **more than one**, the model orders the admitted
  categories and picks the first one, and `origen_M2 = "modelo"`;
- if the model has no second step, the first admitted category is used and
  `origen_M2 = "listado"`.

Provenance is the audit trail. The published traceability counts are:

| Count | Value | Meaning |
|---|---:|---|
| `etiquetas_discursivas` | 91 | test labels with a discourse use |
| `fijadas_listado` | 58 | categories fixed by the listing |
| `fijadas_listado_correctas` | 34 | of those, correct |
| `elegidas_modelo` | 33 | categories chosen by the model |
| `elegidas_modelo_correctas` | 20 | of those, correct |
| `revisar_categoria` | 43 | discourse labels flagged for review |

The distinction is the point of M2. A list-fixed label is a knowledge decision;
a model-chosen label is a learned decision. Without `origen_M2`, the report
could not say how many categories the knowledge fixed and how many the model
chose.

## 2. The 15 frozen rules

The rules come from the grammar and from Fuentes Rodríguez (2009), not from the
pilot comments. They were frozen on 25 November 2026. S5 records them verbatim;
editing them needs an ADR.

Each rule is a boolean feature. It does **not** override the model. The model
sees the rule as one more column and learns how much to trust it.

### General rules

| Rule | What it checks | Why it can matter |
|---|---|---|
| `sig_det_o_num` | next token is `DET` or `NUM`, or starts with a digit | a determiner or number often starts a noun phrase |
| `sig_verbo` | next token is `VERB` or `AUX` | a following verb suggests a predicate, not a list item |
| `ant_verbo` | previous token is `VERB` or `AUX` | the unit may close a predicate |
| `sig_adj_o_adv` | next token is `ADJ` or `ADV` | the unit may modify a following adjective or adverb |
| `ant_det` | previous token is `DET` | the unit may be part of a noun phrase |
| `ant_prep` | previous token is `ADP` | the unit may be the complement of a preposition |
| `sig_que` | next token is `que` | a following `que` often opens a clause |
| `aislada_por_comas` | comma after the unit, and sentence start or comma before | the unit is set off as a parenthetical |
| `fin_tras_verbo` | previous token is a verb and the statement ends | the unit closes the statement after a predicate |
| `en_pregunta` | the unit is inside an interrogative sentence | question context changes the reading |

`en_pregunta` uses `_pregunta`, which looks for the next sentence-ending
punctuation and for an opening `¿`. Like `inicio_oracion`, it treats a newline
as a boundary. The newline question from
[01 — Candidate window](01-candidate-window.md#the-newline-question) therefore
affects M2 as well.

### Unit-specific rules

| Rule | What it checks | Why it can matter |
|---|---|---|
| `hasta_preposicion` | unit `hasta` + `DET`, `NUM`, `PROPN`, `NOUN` or a digit | `hasta` before a noun phrase is often a preposition |
| `ya_temporal` | unit `ya`, no comma after, next token `VERB`, `AUX` or `PRON` | `ya` before a predicate can be temporal |
| `ya_operador` | unit `ya`, sentence start, comma after | `ya` set off at the start can be an operator |
| `solo_adjetivo` | unit `solo`, previous token `VERB`, `AUX` or `PRON`, statement ends | `solo` after a predicate can be an adjective/adverb |
| `mas_comparativo` | unit `más` + `ADJ`, `ADV`, `NOUN`, `NUM` or `que` | `más` before a comparable term is often comparative |

These are the rules the proposal names. They are not a decision list: a rule
firing does not force a label. The model combines them with the window, the
TF-IDF blocks and the embeddings.

## 3. spaCy POS features

`anotar_gramatica` adds five columns for every candidate:

| Column | Value | Example |
|---|---|---|
| `pos_u` | UPOS of the unit | `VERB` |
| `pos_ant` | UPOS of the previous token, or `INICIO` | `DET` |
| `pos_sig` | UPOS of the next token, or `FIN` | `NOUN` |
| `tok_ant` | lowercase previous token, or empty | `el` |
| `tok_sig` | lowercase next token, or empty | `tema` |

The offsets come from the candidate's `inicio` and the unit's length. spaCy is
run once per comment and cached, so the same comment is not parsed repeatedly.

`M2._X` turns these columns into features with `DictVectorizer`:

```text
u=VERB
ant=DET
sig=NOUN
ya|sig=VERB
ya|ant=DET
```

The first three are general; the last two combine the unit with its neighbour,
so the model can learn that a particular unit behaves differently in a
particular context.

## 4. The rare-category flag

`M2.fit` counts the positive training examples for each category:

```text
n_cat = count of training rows where oro != NO, grouped by oro
```

`M2.predict` then sets:

```text
revisar_categoria = n_cat[chosen_category] < 5
```

This is a **review flag**, not an abstention. The label is still predicted. The
flag tells the annotator that the category had too few training examples to be
trusted. The published count is 43.

## 5. The abstention margin

The margin is a band around probability 0.5:

```text
if |p - 0.5| < margin:
    predict NO_DISCURSIVO
    count an abstention
```

M2 learns the margin with `elegir_margen_m`:

- five-fold `GroupKFold` on the training rows, grouped by `thread_id`;
- grid `0.00, 0.05, …, 0.30`;
- skip a margin when abstention on the CV holdout is above 20% or no row
  remains;
- keep the margin with the highest CV F1; a tie keeps the smaller margin.

### Why inside training, not on test

The margin is a decision, not a feature. If it were chosen on the test set, the
test labels would set the operating point. The reported F1 and coverage would
then describe a system tuned on the test, not a system that generalizes. That is
leakage, and it breaks the frozen-test contract.

Grouping by `thread_id` matches the split. A comment and its replies share
context and often repeat words; if a reply were in the fit fold and its parent
in the holdout, the CV estimate would be optimistic. Grouping keeps each thread
on one side.

The 20% cap is also on the CV holdout, not on test. The published seed 2 test
abstention is 30.4%, which is an outcome of the fixed margin, not a violation of
the cap.

### The published-margin mismatch

The prototype reproduces the no-abstention M2 exactly but not the published
margins:

| Seed | Published margin | Prototype margin |
|---|---:|---:|
| 0 | 0.15 | 0.20 |
| 1 | 0.10 | 0.15 |
| 2 | 0.20 | 0.15 |
| 3 | 0.10 | 0.15 |
| 4 | 0.20 | 0.20 |

27 of 439 `abstiene_M2` rows differ. No tested training-only CV variant
(`GroupKFold` 3/4/5/6/10, `GroupShuffleSplit` 5, `KFold` 5) or test-set selection
reproduces the published margins. The training row order matches the notebook.
The likely causes are library drift or an older margin path.

S5 does not solve this by copying the published margins. It investigates the
training-only path and reports the result honestly. If the margins cannot be
reproduced, the slice is partial or fail, not a licence to tune on test.

## Prototype audit

| M2 component | Evidence | Status |
|---|---|---|
| Strict listing restriction | no-abstention labels and `origen_M2` exact | matched |
| 15 frozen rules | `p_M2`, `origen_M2` and traceability exact | matched |
| spaCy POS features | `p_M2` exact | matched |
| Rare-category flag | `revisar_categoria` exact (43) | matched |
| Provenance | 91/58/34/33/20/43 exact | matched |
| Abstention margin | margins differ; 27/439 `abstiene_M2` rows differ | not matched |

The linguistic layer is reproduced. The margin is the only open piece.

## What to remember

- The listing decides which categories are allowed; the model chooses among
  them; provenance records which.
- The 15 rules are features, not overrides.
- POS features give the model grammatical context; the unit-neighbour
  combinations let it learn unit-specific behaviour.
- `revisar_categoria` is a review flag, not an abstention.
- The margin is learned inside training by grouped CV. Choosing it on test
  leaks the test and invalidates the result.
- The published-margin mismatch is a finding to investigate, not a reason to
  copy the answer.
