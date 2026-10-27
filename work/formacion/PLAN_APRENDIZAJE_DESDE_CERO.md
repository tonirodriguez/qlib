# Plan de aprendizaje desde cero — Investigación cuantitativa rigurosa

> **Fecha:** 2026-10-27
> **Objetivo:** construir la base metodológica que permite distinguir un
> resultado real de un artefacto.
> **Duración:** 8-10 semanas a ~5 h/semana, o 4 semanas intensivas.
> **Requisito:** Python y pandas a nivel de uso diario. Estadística de
> instituto (media, desviación, correlación).

---

## Principio cero

> **Valida tu herramienta con datos donde YA SABES la respuesta, antes de
> usarla con datos donde no la sabes.**

Es el principio que más veces salvó este proyecto: tres de los cuatro errores
graves se detectaron porque un test sintético con respuesta conocida no daba
lo que debía (un look-ahead que hacía que el azar ganara, un signo de drawdown
invertido, un cap de pesos que no respetaba el límite).

Sin ese principio, un backtester con un bug **produce números plausibles
durante meses**.

Cada nivel de este plan incluye un **test de respuesta conocida**. No es
opcional: es la puerta de entrada al siguiente nivel.

---

## Las tres reglas del curso

1. **Ningún resultado se interpreta sin su hipótesis nula.** Si no sabes qué
   saldría sin señal, no sabes qué significa tu resultado.
2. **Un resultado negativo es un entregable.** Se documenta con el mismo rigor
   que uno positivo.
3. **No se persigue alfa.** El curso es sobre método. Si en el camino aparece
   una señal, se anota y se prueba **después** del nivel 6, con las reglas del
   nivel 6.

Tampoco en este curso: modelos de machine learning (nivel posterior), datos de
pago, ni capital real.

---

# Nivel 0 — Los datos

**Duración:** 1 semana

### Lo que vas a aprender

Un backtest es, antes que nada, una afirmación sobre unos datos. Si los datos
mienten, todo lo demás sobra.

- Retorno **simple** vs **logarítmico**: cuándo usar cada uno y por qué suman distinto.
- **Precio vs total return**: splits, dividendos, y por qué dos series del mismo activo pueden diferir 2,6 pp/año.
- **Sesgo de supervivencia**: por qué un universo actual de S&P 500 no es el universo de 2018.
- **Datos point-in-time**: lo que sabías en la fecha t, no lo que se publicó después.
- **Huecos**: `ffill`, `bfill` y cómo el relleno hacia atrás mete el futuro en el pasado.

### Ejercicio

Audita el dataset US de qlib (`~/.qlib/qlib_data/us_data`) y responde por
escrito:

1. ¿Qué es exactamente `$close`? ¿Y `$factor`? ¿Cuál de los dos incluye dividendos?
2. ¿Cuántos tickers tienen historia completa en 2018-2026? ¿Cuántos entran y salen?
3. ¿Qué porcentaje de celdas son NaN? ¿Están concentrados en fechas o en tickers?
4. ¿El universo `sp500.txt` tiene sesgo de supervivencia? ¿Cómo lo comprobarías?
5. Calcula el dividend yield implícito del universo. ¿Coincide con el real?

### Entregable

`nivel0_auditoria_datos.py` + `nivel0_informe.md` (1 página, con las respuestas
y **tres riesgos concretos** que hayas identificado).

### Test de respuesta conocida

Construye un precio sintético con:
- 2 splits conocidos (2:1 y 3:1)
- dividendo del 2% anual

Calcula el total return por dos caminos y comprueba que coincide con el que
**tú mismo generaste**. Si tu método de ajuste no recupera el número que
pusiste, el método está mal.

### Sabes que lo tienes cuando...

Puedes explicar por qué dos series del mismo activo difieren 2,64 pp/año y en
qué situación usarías cada una.

---

# Nivel 1 — El motor de backtest

**Duración:** 2 semanas (es el nivel más largo, y el más importante)

