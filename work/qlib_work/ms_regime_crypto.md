# 🧪 Markov-Switching sobre cripto — ¿mejora al régimen-switch v2? (veredicto: NO)

**Fecha:** 2026-10-10 · **Réplica de:** Vansteenberghe (2026), *Quantitative Methods in Finance*, arXiv 2601.12896v3, **§53 (Nonlinear time series models / Markov-switching)**.
**Scripts nuevos:** `work/crypto/ms_regime.py` (modelo + comparativa diaria), `work/crypto/ms_regime_variants.py` (variantes del gate), `work/crypto/ms_regime_freq.py` (semanal/mensual), `work/crypto/ms_regime_freq_sweep.py` (barrido de umbrales y ventana de ajuste).
**Salidas:** `work/crypto/output/sfm_v8/regimenes/ms_regime_results.json`, `ms_regime_daily.csv`, `ms_regime_variants.json`.

---

## 1. Qué se ha hecho

Sustituir la regla heurística de régimen de `regime_switch_v2.py` (MA50 + drawdown ATH + capa de
vitalidad 90d/30% + salida por MA75 bajo 10 días) por un **estado de volatilidad latente estimado
con un modelo de cambio de régimen de varianza**:

- **Modelo:** Markov-switching de **2 estados con varianza conmutada** (equivalente a §53.3,
  Kim et al. 1998 / Hamilton-Susmel 1994), sobre **retornos diarios de BTC** (log-retornos).
- **Señal estrictamente causal:** refit en **ventana expansiva cada 21 días** desde 2017-01-01
  (148 refits). En cada refit los parámetros se estiman **solo con el pasado** y la probabilidad
  se obtiene con el **filtro de Hamilton (one-sided)** con parámetros congelados hasta el
  siguiente refit. Nunca se usa el futuro (no hay look-ahead).
- **Gate:** LONG por defecto; a CASH si `P(estado alta-vol | info ≤ t) > th_enter`, vuelta a LONG
  si `< th_exit`. Umbrales fijados **a priori** (0.5 / 0.3, histéresis 5 días) — no ajustados al
  resultado.
- **Validación §53.1:** **test BDS** (Broock et al. 1996) sobre retornos crudos y sobre retornos
  estandarizados `r/σ_t` (implementado con p-valor por permutación, 150 réplicas; validado con
  controles sintéticos: no rechaza iid, rechaza AR(1) y GARCH).
- **Comparativa:** mismas ventanas de selección/OOS que usa el proyecto cripto y **el mismo
  simulador** que `regime_switch_v2` (coste 0.10%, cash al 4.5% anual), 11.000 USD iniciales.

---

## 2. El modelo estimado

| | Estado 0 (calma) | Estado 1 (turbulencia) |
|---|---|---|
| σ anualizada | **34.7 %** | **103.1 %** |
| media anualizada | +49.9 % | +38.1 % |
| persistencia esperada | 11 días | 7 días |
| p(permanecer) | 0.911 | ~0.849 |

- Los dos estados se separan **por varianza (~9×)**, no por media (ambas medias positivas).
  Es, por tanto, un modelo de **volatilidad**, no de dirección.
- **Sensibilidad con k=3** (como el ejemplo del paper): σ = 22.2 % / 65.7 % / 117.7 %, y el
  **AIC favorece k=3** (−14 856) frente a k=2 (−14 670) → 2 estados se quedan cortos.

### Test BDS (§53.1)

| Serie | m | estadístico D_m | p | veredicto |
|---|---|---|---|---|
| retornos crudos | 2 | +0.01441 | 0.000 | **RECHAZA iid** |
| retornos crudos | 3 | +0.03172 | 0.000 | **RECHAZA iid** |
| estandarizados r/σ_t | 2 | +0.01054 | 0.000 | **RECHAZA iid** |
| estandarizados r/σ_t | 3 | +0.02212 | 0.000 | **RECHAZA iid** |

**Hallazgo incómodo:** en el paper, estandarizar por σ_t hace que los retornos *dejen de rechazar*
iid (el modelo captura la estructura no lineal). **En BTC no ocurre**: sigue rechazando → un
Markov-switching de varianza con 2 estados **no elimina toda la dependencia** de los retornos de
cripto (queda efecto leverage, autocorrelación y saltos). El modelo está **mal especificado** a k=2.

