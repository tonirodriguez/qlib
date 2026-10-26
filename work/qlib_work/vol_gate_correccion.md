# Vol-gate: corrección del percentil de volatilidad (look-ahead y ventana)

> ## 🔴 ACTUALIZACIÓN 2026-10-26 — EL SHARPE 1.136 ES INVÁLIDO
>
> Se ejecutó la re-verificación pendiente (paso 2 de "Próximos pasos") y el
> hallazgo es **más grave que el look-ahead**: la validación de agosto usaba un
> mecanismo que **no podía funcionar**.
>
> `vol_gate_test.py` aplicaba el gate así:
> ```python
> sig_gated = mom.multiply(gate_col, axis=0)
> ```
> Pero `TopkDropoutStrategy` **ordena** la señal y compra el top-k. Multiplicar
> por un escalar NO cambia el orden: `0.5·x` conserva el ranking, y `0·x` deja
> todos los valores empatados. **El gate no podía afectar al backtest.**
>
> **Confirmación empírica:** ejecutado 4 veces (gate=1.0 / P70 / P75 / P80),
> las cuatro dan **resultados idénticos** (Sharpe 1.1513, DD −33.8%, valor final
> 462.476). Ver `vol_gate_validacion_v2.json` y el diagnóstico `{1.0: 240}`.
>
> **Consecuencias:**
> - ❌ El **Sharpe 1.136 de P75 no es reproducible**. La tabla de agosto
>   (0.960 / 0.967 / 1.136 / 1.071) es imposible con este código, porque
>   produciría cuatro valores iguales.
> - ❌ El criterio de promoción ("robusto en todos los umbrales") **no se puede
>   evaluar** con esa validación: los umbrales nunca entraron en juego.
> - ⚠️ El `git show cdd68576` confirma que el código de agosto era **idéntico**;
>   no hubo un cambio posterior que lo rompiera.
> - ✅ **Esto NO invalida `vol_gate.py`**, que es correcto y causal. Invalida
>   únicamente su *medición*.
>
> **Validación correcta:** hecha el 2026-10-26 con el gate aplicado sobre
> exposición real. Ver `vol_gate_e3_validacion.py` y la sección 6 de este
> documento.
>
> **Acción:** no usar 1.136 como referencia en ninguna decisión.

> **Fecha:** 2026-10-18
> **Script:** `work/estrategias/vol_gate.py` (corregido) · `vol_gate_test.py` (validación)
> **Documento previo:** `vol_gate_resultado.md` (validación 2026-08-22)
> **Estado:** BUG REAL CORREGIDO. Re-verificación **COMPLETADA el 2026-10-26**
> (ver aviso superior y sección 6).

---

## 1. Qué es el vol-gate y qué buscamos

El **vol-gate** es la pieza de control de riesgo que modula la exposición al momentum según la volatilidad realizada del mercado. Nace de un hallazgo de la Semana 3 del plan: **el momentum pierde poder predictivo en regímenes de alta volatilidad** (IC ≈ −0.18), así que reducirlo o pausarlo cuando la vol está alta captura ese beneficio.

Regla (de `vol_gate_resultado.md`):

```
vol_pct < P75         → gate = 1.0  (momentum a pleno)
P75 ≤ vol_pct < P90   → gate = 0.5  (momentum a la mitad)
vol_pct ≥ P90         → gate = 0.0  (momentum pausado → cash)
```

…donde `vol_pct` es el **percentil histórico de la volatilidad realizada** en el momento de decidir. Con histéresis para evitar churn diario y evaluación semanal.

**Lo que buscamos aquí:** garantizar que el `vol_pct` que se calcula *en producción* es el **mismo objeto matemático** que se validó en backtest, y que no usa información del futuro. Es un problema de **corrección de bug**, no de estrategia.

---

## 2. Qué estaba mal (los dos bugs)

### 2.1 Rama equivocada con historia corta

El código original:

```python
if hist_win and len(vol) > hist_win:
    pct = vol.rolling(hist_win, ...).apply(lambda x: (x.iloc[-1] > x).mean())
    return vol, pct
return vol, vol / vol.max()          # ← ESTA rama NO es un percentil
```