### Lo que vas a aprender

Vas a escribir tu propio backtester. **Sin qlib.** Unas 100-150 líneas.

La razón: usar una herramienta que no controlas es cómodo hasta que produce un
número que no entiendes. Escribirla te obliga a decidir, y cada decisión es una
fuente de error que aprenderás a reconocer.

- Pesos, rebalanceo, **turnover**
- Costes: comisión, spread, slippage, impacto
- Ejecución: ¿al cierre o a la apertura? ¿con retardo de un día?
- **Look-ahead** en la ejecución: el error de aplicar los pesos del día t al retorno del día t
- Capacidad: por qué una estrategia de 30 millones no escala a 3.000

### Ejercicio

Implementa:

```
entrada:  precios (DataFrame fechas × tickers), calendario de pesos, coste en bps
salida:   serie de retornos diarios netos de costes
```

Sin mirar código ajeno. Cuando funcione, compáralo con una implementación
independiente que escribas después.

### Entregable

`motor_bt.py` con docstring explicando **cada decisión de diseño** y por qué.

### Test de respuesta conocida

Cuatro comprobaciones, las cuatro obligatorias:

1. **Un solo activo, sin costes:** el retorno debe ser exactamente el del activo.
2. **Pesos constantes, sin costes:** debe coincidir con la fórmula analítica de
   rebalanceo periódico.
3. **Turnover:** debe coincidir con la suma manual `0.5·Σ|w_nuevo − w_viejo|`.
4. **Truncamiento:** corta los datos en una fecha, recalcula, y comprueba que
   **el pasado no cambia** (diferencia < 1e-12).

La cuarta es la que detecta look-ahead. Si el pasado cambia al añadir futuro,
tienes una fuga.

### Sabes que lo tienes cuando...

Dos implementaciones independientes dan el mismo resultado, y el test de
truncamiento pasa en verde.

---

# Nivel 2 — Estadística para muestras pequeñas

**Duración:** 1-2 semanas

### Lo que vas a aprender

El nivel que explica por qué casi todos los backtests publicados son falsos.

- **Independencia**: por qué 556.582 filas pueden ser 17 observaciones
- **Tamaño efectivo de muestra**: cómo contarlo de verdad
- **Error estándar e intervalo de confianza**: qué significa "IC = 0,032 ± 0,05"
- **Solapamiento**: labels de 120 días comparten 119 días; el t se infla
- **Potencia**: `n ≈ (t/r)²` — cuántas observaciones necesitas antes de empezar

### Ejercicio

Implementa una función que, dada una señal y un retorno futuro, devuelva:

- IC (correlación de rango, por fecha, en sección cruzada)
- Intervalo de confianza **honesto** (no el clásico inflado)
- t corregido por solapamiento
- El **n efectivo**, no el n aparente

### Entregable

`estadistica.py`

### Test de respuesta conocida

Genera 1.000 datasets donde **tú impones** que el IC sea 0,05. Entonces:

1. La media de los IC estimados debe rondar 0,05 (insesgado).
2. En el **95%** de los casos, el IC verdadero debe caer dentro del intervalo
   de confianza que calculaste. Si cae solo en el 60%, tu intervalo es
   demasiado estrecho — que es exactamente el error a evitar.
3. Con labels solapados, el t clásico debe inflarse y el tuyo no.

### Sabes que lo tienes cuando...

Puedes responder **antes de medir**: *"con estos datos, el efecto más pequeño
que puedo detectar es X. Si el efecto real es menor, no concluiré nada."*

---

# Nivel 3 — La hipótesis nula

**Duración:** 1-2 semanas

### Lo que vas a aprender

El concepto que faltaba en todo el proyecto anterior.

- **Distribución nula**: qué resultados salen cuando NO hay señal
- **Bootstrap y block bootstrap**: remuestrear preservando la estructura (volatility clustering)
- **Permutación**: romper la relación señal-resultado y ver qué queda
- **p-valor**: qué mide y qué no mide
- **Múltiples comparaciones**: `1 − 0,95^k`. Con 30 intentos, 79% de falso descubrimiento.
- **Deflated Sharpe**: corregir el Sharpe por el número de intentos