---

## 3. Comparativa controlada (mismo simulador que v2)

| Ventana | Estrategia | ret% | maxDD% | Sharpe | trades | días LONG |
|---|---|---|---|---|---|---|
| **sel_bull2021** | MS-gate §53.3 | +77.4 | −27.7 | 1.45 | 52 | 91 |
| 2020-11→2021-11 | regime_switch_v2 | **+229.8** | −35.5 | **1.99** | 7 | 290 |
| | buy&hold BTC | +314.0 | −53.1 | 2.04 | — | — |
| **sel_giro2022** | MS-gate §53.3 | **−49.5** | −52.0 | −0.83 | 73 | 266 |
| 2021-06→2022-12 | regime_switch_v2 | **+34.6** | −30.2 | **0.66** | 2 | 192 |
| | buy&hold BTC | −54.9 | −76.7 | −0.42 | — | — |
| | USDT puro | +7.2 | 0.0 | — | — | — |
| **oos_rally2024** | MS-gate §53.3 | −0.6 | −37.5 | 0.15 | 45 | 186 |
| | regime_switch_v2 | **+63.2** | −36.3 | **1.24** | 9 | 306 |
| | buy&hold BTC | +111.3 | −26.2 | 1.67 | — | — |
| **oos_base2025** | MS-gate §53.3 | −0.3 | −44.9 | 0.16 | 43 | 462 |
| 2025-01→2026-08 | regime_switch_v2 | −19.2 | **−35.3** | −0.33 | 12 | 269 |
| | buy&hold BTC | −17.7 | −53.1 | −0.05 | — | — |
| **full 2020-2026** | MS-gate §53.3 | **+54.4** | −57.1 | 0.38 | 225 | 1229 |
| | regime_switch_v2 | **+294.6** | **−40.9** | **0.82** | 28 | 791 |
| | buy&hold BTC | +464.5 | −76.7 | 0.80 | — | — |
| | USDT puro | +29.3 | 0.0 | — | — | — |

**El MS-gate pierde en TODAS las ventanas.** Acuerdo entre clasificaciones MS vs v2: 43.5 %
(bull), 37.5 % (giro), 50.3 % (rally), 48.4 % (base), 43.7 % (full) → son señales
estructuralmente distintas.

### Por qué pierde

1. **El MS mide volatilidad REALIZADA, que va por detrás del precio.** En el giro de 2022 el
   pico de volatilidad llega *después* de la caída: el gate sale tarde y, mientras tanto, se ha
   comido el crash (266 días LONG en 2022 vs 192 de v2, y −49.5 % vs +34.6 %).
2. **Whipsaw.** Con persistencia de solo ~7 días y refit cada 21 días, la probabilidad oscila y
   el gate parpadea: **225 operaciones vs 28** de v2 en el periodo completo → sangrado por costes.
3. **v2 detecta la ruptura de TENDENCIA** (precio bajo MA sostenida + drawdown), que es
   precisamente lo que protege el downside. La volatilidad no sustituye a la tendencia.

---

## 4. Variantes exploratorias — tampoco desbancan a v2

Probadas sobre la `p_high` ya calculada (sin reajustar el modelo). Periodo completo 2020-11→2026-08:

| Variante | ret% | maxDD% | Sharpe | trades |
|---|---|---|---|---|
| A4 · umbral 0.7 con EMA30 de la probabilidad | +435.7 | −77.1 | 0.79 | 11 |
| B2 · sizing continuo `expos = 1 − EMA7(p_high)` | +202.2 | −62.3 | 0.70 | 1327 |
| **C2 · v2 ∧ MS (EMA30, umbral 0.7)** | **+304.6** | **−40.9** | **0.83** | 30 |
| **REF regime_switch_v2** | +294.8 | −40.9 | 0.82 | 28 |
| REF buy&hold BTC | +464.5 | −76.7 | 0.80 | — |

- Las que **baten en retorno** (A4, B2) lo hacen **a costa del drawdown** (−77 %, −62 %): son
  simplemente "más tiempo largo", no mejor gestión de riesgo.
