# Vol-gate — Decisión sobre su adopción (2026-10-26)

> **Pregunta:** ¿mantener el vol-gate en la arquitectura E3?
> **Respuesta:** **SÍ, como seguro de drawdown.** No como fuente de rentabilidad.
> **Base:** dos validaciones independientes con el mecanismo correcto.

---

## 1. Resumen ejecutivo

| Evidencia | Resultado | Veredicto |
|---|---|---|
| Efecto sobre **drawdown** | −41.0% → −33.4% (**+7.6 pp**) | ✅ **Claro y consistente** |
| Efecto sobre **Sharpe** | +0.017 (base 0.257) | ⚠️ Ruido, no concluyente |
| Coste en rentabilidad | −5.765 $ sobre 232k (−2.5% del total) | ⚠️ Real pero pequeño |
| Reducción confirmada por 2º test | −36% → −15% (`jev_backtest_ab.py`) | ✅ Consistente |

**Decisión:** mantener el gate. Protege de la cola izquierda a un coste acotado.

---

## 2. Qué se ha invalidado por el camino

Antes de llegar a esta evidencia se descubrió que **la validación original era
inválida**, y que el gate que creías validado nunca se midió:

| Documento | Estado |
|---|---|
| `vol_gate_resultado.md` (agosto) | 🔴 **Sharpe 1.136 irreproducible.** Mecanismo inerte. |
| `vol_gate_correccion.md` (oct-18) | ✅ Bug de look-ahead real, corregido. Pero la re-verificación pendiente reveló un problema mayor. |

**Ninguno de esos números debe usarse.** La decisión de abajo se basa en
mediciones nuevas, con el mecanismo verificado (`✅ los resultados difieren`).

---

## 3. La medición válida

### 3.1 Arquitectura real (E3)

`simulate_pead_core.py` aplica el gate **solo al libro táctico (35%)**:

```python
core_cash = portfolio_value * NUCLEO_W          # 65% — sin gate
tact_cash = portfolio_value * TACTICO_W * gate  # 35% × gate
```

Replicado en `vol_gate_e3_validacion.py`, periodo 2018-01→2026-08,
200 tickers de `sp500`, benchmark `^GSPC`:

| | Sharpe | MaxDD | Total | Final |
|---|---|---|---|---|
| A) sin gate | 0.257 | −41.0% | +132.3% | 232.322 |
| B) con gate | 0.273 | **−33.4%** | +126.6% | 226.557 |
| **Delta** | +0.017 | **+7.6 pp** | −5.7 pp | −5.765 |

Distribución del gate: 281 días a 0.0, 304 a 0.5, 1570 a 1.0.

### 3.2 Confirmación independiente

`jev_backtest_ab.py`, gate sobre el **capital total** (no solo el táctico),
2018-2026:

| | Sharpe | MaxDD |
|---|---|---|
| Fijo (siempre dentro) | 0.997 | −36.0% |
| **con gate** | **1.128** | **−15.1%** |
| Delta | +0.131 | **+20.9 pp** |

**Los dos tests coinciden en lo esencial: el gate recorta el drawdown.** La
magnitud varía (7.6 vs 20.9 pp) porque el alcance difiere (35% vs 100% del
capital), pero la dirección es la misma.

---

## 4. Cómo interpretar el intercambio

El gate **no es gratis**. La decisión es un intercambio explícito:

| | Sin gate | Con gate |
|---|---|---|
| Caída máxima | −41.0% | **−33.4%** |
| Beneficio final | 232.322 | 226.557 |
| **Renuncias a** | — | **5.765 $ (−2.5%)** |
| **A cambio de** | — | **7.6 pp menos de caída** |

**Es un buen intercambio:** el gate reduce la peor caída un 18% relativo
(−41.0% → −33.4%) pagando un 2.5% del beneficio.

### La pregunta que decide

> ¿Aguantarías un −41% sin desinvertir?

- **Sí** → el gate no compensa; déjalo en 1.0 permanente o elimínalo.
- **No** → el gate vale la pena. Un −33% es más sostenible psicológicamente,
  y evitar el abandono en el peor momento tiene valor real.
- **No lo sé** → mantén el gate. Es la opción conservadora, y el coste es bajo.

---

## 5. Lo que NO está demostrado

Ser explícito sobre los límites, para no repetir el error de agosto:

1. **No mejora el Sharpe.** El +0.017 es ruido. No lo justifiques así.
2. **In-sample, una sola muestra.** Sin walk-forward ni out-of-sample.
3. **El libro PEAD está aproximado con momentum** (los CSVs de earnings no
   están en el repo local). Esto hace núcleo y táctico más parecidos de lo
   que deberían, **diluyendo el efecto del gate**. El efecto real en tu E3
   podría ser **mayor** que el medido.
4. **Los niveles absolutos no son de tu E3.** El Sharpe 0.257 no es el de tu
   estrategia; solo los **deltas** A→B son fiables.
5. **No se ha verificado** si `momentum_vt_backtest.py` (Sharpe 1.07) tiene el
   mismo fallo de mecanismo. **Podría ser también inválido.**

---

## 6. Recomendaciones

### Inmediatas

1. ✅ **Mantener el gate** en E3 con la configuración actual (P75/P90, histéresis).
2. 🔴 **No citar el 1.136 en ninguna decisión.** Ya está marcado en los docs.
3. 🟡 **Verificar `momentum_vt_backtest.py`**: si usa `multiply` sobre la señal,
   su Sharpe 1.07 es inválido y hay que re-medirlo.

### De fondo (más importantes que el gate)

4. 🔴 **Auditar el resto del proyecto con el mismo rigor.** Hoy se descubrieron
   **cuatro** artefactos documentados que no resistieron una comprobación:
   config SP500 inexistente, leak de `vol_pct` inexistente (falso positivo mío),
   xgboost roto, y la validación del gate inválida.
5. 🔴 **Prioridad alta: SFM v8 crypto** (Sharpe 2.17, "10.49x"). Es lo que está
   en producción. Un Sharpe de 2.17 en crypto justifica escepticismo, y ese
   pipeline tuvo un leak temporal conocido en versiones anteriores.
6. 🟡 **Walk-forward del gate** antes de confiar plenamente en él.

---

## 7. Lección metodológica

El fallo más peligroso **no es el que rompe, es el que devuelve un número
creíble**. La validación de agosto corrió sin errores, produjo una tabla
ordenada y llevó a promover el gate — durante dos meses.

Por eso, en toda validación:

1. **Comprobar que el mecanismo ACTÚA.** Si dos configuraciones distintas dan
   el mismo resultado, el mecanismo no está funcionando.
2. **Un control negativo.** Con gate constante 1.0 debe dar exactamente lo
   mismo que sin gate. Si no, hay un bug.
3. **Instrumentar, no leer.** El diagnóstico `{1.0: 240}` resolvió en una
   ejecución lo que tres lecturas del código de qlib no resolvieron.

---

## 8. Ficheros

| Fichero | Qué es |
|---|---|
| `vol_gate_e3_validacion.py` | **Validación en la arquitectura real** (la que decide) |
| `vol_gate_validacion_v3.py` | Validación con estrategia propia (cartera completa) |
| `gated_strategy.py` | Estrategia con gate, sin heredar de `TopkDropoutStrategy` |
| `vol_gate_correccion.md` §6 | Detalle técnico y causa raíz |
| `vol_gate_e3_validacion.json` | Resultados crudos |

---

*Documento de decisión. Cierra el pendiente abierto el 2026-10-18 en
`vol_gate_correccion.md` §5.*
