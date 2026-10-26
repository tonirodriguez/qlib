# Guía Jev — Clasificación de régimen y sizing de exposición

> ## ⛔ VEREDICTO FINAL: NO ADOPTAR
>
> **Jev NO se usará para sizing de exposición.** Se probaron **7 fórmulas** de
> conversión sobre 2018–2026 y **ninguna supera al `vol_gate` que ya tenemos**.
> La causa raíz está identificada y es estructural: **las probabilidades de Jev
> no tienen resolución suficiente** — nunca superó `P(crisis) > 0.5` en 9 años.
>
> **Acción:** quedarse con `vol_gate.py`. No añadir la dependencia de OpenRouter.
> La infraestructura queda como referencia para evaluar futuros modelos de decisión.
>
> Ver [sección 10](#10-veredicto-final-fase-2-cerrada) para el detalle completo.

> **Qué es:** una capa de decisión que convierte indicadores de mercado en una
> exposición concreta de cartera, usando un modelo de decisiones (Jev, de
> TypeSafe) servido vía OpenRouter.
>
> **Estado:** Fase 1 y Fase 2 **cerradas**. Resultado negativo.
> **No está en producción.** No toca el paper-trading vivo. No toca `vol_gate.py`.

---

## Índice

1. [Qué utilizamos y por qué](#1-qué-utilizamos-y-por-qué)
2. [Qué aporta a la estrategia](#2-qué-aporta-a-la-estrategia)
3. [Cómo se integra en nuestras estrategias](#3-cómo-se-integra-en-nuestras-estrategias)
4. [Arquitectura de ficheros](#4-arquitectura-de-ficheros)
5. [Cómo ejecutarlo](#5-cómo-ejecutarlo)
6. [Parámetros, uno por uno](#6-parámetros-uno-por-uno)
7. [Configuración óptima](#7-configuración-óptima)
8. [Solución de problemas](#8-solución-de-problemas)
9. [Limitaciones y advertencias](#9-limitaciones-y-advertencias)
10. [**Veredicto final — Fase 2 cerrada**](#10-veredicto-final-fase-2-cerrada)

---

## 1. Qué utilizamos y por qué

### El problema que resuelve

Tenemos un motor de momentum (top-30 semanal sobre `sp500_liquid`) que funciona
**en promedio**, pero sufre cuando el mercado entra en estrés. Ya lo medimos en
`regimen_test.py`: el IC del momentum cae en estados de volatilidad alta.

Nuestro enfoque actual es un `vol_gate`: si la volatilidad está por encima del
percentil 90, salimos; entre el 75 y el 90, media posición. Es una regla de
**tres estados con umbrales fijos**.

### Por qué Jev y no otro enfoque

Jev no es un LLM de chat. Es un **modelo de decisiones**: recibe un estado y
preguntas, y devuelve opciones **con probabilidades calibradas**:

```json
{"choice": "crisis",
 "probabilities": {"risk_on": 0, "neutral": 0.03, "risk_off": 0.09, "crisis": 0.88},
 "confidence": 0.84}
```

Eso es lo que buscábamos: **un vector de probabilidad, no una etiqueta**. Con una
etiqueta habríamos construido otro `if vol > umbral`, sin ganar nada sobre
`vol_gate`. Con probabilidades podemos hacer *sizing continuo*.

### Las tres razones para usarlo

1. **Sizing gradual en vez de discreto.** `vol_gate` da 0, 0.5 o 1.0. Jev da un
   valor continuo que distingue "crisis al 88%" de "crisis al 100%".
2. **Combina varios indicadores a la vez.** `vol_gate` solo mira volatilidad.
   Jev recibe volatilidad, drawdown y correlación, y los pondera.
3. **Coste despreciable.** ~$0.000022 por decisión. Clasificar 2.000 días de
   historia cuesta **~$0.044**.

### Lo que NO es

- No es un generador de texto. No sirve para redactar análisis.
- No es un modelo de forecasting. **No predice retornos**: clasifica el estado
  *actual* del mercado. La hipótesis es que reducir exposición en estados de
  estrés mejora el perfil riesgo/retorno, no que Jev adivine el futuro.
- No está en producción. Es una línea de investigación con backtest pendiente.

---

## 2. Qué aporta a la estrategia

### Aportación concreta

| Aspecto | `vol_gate` actual | Capa Jev |
|---|---|---|
| Entradas | 1 (volatilidad) | 3+ (vol, drawdown, correlación) |
| Salida | Discreta (0 / 0.5 / 1.0) | Continua (0.00 – 1.00) |
| Umbrales | Fijos (p75, p90) | Aprendidos por el modelo |
| Coste | 0 | ~$0.000022/decisión |

### La fórmula de sizing

```
exposicion = 1 − P(crisis) − 0.5 · P(risk_off)     acotada a [0, 1]
```

- `crisis` resta exposición completa → posición fuera.
- `risk_off` resta media exposición → recorte parcial.
- `neutral` y `risk_on` no restan.

**Ejemplo real medido** (estado tipo 2008, vol p97 + drawdown −28%):

```
P(crisis)=0.88, P(risk_off)=0.09
exposicion = 1 − 0.88 − 0.5·0.09 = 0.075   →  7,5 % de exposición
```

En un mercado calmado la fórmula devuelve **1.00** (exposición plena). Es
monótona: más probabilidad de crisis ⇒ menos exposición, siempre.

### La pregunta que responde el backtest

**¿Jev aporta algo sobre el `vol_gate` que ya tenemos?**

Por eso el backtest compara **tres** estrategias sobre el mismo motor, no dos:

| | Exposición | Papel |
|---|---|---|
| **A** | 1.0 siempre | Baseline |
| **B** | `vol_gate` | El rival a batir |
| **C** | Fórmula Jev | El candidato |

Si Jev no supera a B, **no merece la pena** añadir una dependencia de API
externa. Ese es un resultado perfectamente válido y probable.

### Cómo se mide

- **Sharpe** — retorno ajustado por riesgo. Métrica principal.
- **MaxDD** — caída máxima. Aquí es donde un buen gate debería ayudar.
- **CAGR** — retorno anualizado.
- **Exposición media** — cuánto tiempo estamos dentro. Un gate que reduce el
  Sharpe pero también el drawdown puede ser útil según el mandato.

---

## 3. Cómo se integra en nuestras estrategias

### Flujo completo

```
extract_estados.py          →  indicadores de régimen (vol_pct, drawdown120, mom_crash)
        ↓
jev_regime.py               →  clasificación + fórmula de sizing
        ↓
exposición (0.00 – 1.00)    →  multiplicador
        ↓
simulate.py / simulate_pead.py  →  aplica el multiplicador al top-30
```

### Punto de integración en el paper-trading

El paper-trading actual (`simulation/simulate.py`) asigna capital igualitario
entre 30 tickers. La integración sería multiplicar el capital desplegado por la
exposición:

```
capital_desplegado = capital_total × exposicion_jev
resto              = liquidez (sin remunerar, o en el activo libre de riesgo)
```

**Importante:** esto es un cambio de *cuánto* capital se despliega, no de *qué*
tickers se eligen. El ranking de momentum no cambia. Es una capa ortogonal.

### Estimación de coste en producción

| Escenario | Llamadas/mes | Coste/mes |
|---|---|---|
| Clasificación diaria | ~21 | ~$0.0005 |
| Clasificación semanal (rebalanceo) | ~4 | ~$0.0001 |
| Clasificación diaria durante 1 año | ~252 | ~$0.0055 |

El coste es irrelevante. **El criterio de decisión es la fiabilidad, no el precio.**

### Dónde NO encaja

- **No lo uses en crypto.** El workspace `work/crypto` tiene un leak temporal
  conocido y está marcado como research-only. Meter una capa nueva encima de un
  pipeline inválido no aporta nada.
- **No lo uses con los indicadores de `regimen_test.py` sin revisar** — ese
  script lee `estados_mercado.csv`, que hoy no existe en esta máquina.
- **No lo apliques al mercado chino (CSI300)** sin reentrenar la intuición: los
  criterios de régimen de Jev están redactados para mercado US.

---

## 4. Arquitectura de ficheros

Todos en `work/estrategias/`:

| Fichero | Qué es | ¿Ejecutable? |
|---|---|---|
| **`jev_regime.py`** | **Núcleo.** Cliente de Jev + fórmula de sizing | Sí (`--demo`, `--csv`) |
| **`jev_backtest_ab.py`** | **Backtest A/B** de las tres estrategias | Sí |
| `diagnostico_jev.sh` | Comprueba el entorno antes de ejecutar | Sí (bash) |
| `inspeccionar_qlib_data.py` | Muestra qué datos qlib hay disponibles | Sí |
| `test_jev_backtest_sintetico.py` | Valida el motor sin datos ni API | Sí |
| `jev_phase0_probe.py` | Sonda de metadatos/invocación de Jev | Sí |
| `jev_phase0_noauth.py` | Sondeo sin credenciales | Sí |
| `jev_phase0c_stability.py` | Mide estabilidad del router (48 llamadas) | Sí |
| `jev_phase0d_decisions.py` | Ingeniería inversa del contrato de decisiones | Sí |
| `demo_leak_vol_pct.py` | Verifica que `vol_pct` es causal | Sí |
| `JEV_GUIA.md` | Este documento | — |
| `jev_fase1_diseno.md` | Diseño técnico y veredicto de Fase 0 | — |

**Salidas** (en `jev_phase0_out/`, ignorado por git):

| Fichero | Contenido |
|---|---|
| `jev_exposure_cache.json` | Caché de exposiciones por fecha (evita repetir llamadas) |
| `phase0_report.json` | Metadatos + invocación de Fase 0 |
| `ca_bundle.pem` | Bundle TLS generado automáticamente |
| `jev_backtest_ab_results.csv` | Serie de exposiciones y retornos del backtest |

---

## 5. Cómo ejecutarlo

### Paso 0 — Entorno

```bash
cd work/estrategias                      # el repo es /mnt/c/Users/trodriguez/src/qlib
export OPENROUTER_API_KEY="sk-or-v1-..."  # o tener el .env del repo
```

### Paso 1 — Verificar que todo está en orden (gratis, 5 segundos)

```bash
bash diagnostico_jev.sh
```

Comprueba Python, paquetes, datos qlib, la API key, conectividad con OpenRouter
(**no gasta crédito**) y el motor del backtest. Si algo falla, te dice el
comando para arreglarlo.

### Paso 2 — Inspeccionar los datos disponibles (gratis)

```bash
python3 inspeccionar_qlib_data.py
```

Muestra qué universos existen (`sp500.txt`, `nasdaq100.txt`, `all.txt`...),
cuántos tickers tienen features y el rango de fechas.

### Paso 3 — Prueba de humo sin gastar crédito

```bash
python3 jev_backtest_ab.py --no-jev
```

Ejecuta las estrategias **A y B** sin llamar a la API. Te da el baseline de tu
`vol_gate` actual con este motor. Si el `vol_gate` no mejora nada aquí, la
comparación con Jev pierde sentido.

### Paso 4 — Backtest completo

```bash
python3 jev_backtest_ab.py
```

Tres estrategias, con caché. Primera ejecución ~$0.044 y ~15 min; repetir es
instantáneo y gratis.

### Paso 5 — Probar la capa de decisión sola

```bash
python3 jev_regime.py --demo
```

Clasifica 4 estados de mercado sintéticos (crisis, risk-off, neutral, risk-on)
y muestra la exposición resultante. Útil para ver el comportamiento sin lanzar
un backtest.

---

## 6. Parámetros, uno por uno

### `jev_backtest_ab.py`

| Parámetro | Defecto | Para qué sirve |
|---|---|---|
| `--start` | `2018-01-01` | Fecha de inicio del backtest. Marca qué régimen de mercado se estudia. |
| `--end` | `2026-12-31` | Fecha de fin. |
| `--top-n` | `20` | Cuántos tickers se mantienen en cartera. Más = más diversificación y más coste. |
| `--lookback` | `120` | Días de momentum para el ranking. **120 es el valor validado** (IC +0.066 OOS). |
| `--rebalance-days` | `5` | Cada cuántos días se rebalancea. 5 = semanal. |
| `--cost-bps` | `5.0` | Coste por turnover en puntos básicos. 5 bps ≈ coste IB round-trip. |
| `--max-tickers` | `120` | Tamaño del universo muestreado. **No es truncado alfabético**: muestreo uniforme. |
| `--jev-max-dates` | ninguno | Limita cuántas fechas se clasifican con Jev. Para pruebas baratas. |
| `--no-jev` | desactivado | Ejecuta solo A y B, sin llamar a la API. |
| `--out` | `jev_backtest_ab_results.csv` | Dónde guardar la serie de resultados. |

### `jev_regime.py`

| Parámetro | Defecto | Para qué sirve |
|---|---|---|
| `--demo` | — | Clasifica 4 estados sintéticos. No necesita qlib ni datos. |
| `--csv` | — | Clasifica un CSV de indicadores (p.ej. `estados_mercado.csv`). |
| `--limit` | `20` | Cuántas filas del CSV procesar. |
| `--out` | — | CSV de salida con `label` y `exposure` por fecha. |
| `--model` | `~typesafe/jev-latest` | Modelo de decisiones. **No cambiar sin motivo.** |

### Variables de entorno

| Variable | Defecto | Para qué sirve |
|---|---|---|
| `OPENROUTER_API_KEY` | — | **Obligatoria.** Se lee del entorno o del `.env` del repo. |
| `QLIB_US_DATA` | auto | Ruta a `qlib_data`. Si no se define, se autodetecta. |
| `JEV_NATIVE_MODEL` | `~typesafe/jev-latest` | Alternativa a `--model`. |
| `KASPERSKY_CA_PATH` | ruta Windows | CA local para inspección TLS. **En WSL normalmente no hace falta.** |

---

## 7. Configuración óptima

### Recomendada (empezar aquí)

```bash
cd work/estrategias
export OPENROUTER_API_KEY="sk-or-v1-..."

python3 jev_backtest_ab.py \
  --start 2018-01-01 \
  --end 2026-12-31 \
  --top-n 20 \
  --lookback 120 \
  --rebalance-days 5 \
  --cost-bps 5 \
  --max-tickers 120
```

**Por qué estos valores:**

| Parámetro | Valor | Razón |
|---|---|---|
| `--start 2018-01-01` | Régimen moderno | El `vol_pct` necesita 252 días previos. Empezar antes mete la burbuja dot-com, poco representativa del mercado actual. |
| `--top-n 20` | Ya validado | Tu paper-trading usa top-30 sobre universo amplio; 20 sobre 120 tickers mantiene concentración comparable. |
| `--lookback 120` | **No cambiar** | Es el valor con IC OOS +0.066 medido en `momentum_backtest.py`. |
| `--rebalance-days 5` | Semanal | Igual que tu paper-trading real. |
| `--cost-bps 5` | Realista | Aproxima el coste IB. Ponlo a 0 solo para diagnóstico. |
| `--max-tickers 120` | Equilibrio | Suficiente representatividad, tiempo de ejecución razonable. |

### Variantes útiles

**Ver solo el baseline (gratis):**
```bash
python3 jev_backtest_ab.py --no-jev
```

**Prueba rápida antes del completo (barato):**
```bash
python3 jev_backtest_ab.py --jev-max-dates 60
```

**Universo más amplio (más representativo, más lento):**
```bash
python3 jev_backtest_ab.py --max-tickers 300
```

**Backtest largo con crisis reales (2000 dot-com, 2008):**
```bash
python3 jev_backtest_ab.py --start 2000-01-01 --end 2026-12-31 --max-tickers 300
```
> Interesante porque incluye **dos crisis severas**. Si la capa Jev funciona,
> debería notarse sobre todo aquí. Ojo: en 2000-2008 el mercado era muy
> distinto, así que es un test de estrés, no de rendimiento esperado.

**Sin costes (para ver el efecto puro del sizing, no realista):**
```bash
python3 jev_backtest_ab.py --cost-bps 0
```

### Cómo interpretar el resultado

El script imprime una tabla de deltas frente al baseline. Lo que importa:

```
DELTA vs A_FIXED (positivo = mejor)
  B_VOL_GATE   dSharpe=+0.XX  dMaxDD=+Y.YY%
  C_JEV        dSharpe=+0.XX  dMaxDD=+Y.YY%
```

| Escenario | Lectura | Acción |
|---|---|---|
| C > B en Sharpe | Jev aporta sobre el gate | Merece más investigación |
| C ≈ B | Jev aporta lo mismo | Usa `vol_gate`: sin dependencia externa |
| C < B | Jev no aporta | **Descartar** |
| C mejora Sharpe pero empeora MaxDD | Ambiguo | Depende del mandato de riesgo |

> **✅ RESUELTO (2026-10-26):** el resultado fue **C < B** — Jev queda por debajo
> del `vol_gate` con las 7 fórmulas probadas. **Jev se descarta.** Ver
> [sección 10](#10-veredicto-final-fase-2-cerrada). Este apartado se conserva
> como registro del criterio de decisión fijado *antes* de ver los resultados.

---

## 8. Solución de problemas

### `ValueError: instrument not exists`

El archivo de universo esperado no existe. **Ya resuelto:** el script ahora
prioriza `sp500_liquid.txt` → `sp500.txt` → `nasdaq100.txt` y avisa si usa otro.
Verifica con `python3 inspeccionar_qlib_data.py`.

### `ModuleNotFoundError: No module named 'qlib'`

```bash
pip install pyqlib
```

Si falla por `setuptools_scm`, instala también `pip install setuptools-scm`.

### `CERTIFICATE_VERIFY_FAILED`

Hay inspección TLS (antivirus/proxy corporativo):

```bash
KASPERSKY_CA_PATH=/ruta/a/ca.cer python3 jev_backtest_ab.py
```

En WSL normalmente **no ocurre**; es un problema propio del Windows nativo con
Kaspersky.

### `HTTP 401` de OpenRouter

La clave es inválida, ha caducado o no tiene saldo. Verifica en
<https://openrouter.ai/settings/keys>. El script distingue este caso de un fallo
de red y no lo confunde con un fallo de Jev.

### `HTTP 400` de OpenRouter

El contrato de `/api/alpha/decisions` ha cambiado. Es un endpoint **en alpha sin
documentación pública**. Pásame el mensaje de error completo: suele incluir el
campo esperado.

### El backtest va lento

- La primera ejecución hace ~1 llamada por fecha a 0.44 s → **~15 min**.
- Las siguientes usan la caché y son casi instantáneas.
- Para pruebas, usa `--jev-max-dates 60`.

### Ejecutar desde `/mnt/c/` es lento

Estás accediendo a la unidad C de Windows desde WSL. Funciona, pero el I/O es
lento. Si molesta, copia el repo a `~/src/qlib` dentro de WSL.

---

## 9. Limitaciones y advertencias

### 1. Una sola muestra, sin out-of-sample

El backtest es **in-sample**. No hay validación fuera de muestra ni walk-forward.
**No adoptes ninguna conclusión como definitiva** sin ese paso. Es el siguiente
trabajo natural después de ver el primer resultado.

### 2. El leak está en el código de simulación, no en las features

Verificado con `demo_leak_vol_pct.py`: los tres indicadores (`vol_pct`,
`drawdown120`, `mom_crash`) **son causales**. Pero un backtest puede filtrar
futuro en otros sitios:

- Normalizar retornos sobre la muestra completa.
- Elegir umbrales mirando el resultado del backtest.
- Reutilizar una clasificación de 2026 para fechas de 2019.
- No purgar entre train/test (con `mom_crash` mirando 120 días atrás, las
  observaciones vecinas se solapan).

### 3. Las probabilidades pueden no estar calibradas

Que Jev devuelva `P(crisis)=0.88` **no garantiza** que ocurra el 88% de las
veces. Si no está calibrado, la fórmula de sizing hereda el sesgo. **Pendiente:**
verificar con Brier score. Es el paso 2 de la Fase 2.

### 4. Endpoint en alpha

`POST https://openrouter.ai/api/alpha/decisions` **no está documentado
públicamente** y puede cambiar sin aviso. El contrato se dedujo por ingeniería
inversa de los errores de validación. El código captura errores y los registra
en vez de romperse, pero una actualización de OpenRouter podría dejarlo inútil.

### 5. El modelo base puede cambiar

`~typesafe/jev-latest` es un alias: apunta a la última versión. Hoy resuelve a
`typesafe/jev-1.14-20261014`. **Una actualización del modelo puede cambiar las
clasificaciones** y hacer que un backtest de hoy no se reproduzca mañana. El
código guarda `model_returned` en cada decisión para dejar trazabilidad.

### 6. `typesafe/jev-router` no es lo mismo

Existen dos productos distintos y es fácil confundirlos:

- **`~typesafe/jev-latest`** — modelo de decisiones. Devuelve probabilidades.
  **Es el que usamos.** Solo funciona en `/api/alpha/decisions`.
- **`typesafe/jev-router`** — wrapper de chat. Devuelve texto. Funciona en
  `/chat/completions`, pero **no da probabilidades**, así que no sirve para el
  sizing.

Además, el router **cambia de modelo subyacente** según la dificultad del
prompt (medido: `glm-5.3-flash` para fácil, `glm-5.3` para difícil, con ~20× de
diferencia de coste). Eso lo hace poco reproducible para backtest.

### 7. No predictivo

Jev clasifica el estado **actual**, no predice retornos futuros. La hipótesis es
que reducir exposición en estrés mejora el perfil riesgo/retorno. **Si esa
hipótesis es falsa en tu universo, el backtest lo dirá** — y entonces la capa
completa sobra, por muy bien calibradas que estén las probabilidades.

---

## 10. Veredicto final — Fase 2 cerrada

> **Fecha:** 2026-10-26 · **Periodo:** 2018-01-02 → 2026-10-23 (2.215 sesiones)
> **Motor:** momentum top-20, lookback 120d, rebalanceo semanal, costes 5 bps
> **Resultado:** ❌ **Jev NO se adopta.** Ninguna fórmula supera al `vol_gate`.

### 10.1. Resultados de las 7 fórmulas

| Estrategia | Sharpe | CAGR | MaxDD | Expo. media | Días a 0 |
|---|---|---|---|---|---|
| **B_VOL_GATE** | **0.9687** | 15.30% | **−20.65%** | 0.828 | 260 |
| A_FIXED | 0.9148 | 18.08% | −35.97% | 1.000 | 0 |
| JEV_binaria_.5 | 0.9148 | 18.08% | −35.97% | 1.000 | 0 |
| JEV_binaria_soft | 0.8895 | 16.36% | −35.93% | 0.914 | 29 |
| JEV_orig_1-.5 | 0.8638 | 14.44% | −32.67% | 0.851 | 0 |
| JEV_esperada | 0.8028 | 11.88% | −31.80% | 0.756 | 0 |
| JEV_x2 | 0.7599 | 10.87% | −32.12% | 0.705 | 65 |
| JEV_percentil_causal | 0.7099 | 10.63% | −33.55% | 0.750 | 108 |
| JEV_x2.5 | 0.6841 | 8.77% | −30.16% | 0.605 | 344 |

**Ninguna fórmula Jev supera el Sharpe del `vol_gate`.** El rango de derrota va
de −0.054 (la mejor) a −0.285 (la peor).

### 10.2. Causa raíz: las probabilidades no tienen resolución

El hallazgo decisivo lo da la fórmula `binaria_.5`, que dispara a
*"fuera si P(crisis) > 0.5"*:

```
JEV_binaria_.5   Sharpe=0.9148  expo=1.000  dias=0: 0
A_FIXED          Sharpe=0.9148  expo=1.000  dias=0: 0
```

**Son idénticas hasta el cuarto decimal.** La explicación: **Jev nunca devolvió
`P(crisis) > 0.5` en 9 años.** El umbral jamás se activó, así que la fórmula se
comportó como "siempre dentro".

Esto es **estructural, no un problema de la fórmula**:

- Jev devuelve el peor caso como `P(crisis)=0.88` con `confidence=0.83`
  (medido en Fase 0 con un escenario tipo 2008: vol p97, drawdown −28%).
- La fórmula lineal `1 − P(c) − 0.5·P(ro)` da 0.075 en ese caso extremo.
- Pero en crisis *reales* del periodo, las probabilidades son mucho más suaves,
  y la exposición se quedaba en ~0.37–0.5.

El modelo reparte probabilidad entre `risk_off` y `crisis` en lugar de
concentrarla, y **nunca emite la certeza que un sizing binario necesita**.

### 10.3. La confirmación: cerrar más no ayuda

El segundo hallazgo desmonta la hipótesis de que "faltaba cerrar posiciones":

| Fórmula | Días a 0 | Sharpe |
|---|---|---|
| `vol_gate` | 260 | **0.9687** |
| `x2.5` | **344** | 0.6841 |

`x2.5` cierra la posición **344 días, más que el `vol_gate`**, y tiene el **peor
Sharpe de todos**. Conclusión: el valor del `vol_gate` no está en cerrar mucho,
sino en **cerrar en los días correctos**. La señal de Jev, al forzarla, cierra
en días equivocados.

También descarta la fórmula más prometedora a priori: `percentil_causal`
(adaptar el umbral al rango histórico de la propia señal) quedó **penúltima**
con 0.7099. El mecanismo era razonable pero no se sostiene en los datos.

### 10.4. Qué se aprendió (reusable)

Si en el futuro se evalúa otro modelo de decisiones para este propósito,
**comprobar esto primero**:

1. **Rango dinámico de las probabilidades.** Calcular la distribución de
   `P(estado)` a lo largo de la muestra. Si el máximo de `P(crisis)` no llega a
   0.5, el modelo **no sirve para sizing binario** — no importa lo bien que
   clasifique.
2. **Días en que la señal se activa.** Una fórmula que nunca dispara es
   indistinguible de no tener fórmula. Medir `dias=0` antes de juzgar el Sharpe.
3. **Cerrar más ≠ proteger mejor.** Comparar el Sharpe de la fórmula contra el
   número de días fuera, no asumir que más tiempo fuera es mejor.

### 10.5. Estado de los artefactos

| Elemento | Estado |
|---|---|
| `vol_gate.py` | **Intacto y en uso.** Es el ganador. |
| Paper-trading vivo | **No tocado.** Ninguna integración llegó a producción. |
| `jev_regime.py` | Funcional, sin uso en producción. |
| `jev_backtest_ab.py`, `jev_formulas_test.py` | Funcionales; reutilizables como banco de pruebas. |
| Caché de probabilidades | 2.135 fechas. Evita repetir llamadas si se retoma. |
| Dependencia de OpenRouter | **NO añadida** a producción. |

### 10.6. Coste total del estudio

| Concepto | Importe |
|---|---|
| Fase 0 (sondeo, estabilidad, contrato) | ~$0.002 |
| Fase 2 (2 clasificaciones × 2.135 fechas) | ~$0.09 |
| **Total** | **~$0.09** |

### 10.7. Advertencia sobre la validez de la conclusión

- **In-sample, una sola muestra.** Sin walk-forward ni out-of-sample. La
  conclusión es sólida para 2018–2026, no es un teorema.
- **7 fórmulas probadas sobre los mismos datos.** Existe riesgo de comparaciones
  múltiples; pero como **ninguna** mejoró, el riesgo no afecta a la conclusión
  (habría sido un problema si alguna hubiera ganado por poco).
- **Implementaciones distintas del gate.** `jev_formulas_test.py` reconstruye el
  percentil de volatilidad por su cuenta (`rolling` + umbrales) en lugar de
  llamar a `vol_gate.py` (que incluye histéresis). Por eso el `vol_gate` da
  0.9687 aquí y 1.1283 en `jev_backtest_ab.py`. **La conclusión no cambia** —
  Jev pierde contra ambas versiones — pero si se cita un número del `vol_gate`,
  usar el de `vol_gate.py`, que es el desplegado.

### 10.8. Qué queda abierto (no explorado)

Usos laterales que **no se probaron** y que, dado este resultado, se consideran
de baja prioridad:

- Alerta por **divergencia** entre `P(crisis)` y el `vol_gate` (el valor estaría
  en la discrepancia, no en la señal).
- Clasificación de **contexto de earnings** para revivir el filtro PEAD inerte.
- **Segunda opinión estructurada** sobre tesis discrecionales.

Dado que Jev no discrimina bien en la tarea central (régimen de mercado, que es
su caso de uso nativo declarado), hay que ser **escéptico** sobre que lo haga
mejor en tareas laterales. No se recomienda invertir más esfuerzo sin una
hipótesis concreta de por qué funcionaría ahí.

---

## Referencias

- `jev_fase1_diseno.md` — diseño técnico, contrato de API, veredicto de Fase 0
- `vol_gate.py` — el gate actual, con los bugs de look-ahead documentados y corregidos
- `regimen_test.py` — el test que motivó todo esto (dependencia de régimen del momentum)
- `simulation/sim_utils.py` — costes IB y utilidades del paper-trading
- OpenRouter: <https://openrouter.ai/typesafe/jev-router>