- La **combinación v2 ∧ MS es indistinguible de v2 solo**: mismo maxDD (−40.9 %), Sharpe 0.83 vs
  0.82, 30 vs 28 operaciones; y en `sel_giro2022` incluso **empeora** (+24.6 % vs +34.7 %).
  → **La capa MS no aporta valor incremental.**

> Nota metodológica: las variantes A/B usan un simulador con banda muerta del 2 % y rebalanceo
> continuo (`simulate_exposure`), más aproximado que el simulador on/off del proyecto; sus
> maxDD son indicativos. La comparación **fiable** es la de la §3 (mismo simulador que v2).

---

## 5. Veredicto

**No promover.** El régimen-switch basado en Markov-switching (varianza conmutada, 2 estados,
frecuencia diaria) **no mejora** a la regla heurística `regime_switch_v2` como gate LONG/CASH en
BTC; pierde en todas las ventanas y, combinado, es redundante. Es un **resultado negativo limpio**,
con umbrales fijados a priori y señal estrictamente causal (sin look-ahead).

Además, el propio test BDS del paper **rechaza** que el modelo capture la dependencia de los
retornos de BTC (sigue rechazando iid tras estandarizar) → mal especificación a k=2.

### Si quisiéramos insistir (no ahora)

1. **k=3** (lo favorece el AIC) o `MarkovAutoregression` con términos AR (mis-especificación).
2. **Efecto leverage / EGARCH** en lugar de varianza simétrica.
3. **Frecuencia semanal/mensual**: el paper aplica MS a datos trimestrales/mensuales (GNP, IPC,
   producción industrial), donde la señal es mucho más limpia que en cripto diario.
4. **Usar el MS como medida de RIESGO** (VaR / sizing) y no como interruptor de régimen.
5. Rejilla de `th_enter/th_exit` y frecuencia de refit, con validación walk-forward.

---

## 6. Estudio por FRECUENCIA — semanal y mensual (2026-10-10)

**Motivación:** el libro estima §53.3 sobre retornos **mensuales** de mercado, no diarios. ¿Se
rescata el MS a frecuencia baja, donde el ruido es menor?

**Scripts:** `work/crypto/ms_regime_freq.py`, `work/crypto/ms_regime_freq_sweep.py`.
**Salidas:** `ms_regime_freq_results.json`, `ms_regime_freq_sweep.json`, `ms_regime_freq_sweep_fit2017.json`.
Nota: la comparación usa un **v2 escalado** a la frecuencia (ventanas en días ÷ días-por-periodo);
el `regime_switch_v2.py` diario no se toca. La decisión del periodo `t+1` usa información hasta el
cierre de `t` (señal desplazada 1 periodo).

### 6.1 Ajustando con TODA la historia de BTC (desde 2010)

El estado "alta varianza" queda calibrado con la **era extrema 2010-2017**, así que en 2020-2026 la
probabilidad casi nunca se activa → **el gate degenera a buy&hold y no protege nada.**

- **Mensual** (196 periodos, 24 refits): p_high media **0.072**, máximo **0.704 (mayo-2017)** y
  **máximo 0.124 en toda la ventana 2020-11→2026-08**. El MS da resultados **idénticos a buy&hold
  en las 5 ventanas** (1 sola operación):

| Ventana (mensual) | MS-gate | v2 escalado | buy&hold |
|---|---|---|---|
| giro 2022 | −52.8 % (DD −73.1) | **+5.2 %** (DD −24.0) | −52.8 % (DD −73.1) |
| full 2020-26 | +219.1 % (DD −73.1) | +226.0 % (**DD −30.8**) | +219.1 % (DD −73.1) |

- **Semanal** (848 periodos, 57 refits): p_high media 0.174, q90 0.658, frac>0.5 = 13.8 %. Tampoco
  protege: el DD del MS se queda pegado al de buy&hold en todas las ventanas.

