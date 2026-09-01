# 🚀 Pasos para llevar la estrategia v8 a producción real

> **Documento ÚNICO de referencia.** Aquí están todos los pasos para llevar la
> estrategia **SFM v8** de paper trading a **capital real**.
>
> - **Estado actual:** v8 en **paper trading** (desde 2026-09-01), $10k ficticios,
>   señal diaria, modelo `sfm_top3.pth`.
> - **Alineación:** con los gates de producción de `work/crypto/README.md`
>   ("Required gates before any real-world use").
> - **Regla de oro:** hasta cerrar todos los pasos obligatorios, los outputs son
>   **research-only** y **no válidos como evidencia out-of-sample**.

---

## 📍 Punto de partida (hoy)

| Aspecto | Estado actual |
|---|---|
| Modelo | `sfm_top3.pth` (ensemble Top-K v8), label 1d, walk-forward |
| Señal diaria | `signal_YYYY-MM-DD.json` (COMPRA mejor score si confianza ALTA) |
| Paper trading | `state_paper_trading.json`, $10k, coste 0.1% (fee Binance), máx. 2 posiciones |
| Pipeline diario | `run_daily_pipeline.sh` → Coinbase → `data/qlib` → señal → paper (con risk controls + fee Binance) |
| Risk controls | ✅ Activos: reconciliation, exposure, drawdown, stale, kill-switch, alertas |

---

## ✅ Lista de pasos (en orden de ejecución)

> Marca cada checkbox conforme se complete.

### Paso 1 — Cerrar los risk controls del sistema de trading ✅ (2026-09-01)
Implementados en `work/crypto/risk_controls.py` + integrados en `sfm_paper_trading.py`:
- [x] **Reconciliation**: `rc.reconcile()` valida cash/posiciones/precios vs valor real.
- [x] **Exposure limits**: `rc.check_exposure()` limita % por moneda y total.
- [x] **Drawdown limit**: `rc.check_drawdown()` detiene si drawdown > límite.
- [x] **Stale-data protection**: `rc.check_stale_data()` no opera si la señal es de ayer.
- [x] **Kill-switch** testeado: manual (archivo `KILL_SWITCH`) + config.
- [x] **Alertas**: `rc.emit_alerts()` notifica; `rc.run_all_checks()` orquesta y bloquea.

**Entregable:** `sfm_paper_trading.py` con reconciliación + drawdown + stale + kill-switch + alertas. ✅

### Paso 2 — Re-entrenar / reconectar el modelo al dataset de génesis ⏸️ (aplazado)
> Aplazado hasta disponer de máquina con **GPU** (se decidirá al tenerla).
- [ ] Decidir si re-entrenar v8 sobre el dataset de génesis (`data/qlib`, 2010+) y re-evaluar en walk-forward, o mantener el modelo actual.
- [ ] Documentar qué versión de dataset/modelo se usa (trazabilidad).

**Entregable:** modelo decidido y documentado.

### Paso 3 — Modelo de ejecución y costes reales ✅ (2026-09-01, parcial)
- [x] **Fee schedule real de Binance** en `work/crypto/config/binance_fee_schedule.json` (cuenta base 0.1% maker/taker, tiers VIP por volumen).
- [x] `execution_costs_v2.py` corregido (bugs: case CSV y vol nan) y calibrado con datos reales + fee Binance.
- [x] `sfm_paper_trading.py` usa la fee de Binance real vía `CRYPTO_FEE_SCHEDULE_JSON`.
- [ ] Pendiente: slippage real (order book), profundidad, funding/borrow, latencia y calendario 24/7 (los `*_source:"proxy"` requieren order book real).
- [ ] Backtest final con costes calibrados realistas antes de producción.

**Entregable:** modelo de ejecución con costes realistas (fee Binance integrado; microstructure pendiente).

