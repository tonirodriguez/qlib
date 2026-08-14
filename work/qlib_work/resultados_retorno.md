# 📈 Resultados de Retorno — Análisis del Portfolio (Qlib)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — backtest del universo tech_giants
> **Modelo:** LightGBM + Alpha158 · label retorno 10 días · topk 5 · rebalanceo semanal
> **Costes:** Interactive Brokers España (round-trip ~0.10%)

---

## 1. Resumen de las métricas de retorno

### 1.1 Exceso vs benchmark (PortAnaRecord estándar de Qlib)

Este es el reporte fiable de exceso (generado por `PortAnaRecord` de Qlib en cada ejecución qrun).

| Versión | Exceso sin costes | Exceso con costes | IR (con costes) |
|---|---|---|---|
| v1 (original) | −14.6% | −37.1% | −1.62 |
| v2 (+regularización) | −9.0% | −11.9% | −0.56 |
| v3 (+tech_giants) | +7.3% | +2.1% | +0.10 |
| v4 (+semanal) | +8.5% | **+7.3%** | **+0.38** |

### 1.2 Retorno ABSOLUTO (cálculo propio — donde se ve el vol-targeting)

Cálculo manual sobre `report_normal['portfolio']` (valor del account por fecha), con costes IB.

| Métrica | v4 (sin VT) | v5 (con VT) |
|---|---|---|
| Valor inicial | $100,000 | $100,000 |
| **Valor final** | $265,664 | **$273,638** |
| **Retorno anualizado absoluto** | +23.56% | **+24.26%** |
| Volatilidad anualizada | 21.81% | 22.10% |
| **Max drawdown absoluto** | −23.32% | **−23.16%** |
| **Sharpe absoluto** | 1.08 | **1.10** |

---

## 2. Aclaraciones metodológicas IMPORTANTES

### 2.1 Exceso vs. Absoluto — por qué miden cosas distintas

- **Exceso vs benchmark**: retorno de la cartera MENOS el del índice (^NDX). El drawdown del exceso NO cambia con el vol-targeting porque es una medida **relativa** — si reduces la exposición, el benchmark "se reduce" igualmente en la comparación.
- **Retorno absoluto**: el retorno real de tu dinero. Aquí SÍ se ve el efecto del vol-targeting (reducción de exposición en periodos de alta volatilidad).

➡️ **Para validar el vol-targeting hay que mirar el retorno ABSOLUTO**, no el exceso.

### 2.2 ✅ Métricas fiables

- **Retorno anualizado absoluto, volatilidad, drawdown absoluto y Sharpe absoluto**: fiables (calculados directamente de la serie de valor del account).
- **Exceso vs benchmark** en el PortAnaRecord estándar de Qlib (reportes de qrun): fiables.

### 2.3 ⚠️ Métrica NO fiable (bug de mi script de análisis)

En `toni/abs_return_analysis.py`, las métricas de **"exceso vs benchmark"** dieron valores absurdos:
- "Exceso anualizado +10291%" 
- "Benchmark drawdown −217%"

**Causa del bug:** mi script anualizaba el exceso semanal multiplicando los retornos semanales como si fueran compuestos diarios, sobre-multiplicando el resultado. **Estos valores hay que ignorarlos por completo.**

**Lo que NO está corregido:** la anualización automática en `abs_return_analysis.py`. Para el exceso fiable, usar siempre el `PortAnaRecord` de Qlib (qrun), no el cálculo manual del script.

### 2.4 Costes incorporados

- Los valores de este documento usan **costes Interactive Brokers España** (round-trip ~0.10%): `open_cost 0.0004`, `close_cost 0.0006`, `min_cost 1.0`.
- Detalle completo: ver `comisiones_interactive_brokers.md` y `toni/ib_costs.py`.

---

## 3. Interpretación de los resultados

### 🎯 La estrategia final (v5)
Con universo tech_giants + rebalanceo semanal + vol-targeting + costes IB reales:

| Métrica | Valor |
|---|---|
| Retorno anualizado absoluto | **+24.3%** |
| Sharpe absoluto | **1.10** |
| Max drawdown | **−23.2%** |
| Valor final ($100k inicial en 2022) | **$273,638** |

### 📈 Progreso acumulado
| Versión | Mejora clave | Resultado |
|---|---|---|
| v1 | original | −37% exceso con costes |
| v2 | +regularización, topk 10 | −12% exceso |
| v3 | +universo tech_giants | +2% exceso |
| v4 | +rebalanceo semanal | +7.3% exceso |
| v5 | +vol-targeting | **+24.3% absoluto, Sharpe 1.10, DD −23%** |

### 💡 Lectura honesta
- La estrategia es **competitiva**: +24% anual absoluto con Sharpe >1 y drawdown −23% es un perfil sólido para un universo de megacaps tech.
- **Queda margen** en el drawdown (−23% aún relevante) y en el exceso sobre el benchmark.
- **Aviso de overfitting**: hemos tuneado progresivamente sobre el mismo periodo de test (2024-2026). Los resultados pueden degradarse en datos fuera de muestra. Para robustez real habría que: validar walk-forward, o probar en un periodo no visto.

---

## 4. Cómo reproducir

```bash
# Entrenar + backtest estándar (exceso vs benchmark)
cd /opt/data/qlib
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib /opt/data/qlib-venv/bin/qrun toni/tech_experiment_v5.yml

# Análisis de retorno absoluto (v4 vs v5)
MLFLOW_ALLOW_FILE_STORE=true PYTHONPATH=/opt/data/qlib /opt/data/qlib-venv/bin/python toni/abs_return_analysis.py
```

**Archivos relevantes:**
- `toni/tech_experiment_v4.yml` / `v5.yml` — configs de los experimentos
- `toni/vol_target_strategy.py` — estrategia vol-targeting
- `toni/abs_return_analysis.py` — análisis retorno absoluto
- `toni/ib_costs.py` — costes IB
- `qlib_work/comisiones_interactive_brokers.md` — detalle de costes

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
