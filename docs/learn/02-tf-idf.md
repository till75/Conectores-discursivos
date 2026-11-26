# 02 — TF-IDF

**Slice:** S4 — M1 replay
**Related:** [01 — Candidate window](01-candidate-window.md),
[03 — Window embeddings](03-window-embeddings.md)

TF-IDF turns a window of text into a vector of numbers. Each word, n-gram or
character fragment gets a weight with two ingredients:

- **TF — term frequency.** How often the term appears in *this* window.
- **IDF — inverse document frequency.** How rare the term is across the
  *training* windows.

The weight is `TF × IDF`. Common words (`el`, `de`, `que`) are downweighted;
rare words (`pero`, `sin embargo`) are upweighted.

## The exact formula

The project uses `TfidfVectorizer` with `sublinear_tf=True`, `smooth_idf=True`
(the default) and `norm="l2"` (the default).

For a term `t` in a window `d`:

```text
tf(t,d) = 1 + ln(count(t,d))              if count > 0, because sublinear_tf=True
idf(t)  = ln((1 + n) / (1 + df(t))) + 1
weight  = tf(t,d) × idf(t)
```

`n` is the number of training windows and `df(t)` is the number of training
windows containing `t`. After the weights are computed, each window vector is
divided by its L2 norm, so every window has length 1.

## A worked example

Suppose the training set has four synthetic windows:

```text
d1: el ya pero no
d2: el bus ya llego
d3: el ya que solo
d4: el por lo tanto ya
```

Here `n = 4`.

- `el` appears in 4 windows: `idf = ln(5/5) + 1 = 1`.
- `ya` appears in 4 windows: `idf = 1`.
- `pero` appears in 1 window: `idf = ln(5/2) + 1 ≈ 1.916`.
- `no`, `bus`, `llego`, `que`, `solo`, `por`, `lo`, `tanto` each appear in
  1 window: `idf ≈ 1.916`.

For `d1 = el ya pero no`, every count is 1, so `tf = 1`:

```text
el   1 × 1     = 1.000
ya   1 × 1     = 1.000
pero 1 × 1.916 = 1.916
no   1 × 1.916 = 1.916
```

The L2 norm is `sqrt(1² + 1² + 1.916² + 1.916²) ≈ 3.057`. After normalisation:

```text
el 0.327 · ya 0.327 · pero 0.627 · no 0.627
```

So `pero` and `no` weigh almost twice as much as `el` and `ya` in this toy
corpus. In the real corpus, `el` is even more common and its IDF stays close to
1; a rare connector gets a larger IDF.

## Sublinear TF

If `d1` were `el ya ya ya pero no`, the count of `ya` is 3. With
`sublinear_tf=True`, the TF is not 3:

```text
tf(ya) = 1 + ln(3) ≈ 2.099
```

Repeating a word matters, but not three times as much. This prevents one
repeated form from dominating the window.

## N-grams

The word block uses `ngram_range=(1, 2)`, so it sees unigrams and adjacent
bigrams. For `por lo tanto ya` it creates:

```text
unigrams: por, lo, tanto, ya
bigrams:  por lo, lo tanto, tanto ya
```

It does **not** create the 3-gram `por lo tanto`. The unit block handles that:
the whole `unidad` string is one token, so `por lo tanto` is a single unit
feature. That is also how the model knows which listing form it is classifying.

The character block uses `char_wb` with 2–5 character n-grams, within word
boundaries. It captures morphology, accents and small typos:
`reformulativo` and `reformulativos` share most of their character n-grams.
`min_df=2` drops character n-grams that appear in fewer than two training
windows, which filters idiosyncratic noise.

## Why L2 normalisation

A long window has more non-zero features than a short one. Without
normalisation, its vector would have a larger norm and the logistic regression
would be dominated by window length. L2 normalisation makes every window a unit
vector, so the classifier compares the pattern of terms, not how many terms
there are.

## The three TF-IDF blocks in M1

| Block | Input | Analyzer | What it captures | Settings |
|---|---|---|---|---|
| Word TF-IDF | `ventana` | word 1–2 grams | context words and adjacent pairs | `min_df=1`, `sublinear_tf=True` |
| Character TF-IDF | `ventana` | `char_wb` 2–5 grams | morphology, accents, small typos | `min_df=2`, `sublinear_tf=True` |
| Unit TF-IDF | `unidad` | whole form as one token | which listing form is being classified | `analyzer=lambda u: [u]` |

The six flags and the 384-dimensional window embedding are separate blocks, not
TF-IDF. The model concatenates all of them into one sparse matrix and learns a
weight per feature. See [01 — Candidate window](01-candidate-window.md) for the
flags and [03 — Window embeddings](03-window-embeddings.md) for the embedding.

## Fit on training only

The vocabulary and IDF must be learned from the training windows; the test
windows are only transformed. Fitting on all data would leak test information
into the model. In the code this is the `fit=True` path for training and the
`fit=False` path for test.

## The training corpus is small

Each seed has only about 149–212 training candidates, so IDF estimates are
noisy. A form that appears twice can get a very different weight than in a large
corpus. The unit block and the listing restriction compensate partly; the small
sample is one reason the project reports intervals and abstention.

## Common confusions

- **TF-IDF is not a model.** It is a feature transformation. The logistic
  regression learns the weights on top of it.
- **The 384-dimensional embedding is not TF-IDF.** It is a separate dense block
  produced by a transformer. See
  [03 — Window embeddings](03-window-embeddings.md).
- **A bigram is two words.** `por lo tanto` is a three-word form; the word
  block sees its unigrams and two bigrams, while the unit block sees the whole
  form as one token.
- **IDF is learned from training, not from the test split.** This is a leakage
  control, not a detail.
