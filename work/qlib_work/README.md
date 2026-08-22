# Qlib Work — Espacio de trabajo y aprendizaje

> Proyecto de inversión cuantitativa con **Qlib** sobre NASDAQ, S&P 500 y criptos.
> Este directorio documenta el plan, la bibliografía y el avance del proyecto.

**Última actualización:** 2026-08-14

---

## 🎯 Objetivo

Aprender y aplicar **Qlib** (plataforma de inversión cuantitativa con ML de Microsoft) para diseñar, backtestear y ejecutar estrategias de inversión sobre:
- **NASDAQ** (índice y tecnológicas)
- **S&P 500**
- **Criptomonedas**

## 📋 Plan de trabajo

### Fase 1 — Entender el setup actual ✅ (en curso)
- [x] Clonar el repo de Qlib (`tonirodriguez/qlib`)
- [x] Revisar los scripts personales en `toni/` (lector US, señal momentum, experimento tech)
- [x] Crear entorno virtual dedicado (Python 3.11.15 en `/opt/data/qlib-venv`)
- [x] Instalar Qlib desde el repo (modo editable, `0.9.8.dev153`)
- [ ] Transferir los datos US (`~/.qlib/qlib_data/us_data`) — en curso (subida por partes)
- [ ] Verificar que los scripts corren con los datos

### Fase 2 — Hacer funcionar el flujo completo
- [ ] Ejecutar `qlib_us_read.py` (lectura de datos US)
- [ ] Ejecutar `qlib_us_simple_signal.py` (señal momentum 20d)
- [ ] Lanzar `tech_experiment.yml` (LightGBM + Alpha158 + backtest NDX)
- [ ] Entender los resultados (Sharpe, drawdown, retorno)

### Fase 3 — Evolucionar las estrategias
- [ ] Añadir **criptos** (tercer mercado — requiere conector propio)
- [ ] Probar variaciones: topk, modelos, universos, más factores
- [ ] Añadir gestión de riesgo (sizing, stops, vol-targeting)

### Fase 4 — Documentación y seguimiento
- [ ] Mantener este README actualizado con cada avance
- [ ] Guardar cada documento/experimento con fecha y resumen

---

## 📚 Bibliografía recomendada

### Nivel 1 — Fundamentos de inversión
| Libro | Autor | Tema |
|---|---|---|
| A Random Walk Down Wall Street | Burton Malkiel | Eficiencia de mercados, por qué es difícil batir al mercado |
| The Intelligent Investor | Benjamin Graham | Value investing, riesgo, margen de seguridad |
| Common Stocks and Uncommon Profits | Philip Fisher | Crecimiento y calidad |

### Nivel 2 — Inversión cuantitativa / sistemática
| Libro | Autor | Tema |
|---|---|---|
| **Quantitative Trading** | Ernest Chan | ⭐ Diseño, backtest y ejecución de estrategias cuantitativas (punto de partida) |
| Algorithmic Trading: Winning Strategies | Ernest Chan | Estrategias concretas |
| **Advances in Financial Machine Learning** | Marcos López de Prado | ⭐ ML aplicado a finanzas sin overfitting (purged CV, data snooping) |

### Nivel 3 — Factores y alpha
| Libro | Autor | Tema |
|---|---|---|
| Quantitative Equity Portfolio Management | Qian, Hua, Sorensen | Teoría de factores (value, momentum, quality, size) |
| **Finding Alphas** | Igor Tulchinsky (WorldQuant) | ⭐ Cómo descubrir y validar alphas/factores |
| The Little Book of Quantitative Investing | Bruce Jacobs | Intro accesible a los factores |

### Nivel 4 — Gestión de riesgo
| Libro | Autor | Tema |
|---|---|---|
| The Man Who Solved the Market | Gregory Zuckerman | Historia de Jim Simons/Renaissance (inspiración) |
| Risk Management and Financial Institutions | John Hull | Teoría de riesgo (VaR, stress testing) |
| Trading and Exchanges | Larry Harris | Microestructura, costes, ejecución |

### Nivel 5 — Psicología y tácticas
| Libro | Autor | Tema |
|---|---|---|
| Thinking, Fast and Slow | Daniel Kahneman | Sesgos cognitivos |
| Trading in the Zone | Mark Douglas | Mentalidad del trader sistemático |

