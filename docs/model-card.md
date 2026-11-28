# Ficha de modelo — B0, B1, M1 y M2

**Proyecto:** Fondecyt 11260185 — conectores y operadores discursivos en
comentarios de YouTube en español de Chile.
**Tarea:** decidir, para cada coincidencia del listado de Fuentes Rodríguez
(2009), si tiene uso discursivo y qué categoría lleva.
**Estado:** sistemas del piloto reproducidos; corpus de aplicación diferido.

## Detalles del modelo

| Campo | Valor |
|---|---|
| Desarrollado por | Equipo 11: Diana Aguilera Fredes, Vannia Fernández-Mutis y Till Seyfarth |
| Financiado por | Fondecyt 11260185 |
| Fecha | 2026-11-27 |
| Versión | 0.1.0 (paquete S6; código `8686ba7`) |
| Tipo | Pipeline de clasificación de ocurrencias: regresión logística en dos pasos, reglas congeladas, POS de spaCy y embeddings congelados |
| Idioma | Español de Chile, comentarios de YouTube |
| Licencia | Pendiente de confirmar con el equipo; no hay archivo `LICENSE` en el repositorio |
| Cita | Pendiente de cita formal; ver “Cita, licencia y contacto” |
| Contacto | Issues del repositorio; contacto formal pendiente |
| Repositorio | <https://github.com/till75/Conectores-discursivos> |
| Artefacto | No hay modelo serializado: el pipeline se reajusta desde las entradas congeladas y el código versionado |
| Autores de la ficha | Equipo 11; edición de Till Seyfarth |

### Sistemas

| Sistema | Qué hace |
|---|---|
| B0 | Etiqueta cada coincidencia con la primera categoría del listado; ignora el contexto. |
| B1 | Etiqueta cada forma con su categoría más frecuente en entrenamiento; las formas no vistas usan la primera categoría del listado. |
| M1 | Regresión logística en dos pasos: uso discursivo y luego categoría, con ventana, TF-IDF, banderas y embeddings. |
| M2 | M1 + restricción estricta por el listado, 15 reglas congeladas, categorías gramaticales de spaCy, bandera de categoría rara y procedencia. |
| M1 con abstención | M1 con el margen aprendido; las probabilidades cercanas a 0,5 se abstienen. |
| M2 con abstención | M2 con el mismo protocolo de margen. |

B0 y B1 son baselines; M1 y M2 son los modelos entrenados. Las variantes con
abstención comparten el modelo y cambian el punto de operación.

## Uso previsto

**Usos primarios.** Asistir al anotador del equipo: proponer candidatas,
etiquetas, abstención y una cola de revisión con procedencia. Apoyar la
investigación del Fondecyt sobre conectores y operadores en español de Chile.

**Usuarios previstos.** Primero el anotador del equipo; segundo el equipo de
investigación del Fondecyt. No está pensado para el público general ni para
decisiones autónomas.

**Usos fuera de alcance.**

- Moderación automática de comentarios o decisiones sobre personas.
- Decisiones legales, laborales, médicas, educativas o de perfilamiento
  individual.
- Otras lenguas o variedades distintas del español de Chile en YouTube.
- Comentarios sin contexto, textos muy cortos o dominios no representados.
- Aplicar el sistema al corpus de aplicación como si estuviera validado: no
  tiene etiquetas de referencia.
- Usar las predicciones como verdad de referencia o como etiquetas definitivas.
- Publicar texto de comentarios, ventanas de contexto o `author_hash`.

**Uso directo.** Ejecutar el pipeline sobre comentarios normalizados y revisar
la cola de candidatas, la abstención y la bandera `revisar_categoria`.

**Uso posterior.** Investigación y anotación asistida dentro del piloto. No hay
un uso posterior validado fuera del piloto; el corpus de aplicación queda
diferido.

## Factores

Los factores relevantes son los que pueden cambiar el rendimiento. Solo algunos
se evaluaron de forma desagregada.

| Factor | ¿Relevante? | ¿Evaluado? | Nota |
|---|---|---|---|
| Unidad o forma del listado | Sí | Parcial | 614 formas; no se reporta F1 por forma |
| Categoría | Sí | No | 7 de 12 categorías tienen tres o menos ejemplos; solo se reporta macro CON/OP |
| Hilo | Sí | Sí | La partición y el bootstrap son por hilo |
| Video o tema | Sí | No | El piloto cubre un solo video |
| Comentario raíz vs respuesta | Sí | No | `is_reply` es un rasgo, no un eje de evaluación |
| Longitud del comentario | Sí | No | No se desagrega por longitud |
| Normalización | Sí | No | Cambia 6.984 comentarios y puede borrar énfasis |
| Anotador o adjudicación | Sí | No | La referencia es adjudicada o seleccionada, no acuerdo medido |
| Variedad de español | Sí | No | Solo español de Chile en YouTube |
| Corpus de aplicación | Sí | No | Sin etiquetas; ejecución diferida |