### Ejercicio

El experimento central del curso:

1. Genera **200 mercados sintéticos** por block-bootstrap de los retornos
   reales del universo. En ellos **no hay señal por construcción**.
2. Corre en cada uno una estrategia de selección (top-30 por cualquier criterio).
3. Guarda la distribución de Sharpes resultante.

### Entregable

`calibracion_nula.py` + histograma + las tres conclusiones por escrito.

### Test de respuesta conocida

Sobre datos **puramente aleatorios**, tu test de significancia debe rechazar la
hipótesis nula **~5% de las veces**, no 50%.

Si rechaza más, tu test está roto. Lo sabes sin ambigüedad, porque en datos
aleatorios la respuesta correcta es conocida.

### Sabes que lo tienes cuando...

Puedes decir: *"un Sharpe de X es lo normal por azar si he hecho K intentos.
Mi resultado está por encima / dentro / por debajo de eso."*

---

# Nivel 4 — Factores y atribución

**Duración:** 1 semana

### Lo que vas a aprender

La diferencia entre **beta** (estar en el mercado) y **alfa** (habilidad).

- CAPM: retorno = alfa + beta · mercado + ruido
- Fama-French: añadir tamaño y valor
- Momentum como factor
- Regresión: qué significan los coeficientes, y el R²
- **Descomposición**: cuánto de mi retorno se explica y cuánto sobra

### Ejercicio

1. Construye los factores que puedas con datos gratuitos: mercado (^GSPC),
   tamaño (diferencia entre los pequeños y los grandes), y momentum.
2. Regresa los retornos de **cualquier** cartera contra ellos.
3. Responde: ¿cuánto es mercado? ¿cuánto es tamaño? ¿cuánto sobra?

### Entregable

`atribucion.py` + una tabla de descomposición.

### Test de respuesta conocida

- Una cartera que **es exactamente el mercado** debe dar: beta = 1,00, alfa = 0,00, R² = 1,00.
- Una cartera que es el mercado ×2 debe dar beta = 2,00.
- Una cartera aleatoria de 30 acciones debe dar alfa ≈ 0 **y beta ≈ 1**.

Si tu regresión no reproduce estos casos, está mal especificada.

### Sabes que lo tienes cuando...

Antes de llamar "alfa" a un retorno, lo has descompuesto.

---

# Nivel 5 — Validación temporal

**Duración:** 1 semana

### Lo que vas a aprender

Por qué el k-fold estándar **rompe** con series temporales, y qué se usa en su
lugar.

- Por qué no puedes mezclar aleatoriamente el pasado y el futuro
- **Walk-forward**: entrenar en el pasado, probar en el futuro
- **Purged CV**: eliminar las observaciones cuyos labels se solapan con el test
- **Embargo**: dejar un hueco entre train y test
- Por qué "dividir por número de filas" no es purgar nada

### Ejercicio

Implementa purged CV con embargo y **demuéstralo**:

1. Genera datos donde la relación señal-retorno sea **cero** por construcción.
2. Con k-fold ingenuo, el IC debe salir **inflado** (positivo).
3. Con purged CV + embargo, debe salir **≈ 0**.

Si tu purged CV no corrige el sesgo, no está purgando.

### Entregable

`purged_cv.py`

### Test de respuesta conocida

El del punto 2-3. Es un test perfecto porque conoces la respuesta: cero.

### Sabes que lo tienes cuando...

Puedes mirar cualquier script de validación y decir si realmente purga o solo
lo aparenta.

---

# Nivel 6 — El protocolo de investigación

**Duración:** 1 semana

### Lo que vas a aprender

El nivel que convierte el conocimiento técnico en investigación.

