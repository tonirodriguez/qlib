# ⚙️ Vol-Gating — Resultado de validación (2026-08-22)

> # 🔴 INVALIDADO EL 2026-10-26 — NO USAR ESTOS NÚMEROS
>
> **Los resultados de este documento son irreproducibles y no deben citarse.**
>
> `vol_gate_test.py` aplicaba el gate como `mom.multiply(gate_col, axis=0)`,
> pero `TopkDropoutStrategy` **ordena** la señal y compra el top-k. Multiplicar
> por un escalar **no cambia el orden**: el gate no podía afectar al backtest.
>
> **Prueba:** ejecutado con los 4 niveles (sin gate / P70 / P75 / P80), los
> cuatro dan **resultados idénticos** (Sharpe 1.1513, DD −33.8%, final 462.476).
> Ver `vol_gate_validacion_v2.json` y el diagnóstico `{1.0: 240}`.
>
> **La tabla de abajo es imposible con este código:** cuatro umbrales distintos
> producirían cuatro valores iguales, no 0.960 / 0.967 / 1.136 / 1.071.
> Se desconoce el origen de esas cifras. `git show cdd68576` confirma que el
> código de agosto no cambió después.
>
> **Consecuencias:**
> - ❌ El **Sharpe 1.136** no es reproducible → inválido como referencia.
> - ❌ El criterio de promoción **no se puede evaluar** (los umbrales nunca
>   entraron en juego).
> - ✅ **`vol_gate.py` sí es correcto** y es causal. Lo invalidado es su
>   *medición*, no la regla.
>
> **→ Validación correcta:** `vol_gate_correccion.md` §6 (2026-10-26).
> **→ Resumen:** el gate **reduce el drawdown** (−41.0% → −33.4%, +7.6 pp) pero
> **no mejora el Sharpe** de forma significativa (+0.017).
>
> ---
>
> *El contenido original se conserva abajo como registro histórico.*

**Script:** `vol_gate.py` + `vol_gate_test.py` (motor de backtest Qlib) · **Semana 5** del plan de Quinn.

## Resultado (momentum 120d topk 30, motor Qlib)

> ⚠️ **TABLA INVÁLIDA** — ver aviso superior. Se conserva solo como registro.

| Estrategia | Sharpe | MaxDD | Anual |
|---|---|---|---|
| **Momentum puro** | 0.960 | −19.3% | 18.5% |
| **mom + gate P70** | 0.967 | **−15.0%** | 18.9% |
| **mom + gate P75** | **1.136** | −16.6% | **23.2%** |
| **mom + gate P80** | 1.071 | −17.7% | 21.5% |

## Criterio de promoción (Quinn) — ❌ NO EVALUABLE

> El criterio se declaró "cumplido", pero **los umbrales nunca se aplicaron**,
> así que la robustez en el grid no se llegó a medir. Ver aviso superior.

- **Mejoran Sharpe: 3/3** ⚠️ *(números inválidos)*
- **Reducen ≥20% DD: 2/3** ⚠️ *(números inválidos)*
- **→ ROBUSTO: promover vol-gating** ❌ **conclusión retirada**

## Lectura (❌ CONCLUSIONES RETIRADAS)

> Las conclusiones originales se conservan tachadas como registro. La lectura
> vigente está en `vol_gate_correccion.md` §6.

- ~~**El vol-gating es robusto en todos los umbrales del grid**~~ ❌ **retirado:
  los umbrales nunca se aplicaron, no hay evidencia de robustez.**
- ~~**Confirma la Semana 3:** el momentum falla en alta vol (IC −0.18)~~ ✅
  **este hallazgo sigue siendo válido**: lo mide `regimen_test.py`, que es
  independiente del fallo de mecanismo. El IC bajo en estrés está verificado.
- ~~Consistente con `momentum_vt_backtest.py` previo (Sharpe 1.07)~~ ❌
  **RETIRADO (auditado 2026-10-26).** Dos razones independientes:
  1. **El script no es ejecutable desde este repo**: usa
     `module_path: "toni.vol_target_strategy"`, y `toni/` no es un paquete
     Python (no tiene `__init__.py`; contiene artefactos de MLflow). El import
     falla con `ModuleNotFoundError`, que qlib **no** captura.
  2. Aunque corriera, `vol_target_strategy` implementa **vol-targeting continuo**
     (`vol_target/vol` con clip), que **no es el mismo mecanismo** que el gate de
     3 estados con histéresis. No es una confirmación: es otra estrategia.
  Ver `auditoria_momentum_vt.md`.
  ✅ **Lo que sí se salva:** `risk_degree` es la vía CORRECTA para modular
  exposición en qlib (`signal_strategy.py:365` lo llama en cada decisión).

### Lectura vigente (2026-10-26)

- ✅ **El gate reduce el drawdown:** −41.0% → −33.4% (**+7.6 pp**) en la
  arquitectura real E3, y −36% → −15% en `jev_backtest_ab.py`. Dos tests
  independientes coinciden.
- ⚠️ **No mejora el Sharpe** de forma significativa: +0.017 (ruido).
- ⚠️ **Tiene coste:** ~5.765 $ menos de beneficio final sobre 232k.
- 🎯 **Conclusión:** adoptarlo como **seguro de drawdown**, no como mejora de
  rentabilidad. La decisión depende de la tolerancia al −41% sin gate.

## Regla final del gate (a integrar en E3)

```
vol_pct < P75         → gate = 1.0  (momentum a pleno)
P75 ≤ vol_pct < P90   → gate = 0.5  (momentum a la mitad)
vol_pct ≥ P90         → gate = 0.0  (momentum pausado → cash)
```
Con histéresis para evitar churn diario. Evaluación semanal (con el rebalanceo).

## Nota metodológica

La primera versión de `vol_gate_test.py` usaba un cálculo manual erróneo (turnover 841%, costes 0); **se reescribió usando el motor de backtest de Qlib** (el mismo que valida el momentum), dando métricas correctas y comparables con el backtest real.

---

*Documento de referencia del proyecto Qlib Work. Complementa `plan_E3_quinn_futuro.md` (Semana 5).*