La evaluación desagrega por semilla e hilo. No hay análisis por categoría,
video, longitud, respuesta ni interseccional; esa ausencia es una limitación,
no una afirmación de equidad.

## Métricas y umbrales

| Métrica | Definición |
|---|---|
| F1 de etiqueta completa | F1 exacta entre la etiqueta predicha y la de referencia; métrica primaria |
| F1 de uso discursivo | F1 binaria entre uso discursivo y `NO_DISCURSIVO` |
| F1 macro CON/OP | Promedio de F1 para las macroclases `CON` y `OP` |
| Precisión | Verdaderos positivos / etiquetas predichas como discursivas |
| Cobertura | Verdaderos positivos / (etiquetas de referencia + no detectadas por el listado) |
| Abstención | Fracción de candidatas con `abs(p - 0,5) < margen` |

El margen se aprende dentro de entrenamiento con `GroupKFold` de 5 pliegues por
hilo, grilla de 0,00 a 0,30, tope de 20 % de abstención y margen menor en caso
de empate. El test no se usa para elegir el margen.

| Semilla | Margen | Abstención en test | M2 con abstención F1 |
|---|---:|---:|---:|
| 0 | 0.15 | 12,31 % | 0.452 |
| 1 | 0.10 | 5,15 % | 0.571 |
| 2 | 0.20 | 30,43 % | 0.476 |
| 3 | 0.10 | 8,87 % | 0.449 |
| 4 | 0.20 | 21,31 % | 0.615 |

La abstención media es 15,6 %. Las semillas 2 y 4 superan el 20 % en test; el
tope se aplica al pliegue de validación, no al resultado de test. En uso, la
abstención y `revisar_categoria` alimentan la revisión humana; no se debe bajar
el margen para maximizar cobertura sin revisar.

La incertidumbre se reporta con cinco semillas, media y desviación estándar, e
intervalos bootstrap por hilo. No se declara significación estadística.

## Datos de entrenamiento

El piloto tiene 1.268 comentarios de 6 videos y 798 hilos; la referencia son 150
comentarios, de los cuales 65 tienen al menos una etiqueta y 96 spans en 12
categorías. La referencia cubre un solo video (alza de combustibles).

Las 284 coincidencias brutas se reducen a 273 candidatas: 8 dentro de una CSL,
3 segundas piezas y 273 restantes. De ellas, 64 son positivas y 209 son
negativas implícitas; 16 etiquetas de referencia no son detectadas por el
listado. Las 16 CSL se excluyen del puntaje.

El listado tiene 705 filas y 614 formas; 548 formas admiten una sola categoría y
66 admiten varias. La normalización convierte menciones a `@USER`, emojis,
mayúsculas, risas, abreviaciones, nombres y puntuación; puede borrar señales de
énfasis.

La partición es por hilo, con semillas 0–4 y test congelado. El entrenamiento
tiene pocos positivos y clases desbalanceadas; por eso se reportan intervalos y
no se afirma estabilidad. Ver [`docs/data-card.md`](data-card.md).

## Datos de evaluación

La evaluación usa el mismo piloto: 150 comentarios de referencia, 65 con
etiqueta, un solo video. Cada semilla tiene 19 hilos de test; las cinco semillas
producen 439 apariciones, 256 candidatas únicas y 17 candidatas que nunca entran
en un test.

Los conteos de etiquetas no detectadas por semilla son 5/3/4/8/4; se incluyen
como falsos negativos en la cobertura. Las CSL se excluyen. Los IDs y hashes de
test están congelados y el pipeline no vuelve a ejecutar `GroupShuffleSplit`.

La motivación es el único conjunto con etiquetas del proyecto. No hay datos de
evaluación del corpus de aplicación, que cambia de tema y no tiene referencia.
Ver [`docs/data-card.md`](data-card.md).

## Análisis cuantitativos

Medias y desviaciones estándar sobre las cinco semillas:

| Sistema | F1 etiqueta | F1 uso | Macro CON/OP | Precisión | Cobertura |
|---|---:|---:|---:|---:|---:|
| B0 | 0.315 ± 0.035 | 0.388 ± 0.032 | 0.433 ± 0.032 | 0.207 ± 0.030 | 0.666 ± 0.033 |
| B1 | 0.328 ± 0.099 | 0.471 ± 0.136 | 0.493 ± 0.139 | 0.572 ± 0.099 | 0.236 ± 0.090 |
| M1 | 0.360 ± 0.108 | 0.499 ± 0.082 | 0.489 ± 0.144 | 0.438 ± 0.121 | 0.310 ± 0.108 |
| M2 | 0.483 ± 0.044 | 0.606 ± 0.019 | 0.634 ± 0.063 | 0.599 ± 0.050 | 0.407 ± 0.049 |
| M1 con abstención | 0.394 ± 0.096 | 0.516 ± 0.048 | 0.531 ± 0.115 | 0.528 ± 0.140 | 0.317 ± 0.077 |
| M2 con abstención | 0.513 ± 0.076 | 0.639 ± 0.046 | 0.689 ± 0.090 | 0.715 ± 0.112 | 0.401 ± 0.062 |