### Paso 4 — Testing y reproducibilidad ✅ (2026-09-01)
- [x] **Entorno completo**: `qlib-venv` con torch(CPU), optuna, ccxt, PyWavelets, pandas, numpy, etc. (`requirements.txt` reflejado en `work/crypto/config/requirements.lock.txt`).
- [x] **pytest instalado** en el entorno (9.1.1).
- [x] **Suite de tests crypto** verde: **71/71 pasan** (`pytest tests/crypto/`).
  - [x] Tests preexistentes (10 archivos: universe, baselines, execution_costs_v2, conversión, descarga, temporal_validation...)
  - [x] **Nuevos tests**: `test_risk_controls.py` (19 tests, punto 1) + `test_sfm_paper_trading.py` (10 tests, lógica compra/venta/fee/max_posiciones).
- [x] **Lockfile reproducible**: `work/crypto/config/requirements.lock.txt` con el estado exacto del entorno.
- [ ] *(opcional)* entorno limpio que re-ejecute un experimento pequeño desde el lockfile — pendiente de documento/CI.

**Entregable:** suite de tests verde (71) + entorno completo + lockfile. ✅

### Paso 5 — Holdout de evaluación ◐ (registrado, apertura bloqueada)
> ⚠️ **Hallazgo honesto:** un holdout legítimo exige **re-entrenar** dejando el 15%
> final sin tocar. Eso es el **Paso 2 (GPU)**. El modelo actual ya se entrenó con todos
> los datos, así que NO se puede abrir un holdout honesto sin re-entrenar.
- [x] **Umbrales PRE-REGISTRADOS e inmutables** en `work/crypto/config/holdout_thresholds_v8.json`
  (sharpe≥0.5, sortino≥0.7, max_dd≤0.30, calmar≥0.6, win_rate≥0.40, etc. — definidos ANTES de ver resultados).
- [x] **Script de evaluación listo** `work/crypto/evaluate_holdout_v8.py` (open_once, resultado inmutable, costes Binance).
- [ ] **Pendiente (GPU):** re-entrenar en génesis dejando el holdout sin tocar, abrirlo UNA vez, registrar resultado inmutable.

**Entregable:** umbrales pre-registrados + script listo ✅ · apertura pendiente de re-entrenado (Paso 2).

### Paso 6 — Métricas y monitor del paper ✅ (2026-09-01)
- [x] **`work/crypto/paper_metrics.py`**: calcula Sharpe, Sortino, Calmar, VaR, CVaR, max_drawdown, win rate y P&L curve desde `history_paper_trading.csv`.
- [x] **`sfm_paper_trading.py` guarda historial SIEMPRE** (arreglado: antes los early-returns por riesgo/kill-switch no registraban) + calcula métricas en cada ejecución.
- [x] **Integrado en `run_daily_pipeline.sh`** como paso 5/5: cada ejecución diaria actualiza `metrics_paper_latest.json`.
- [x] **Test** `test_paper_metrics.py` (7 tests). Suite total: **78/78 verde**.
- [ ] Pendiente (solo al tener historia): reportar las métricas con datos reales (>1 día de paper). Hoy solo hay snapshot (+0.34%).

**Entregable:** infraestructura de métricas/monitor integrada. ✅

### Paso 7 — Credenciales y notificación ◐ (notificación ✅, credenciales pendientes de capital real)
- [x] **Notificación diaria por Telegram** (¡sin necesidad de credenciales extra!):
  - Usa `hermes send` (reutiliza las credenciales del gateway de Hermes) → **no requiere bot token nuevo ni credenciales de exchange**.
  - **Resumen diario** del paper trading (capital, P&L, posiciones) → `sfm_paper_trading.py`.
  - **Alertas de riesgo** (drawdown, stale, kill-switch, exposición) → `sfm_paper_trading.py` + `risk_controls.py`.
  - **Monitor de métricas** (Sharpe, Sortino, Calmar, VaR, drawdown) → paso 6/6 en `run_daily_pipeline.sh`.
  - Target por defecto: Telegram DM (chat_id `899024572`), configurable vía `NOTIFY_TARGET`.