- **Pre-registro**: escribir la hipótesis y el criterio de decisión **antes** de mirar los datos
- **Hipótesis nula obligatoria** en cada test
- **Registro de intentos**: contar cuántas variantes se prueban
- **Holdout**: reservar datos y no tocarlos
- **Resultados negativos**: cómo se documentan

### Ejercicio

Coge **una** hipótesis. Escribe su pre-registro:

```markdown
## Hipótesis 001

**Predicción:** [qué espero]
**Datos:** [universo, periodo, frecuencia]
**Test:** [exactamente qué voy a medir]
**Hipótesis nula:** [contra qué me comparo]
**Criterio de éxito:** [qué número me haría adoptarla]
**Criterio de abandono:** [qué número me haría descartarla]
**Número de variantes que probaré:** [N, y no más]
**Fecha de pre-registro:** [antes de ejecutar]
```

Después ejecútala **una sola vez** y documenta el resultado, sea cual sea.

### Entregable

`hipotesis/001_*.md` con el pre-registro y el resultado.

### Test de respuesta conocida

Aquí el test no es técnico: **el criterio de abandono estaba escrito antes del
resultado**. Si lo ajustaste después, has fallado el nivel.

### Sabes que lo tienes cuando...

Puedes entregar un resultado negativo sin sentir que has perdido el tiempo.

---

# Calendario

| Semana | Nivel | Entregable |
|---|---|---|
| 1 | 0 — Datos | Auditoría + informe |
| 2-3 | 1 — Motor de backtest | `motor_bt.py` + 4 tests |
| 4-5 | 2 — Estadística | `estadistica.py` + cobertura 95% |
| 6-7 | 3 — Hipótesis nula | `calibracion_nula.py` + histograma |
| 8 | 4 — Factores | `atribucion.py` + descomposición |
| 9 | 5 — Validación temporal | `purged_cv.py` |
| 10 | 6 — Protocolo | `hipotesis/001_*.md` |

Si un nivel se alarga, se alarga. **No se salta el test de respuesta conocida.**

---

# Lectura (mínima y dirigida)

No antes de empezar el nivel correspondiente:

| Nivel | Lectura |
|---|---|
| 0 | Documentación de qlib sobre `$factor`; cualquier nota sobre ajuste por splits |
| 1 | *Advances in Financial Machine Learning*, cap. 1-2 (estructura de datos financieros) |
| 2 | Cualquier texto de inferencia estadística, capítulo de intervalos de confianza |
| 3 | Bailey et al. (2016), *The Probability of Backtest Overfitting* |
| 3 | Bailey & López de Prado (2014), *The Deflated Sharpe Ratio* |
| 4 | Ang, *Asset Management*, cap. 2-4 (beta vs alfa) |
| 5 | *Advances in Financial Machine Learning*, cap. 7 (purged CV) |
| 6 | Harvey, Liu & Zhu (2016), *…and the Cross-Section of Expected Returns* |

---

# Criterio de finalización

El curso está terminado cuando puedes hacer esto **sin ayuda**:

1. Dado un dataset, auditar su integridad y detectar 3 formas de fuga.
2. Dado un backtest ajeno, encontrar el look-ahead en menos de 10 minutos.
3. Dada una señal, decir **antes de medir** si el dataset permite concluir algo.
4. Dada una estrategia, construir su hipótesis nula.
5. Dado un retorno, descomponerlo en factores.
6. Dado un resultado positivo, calcular cuántos intentos lo invalidarían.

Y sobre todo: **entregar un resultado negativo con la misma calidad que uno
positivo.**

---

# Lo que este curso NO es

- No es una ruta para batir al mercado.
- No es una introducción a machine learning.
- No es una colección de tutoriales.

Es entrenamiento para **no engañarte a ti mismo con datos**. Que es más
difícil de lo que parece, y más útil de lo que promete.

---

*Plan creado el 2026-10-27. Cada nivel produce un artefacto reutilizable y
verificable. El progreso no se mide por niveles leídos, sino por tests de
respuesta conocida superados.*