Por semilla:

| Semilla | B1 F1 | M2 F1 | M2 con abstención F1 | Margen | Abstención |
|---|---:|---:|---:|---:|---:|
| 0 | 0.444 | 0.432 | 0.452 | 0.15 | 12,31 % |
| 1 | 0.229 | 0.545 | 0.571 | 0.10 | 5,15 % |
| 2 | 0.278 | 0.500 | 0.476 | 0.20 | 30,43 % |
| 3 | 0.267 | 0.452 | 0.449 | 0.10 | 8,87 % |
| 4 | 0.424 | 0.486 | 0.615 | 0.20 | 21,31 % |

La ganancia media M2 − B1 es +0.155. Los intervalos M2 − B1 excluyen cero solo
en la semilla 3; M2 − M1 lo excluyen en las semillas 1 y 2. La ganancia es una
estimación puntual, no una prueba de significación.

La trazabilidad agregada es `91/58/34/33/20/43`: 91 etiquetas discursivas, 58
categorías fijadas por el listado (34 correctas), 33 elegidas por el modelo
(20 correctas) y 43 marcas de revisión. El listado fija 63,7 % de las
categorías; el modelo elige 36,3 %. La bandera de revisión cubre 43 de 91
etiquetas discursivas (47,3 %).

No hay análisis por categoría, video ni interseccional; la muestra no lo
sostiene. Las tablas por semilla y los intervalos completos están en
[`docs/results/0005-m2-replay-diagnostics.md`](results/0005-m2-replay-diagnostics.md).

## Riesgos, ética y recomendaciones

**Datos sensibles.** Se usan comentarios públicos de YouTube. R5 exige no
publicar texto, ventanas de contexto, `author_hash` ni `@name`; solo IDs, formas,
etiquetas, conteos y métricas. `@USER` es el marcador anonimizado.

**Personas afectadas.** Autores de los comentarios (privacidad), anotadores
(carga de revisión) e investigadores (validez de las conclusiones).

**Riesgos y daños.**

- **Falsos negativos:** un conector omitido desaparece del corpus; la cobertura
  es 0.407 y 16 etiquetas no son detectables por el listado.
- **Falsos positivos:** una falsa alarma consume tiempo del anotador; la
  precisión es 0.599.
- **Sesgo y validez:** un solo video, un solo tema, referencia adjudicada y
  muestra pequeña; 7 de 12 categorías tienen tres o menos ejemplos.
- **Cambio de dominio:** el corpus de aplicación trata otros temas y no tiene
  etiquetas; no se puede afirmar que el sistema generalice.
- **Exceso de confianza:** las predicciones son propuestas, no verdad de
  referencia; la abstención y la revisión humana son obligatorias.
- **Privacidad:** cualquier fuga de texto o de nombres de usuario viola R5.
- **Normalización:** borra mayúsculas, alargamientos y otras señales de énfasis
  que pueden distinguir un operador de un adverbio.
- **Punto de operación:** dos semillas superan el 20 % de abstención en test; el
  margen no es universal.
- **Mal uso:** moderación automática, perfilamiento individual, inferencia
  política o vigilancia.

**Recomendaciones.**

- Mantener la revisión humana y la cola de revisión; no automatizar decisiones.
- Usar la abstención y `revisar_categoria`; no bajar el margen para maximizar
  cobertura sin revisar.
- Reportar cobertura y falsos negativos, no solo F1.
- Revalidar en videos y temas nuevos, y en el corpus de aplicación, antes de
  afirmar generalización.
- Mantener R5 y el escaneo de `@name`; no publicar texto.
- Versionar la ficha y repetir los tests lentos cuando cambien reglas, split,
  modelos o dependencias.
- No usar el sistema para decisiones legales, laborales, médicas, educativas o
  de perfilamiento individual.

No consta una revisión ética externa; el equipo revisa los usos y la
privacidad.

## Limitaciones

- El piloto cubre un solo video y un solo tema; la partición por hilo no mide
  generalización a otro video.
- El corpus de aplicación cambia de tema y no tiene etiquetas.
- Las 209 negativas implícitas son un supuesto; la auditoría de 20 candidatas
  sigue diferida.
- 16 etiquetas no son detectables por el listado y 17 candidatas nunca entran en
  un test.
- La muestra es pequeña; 7 de 12 categorías tienen tres o menos ejemplos; los
  intervalos son anchos y no se declara significación.
