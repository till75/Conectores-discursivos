# Input audit — files, annotations, and the published counts

**Date:** 2026-11-20
**Status:** exploratory data audit, not a slice
**Owner:** Till
**See also:** [corpus overview](corpus-overview.md) for the shape of the
application corpus.

This note establishes what each input file is, how the annotations were produced,
and where the published numbers come from. Every number below is reproduced by
`audit_inputs.py` from the local, gitignored files in `doc/`.

## How this was produced

```powershell
.\.venv\Scripts\python.exe docs/results/data-overview/audit_inputs.py
```

The script reads the listing, both comment CSVs, the reference, the CSL file,
and the annotation workbook. It writes only counts, comment IDs, units, and
labels (`audit_summary.txt`, `annotators.csv`, `agreement.csv`,
`reference_candidates.csv`). No comment text is written, so the outputs can be
published under R5.

## Files and their roles

| File | Role | Versioned? |
|---|---|---|
| `comentarios_youtube.csv` | application corpus, 10,505 comments, 20 videos | no (comment text) |
| `comentarios_youtube_normalizados.csv` | same corpus, anonymised and normalised | no (comment text) |
| `Corpus piloto youtube__anotado.xlsx` | pilot workbook: 1,268 comments, 6 videos, annotations | no (comment text) |
| `referencia_piloto.csv` | the 150-comment reference used by the notebook | no (comment text) |
| `csl_excluidas.csv` | 16 semi-free constructions excluded from scoring | yes |
| `listado_fuentes2009.csv` | 705 listing rows, 614 distinct forms | yes |

Note the two different corpora: the application corpus and the pilot reference
share **zero** comment IDs. The pilot is about fuel prices; the application
corpus is about migration, defence, crime, and social policy.

## The listing

| | |
|---|---|
| Rows | 705 |
| Distinct forms | 614 (numbered variants collapse) |
| Operators / connectors | 460 / 245 |
| Forms with one category | **548** |
| Forms with several categories | 66 |
| Marked polyfunctional | 155 |

The file is valid **UTF-8 without BOM**. The bytes are `Adici\xc3\xb3n`, which is
"Adición". Excel reads it as cp1252 and shows "AdiciÃ³n"; the `─` character is
the placeholder for an empty subcategory. Import it as UTF-8 (File Origin 65001)
or save a copy with BOM for Excel. The data is not corrupted.

## Raw versus normalised

The normalised file drops `comment_text_raw` (privacy) and adds
`text_normalized` and `revisar`. `comment_text` is already anonymised: 1,830
`@USER` occurrences, against zero in `comment_text_raw`, with 1,814 rows
differing.

Normalisation is deterministic, rule-based, and applied in this order:

| Step | Example |
|---|---|
| mentions to `@USER` | `@juan` to `@USER` |
| emoji to text | 😂😂😂 to `[3 emoticonos de risa]` |
| all-caps to lower case | `EXIJO` to `exijo` |
| laughter | `jajajaja` to `jajaja` |
| lengthening | `Nooo` to `No` |
| abbreviations | `q` to `que`, `xq` to `porque`, `pa` to `para` |
| names and acronyms | `boric` to `Boric`, `tvn` to `TVN` |
| punctuation | `...` to `…`, `???` to `?` |
| opening marks | `Y la zanja?` to `¿Y la zanja?` |
| sentence capital | `y la zanja` to `Y la zanja` |

It changes **6,984 comments (66.5 %)**, inserts 3,271 emoji tokens, and flags 50
rows in `revisar`. It does **not** add accents, fix spelling, or resolve
*porque / por qué*.

Two consequences matter:

- Normalisation removes emphasis cues. All-caps and lengthened forms are often
  the signal that separates an emphatic operator from an ordinary adverb.
- It changes the candidate count: **19,741** matches on `comment_text`, **20,097**
  on `text_normalized` (+356). The v4 proposal reports 19,741, so that figure is
  the pre-normalisation count. The notebook would now find 20,097.

## The pilot workbook

| | |
|---|---|
| Comments | 1,268 |
| Videos | 6 |
| Channels | 4 |
| Threads | 798 |
| With `text_normalized` | 399 |
| With any annotation | 150 |
| Reference rows | 150 |

