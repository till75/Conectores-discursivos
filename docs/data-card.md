# Ficha de datos — corpus piloto y de aplicación

**Proyecto:** Fondecyt 11260185 — conectores y operadores discursivos en
comentarios de YouTube en español de Chile.
**Marco:** Fuentes Rodríguez (2009).
**Estado:** datos del piloto cerrados; corpus de aplicación sin etiquetas.

## Corpus piloto

El piloto contiene 1.268 comentarios de 6 videos de noticias chilenas, en 798
hilos. La referencia anotada son 150 comentarios: 65 tienen al menos una
etiqueta y el resto fueron revisados sin marcar. Las 150 filas producen 96
etiquetas en 12 categorías.

La referencia cubre un solo video del piloto (alza de combustibles). La
columna `anotacion` es una versión adjudicada o seleccionada, no una medida de
acuerdo entre anotadores: solo 48 filas tienen `anotacion_final`.

## Corpus de aplicación

El corpus de aplicación contiene 10.505 comentarios de 20 videos y 6.264
hilos. No tiene etiquetas de referencia. Comparte **cero** IDs de comentario
con el piloto. La ejecución sobre este corpus queda diferida hasta que el
pipeline del piloto esté validado.

## Listado

El listado de Fuentes Rodríguez (2009) tiene 705 filas y 614 formas distintas
después de normalizar los números de sentido. 548 formas admiten una sola
categoría y 66 admiten varias; 155 filas están marcadas `polifuncional`.

`polifuncional` es una marca de la fuente (155 filas); las 66 formas con varias
categorías son las que tienen más de una etiqueta distinta en `categoria`
después de normalizar. Son conteos distintos y no se derivan uno del otro.

Las 16 construcciones semilibres (CSL) anotadas se excluyen del puntaje: su
función pertenece a la construcción completa, no a la palabra suelta. Una CSL
tiene una parte fija y un hueco variable; el listado contiene la palabra suelta,
pero la función pertenece a la construcción.

## Esquema de las tablas

| Archivo | Columnas principales | Uso |
|---|---|---|
| `referencia_piloto.csv` | `fila`, `comment_id`, `thread_id`, `is_reply`, `video_id`, `text_normalized`, `anotacion` | Referencia del piloto; `anotacion` usa el marcado `[unidad::ETIQUETA]` |
| `comentarios_youtube_normalizados.csv` | metadatos del video, `comment_id`, `parent_comment_id`, `thread_id`, `is_reply`, `total_thread_replies`, `comment_position`, `published_at`, `like_count`, `author_hash`, `comment_text`, `text_normalized`, `revisar` | Corpus de aplicación; `comment_text` ya está anonimizado |
| `comentarios_youtube.csv` | las columnas anteriores más `comment_text_raw` | Corpus crudo; `comment_text_raw` es el texto original y nunca se publica |
| `csl_excluidas.csv` | `comment_id`, `unidad` | Pares comentario/unidad dentro de una CSL, excluidos del puntaje |
| `listado_fuentes2009.csv` | `unidad`, `macrofuncion`, `categoria`, `subcategoria`, `polifuncional` | Listado de Fuentes Rodríguez (2009) |

`anotacion_final` no está en `referencia_piloto.csv`: es una columna del libro de
anotación y solo está llena en 48 de las 65 filas etiquetadas. `author_hash` es
un hash seudónimo del autor; no se publica y no debe entrar en los artefactos.
`@USER` es el marcador de mención anonimizada: el texto crudo no tiene ninguna y
el normalizado tiene 1.830; 1.814 filas cambian entre ambos.

El `video_id` de `referencia_piloto.csv` contiene un título de video, no un ID.
Se documenta así para no confundirlo con el `video_id` de la aplicación.

## Normalización

La normalización es determinista y se aplica en este orden: menciones a
`@USER`; emojis a texto; mayúsculas a minúsculas; risas a `ja`/`jaja`/`jajaja`;
alargamientos; abreviaciones; nombres y siglas; puntuación (`...` a `…`,
`???` a `?`); signos de apertura; mayúscula inicial de oración.

Cambia 6.984 comentarios (66,5 %), inserta 3.271 tokens de emoji y marca 50
filas en `revisar`. No agrega tildes, no corrige ortografía y no resuelve
*porque / por qué*. Puede borrar señales de énfasis (mayúsculas, alargamientos)
que separan un operador de un adverbio.

La normalización cambia el número de candidatas del corpus de aplicación:
19.741 sobre `comment_text` y 20.097 sobre `text_normalized` (+356). El pipeline
del piloto usa `text_normalized`.

