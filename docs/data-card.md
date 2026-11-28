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
categoría y 66 admiten varias; 155 están marcadas como polifuncionales.

Las 16 construcciones semilibres (CSL) anotadas se excluyen del puntaje: su
función pertenece a la construcción completa, no a la palabra suelta.

## Candidatas

Las 284 coincidencias brutas del listado se reducen a 273 candidatas:

- 8 coincidencias dentro de una CSL;
- 3 segundas piezas de una unidad mayor;
- 273 candidatas restantes.

De las 273, 64 tienen etiqueta de referencia y 209 son negativas implícitas
(sin etiqueta). El listado no detecta 16 etiquetas de referencia; se cuentan
como falsos negativos en la cobertura.

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