The 150 reference rows are **exactly** the comments with two or more annotator
columns (Hernán's text column counts as one), and all come from **one video**
(fuel prices). 143 of the 150 have two or more *real* annotations. The workbook's
other five videos were not used for the reference.

| Column | Reviewed | With a label | Spans | "Sin etiquetas" |
|---|---:|---:|---:|---:|
| Jorge | 149 | 65 | 100 | 83 |
| Hernán | 399 | **5** | 7 | 0 |
| Javier | 94 | 51 | 79 | 14 |
| Vannia | 144 | 61 | 93 | 83 |

Hernán's column covers all 399 normalised comments but contains the working text
rather than bracket markup; it agrees with the others on essentially no active
comment (0–1.5 %). Treat it as the text column until the team confirms his role.
Among the 150 reference comments, 94 have three real annotators, 49 have two, and
7 have only one (6 Jorge, 1 Vannia). `anotacion_final` is filled in only **48**
rows against 65 labelled reference rows.

### Agreement

Conflicts are common. When both annotators marked something, they produced the
same label set in about half the comments:

| Pair | Shared | Both empty | Both marked | Identical | Same unit, other category | Different units | One marked only |
|---|---:|---:|---:|---:|---:|---:|---:|
| Jorge–Vannia | 143 | 70 | 51 | 30 (59 %) | 8 | 13 | 22 |
| Jorge–Javier | 94 | 40 | 35 | 18 (51 %) | 7 | 10 | 19 |
| Javier–Vannia | 94 | 40 | 38 | 19 (50 %) | 7 | 12 | 16 |

The reference is closest to Vannia (58 of 65 labelled rows identical), then Jorge
(31), Javier (19), and Hernán (3). The single `anotacion` column in
`referencia_piloto.csv` is therefore an adjudicated or selected version, not
evidence that the annotators agreed.

## Semi-free constructions (CSL)

`csl_excluidas.csv` has **16 rows** (17 with the header), 15 distinct units, and
14 comments, all inside the reference: `como si`, `como si nada`, `dale`,
`es obvio que`, `gracias`, `ni un solo peso`, `no sacamos nada con`, `no, si`,
`para qué decir`, `por culpa de`, `y el pelado`, `y san boric`, `y tú`,
`ya es mucho`.

A *construcción semilibre* has a fixed part and a variable slot (`Dale + noun
phrase`, `Como si + clause`). The listing contains the individual word, but the
function belongs to the whole construction, so it is not scored as a lone
connector. The notebook removes the 16 construction labels from the gold and
excludes any listing match inside their span (8 matches).

## The reference and the 273 candidates

```
150 reference comments
  → 284 raw listing matches
    − 8 inside a CSL
    − 3 second pieces of a longer unit
    = 273 candidates
      64 positive (have a gold label)
     209 negative (no label)
```

The 96 reference labels decompose as **64 detectable + 16 not in the listing +
16 CSL constructions**. After removing the CSL labels, 80 spans remain; 64 of
them are detectable, and 16 are forms the listing never finds.

Of the 209 negatives, **84 come from the 85 rows marked "Sin etiquetas"**. Those
rows are not useless: they are the negative class. Without them the model would
have no examples of ordinary uses such as temporal *ya*.

But 125 negatives sit inside comments that *were* annotated. The protocol marks
connectors, not every non-connector, so the negative class assumes that an
unmarked occurrence was seen and rejected. If annotators only marked what caught
their eye, the gold contains silent misses — which would directly depress recall,
the weakest reported number.

## Open questions

- What is Hernán's role? His column behaves like text, not annotation.
- How was the reference adjudicated, given that `anotacion_final` covers only 48
  rows and the reference matches Vannia in 58 of 65?
- Was every candidate reviewed, or only the salient ones? An audit of 20
  unmarked candidates would settle whether 209 implicit negatives are real.
- Which candidate count should the 25 Nov application run use, 19,741 or 20,097?
  The abstention denominator depends on it.

## Files

| File | Content |
|---|---|
| `audit_inputs.py` | regenerates every number in this note from `doc/` |
| `audit_summary.txt` | the full audit output in plain text |
| `annotators.csv` | per-annotator reviewed, labelled, spans, "Sin etiquetas" |
| `agreement.csv` | pairwise agreement, including empty and conflict counts |
| `reference_candidates.csv` | the 273 candidates: comment ID, unit, gold flag |