## Candidatas

De las 284 coincidencias brutas del listado se excluyen 8 dentro de una
construcción semilibre (CSL) y 3 segundas piezas de una unidad mayor; quedan
273 candidatas (284 − 8 − 3 = 273). De las 273, 64 tienen etiqueta de referencia
y 209 son negativas implícitas (sin etiqueta). El listado no detecta 16
etiquetas de referencia; se cuentan como falsos negativos en la cobertura.

## Partición

La evaluación usa un 30 % de hilos en test y el resto en entrenamiento, con
semillas 0–4. Los IDs de test y sus hashes están congelados; no se vuelve a
ejecutar `GroupShuffleSplit`.

Cada semilla tiene 19 hilos de test. Las cinco semillas producen 439
apariciones de candidatas, 256 candidatas únicas vistas al menos una vez en
test y 17 candidatas que nunca entran en un test.

## Referencia

La referencia tiene 150 comentarios y 65 con al menos una etiqueta. El acuerdo
entre anotadores es variable: Jorge–Vannia coincide en 59 % de los comentarios
compartidos, Jorge–Javier en 51 % y Javier–Vannia en 50 %. La referencia está
más cerca de Vannia (58 de 65 filas etiquetadas idénticas). Por eso la etiqueta
se trata como adjudicada o seleccionada, no como verdad medida.

## Recolección y procedencia

- **Origen.** Comentarios públicos de YouTube de videos de noticias chilenas.
  El piloto tiene 6 videos y 4 canales; la aplicación tiene 20 videos y 3
  canales (Meganoticias 6.391; 24 Horas TVN 2.421; CHV Noticias 1.693).
- **Fechas.** Los comentarios de la aplicación van del 2023-03-21 al
  2026-11-14; 19 videos se publicaron entre abril y noviembre de 2026 y uno en
  marzo de 2023. La auditoría de entradas es del 2026-11-20. La fecha exacta de
  descarga o snapshot no está registrada en el repositorio.
- **Idioma y ruido.** El material es español de Chile; no se documenta un filtro
  de idioma explícito, sino una selección de canales de noticias. La
  normalización reduce ruido, pero no elimina spam, ironía, temas fuera de foco
  ni comentarios sin contexto.
- **Términos y retención.** El corpus está sujeto a los términos de la API de
  YouTube y a las condiciones del proyecto. El repositorio no redistribuye
  texto; `doc/` es local y está en `.gitignore`; solo se publican IDs, formas,
  etiquetas, conteos y métricas. La licencia del corpus y del listado, y la
  retención del texto, deben confirmarse con el equipo antes de publicar.
- **Relación piloto–aplicación.** Comparten cero IDs de comentario y tratan
  temas distintos: el piloto es sobre el alza de combustibles; la aplicación
  cubre seguridad, migración, delito y política social. La aplicación no tiene
  etiquetas y su ejecución está diferida.

## Privacidad

R5: el repositorio publica solo IDs, formas del listado, etiquetas, conteos y
métricas. Nunca se versionan texto de comentarios, ventanas de contexto ni
`author_hash`. Tampoco se publican nombres de usuario: `@USER` es el marcador
anonimizado; cualquier otro `@name` es un defecto.

`doc/` es material de origen de solo lectura y sus corpus están en
`.gitignore`. Los artefactos del pipeline se escriben en un directorio local y
no contienen texto.

## Limitaciones

- El piloto cubre un solo video y un solo tema; la partición por hilo no es una
  partición por video.
- El corpus de aplicación cambia de tema y no tiene etiquetas; no se puede
  medir su calidad con la referencia del piloto.
- Las 209 negativas implícitas dependen del supuesto de que fueron revisadas y
  rechazadas; la auditoría de 20 candidatas sigue diferida.
- 16 etiquetas no son detectables por el listado; la cobertura las incluye como
  falsos negativos.
- 17 candidatas nunca entran en un test; quedan fuera de la evaluación.
- La muestra por categoría es pequeña; los intervalos son anchos.

## Fuentes

- [`docs/00-brief.md`](00-brief.md)
- [`docs/results/data-overview/inputs-audit.md`](results/data-overview/inputs-audit.md)
- [`docs/results/data-overview/corpus-overview.md`](results/data-overview/corpus-overview.md)
- [`docs/results/0002-candidate-replay-diagnostics.md`](results/0002-candidate-replay-diagnostics.md)
- [`docs/results/0005-m2-replay-diagnostics.md`](results/0005-m2-replay-diagnostics.md)
- [`docs/model-card.md`](model-card.md)
