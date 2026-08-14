# 🗺️ Plan de Aprendizaje — Inversión Cuantitativa con Qlib

> **Fecha de creación:** 2026-08-14
> **Propósito:** Plan de estudio y fases del proyecto para aprender inversión cuantitativa y aplicarla con Qlib sobre NASDAQ, S&P 500 y criptos.

---

## Objetivo

Aprender y aplicar **Qlib** para diseñar, backtestear y ejecutar estrategias de inversión sobre:
- **NASDAQ** (índice y tecnológicas)
- **S&P 500**
- **Criptomonedas**

---

## Fases del proyecto

### Fase 1 — Entender el setup actual
**Objetivo:** Conocer qué tenemos montado y hacerlo funcionar.

| Tarea | Estado |
|---|---|
| Clonar el repo de Qlib | ✅ Hecho |
| Revisar scripts personales (`toni/`) | ✅ Hecho |
| Crear entorno virtual (Python 3.11.15) | ✅ Hecho |
| Instalar Qlib desde el repo (editable) | ✅ Hecho |
| Transferir datos US | 🔄 En curso (subida por partes) |
| Verificar que los scripts corren | ⏳ Pendiente |

### Fase 2 — Hacer funcionar el flujo completo
**Objetivo:** Ejecutar el pipeline de Qlib de principio a fin.

| Tarea | Estado |
|---|---|
| Ejecutar `qlib_us_read.py` | ⏳ Pendiente |
| Ejecutar `qlib_us_simple_signal.py` | ⏳ Pendiente |
| Lanzar `tech_experiment.yml` (LightGBM + Alpha158) | ⏳ Pendiente |
| Entender resultados (Sharpe, drawdown, retorno) | ⏳ Pendiente |

### Fase 3 — Evolucionar las estrategias
**Objetivo:** Ampliar y mejorar las estrategias.

| Tarea | Estado |
|---|---|
| Añadir criptos (tercer mercado) | ⏳ Pendiente |
| Probar variaciones (topk, modelos, universos) | ⏳ Pendiente |
| Añadir gestión de riesgo (sizing, stops, vol-targeting) | ⏳ Pendiente |

### Fase 4 — Documentación y seguimiento
**Objetivo:** Mantener el avance documentado.

| Tarea | Estado |
|---|---|
| Mantener README actualizado | ✅ En curso |
| Guardar cada documento con fecha y resumen | ✅ En curso |

---

## Conceptos clave a dominar

### Datos
- Calidad de datos, sesgo de supervivencia, look-ahead bias
- Ajuste por splits/dividendos, costes de transacción
- Universos de instrumentos (nasdaq100, tech_giants_universe)

### Factores
- Momentum, value, quality, size, low-volatility
- Rotación y decaimiento de factores
- Alpha158 (158 factores técnicos de Qlib)

### Modelos
- LightGBM (el que usa tu `tech_experiment.yml`)
- Redes (LSTM, Transformer, AlphaNet)
- Validación: walk-forward, purged cross-validation

### Estrategia
- TopkDropout (top 1 por día)
- Señales dólar-neutral (long/short)
- Rebalanceo y sizing

### Riesgo
- Drawdown máximo, Sharpe, VaR
- Correlación entre activos, riesgo de cola
- Stops y vol-targeting

---

## Próximos pasos inmediatos

1. **Terminar la transferencia de datos US** (subida por partes en curso)
2. **Recombinar y descomprimir** los datos en `~/.qlib/qlib_data/us_data`
3. **Ejecutar los scripts** de `toni/` para verificar el flujo
4. **Lanzar el primer backtest** con `tech_experiment.yml`
5. **Documentar los resultados** en este espacio de trabajo

---

*Documento de referencia del proyecto Qlib Work. Se actualizará con cada avance.*