- El embedding es externo y congelado; no se entrenó con las etiquetas del
  piloto, pero puede haber visto texto parecido.
- La regla de `inicio_oracion`/`_pregunta` que trata el salto de línea como
  frontera de oración está congelada; cambiarla exige un ADR.
- El tope medio de abstención se cumple, pero dos semillas superan el 20 % en
  test.
- No hay análisis por categoría, video, longitud, respuesta ni interseccional.
- B0 y B1 son baselines simples; no representan el estado del arte.
- No hay modelo serializado: el pipeline se reajusta; la reproducibilidad
  depende de las entradas, el código y las versiones del entorno.
- La referencia es adjudicada o seleccionada, no una medida de acuerdo.

## Especificaciones técnicas

| Campo | Valor |
|---|---|
| Lenguaje | Python 3.14 |
| Entorno | `.venv`; Windows/PowerShell; solo CPU |
| scikit-learn | 1.9.1 observado |
| numpy | 2.5.5 observado |
| pandas | 3.1.1 observado |
| scipy | 1.18.1 observado |
| spaCy | 3.8.18 observado; modelo `es_core_news_sm` |
| Embeddings | `paraphrase-multilingual-MiniLM-L12-v2`, 384 dimensiones, CPU, congelado |
| Entrenamiento | Regresión logística en dos pasos; `C=1.0`; `max_iter=2000`; semillas 0–4 |
| Margen | `GroupKFold` de 5 pliegues por hilo; grilla 0,00–0,30; tope 20 %; margen menor en empate |
| Reproducibilidad | El desempate de `GroupKFold` anterior al cambio de scikit-learn se reproduce explícitamente |
| Latencia | p95 0.081 s por comentario en el piloto (R6; objetivo ≤ 1 s); no re-medida en S6 |
| Serialización | No hay artefacto de modelo; el pipeline se reajusta |

`pyproject.toml` declara versiones mínimas, no versiones exactas; las versiones
de la tabla son las observadas en el entorno de reproducción. Para reproducir
los números publicados hay que usar el entorno del repositorio y comprobar los
tests lentos.

## Impacto ambiental

No se midió energía ni carbono. El entrenamiento y la inferencia son locales,
solo CPU, sin GPU y sin API pagada; el embedding se usa congelado. No hay una
estimación de kWh ni de CO₂ que reportar. El costo computacional es bajo, pero
“bajo” no es una medición.

## Privacidad

R5: el pipeline y esta ficha no publican texto de comentarios, ventanas de
contexto ni `author_hash`. Solo se usan IDs, formas, etiquetas, conteos y
métricas. `@USER` es el marcador anonimizado; cualquier otro `@name` es un
defecto.

Los comentarios son públicos, pero se aplican minimización y anonimización. El
pipeline lee texto en memoria para candidatas, embeddings y spaCy; escribe solo
la tabla pública y los agregados. `doc/` es de solo lectura y está gitignored.
La revisión humana es parte del uso previsto. Ver
[`docs/data-card.md`](data-card.md).

## Cita, licencia y contacto

**Licencia.** Pendiente de confirmar con el equipo. No hay archivo `LICENSE` en
el repositorio a la fecha. El código, el listado, el corpus y el modelo de
embeddings pueden tener condiciones distintas; hay que revisarlas antes de
publicar o reutilizar.

**Cita sugerida.** Equipo 11 (2026). *Conectores discursivos: anotación
automática de conectores y operadores en comentarios de YouTube*. Fondecyt
11260185. <https://github.com/till75/Conectores-discursivos>. La cita formal
está pendiente.

**Contacto.** Issues del repositorio para preguntas, correcciones o
actualizaciones de la ficha. El contacto formal del equipo está pendiente.

**Autores de la ficha.** Equipo 11; edición de Till Seyfarth.
**Versión de la ficha.** 2026-11-27, v1.

## Reproducción

Comandos rápidos:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q -m slow
.\.venv\Scripts\python.exe -m conectores.pipeline --help
```

El comando completo del paquete de publicación, con la extracción del zip y las
rutas de las entradas congeladas, está en [`README.md`](../README.md).

- [`docs/data-card.md`](data-card.md) — corpus, partición y privacidad.
- [`docs/specs/0005-m2-replay.md`](specs/0005-m2-replay.md) — contrato de M2.
- [`docs/results/0005-m2-replay-diagnostics.md`](results/0005-m2-replay-diagnostics.md)
  — evidencia del replay de M2.
- [`docs/results/0006-publication-pack-diagnostics.md`](results/0006-publication-pack-diagnostics.md)
  — evidencia del paquete de publicación.
- [`docs/results/0001-metric-replay-diagnostics.md`](results/0001-metric-replay-diagnostics.md)
  — tabla de métricas publicada.