El fallback `vol / vol.max()` **no es un percentil**: es "fracción de la volatilidad máxima de la muestra". Son reglas distintas:

| | percentil verdadero | `vol / vol.max()` |
|---|---|---|
| Qué mide | fracción de días pasados con vol menor que hoy | cuánto supone la vol de hoy respecto al máximo histórico |
| Umbral P75 | dispara ~25 % de los días | NO tiene la misma semántica |
| Sensible a un pico extremo | poco | mucho (un solo día de pánico baja todos los demás valores) |

**Y aquí estaba el problema gordo:** la validación (`vol_gate_test.py`) corría sobre años de historia Qlib (>252 filas) → ejecutaba **el percentil**. Pero la simulación en vivo usa `prices_live.csv`, que tenía **160 filas** (< 252) → ejecutaba **el fallback**. Es decir:

> 🔴 **El gate validado y el gate desplegado eran reglas diferentes.** El backtest prometía Sharpe 1.136 con percentil P75, pero en producción se aplicaba otra fórmula con otro comportamiento de umbral.

### 2.2 Look-ahead

```python
vol / vol.max()   # vol.max() = estadística de TODA la muestra, incluido el futuro
```

`vol.max()` se calcula sobre la serie completa: el máximo de la volatilidad *incluye días posteriores al momento de decidir*. Un pico de vol en el futuro encoge retroactivamente el valor normalizado de todos los días anteriores → el gate "sabía" que venía una crisis. Look-ahead clásico.

El percentil de la primera rama (`(x.iloc[-1] > x).mean()`) tenía el mismo problema en grado leve: comparaba contra `x` completo, incluido el propio último valor.

---

## 3. La corrección

`vol_percentile()` reescrita (marcada `CORREGIDO 2026-10-17` en el código):

```python
vol = realized_vol(close, vol_win)
n = int(len(vol))
if n == 0:
    return vol, vol
win = int(min(hist_win, n)) if hist_win else n       # ← ventana ESCALADA
if win < 10:
    return vol, pd.Series(np.nan, index=vol.index)   # ← sin historia: NaN, no regla falsa
minp = max(10, min(win // 2, 60))
pct = vol.rolling(win, min_periods=minp).apply(
    lambda x: (x.iloc[-1] > x.iloc[:-1]).mean(), raw=False   # ← SOLO pasado
)
return vol, pct
```

Dos cambios de fondo:

1. **Una sola semántica (percentil) en todos los regímenes de historia.** La ventana se **escala** a la historia disponible (`win = min(hist_win, n)`) en vez de cambiar de fórmula. Con 160 filas usa percentil sobre 160 días; con 2.000, sobre 252. **Validado y desplegado vuelven a ser la misma regla.**
2. **Causalidad estricta.** El percentil compara contra `x.iloc[:-1]` — **solo días pasados**. Eliminado el look-ahead de `vol.max()`. Si no hay historia suficiente (<10 puntos), devuelve `NaN` en vez de una regla falsa.

Además: `gate_level_from_pct()` y la histéresis (`_apply_hysteresis`) quedaron intactas — la lógica de umbrales P75/P90 y el anti-churn no eran el problema.

---

## 4. Qué obtenemos

### 4.1 El gate ya no depende de cuánta historia tenga `prices_live.csv`

| Escenario | Antes | Ahora |
|---|---|---|
| Historia larga (>252, backtest Qlib) | percentil (ventana 252) | percentil (ventana 252) — igual |
| Historia corta (160, producción) | `vol/vol.max()` ❌ | percentil (ventana 160) ✅ |
| Historia muy corta (<10) | `vol/vol.max()` (ruido) | `NaN` → gate no actúa ✅ |

### 4.2 Test con historia corta (160 filas)

Ejecutado con el `prices_live.csv` real de 160 filas: el percentil ahora **sí corre** (antes caía al fallback). La distribución de gates resultante es coherente con la validación:

| Gate | Días (historia 160 filas) |
|---|---|
| 1.0 | 115 |
| 0.5 | 12 |
| 0.0 | 13 |