### 📖 Orden de lectura recomendado
1. **Quantitative Trading** (Chan) — marco completo diseño/backtest
2. **Advances in Financial ML** (López de Prado) — evitar overfitting con LightGBM
3. **Finding Alphas** (Tulchinsky) — generar más factores para Qlib
4. *The Man Who Solved the Market* — lectura ligera/motivacional en paralelo

---

## 📊 Factores clave a considerar

| Área | Qué considerar |
|---|---|
| **Riesgo** | Drawdown máximo, Sharpe, VaR, correlación, riesgo de cola |
| **Datos** | Calidad, sesgo de supervivencia, look-ahead bias, splits/dividendos, costes |
| **Overfitting** | Validación correcta (walk-forward, purged CV), pocos parámetros, robustez |
| **Factores** | Momentum, value, quality, size, low-vol — rotación y decaimiento |
| **Ejecución** | Slippage, comisiones, impacto de mercado, liquidez |
| **Tácticas** | Rebalanceo, sizing (Kelly, vol-targeting), stops, diversificación |
| **Macro** | Tipos, ciclo, correlación con el mercado (beta) |

---

## 📁 Registro de documentos

| Fecha | Documento | Resumen |
|---|---|---|
| 2026-08-22 | `guia_purged_cv.md` | 🧬 Guía de Purged Cross-Validation (López de Prado): purge+embargo, cuándo usarla, implementación práctica, aplicación a momentum/PEAD |
| 2026-08-22 | `documentacion_pead.md` | Documentación PEAD y workflow de scripts (fetch, faseA, faseA2, combo, eventos, backtest) |
| 2026-08-22 | `documentacion_momentum.md` | Documentación Momentum 120 y workflow de scripts (walkforward, backtest, vol-targeting, paper-trading) |
| 2026-08-22 | `estrategia_pead_eventos.md` | Estrategia de eventos PEAD: cómo operar al sorprender resultados (señal SUE, entrada/salida, sizing, combinación con momentum) |
| 2026-08-22 | `pead_faseC.md` | PEAD Fase C: combo momentum+PEAD IC +0.008 total (+0.023 anual); notas sobre integración por eventos |
| 2026-08-19 | `pead_hallazgo.md` | 🚀 PEAD con alpha confirmado: sorpresa de earnings predice retorno post-anuncio (IC Spearman 0.19-0.22, long-short +5-7%) |
| 2026-08-14 | `plan_post_paper_pead.md` | Plan post-paper-trading (validación/escalado), descripción de PEAD/SUE, y cómo conseguir datos fundamentales para Qlib |
| 2026-08-14 | `lowvol_diagnostico.md` | Factor low-vol: no mejora en mercado alcista (IC +0.13 a favor de high-vol); usar vol como control de riesgo, no selección |
| 2026-08-14 | `backtest_momentum.md` | Backtest momentum 120d sobre sp500_liquid: +18.5% anual, Sharpe 0.96, DD −19.4% (primer resultado completo) |
| 2026-08-14 | `momentum_largo_alpha.md` | 🚀 HALLAZGO CLAVE: momentum 120d + label 120d sobre S&P 500 → IC OOS +0.066 (primer alpha genuino) |
| 2026-08-14 | `roadmap_aprendizaje.md` | Roadmap de aprendizaje Qlib: direcciones A-E (universo amplio+momentum, factor mining, beta calidad, datos fundamentales, validación) |
| 2026-08-14 | `meta_quinn_analisis.md` | Quinn: análisis de la posición META (coste $664, hoy ~$595) → mantener + promediar por tramos $540/$480, tope 15% |
| 2026-08-14 | `ic_y_oos_guia.md` | Guía del IC (Information Coefficient) y del OOS (out-of-sample): qué son, origen, interpretación y cómo usarlos como inversor |
| 2026-08-14 | `walk_forward_diagnostico.md` | Walk-forward: IC OOS 0.008 → el +24% era overfitting; no hay alpha robusto; hoja de ruta |
| 2026-08-14 | `resultados_retorno.md` | Resultados de retorno (exceso y absoluto) con aclaraciones metodológicas; validación del vol-targeting |
| 2026-08-14 | `comisiones_interactive_brokers.md` | Comisiones reales de IB España y cómo caracterizarlas en Qlib (open/close cost, conversión por precio del universo) |
| 2026-08-14 | `experimento_v1_v2_diagnostico.md` | Resultados v1-v5, comparativa, diagnóstico, test de dirección, retorno absoluto |
| 2026-08-14 | `README.md` (este) | Creación del espacio de trabajo: plan, bibliografía, registro de avance |
| 2026-08-14 | `bibliografia.md` | Lista detallada de libros recomendados por nivel y tema |
| 2026-08-14 | `plan_aprendizaje.md` | Plan de estudio y fases del proyecto |

