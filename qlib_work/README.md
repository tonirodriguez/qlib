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
| 2026-08-14 | `comisiones_interactive_brokers.md` | Comisiones reales de IB España y cómo caracterizarlas en Qlib (open/close cost, conversión por precio del universo) |
| 2026-08-14 | `resultados_retorno.md` | Resultados de retorno (exceso y absoluto) con aclaraciones metodológicas; validación del vol-targeting |
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
- **Datos US:** `~/.qlib/qlib_data/us_data` (transferencia en curso)
- **Scripts personales:** `toni/` (qlib_us_read.py, qlib_us_simple_signal.py, tech_experiment.yml)
