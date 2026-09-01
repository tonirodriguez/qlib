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

### Paso 7 — Credenciales y notificación (solo si se va a capital real)
- [ ] Credenciales least-privilege con retiros desactivados (exige README). Nunca hardcodear.
- [ ] Alertas diarias: pipeline detenido, falta de datos, señal anómala, drawdown > umbral.

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