Último día con gate = 1.0. Los umbrales P75/P90 disparan en ~18 % y ~9 % de los días respectivamente — en línea con lo esperado por construcción (25 % y 10 % teóricos, con menos días por el warm-up del rolling).

### 4.3 Diferencia clave frente a la validación

⚠️ Con solo 160 días de historia, el percentil se calcula sobre una ventana de 160 días (no 252). Eso es **correcto y deseable** (es lo que hay), pero implica que **el número exacto de días con cada gate no reproduce el backtest de años**. La semántica es la misma; la muestra es distinta. No es un bug — es la limitación de tener poca historia en vivo.

---

## 5. Próximos pasos

### Inmediatos
1. ✅ **HECHO (2026-10-26).** Re-verificar con el gate corregido. Resultado: el
   1.136 era irreproducible por un fallo de mecanismo, no de look-ahead.
   Ver sección 6.
2. ✅ **HECHO (2026-10-26).** Re-ejecutado. Los números de agosto **NO se
   mantienen**: la validación nunca midió el gate (los 4 umbrales daban el
   mismo resultado). Ver aviso superior.
3. **Vigilar `prices_live.csv`:** si crece por encima de 252 filas, la ventana
   pasará sola a 252 y convergerá con la validación. Documentar cuándo ocurre.

### De fondo
4. **Aplicar el mismo examen a las demás señales**: ¿alguna otra usa `max()`/`mean()` globales sobre la serie completa (look-ahead) o cambia de fórmula según la longitud de la historia? El patrón "validado ≠ desplegado" es fácil de repetir.
5. **Test de invarianza de la historia:** comparar el gate con 160 vs 252 vs 504 filas de historia para cuantificar cuánta señal depende del warm-up.
6. **Añadir un guard automático** (test en CI o en el cron de healthcheck) que detecte si `vol_percentile` vuelve a caer en una rama no-percentil.

---

## 6. Re-verificación y validación correcta (2026-10-26)

### 6.1 Qué se hizo

Se intentó reproducir la validación de agosto con el `vol_gate.py` corregido.
Cuatro intentos, cada uno descartando una causa:

| Intento | Script | Mecanismo | Resultado |
|---|---|---|---|
| 1 | `vol_gate_reverificacion.py` | `mom.multiply(gate)` (el original) | 4 resultados **idénticos** |
| 2 | `vol_gate_validacion_v2.py` | subclase de `TopkDropout`, `self.topk` dinámico | idénticos; diag `{1.0: 240}` |
| 3 | `gated_strategy.py` | estrategia propia, órdenes explícitas | **funciona** |
| 4 | `vol_gate_e3_validacion.py` | **arquitectura real E3** (núcleo 65% + táctico 35%×gate) | ver 6.3 |

**Causa raíz de los intentos fallidos 1 y 2:**

- **Intento 1:** multiplicar la señal no cambia el orden del top-k.
- **Intento 2:** `qlib/utils/mod.py:178-184` hace
  ```python
  try:    klass(**cls_kwargs, **try_kwargs, **kwargs)
  except TypeError: klass(**cls_kwargs, **kwargs)
  ```
  Si el constructor lanza `TypeError`, qlib **reintenta sin los kwargs extra**
  (el `gate`). La estrategia se construye sin gate, el backtest corre, y el
  resultado sale idéntico al puro **sin ningún error visible**. Fallo silencioso.

### 6.2 Resultado del mecanismo correcto (cartera completa)

Con el gate sobre el **número de posiciones** de toda la cartera
(`vol_gate_validacion_v3.py`), período 2022-01→2026-08, universo `sp500`:

| | Sharpe | MaxDD | Anual | Final |
|---|---|---|---|---|
| Momentum puro | 1.151 | −33.8% | 39.2% | 462.476 |
| gate P75 | **0.972** | −34.3% | 27.9% | 297.311 |

- Gate activo: **169 días en cash**, 76 a media posición, 1911 a pleno.
- Chequeo: ✅ los resultados difieren (el gate actúa).
- **Delta Sharpe: −0.180. Delta MaxDD: −0.5 pp (sin mejora).**

