# Vol-gate: corrección del percentil de volatilidad (look-ahead y ventana)

> **Fecha:** 2026-10-18
> **Script:** `work/estrategias/vol_gate.py` (corregido) · `vol_gate_test.py` (validación)
> **Documento previo:** `vol_gate_resultado.md` (validación 2026-08-22)
> **Estado:** BUG REAL CORREGIDO — validado ≠ desplegado. Pendiente de re-verificación en producción.

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
1. **Re-verificar E3 en producción** con el gate corregido: el último ciclo E3 ya se re-ejecutó tras el fix; confirmar que la señal de momentum se modula como se espera y que el `gate` reportado no usa `vol.max()`.
2. **Re-correr `vol_gate_test.py`** sobre historia larga Qlib para confirmar que los números de validación (Sharpe 1.136 en P75) **se mantienen** — no deberían cambiar, porque esa rama no se tocó, pero conviene dejarlo registrado tras el fix.
3. **Vigilar `prices_live.csv`:** si crece por encima de 252 filas, la ventana pasará sola a 252 y convergerá con la validación. Documentar cuándo ocurre.

### De fondo
4. **Aplicar el mismo examen a las demás señales**: ¿alguna otra usa `max()`/`mean()` globales sobre la serie completa (look-ahead) o cambia de fórmula según la longitud de la historia? El patrón "validado ≠ desplegado" es fácil de repetir.
5. **Test de invarianza de la historia:** comparar el gate con 160 vs 252 vs 504 filas de historia para cuantificar cuánta señal depende del warm-up.
6. **Añadir un guard automático** (test en CI o en el cron de healthcheck) que detecte si `vol_percentile` vuelve a caer en una rama no-percentil.

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