*Este registro se actualiza con cada documento/experimento nuevo.*

---

## 🛠️ Entorno

- **Repo:** `/opt/data/qlib` (clon de `tonirodriguez/qlib`, rama `main`)
- **Venv:** `/opt/data/qlib-venv` (Python 3.11.15)
- **Qlib:** instalado en modo editable desde el repo (`0.9.8.dev153`)
- **Datos US (Qlib):** `~/.qlib/qlib_data/us_data` (12,737 tickers en `all.txt`)
- **Scripts personales:** `toni/` (qlib_us_read.py, qlib_us_simple_signal.py, tech_experiment*.yml)

---

## 📈 Paper-Trading — Estrategia momentum 120d (dinero ficticio)

**Estado:** EN MARCHA. Simulación con **€20,000 ficticios**, rebalanceo semanal.

### La estrategia (validada)
- **Señal:** momentum 120d (retorno acumulado 120 días) sobre `sp500_liquid` (292 tickers)
- **Selección:** topk 30, asignación igualitaria
- **IC out-of-sample:** +0.066 (primer alpha genuino del proyecto)
- **Backtest:** +21.7% anual, Sharpe 1.07, max drawdown −18.6%

### Flujo semanal (cronjobs, hora de España)
| Hora (sábado) | Acción | Qué hace |
|---|---|---|
| **00:00** | `update_data_light.py` | Baja sp500_liquid (292 tickers) desde Yahoo → `prices_live.csv` |
| **15:00** | `simulate.py` | Lee `prices_live.csv`, rebalancea al nuevo topk 30, reporta P&L ficticio por Telegram |

### Archivos de la simulación (`toni/simulation/`)
- `simulate.py` — lógica de la simulación (capital ficticio, topk, valoración, rebalanceo)
- `update_data_light.py` — **actualizador LIGERO** de sp500_liquid desde Yahoo
- `state.json` — estado persistente (cash, posiciones, FX) entre semanas
- `prices_live.csv` — datos frescos de precios (generado por el actualizador ligero)
- `state.json` se recrea con `--reset`; la ejecución normal rebalancea sobre el estado previo

### Uso
```bash
# Actualizar datos frescos
python toni/simulation/update_data_light.py
# Ejecutar simulación (rebalancea sobre estado previo)
python toni/simulation/simulate.py
# Reiniciar la simulación con el capital inicial
python toni/simulation/simulate.py --reset
```

### Salida
Cada ejecución muestra: capital inicial, valor actual (USD y EUR), P&L ficticio (USD, EUR y %), y la **tabla de posiciones con acciones fraccionarias y redondeadas a entero** con sus costes.

---

## ⚙️ Configuración específica de ESTA máquina (vinculada a Hermes)

### Limitación de RAM (importante)
Esta máquina tiene solo **7.6 GB de RAM**. El pipeline de actualización oficial de Qlib (`update_us_qlib_daily.sh` / `update_us_all.py`) normaliza el universo completo `all.txt` (12,737 tickers) → **falla con "Killed" (OOM)**.

**Solución aplicada:** se creó el **actualizador ligero** `update_data_light.py` que baja **solo sp500_liquid** (292 tickers) desde Yahoo con peticiones espaciadas (delay 0.35s, evita rate-limit). Es un **canal PARALELO** — los scripts oficiales de Qlib NO se modifican.

### Regla de oro
**No tocar los scripts oficiales de actualización de Qlib** (`update_us_qlib_daily.sh`, `update_us_qlib_rebuild.sh`, `update_us_all.py`). Todo lo específico de esta máquina vive en `toni/simulation/` en paralelo.

### El factor de ajuste de precios (dato crítico)
Qlib guarda `$close` **normalizado** por un factor de splits. El **precio real = `$close / $factor`**. La simulación usa esta corrección (y el CSV del actualizador ligero ya trae precios reales de Yahoo).

### Cronjobs activos (Hermes)
- **`f8b5bcf189a2`** — Actualizar datos Qlib US (sábado 00:00)
- **`b4a7ab201e90`** — Simulación momentum (sábado 15:00)

---

*Este registro se actualiza con cada documento/experimento nuevo.*