⚠️ Este mecanismo **no es el del proyecto**: reducir el número de posiciones
concentra la cartera y es conceptualmente distinto a reducir capital.

### 6.3 Resultado en la ARQUITECTURA REAL (E3)

`simulate_pead_core.py` aplica el gate así (líneas 204-205):

```python
core_cash = portfolio_value * NUCLEO_W          # 65%, el gate NO lo toca
tact_cash = portfolio_value * TACTICO_W * gate  # 35% × gate
```

`vol_gate_e3_validacion.py` replica esa estructura. Período 2018-01→2026-08,
200 tickers de `sp500`, benchmark `^GSPC` real:

| | Sharpe | MaxDD | Total | Final |
|---|---|---|---|---|
| A) sin gate | 0.257 | −41.0% | +132.3% | 232.322 |
| B) con gate (35%×gate) | **0.273** | **−33.4%** | +126.6% | 226.557 |
| **Delta** | **+0.017** | **+7.6 pp** | −5.7 pp | −5.765 |

Gate: 281 días a 0.0, 304 a 0.5, 1570 a 1.0.

### 6.4 Interpretación

**El gate funciona como seguro de drawdown, no como mejora de rentabilidad.**

- ✅ **Reduce el drawdown de forma sustancial:** −41.0% → −33.4% (**7.6 pp**).
  Coherente con `jev_backtest_ab.py`, donde el gate sobre capital redujo el
  DD de −36% a −15%.
- ⚠️ **El Sharpe apenas cambia:** +0.017 sobre una base de 0.257 es ~6%, dentro
  del margen de ruido de una sola muestra.
- ⚠️ **Tiene un coste:** 5.765 $ menos de beneficio final (sobre 232k).

**La pregunta correcta no es "¿gana más?" sino "¿es un intercambio que quieres?"**

| | Sin gate | Con gate |
|---|---|---|
| Renuncias a | — | 5.765 $ |
| A cambio de | — | 7.6 pp menos de caída máxima |

### 6.5 Limitaciones de esta validación

1. **El libro PEAD está aproximado con momentum**, no con SUE real, porque los
   CSVs de earnings (`pead_earnings*.csv`) **no existen en el repo local** —
   viven en la máquina con `/opt/data/`. Esto hace que núcleo y táctico sean
   más parecidos de lo que deberían, **diluyendo el efecto diferencial del
   gate** y probablemente deprimiendo el Sharpe absoluto (0.257 frente a
   0.97-1.15 medidos en otros tests).
2. **In-sample, una sola muestra.** Sin walk-forward ni out-of-sample.
3. **200 tickers** (muestreo uniforme de 1.180), no el universo completo.
4. Los **deltas A→B** son la parte fiable (la comparación es limpia, mismos
   datos y costes); los **niveles absolutos** no deben citarse como el Sharpe
   real de E3.

### 6.6 Decisión recomendada

Adoptar el gate **por su efecto sobre el drawdown**, con la evidencia
consistente de dos tests independientes. No justificarlo por mejora de Sharpe,
que no está demostrada.

---

## Anexo — Diff resumido

```diff
-    if hist_win and len(vol) > hist_win:
-        pct = vol.rolling(hist_win, min_periods=hist_win // 2).apply(
-            lambda x: (x.iloc[-1] > x).mean(), raw=False)
-        return vol, pct
-    return vol, vol / vol.max()
+    n = int(len(vol))
+    if n == 0:
+        return vol, vol
+    win = int(min(hist_win, n)) if hist_win else n
+    if win < 10:
+        return vol, pd.Series(np.nan, index=vol.index)
+    minp = max(10, min(win // 2, 60))
+    pct = vol.rolling(win, min_periods=minp).apply(
+        lambda x: (x.iloc[-1] > x.iloc[:-1]).mean(), raw=False)
+    return vol, pct
```

```bash
# verificación
cd /opt/data/qlib/work/estrategias
git diff vol_gate.py
```

*Documento de referencia del proyecto Qlib Work. Complementa `vol_gate_resultado.md`.*
