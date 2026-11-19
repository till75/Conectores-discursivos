# Local data

Put local working copies of the corpus here. Nothing in this folder is
versioned except this file, because the YouTube API terms and requirement R5
forbid publishing comment text.

Expected inputs for the pilot notebook and pipeline:

| File | Content | Committed? |
|---|---|---|
| `referencia_piloto.csv` | 150 annotated comments, `[unidad::ETIQUETA]` spans | no (comment text) |
| `csl_excluidas.csv` | semi-free constructions excluded from evaluation | yes, keep in `doc/` |
| `listado_fuentes2009.csv` | Fuentes Rodríguez (2009) unit listing | yes, keep in `doc/` |
| `comentarios_youtube_normalizados.csv` | normalised application corpus, no labels | no |

Keep the canonically versioned copies of the listing and the exclusion list in
`doc/`; copy them into `data/` only when running the notebooks locally.
