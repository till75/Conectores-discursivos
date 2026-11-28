# Ficha de modelo — B0, B1, M1 y M2

**Proyecto:** Fondecyt 11260185.
**Tarea:** decidir, para cada coincidencia del listado, si tiene uso discursivo
y qué categoría lleva.
**Estado:** sistemas del piloto reproducidos; corpus de aplicación diferido.

## Sistemas

| Sistema | Qué hace |
|---|---|
| B0 | Etiqueta cada coincidencia con la primera categoría del listado; ignora el contexto. |
| B1 | Etiqueta cada forma con su categoría más frecuente en entrenamiento; las formas no vistas usan la primera categoría del listado. |
| M1 | Regresión logística en dos pasos: uso discursivo y luego categoría, con ventana, TF-IDF, banderas y embeddings. |
| M2 | M1 + restricción estricta por el listado, 15 reglas congeladas, categorías gramaticales de spaCy, bandera de categoría rara y procedencia. |
| M1 con abstención | M1 con el margen aprendido; las probabilidades cercanas a 0,5 se abstienen. |
| M2 con abstención | M2 con el mismo protocolo de margen. |

## Rasgos

- Ventana de ±6 palabras alrededor de la coincidencia, con la unidad marcada
  como `[[...]]`.
- TF-IDF de palabras (1–2 gramos), de caracteres (`char_wb`, 2–5) y de la
  unidad.
- Seis banderas: coma antes, coma después, inicio de comentario, inicio de
  oración, fin de enunciado y si es respuesta.
- Embedding congelado de la ventana, 384 dimensiones
  (`paraphrase-multilingual-MiniLM-L12-v2`), en CPU.
- 15 reglas de contexto congeladas el 25 de noviembre de 2026.
- UPOS de la unidad y de sus vecinos, más el token anterior y siguiente.
- Bandera `revisar_categoria` para categorías con menos de 5 ejemplos de
  entrenamiento.

## Entrenamiento

El modelo es una regresión logística en dos pasos, con `C=1.0`,
`max_iter=2000` y `random_state` fijado por semilla. El paso 1 usa
`class_weight="balanced"`; el paso 2 se entrena solo con las filas positivas.

Las semillas son 0–4. La partición es por hilo y los IDs de test están
congelados. El margen de abstención se aprende dentro de entrenamiento con
`GroupKFold` de 5 pliegues por hilo, una grilla de 0,00 a 0,30 en pasos de
0,05, un tope de 20 % de abstención y la regla de conservar el margen menor en
caso de empate. El test nunca se usa para elegir el margen.

Para reproducir los márgenes publicados se conserva el desempate de
`GroupKFold` anterior al cambio de scikit-learn: los grupos del mismo tamaño se
ordenan con `np.argsort` inestable antes de invertir el orden. La versión
1.9.1 usa un orden estable y cambia los pliegues y los márgenes de M2.

## Métricas

La métrica primaria es F1 de etiqueta completa. También se reportan F1 de uso
discursivo, F1 macro CON/OP, precisión y cobertura. La cobertura incluye como
falsos negativos las etiquetas que el listado no detecta. Los intervalos se
calculan por bootstrap de hilos. El orden de filas del test publicado fija el
orden de remuestreo; no se leen etiquetas ni probabilidades publicadas para
construir las predicciones.

## Resultados

En el piloto, M2 obtiene F1 de etiqueta 0.483 y M2 con abstención 0.513. B1
obtiene 0.328; la ganancia media es +0.155. La cobertura media es 0.407 y la
precisión 0.599.

La abstención media es 15,6 %. Las semillas 2 (30,43 %) y 4 (21,31 %) superan
el 20 % en test; el tope del 20 % se aplica al pliegue de validación, no al
resultado de test.

La trazabilidad agregada es `91/58/34/33/20/43`: 91 etiquetas discursivas, 58
categorías fijadas por el listado (34 correctas), 33 elegidas por el modelo
(20 correctas) y 43 marcas de revisión.

Los intervalos M2 − B1 excluyen cero solo en la semilla 3; M2 − M1 lo excluyen
en las semillas 1 y 2. La ganancia es una estimación puntual, no una prueba de
significación.

## Uso previsto

El sistema asiste al anotador: propone candidatas, etiquetas, abstención y una
cola de revisión con procedencia. No es un anotador autónomo. La decisión final
y la revisión de categorías raras son humanas.

El corpus de aplicación no tiene etiquetas; su ejecución queda diferida y no se
usa para afirmar calidad.

## Limitaciones

- El piloto cubre un solo video y un solo tema; la partición por hilo no mide
  generalización a otro video.
- El corpus de aplicación cambia de tema; no hay referencia para medirlo.
- Las 209 negativas implícitas son un supuesto; la auditoría de 20 candidatas
  sigue diferida.
- 16 etiquetas no son detectables por el listado y 17 candidatas nunca entran
  en un test.
- La muestra es pequeña; los intervalos son anchos y no se declara
  significación.
- El embedding es externo y congelado; no se entrenó con las etiquetas del
  piloto, pero puede haber visto texto parecido.
- La regla de `inicio_oracion`/`_pregunta` que trata el salto de línea como
  frontera de oración está congelada; cambiarla exige un ADR.
- El tope medio de abstención se cumple, pero dos semillas superan el 20 % en
  test.

## Privacidad

R5: el pipeline y esta ficha no publican texto de comentarios, ventanas de
contexto ni `author_hash`. Solo se usan IDs, formas, etiquetas, conteos y
métricas. `@USER` es el marcador anonimizado; cualquier otro `@name` es un
defecto. La revisión humana es parte del uso previsto.

## Reproducción

- [`README.md`](../README.md) — comandos de instalación, tests y pipeline.
- [`docs/data-card.md`](data-card.md) — corpus, partición y privacidad.
- [`docs/specs/0005-m2-replay.md`](specs/0005-m2-replay.md) — contrato de M2.
- [`docs/results/0005-m2-replay-diagnostics.md`](results/0005-m2-replay-diagnostics.md)
  — evidencia del replay de M2.
- [`docs/results/0001-metric-replay-diagnostics.md`](results/0001-metric-replay-diagnostics.md)
  — tabla de métricas publicada.
