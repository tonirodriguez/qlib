# Estado del Proyecto Cuantitativo Qlib

> **Fecha del informe:** Agosto 2026  
> **Repositorio:** `tonirodriguez/qlib` (fork de microsoft/qlib)  
> **Propósito:** Generar una estrategia de inversión cuantitativa rentable con señales diarias, basada en Microsoft Qlib.

---

## Índice

1. [Estado General del Proyecto](#1-estado-general-del-proyecto)
2. [Estrategias y Paper-Trading (`work/estrategias`)](#2-estrategias-y-paper-trading-workestrategias)
3. [Investigación Crypto (`work/crypto`)](#3-investigación-crypto-workcrypto)

---

## 1. Estado General del Proyecto

### 🧭 ¿Qué es este repositorio?

Es un **fork personal** (`tonirodriguez/qlib`) del [Microsoft Qlib](https://github.com/microsoft/qlib), una plataforma cuantitativa open-source orientada a IA para inversión sistemática. Se está utilizando para desarrollar estrategias de trading automatizadas, primero en mercado chino (CSI300) y progresivamente en mercado US (S&P 500) y criptomonedas (SFM).

### ✅ Lo que funciona / está completado

1. **Modelo LightGBM probado y optimizado en mercado chino (CSI300):**

   > ## 🔴 NO VERIFICADO — CONTRADICCIÓN DETECTADA (2026-10-26)
   >
   > Auditoría: [`work/qlib_work/auditoria_csi300.md`](work/qlib_work/auditoria_csi300.md)
   >
   > **Dos problemas:**
   >
   > 1. **Los experimentos MLflow no existen en el repositorio.** Ninguno de
   >    los `experiment_id` citados en `baselines.md` está en `mlruns/`
   >    (la base MLflow local tiene **0 runs**). Los números se generaron en
   >    otra máquina y solo se copiaron los documentos.
   >
   > 2. **Contradicción sobre SoftTopk20 (~10x):**
   >
   >    | Documento | Valor | ¿Cita run_id? |
   >    |---|---|---|
   >    | `baselines.md`, `hypotheses.md`, `dashboard.md`, `signal-vs-portfolio.md` | **3.29%** | ✅ sí |
   >    | **este documento**, `ROADMAP`, `Cambios_Qlib.md` | **31.40%** | ❌ no |
   >
   >    Los documentos que citan el `run_id`
   >    (`3b121593ab2b45cea2bd85467a6302fc`) dan **0.0329** e IR 0.2635 con
   >    DD −24.3%, y lo describen como resultado **flojo**.
   >    `hypotheses.md` lo llama literalmente *"resultado flojo"*.
   >
   > **No usar las cifras de esta sección hasta reconciliarlas.** El 31.40%
   > podría ser 0.0329 con el punto decimal desplazado, pero no está confirmado
   > y no hay datos en el repo para zanjarlo.

   - Baseline con alpha158: 14.73% anual (Top50, label 1d) ⚠️ *no verificado*
   - Label 5d mejora: 20.52% anual con Rank IC 0.0793 ⚠️ *no verificado*
   - SoftTopk20: **31.40%** 🔴 **en disputa** (otros docs citan 3.29% con run_id)
   - Se probaron múltiples configuraciones: baseline, v2, improved, improved_v2, optuna
   - La config `config_lightgbm_improved_v2` es la que mejor resultados netos tras costes ha dado

2. **Modelo SFM (Stochastic Factor Model):**
   - Variante **SFM v4**: backtest ejecutado sobre datos históricos 2018-2026
   - Variante **SFM v5**: preparada para S&P 500
   - Múltiples runs analizados con fixes aplicados

3. **Experimentación registrada:**
   - 9 experimentos almacenados en MLflow
   - 14 configuraciones YAML para distintos universos y variantes
   - 3 notebooks de análisis

4. **Auto Trading System (WIP):**
   - Arquitectura definida con configuraciones progresivas (v1 → improved_v2 → optuna)
   - Sistema de señales diario funcionando sobre el modelo improved_v2
   - Resultados del scanner al 2026-04-01 muestran detección de oportunidades (LYB, OXY, APA, etc.)

### ⏳ En progreso / Pendiente

1. **🔴 SP500 US Baseline (Prioridad 1):**
   - Config lista: `workflow_baseline_lightgbm_alpha158_sp500_us.yaml`
   - **No ejecutado aún** — es la tarea más urgente del roadmap
   - También preparada la variante `label5d`

2. **🔴 Pipeline diario automatizado:**
   - Scripts de actualización de datos existentes pero **no unificados en un pipeline automático**
   - Falta: descarga automática → generar predicciones → señales → órdenes → broker

3. **🔴 Calidad de datos US:**
   - Histórico de problemas con datos corruptos (NaN en `2026-03-03`, bins truncados)
   - Scripts de validación creados: `check_us_bin_rebuild.py`, `fix_all_txt.py`
   - El `--clean-rebuild` se ha usado para regenerar datasets
   - El dataset `us_data` tiene ~9049 instrumentos y 6593 días de calendario

4. **🟡 Modelos avanzados pendientes:**
   - GRU y Transformer de Qlib sin probar
   - alpha360 (más features) config listo pero no ejecutado
   - Ensemble multimodelo (LightGBM + GRU + Transformer) — planificado a largo plazo
   - Walk-forward validation — pendiente

5. **🟡 Operaciones / Infraestructura:**
   - Docker-compose por ajustar
   - Backup system por establecer
   - Wiki mkdocs por mantener

### 🛠️ Problemas conocidos / Riesgos

| Problema | Impacto | Estado |
|----------|:-------:|:------:|
| Datos US corruptos en ciertas fechas (NaN en bins) | Alto — bloquea backtesting US | 🟡 Scripts de fix creados, rebuild funcional |
| Rutas absolutas en scripts apuntan a otra máquina (`/home/toni/`, `/mnt/c/`) | Medio — impide ejecución directa en Hermes | 🟡 Documentado en `Cambios_Qlib.md`, NO modificar |
| Overfitting en modelo `improved` (mejor loss en paso 0) | Medio — riesgo de señal espuria | 🟢 `improved_v2` lo mejora (mejor loss en paso 31) |
| `improved` no sobrevive a costes de transacción | Alto — retorno neto negativo | 🟢 `improved_v2` sí sobrevive (+12.24% neto) |

### 📂 Estructura del proyecto

```
qlib/                          → Fork de Microsoft Qlib (core framework)
├── scripts/                   → Scripts de data collection y utilidades
│   ├── update_us_all.py       → Script principal de actualización US
│   ├── update_us_qlib_daily.sh → Wrapper bash (ruta otra máquina)
│   └── Precios_Valores.md     → Documentación sobre normalización
├── work/                      → NUESTRO trabajo (no existe en el repo original)
│   ├── auto_trading_system/   → Sistema de trading automático (configs, docs)
│   ├── estrategias/           → Estrategias cuantitativas y paper-trading
│   │   └── simulation/        → Paper-trading vivo (momentum 120d + PEAD)
│   ├── formacion/             → Documentación, investigación y experimentos
│   │   ├── 04 Experiments/    → Roadmap, hipótesis, análisis de resultados
│   │   ├── 01 Literature/     → Conceptos, papers, notas de estudio
│   │   ├── 03 Strategies/     → Estrategias de inversión
│   │   └── ...
│   └── crypto/                → Investigación de SFM sobre criptomonedas
└── CHANGELOG.md               → Vacío (no se ha mantenido)
```

### 📌 Resumen ejecutivo

El proyecto completó la fase de **prototipado en mercado chino** (CSI300). 🔴
**Los resultados de esa fase NO están verificados** y hay una contradicción
documental de ~10x sobre SoftTopk20 (31.40% aquí vs 3.29% en los documentos que
citan `run_id`); los experimentos MLflow no están en el repositorio. Ver
`work/qlib_work/auditoria_csi300.md`. La expansión a **mercado US (S&P 500)** se
ejecutó el 2026-10-26 (Rank IC 0.005, con costes −5.9% anual — tampoco viable). La infraestructura de datos US tiene cierta fragilidad pero ya existen herramientas de reparación y validación. El sistema de trading automático tiene la arquitectura definida pero **no está en producción**. Los modelos avanzados (GRU, Transformer, SFM v5, Ensemble) están documentados pero sin implementar.

El próximo paso es **medir vol-targeting sobre equal-weight**, que es lo único
que queda con efecto medible y potencia estadística suficiente. No se abrirán
líneas nuevas de búsqueda de alfa con factores de precio en large caps US: este
dataset no puede distinguir un IC de 0,03 de cero (solo ~17 observaciones
independientes a 120 días, ~69 a 30 días), y nueve auditorías han mostrado que
esa combinación produce ruido con apariencia de señal.

---

## 2. Estrategias y Paper-Trading (`work/estrategias`)

Este directorio contiene el **núcleo del trabajo de trading cuantitativo "artesanal"**: estrategias que no pasan por el pipeline estándar de Qlib (modelo → dataset handler → backtest), sino que construyen las señales directamente con pandas y datos de Qlib, y ejecutan backtests custom y paper-trading en vivo.

### ✅ Paper-trading activo

> ## 🔴 LÍNEA MOMENTUM CERRADA (2026-10-27)
>
> **El ranking de momentum 120d no aporta valor ajustado por riesgo.**
> Auditoría completa: [`work/qlib_work/auditoria_momentum_alpha.md`](work/qlib_work/auditoria_momentum_alpha.md)
>
> Test decisivo: TOP-30 vs **500 carteras de 30 elegidas al azar** del mismo
> universo, mismo calendario, mismos costes.
>
> | Cartera | 2018-2026 (8,8a) | 2022-2026 (4,6a) |
> |---|---|---|
> | TOP-30 momentum | CAGR 10,3% · Sharpe 0,59 · **pct 57** | CAGR 17,0% · Sharpe 0,98 · **pct 81** |
> | BOTTOM-30 (inverso) | CAGR 18,1% · Sharpe 0,72 | CAGR 21,9% · Sharpe 1,04 |
> | EW universo (283) | CAGR 12,2% · Sharpe **0,70** | CAGR 14,9% · Sharpe **1,04** |
>
> **Tres hechos idénticos en ambas ventanas:**
> 1. **El inverso no es peor** → no hay información direccional.
> 2. **El equal-weight empata o gana** con menos volatilidad y sin rotación.
> 3. **El percentil de Sharpe nunca llega a 95** (umbral de habilidad real).
>
> **Conclusión:** el retorno de estas carteras es **exposición al mercado, no
> selección de acciones**. El +18,5% del backtest era real pero de una ventana
> favorable (2022-2026 excluía el crash COVID y el *momentum crash* de 2021).
>
> **Decisión:** no se asignará capital real a esta línea. El paper-trading se
> mantiene solo como **registro de datos forward** (coste cero), no como
> evidencia de edge. No se seguirán probando variantes de momentum.

Hay **tres estrategias en paper-trading** con carteras simuladas, estado persistido en JSON y rebalanceos semanales:

| Estrategia | Archivos | Estado | Cartera actual |
|---|---|---|---|
| **Momentum 120d** (topk30 semanal sobre sp500_liquid) | `simulation/simulate.py`, `state.json`, `update_data_light.py` | 🔴 **Sin edge demostrado** — se mantiene solo como registro forward | ~$22,600 USD ficticios, 30 tickers |
| **Momentum + Filtro PEAD** (momentum 120d pero excluye tickers con sorpresa negativa) | `simulation/simulate_pead.py`, `state_pead.json` | 🔴 **Sin edge + filtro inerte** — solo 2 de 292 tickers cumplen las condiciones del filtro | Idéntica a momentum puro |
| **PEAD-núcleo + táctico** (E3: 22 núcleo por SUE + 12 táctico por momentum) | `simulation/simulate_pead_core.py`, `state_pead_core.json` | ⚠️ **Sin validar** — la pata PEAD no es backtesteable (ver limitación de datos) | 22 núcleo + 12 táctico |

**Mecánica del paper-trading:**
- Capital inicial: 20.000 EUR (~22.600 USD)
- Universo: `work/estrategias/sp500_liquid.txt` (**292 tickers**; el "~390" que se citaba no coincidía con el fichero)
- Frecuencia: rebalanceo semanal (viernes)
- Asignación: igualitaria
- Costes: estilo Interactive Brokers (~0,10% round-trip)
- Datos: `prices_live.csv` si existe, si no Qlib local vía `simulation/rutas_entorno.py`

> ### ⚠️ Limitación de datos del PEAD (verificado 2026-10-27)
>
> `pead_earnings_data_full.csv` contiene **2.819 eventos de 670 tickers**, pero
> **615 de esos tickers tienen exactamente 4 trimestres** (615×4 ≈ 2.460).
> Los eventos se concentran en 2025 (579) y 2026 (2.230).
>
> **Yahoo solo devuelve el último año de earnings.** Consecuencia:
> **el PEAD NO se puede backtestear**, solo observar en vivo.
> Un backtest PEAD necesita 3-5 años de eventos para tener muestra.
>
> Por tanto la pata PEAD de E3 **no tiene validación histórica posible** con
> los datos actuales. Para obtenerla haría falta una fuente de earnings
> históricos (no Yahoo).

### 🔬 Backtests realizados y resultados conocidos

| Script | Estrategia | Resultado conocido |
|---|---|---|
| `momentum_backtest.py` | Momentum 120d + top30, costes IB, 2018-2026 | ⚠️ El IC +0.066 está **retirado**: este script NO calcula IC. Auditado: +0.032 no significativo (120d), ≈0 (60d) |
| `momentum_pead_backtest.py` | Momentum 120d + PEAD (suma de z-scores) | Backtest de la combinación de señales |
| `momentum_pead_filter_backtest.py` | Momentum 120d con **filtro PEAD negativo** (excluye sorpresa < umbral) | Valida la estrategia 2 (la que está en paper-trading) |
| `momentum_purgedcv.py` | Purged CV del momentum 120d (validación rigurosa sin leakage) | Único script que mide IC. Con embargo real: +0.032 (120d, no significativo) y ≈0 (60d) |
| `momentum_walkforward.py` | Walk-forward del momentum | Validación temporal alternativa |
| `lowvol_walkforward.py` | Low volatility + walk-forward | Estrategia de baja volatilidad |
| `pead_faseA.py` / `pead_faseA2.py` | **FASE A — PEAD**: test del alpha de earnings surprise | Mide IC entre sorpresa de resultados y retorno post-anuncio |
| `pead_purgedcv.py` | Purged CV del PEAD (earnings surprise → retorno futuro) | Valida si el PEAD tiene IC real OOS |
| `reversal_illiquidity_purgedcv.py` | Reversal + illiquidity con purged CV | Estrategia de reversión a la media en illíquidos |
| `pead_combo.py` | Combinación de señales PEAD | Integración de múltiples variantes |

### 🧪 Experimentos adicionales y utilidades

| Archivo | Propósito |
|---|---|
| `tech_experiment.yml` → `v5` | **5 configuraciones YAML** para el experimento de las 3 tecnológicas (AAPL, MSFT, META) con LightGBM. La `v5` es la más refinada |
| `tech_experiment.yml` (v1 original) | El primer experimento que comparó AAPL, MSFT, META — resultado: **AAPL ganaba con score 0.035** (vs MSFT 0.032, META 0.009) a 2026-03-13 |
| `qlib_us_read.py` | Utilidad para leer datos de Qlib directamente |
| `qlib_us_simple_signal.py` | Generador de señales simple sobre datos US |
| `ib_costs.py` | Cálculo de costes estilo Interactive Brokers |
| `vol_gate.py` / `vol_gate_test.py` | Compuerta de volatilidad (filtro de entrada basado en régimen de vol) |
| `vol_target_strategy.py` | Estrategia de target de volatilidad (posicionamiento dinámico) |
| `abs_return_analysis.py` | Análisis de retornos absolutos |
| `direction_test.py` | Test de dirección (accuracy direccional de la señal) |
| `regimen_test.py` | Detección de régimen de mercado |
| `extract_estados.py` | Extracción de datos de estado del paper-trading |
| `walk_forward.py` | Utilidad genérica de walk-forward |
| `sp500_liquid.txt` | **Universo de trabajo**: ~390 tickers del S&P 500 filtrados por liquidez |
| `pead_eventos.py` | Utilidad de eventos de earnings |
| `pead_fetch_append.py` / `pead_fetch_full.py` | Descarga y actualización de datos de earnings desde Yahoo Finance |

### 📊 Simulación de paper-trading — detalle de carteras

**Cartera Momentum puro** (`state.json`, fecha: 2026-08-21):
```
Capital: ~$22,600 | 30 posiciones igualitarias (~$735 c/u)
Tickers: MU, HUM, INTC, WDC, VLO, HPQ, EXPE, TGT, STT, CSCO,
         BBY, APA, ELV, NUE, A, BAX, WAT, USL, BNY, AMAT,
         UNH, PAYX, ADP, RVTY, GEN, EXPD, MET, MS, BEN, NTRS
Último rebalanceo: 2026-08-14 → 2026-08-21 (semanal)
Próximo rebalanceo estimado: 2026-08-28
```

**Cartera Momentum + Filtro PEAD** (`state_pead.json`):
- Mismos tickers (el filtro PEAD no ha excluido ninguno en los rebalanceos)
- 2 rebalanceos ejecutados hasta la fecha

### 🔗 Relación con el roadmap general

En el roadmap de `04 Experiments/ROADMAP TRABAJO.md`, estas estrategias corresponden a:

- **Fase 1** (mejorar modelo) → los walk-forwards y purged CVs validan robustez
- **Fase 2** (expandir universos) → el trabajo está directamente sobre SP500 US
- **Fase 3** (pipeline diario automatizado) → **el paper-trading es el prototipo** de ese pipeline: descarga ligera → señal → rebalanceo → estado persistido, pero aún requiere ejecución manual (no hay cronjob)
- **Fase 4** (modelos avanzados) → aún no abordado aquí

### ⚠️ Puntos a destacar

1. **El paper-trading se ejecuta manualmente** — no hay cron automatizado
2. ⚠️ **La cartera momentum y momentum+PEAD son idénticas.** Causa raíz
   encontrada (2026-10-27): no era el umbral ni "sorpresas siempre positivas".
   El embudo del filtro deja **2 candidatos de 292** (670 tickers con earnings
   → 144 frescos ≤40d → 84 en el universo → 2 con SUE < −2). Con 2 de 292, la
   probabilidad de que alguno esté en el top-30 es ~21%. **El filtro no puede
   activarse casi nunca por diseño.**
3. 🔴 **El momentum no tiene edge demostrado.** IC +0.032 no significativo a
   120d, ≈0 a 60d, y el ranking queda en el **percentil 57** frente a carteras
   aleatorias. Ver `work/qlib_work/auditoria_momentum_alpha.md`.
4. ⚠️ **El PEAD no es backtesteable** con los datos disponibles: Yahoo solo da
   el último año (615 de 670 tickers tienen 4 trimestres). La FASE A del PEAD
   no puede completarse sin una fuente de earnings históricos.
5. **Todo el stack es post-Qlib**: las señales se construyen con datos de Qlib
   pero los backtests son custom (no usan `qrun` ni el workflow estándar), lo
   que da flexibilidad pero requiere mantener más código propio
6. **Línea abierta única:** vol-targeting sobre equal-weight. Es lo único con
   efecto medible en estos datos (drawdown −41,0% → −33,4% en la arquitectura
   E3) y con potencia estadística suficiente para concluir.

---

## 3. Investigación Crypto (`work/crypto`)

### ⚠️ Advertencia fundamental

**TODO el trabajo en crypto está etiquetado explícitamente como "research-only".** Ningún modelo, métrica o artifact puede usarse para trading real. La razón principal: las versiones v2, v3 y v4 del pipeline **tienen un leak temporal conocido**: el wavelet denoising se aplica sobre la serie temporal completa *antes* del split train/validation/test, y en v4 el percentil clipping global también se computa antes del split. Esto significa que observaciones futuras contaminan las features históricas — todas las métricas OoS son inválidas como evidencia financiera.

### 🧱 Arquitectura del pipeline de datos

El workspace tiene un pipeline de datos propio (no usa los colectores de Qlib):

| Paso | Script | Estado |
|---|---|---|
| **1. Descarga** de OHLCV desde Binance (publico) via `ccxt` | `download_crypto.py` | Verde - Funcional, descarga incremental, configurable via `.env` |
| **2. Conversion** a formato Qlib (`.bin`) | `convert_crypto_qlib.py` | Verde - Funcional, genera dataset Qlib en `data/qlib_crypto/` |
| **3. Validacion** del provider Qlib | (mencionado en README) | Rojo - No encontrado como script independiente |
| **4. Pipeline de entrenamiento SFM** | Varios scripts (v2, v3, v4, v5) | Rojo - Todas las versiones tienen leak temporal conocido |

### Versiones del modelo SFM

| Version | Activos | Pipeline | Estado |
|---|---|---|---|
| **SFM v2/v3** | Crypto | Pipeline legacy | Rojo - Invalido (leak temporal por denoising global) |
| **SFM v4** | Crypto | Optuna + walk-forward | Rojo - Invalido (leak temporal + clipping global pre-split) |
| **SFM v4 causal** (remediacion) | Crypto | Denoising desactivado, clipping fit intra-fold | Amarillo - Candidato a remediacion, requiere validacion adicional |
| **SFM v5** | **SP500 (no crypto!)** | Misma base que v4 | Rojo - Invalido (mismo leak, y ademas mal ubicado) |
| **Nested walk-forward** (smoke test) | Crypto | Validacion anidada (nested CV) | Amarillo - Smoke tests ejecutados, presupuesto minimo |

### Experimentos formales y su estado

Se diseno un **protocolo de experimento formal** (`experiment_protocol.json`) con:

- **3 universos** a comparar: `original_5` (BTC,ETH,SOL,XLM,ADA), `full_9` (+XRP,DOGE,LINK,LTC), `reduced_8_no_xlm`
- **Presupuesto piloto**: 2 seeds, 3 folds, 5 trials, 10 epochs (ya ejecutado como `universe_comparison_pilot`)
- **Presupuesto formal**: 3 seeds, 3 folds, 30 trials, 60 epochs (no ejecutado)
- **Gates predeclarados** para decidir si un universo merece abrir el holdout final
- **Politica de holdout**: solo se abre si un universo pasa todos los gates; se abre una sola vez y no se retunea

**Resultado de la evaluacion de gates** (`gate_evaluation.json`):

| Universo | Paso? | Que fallo? |
|---|---|---|
| `original_5` | NO | Seed count insuficiente (solo 2), drawdown, folds insuficientes |
| `full_9` | NO | Multiples fallos: Sharpe negativo, drawdown, etc. |
| `reduced_8_no_xlm` | NO | Casi todo falla |

**Conclusion: ningun universo pasa los gates.** El holdout final permanece cerrado. Esto es correcto: el experimento piloto no estaba disenado para pasar los gates, solo para validar que la infraestructura funciona.

### Outputs generados

| Directorio | Contenido | Estado |
|---|---|---|
| `output/optuna_sfm_v4/` | 5 top checkpoints, 3 walk-forward, charts, JSONs | Rojo - Invalido (leak temporal) |
| `output/optuna_sfm_v4_causal_smoke/` | Smoke test causal (1 seed, 1 fold) | Amarillo - Smoke, no conclusivo |
| `output/optuna_sfm_v4_causal_smoke_9assets/` | Idem con universo completo de 9 assets | Amarillo - Smoke |
| `output/optuna_sfm_v5/` | SP500 checkpoints, walk-forwards, charts | Rojo - Invalido + mal ubicado |
| `output/universe_analysis/` | Correlacion entre criptos, summary.json | Verde - Analisis exploratorio OK |
| `output/universe_comparison_pilot/` | Comparacion piloto (2 seeds, 3 folds) | Amarillo - Ejecutado, gates no pasados |
| `output/universe_comparison_cost_smoke/` | Comparacion con costes calibrados | Amarillo - Smoke |
| `output/nested_walk_forward_smoke/` | Smoke test nested CV sin costes | Amarillo - Smoke |
| `output/nested_walk_forward_cost_smoke/` | Smoke test nested CV con costes | Amarillo - Smoke |
| `output/nested_v2_demo/` | Demostracion tecnica | Amarillo - Demo |
| `output/cost_calibration/` y `cost_calibration_v2/` | Calibracion de costes de ejecucion | Amarillo - Preliminar |

### Scripts de soporte

| Script | Proposito |
|---|---|
| `baselines.py` | Implementacion rigurosa de baselines: cash, equal-weight, buy-and-hold, momentum. Incluye bootstrap de Sharpe, PSR y DSR (correccion por multiples tests) |
| `calibrate_execution_costs.py` | Calibracion de costes de ejecucion desde OHLCV |
| `execution_costs_v2.py` | Segunda version de modelo de costes |
| `evaluate_experiment_gates.py` | Evaluador de gates contra el protocolo predeclarado |
| `analyze_crypto_universe.py` | Analisis exploratorio del universo crypto |
| `generate_daily_signals.py` | Experimentacion incompleta - no debe programarse ni conectarse a un exchange |
| `Modelo_SFM_Crypto.ipynb` | Notebook del modelo SFM |

### Que funciona

1. **Pipeline de datos completo**: descarga (ccxt/Binance) -> conversion a Qlib -> dataset listo para entrenar
2. **Protocolo de experimentacion formal**: gates predeclarados, politica de holdout, seleccion de universo
3. **Evaluacion de gates automatizada**: script que decide si un universo puede abrir holdout
4. **Baselines estadisticamente rigurosas**: con bootstrap, PSR, DSR
5. **Multiples smoke tests ejecutados**: la infraestructura de nested CV, walk-forward y costes esta validada como concepto

### Que no funciona / pendiente critico

1. **Rojo - Pipeline de entrenamiento invalido** - todas las versiones (v2-v5) tienen leak temporal. La v4 causal es un *candidato* a remediacion pero no ha sido validado formalmente
2. **Rojo - Presupuesto formal no ejecutado** - solo existe el smoke test piloto (2 seeds, 5 trials). El experimento formal completo (3 seeds, 30 trials, 60 epochs) esta pendiente
3. **Rojo - Ningun universo pasa los gates** - no se puede abrir el holdout, no se puede seleccionar universo
4. **Rojo - SFM v5 mal ubicado** - resultados sobre SP500 dentro del directorio crypto, creando confusion
5. **Amarillo - generate_daily_signals.py incompleto** - no debe usarse para nada operativo
6. **Amarillo - No hay modelo candidato a paper-trading** - a diferencia de `work/estrategias` que tiene paper-trading vivo, crypto esta muy lejos de eso

### Resumen ejecutivo

El workspace crypto esta en una **fase de investigacion temprana con base metodologica solida pero ejecucion inconclusa**. Se ha hecho un trabajo muy correcto de *diseno*: protocolo formal, gates, baselines rigurosas, pipeline de datos reproducible. Pero la *ejecucion* del experimento formal no se ha completado porque el pipeline de entrenamiento (SFM) genera resultados invalidos por el leak temporal.

La v4 causal (con denoising desactivado y clipping intra-fold) es el camino correcto, pero necesita:
1. Una ejecucion formal completa (3 seeds, 30 trials, 60 epochs)
2. Superar los gates predeclarados
3. Abrir holdout
4. Validacion post-holdout

Hasta entonces, **todo en este directorio es investigacion**, no produccion. Contrasta con `work/estrategias` donde hay paper-trading vivo y senales validadas con backtest.