- [x] **Módulo**: `work/crypto/notifications.py`.
- [ ] **Credenciales de exchange (Binance)** — SOLO si se va a capital real: API key + secret **least-privilege, retiros desactivados**, en `.env` (gitignored). No necesarias para el paper.
- [x] **Alerta de "pipeline detenido / falta de datos"** (watchdog): 
  - `work/crypto/watchdog_v8.py` comprueba (1) que el pipeline haya corrido en las últimas 27h, (2) que los datos de `data/qlib` estén al día (≤2 días), (3) estado del paper. 
  - Notifica a @oscarbot_toni_bot si hay problema; **silencioso si todo OK** (modo vigilancia); `--report` notifica siempre.
  - Cronjob Hermes **"Healthcheck paper v8 (watchdog 9:30)"** (9:30, 30 min. después del pipeline principal) → detecta fallos silenciosos del cron de las 9:00.

---

## 🔍 Conclusiones del Backtest y Validación (2026-09-01) — ⚠️ Impacto en producción

Análisis realizado esta sesión (`backtest_v8_2025.py`, `sensibilidad_v8.py`,
`mini_holdout_v8.py`) → **recomendación: NO mover la v8 a capital real todavía.**

### Resultados (multi-moneda, costes Binance + yield cash USDT)
| Métrica | Valor |
|---|---|
| Backtest completo (2025-01-01 → 2026-08-30) | **+4,3% USD / -6,9% EUR** |
| Mejor config aislada en 2026 (holdout real) | **+9,6% USD** (BASE actual) |
| Drawdown máximo | -34% |
| Rotación | ~500 operaciones en 607 días |

### Hallazgos clave
1. **El "Sharpe 2.74" del training era un espejismo**: usar `top1_long_returns`
   **sin costes**. Con costes reales de Binance, el top-1 colapsa a **-49% USD**.
2. **La estrategia multi-moneda (BASE) es "plana pero estable" en USD**: no destruye
   valor con costes (a diferencia del top-1), pero **en EUR es negativa** (por FX).
3. **La optimización no sobrevivió a la validación**: la config "ganadora" (+28,6%)
   era **sobreajuste a 2025**. En el mini-holdout real (2026) **no superó a la BASE**
   (+9,0% vs +9,6%). → Confirmado con `mini_holdout_result.json`.
4. **El yield del cash USDT (~4,5% APY) es valor real y accesible** (stake): empuja
   el resultado de plano a +4,3%. Es lo único escalable sin riesgo de sobreajuste.
5. **La config BASE actual (0.025/0.015, 2 pos) es la más robusta** de las probadas.

### Recomendación para producción
- 🟢 **Seguir en paper trading con la BASE** + yield del cash USDT. No cambiar config.
- 🔴 **NO producir con capital real** hasta que la v8 pase el **holdout final inmutable**
  (Paso 5), que exige **re-entrenar en génesis (Paso 2, GPU)**.
- ⚠️ Si se va a capital real, asumir: **EUR negativo por FX** y drawdown hasta ~30%.
  El edge del modelo, neto de costes, es **débil (~plano)**; el yield del cash es
  el componente más fiable.
- Registrar únicamente el **yield del cash USDT** como mejora legítima a incorporar.

---

## 📊 Tabla: dónde estamos vs dónde ir

| Aspecto | Hoy (paper) | Producción real (meta) |
|---|---|---|
| Modelo | `sfm_top3.pth` (2017→) | Decidir re-entrenado en génesis |
| Costes | 0.1% | Slippage + liquidez + funding + latencia + calendario 24/7 |
| Risk controls | ❌ No hay kill-switch / drawdown / stale | Reconciliación + límites + kill-switch + alertas |
| Evaluación | Walk-forward interno | + Holdout inmutable cerrado |
| Testing | Parcial | Suite completa + lockfile |
| Datos | Génesis hoy | Fresco + alertas de gap |
| Credenciales | Ninguna | Least-privilege + retiros desactivados |

---

*Documento único de referencia para producción de v8. Complementa `work/crypto/README.md` (gates). Es la única fuente de pasos; los demás docs de qlib_work referencian a este.*