| Ventana (semanal) | MS-gate | v2 escalado | buy&hold |
|---|---|---|---|
| bull 2021 | +364.5 % (DD −48.2) | +245.4 % (**DD −33.3**) | +316.6 % (DD −47.0) |
| giro 2022 | **−52.8 %** (DD −75.0) | **+16.0 %** (DD −31.3) | −53.0 % (DD −75.2) |
| rally 2024 | +112.9 % (DD −23.0) | +48.8 % (DD −38.4) | +112.9 % (DD −23.0) |
| base 2025 | −21.0 % (DD −51.8) | −21.3 % (**DD −28.5**) | −21.0 % (DD −51.8) |
| full 2020-26 | +527.6 % (DD −75.0) | +290.8 % (**DD −38.8**) | +464.5 % (DD −75.2) |

### 6.2 Ajustando sólo desde 2017 (mismo periodo de información que el estudio diario)

**El resultado se invierte por completo.** El modelo pasa a clasificar 2017-2020 como "alta
varianza" y el estado queda activado de forma casi permanente:

- **Semanal:** p_high media **0.655**, frac>0.5 = **66 %**, q75 = 0.971.
- **Mensual:** p_high media **0.890**, frac>0.5 = **89 %**.
- → El gate se queda **permanentemente en CASH**: full 2020-26 = **+29.3 % (semanal) / +27.9 %
  (mensual) con DD 0.0 %** — exactamente el rendimiento del USDT. No participa de ninguna subida.

### 6.3 Barrido de umbrales (¿es culpa del umbral 0.5? No)

| Fit | Frecuencia | full 2020-26 con umbral 0.2 / 0.3 / 0.5 / 0.7 |
|---|---|---|
| historia completa | semanal | +105.9 % (DD −78.4) / +361.5 % (DD −77.5) / +527.6 % (DD −75.0) / +413.4 % (DD −74.3) |
| historia completa | mensual | +219.1 % (DD −73.1) en **todos** los umbrales (= buy&hold) |
| desde 2017 | semanal | +29.3 % (DD 0.0) / +29.3 % / −6.9 % / +10.5 % |
| desde 2017 | mensual | +27.9 % (DD 0.0) / +27.9 % / +5.6 % / −2.3 % |

**La anomalía no es del umbral: es del modelo.** En todos los casos el MS o **nunca se activa**
(→ buy&hold, DD −75 %) o **se activa siempre** (→ cash, 0 % de participación). Nunca hay un régimen
intermedio útil.

### 6.4 Conclusión del estudio por frecuencia

1. **Cambiar a semanal/mensual NO rescata el MS-gate.** No bate a v2 en ninguna combinación.
2. Es **inestable al borde de la navaja**: el resultado depende por completo de la ventana de
   estimación (¿se incluye la era 2010-2017?), pasando de "nunca dispara" a "siempre dispara".
   Esto **confirma empíricamente la advertencia del propio autor** ("este modelo es muy sensible a
   los datos"; incluir 2020 rompe la inferencia de estados).
3. **El v2 escalado sí es estable** en las dos frecuencias y en todas las ventanas: protección
   real del downside (DD −24 % a −39 % frente a −73 %/−75 % de buy&hold) y siguen rechazándose los
   iid en los retornos estandarizados por BDS (semanal: D₂=+0.024, p<0.001).
4. **Veredicto sin cambios: no promover el MS como gate.** La regla heurística (tendencia + drawdown
   + vitalidad) es superior y mucho más robusta a decisiones de diseño.

---

## 7. Reproducir

```bash
cd /opt/data/qlib
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib \
  /opt/data/qlib-venv/bin/python work/crypto/ms_regime.py          # ~20 min (148 refits + BDS)
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib \
  /opt/data/qlib-venv/bin/python work/crypto/ms_regime_variants.py # ~30 s
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib \
  /opt/data/qlib-venv/bin/python work/crypto/ms_regime_freq.py        # ~90 s (semanal + mensual)
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib \
  /opt/data/qlib-venv/bin/python work/crypto/ms_regime_freq_sweep.py --tag fit2017 --fit-start 2017-01-01
```

Sin cambios en los scripts oficiales del proyecto (`regime_switch_v2.py`, `regime_switch.py`,
`calibra_*.py` intactos): todo va en scripts nuevos en paralelo.
