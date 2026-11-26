# 03 — The 384-dimensional window embedding

**Slice:** S4 — M1 replay
**Related:** [01 — Candidate window](01-candidate-window.md),
[02 — TF-IDF](02-tf-idf.md)

**Privacy exception (documentation only).** This page contains one short
fragment requested by Till on 2026-11-26; the exception is limited to
`docs/learn/`. See the [index](README.md#privacy).

## What 384 means

A **384-dimensional window embedding** is one list of 384 real numbers that
represents the whole window. It is not 384 words, and it is not 384 windows.
The window goes in; one vector of width 384 comes out.

The model is `paraphrase-multilingual-MiniLM-L12-v2`:

| Property | Value |
|---|---|
| Type | MiniLM transformer, 12 layers |
| Output | 384-dimensional vector per window |
| Pooling | mean pooling of the contextual token vectors |
| Maximum input | 128 tokens |
| Training objective | paraphrase similarity, multilingual |
| Status in this project | frozen; not fine-tuned on the pilot labels |

The project uses it only as a feature extractor. The 384 is fixed by the model,
not chosen by the project. Changing the model would change the width and the
published M1/M2 numbers.

## How a window becomes 384 numbers

For the `mientras` window:

```text
ganancias de 850 millones de dólares, [[mientras]] tenemos uno de los combustibles más
```

the model does this:

1. **Tokenise** the window into subword tokens. The `[[` and `]]` markers are
   tokens too, but there are only a few, and the window is far below the
   128-token limit.
2. **Run the transformer** over the tokens. Each token becomes a contextual
   vector: the vector for `mientras` depends on `dólares` before it and
   `tenemos` after it.
3. **Pool** the token vectors. This model uses mean pooling: it averages the
   contextual token vectors into one vector.
4. **Output** that one vector. Its shape is `(384,)`.

For a batch of windows, the output is a matrix of shape
`(number_of_windows, 384)`. For the 273 pilot candidates, that is `(273, 384)`.

## What the numbers mean

They are **latent coordinates**, not named features. You cannot point at
dimension 17 and say “this means contrast”. The useful property is the geometry:

- two windows with similar meaning have similar vectors;
- two windows with different meaning have different vectors;
- the model was trained on paraphrase pairs, so it puts paraphrases and
  synonyms close together.

For the `mientras` window, the vector starts like this:

```text
[-0.0223, 0.0046, -0.0299, 0.2228, -0.2867, -0.1145, 0.2180, 0.3271, ...]
```

and its length (L2 norm) is about `3.95`, with values roughly between `-0.73`
and `0.67`. Those numbers look arbitrary because they are: the information is
in the relative position of the whole vector, not in one coordinate. This is why
the model is a black box compared with TF-IDF, where each feature has a
readable name like `pero` or `lo tanto`.

## Dense versus sparse

| Property | TF-IDF | Window embedding |
|---|---|---|
| Shape | one column per vocabulary term | exactly 384 columns |
| Density | sparse; most values are zero | dense; most values are non-zero |
| Names | each column is a word, n-gram or form | columns are unnamed latent coordinates |
| Captures | exact lexical overlap | semantic similarity, paraphrases |
| Interpretability | readable feature weights | black box; useful through distance |

The embedding block is wrapped as a matrix and appended to the sparse TF-IDF
blocks. They are different kinds of features, and the logistic regression
learns a weight for every column of both.

## How M1 uses it

The M1 feature matrix has these blocks:

```text
word TF-IDF     sparse, many columns
char TF-IDF     sparse, many columns
unit TF-IDF     sparse, one form column
six flags       six binary columns
embedding       dense, 384 columns
```

`hstack` concatenates them. The logistic regression then learns one weight per
column for step 1 (discourse versus `NO_DISCURSIVO`) and, for step 2, one
weight per column for the category decision. The embedding contributes semantic
evidence: “this window talks about prices and fuel in a way similar to other
windows where `mientras` was a conjunction”. The TF-IDF blocks contribute exact
words and morphology; the flags contribute punctuation and position; the unit
block contributes the identity of the form.

The notebook caches each window's vector by its text, so a window reused across
seeds or cross-validation folds is encoded only once. That matters because the
margin search fits the model five times per seed.

## Not normalised by default

`SentenceTransformer.encode` does not normalise by default, and the notebook
does not ask it to. The vector length therefore varies with the window. The
logistic regression can learn from the raw coordinates; normalising would change
the scale but not the direction. If you wanted to compare two windows by cosine
similarity, you would normalise first; the classifier does not need that.

## The short version

> The window is one document. The model reads it and returns one point in a
> 384-dimensional semantic space. The 384 numbers are the coordinates of that
> point. Similar windows have similar coordinates, and the classifier learns
> which coordinates push toward discourse use and which category.
