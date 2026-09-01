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
| Paper trading | `state_paper_trading.json`, $10k, coste 0.1%, máx. 2 posiciones |
| Pipeline diario | `run_daily_pipeline.sh` → Coinbase → `data/qlib` → señal → paper |
| Risk controls | ❌ No hay kill-switch / drawdown / stale-protection |

---

## ✅ Lista de pasos (en orden de ejecución)

> Marca cada checkbox conforme se complete.

### Paso 1 — Cerrar los risk controls del sistema de trading
El paper actual NO tiene estos controles que el README exige antes de producción:
- [ ] **Reconciliation**: validar la cartera simulada vs el dato real de mercado cada día (cash, posiciones, valor).
- [ ] **Exposure limits**: límite de exposición por moneda y total (hoy solo `MAX_POSITIONS=2`, falta cap por % de cartera).
- [ ] **Drawdown limit**: máximo drawdown que detiene el sistema.
- [ ] **Stale-data protection**: no operar si la señal es de ayer o el precio no está fresco.
- [ ] **Kill-switch** testeado: interruptor manual/automático para detener toda operación.
- [ ] **Alertas**: notificaciones ante anomalías (drawdown, stale, error de API).

**Entregable:** `sfm_paper_trading.py` con reconciliación + drawdown + stale + kill-switch + alertas.

### Paso 2 — Re-entrenar / reconectar el modelo al dataset de génesis
- [ ] Decidir si re-entrenar v8 sobre el dataset de génesis (`data/qlib`, 2010+) y re-evaluar en walk-forward, o mantener el modelo actual.
- [ ] Documentar qué versión de dataset/modelo se usa (trazabilidad).

**Entregable:** modelo decidido y documentado.

### Paso 3 — Modelo de ejecución y costes reales
- [ ] Añadir slippage, liquidez, funding/borrow, latencia y calendario 24/7 cripto (`execution_costs_v2.py`, pendiente de datos reales).
- [ ] Backtest con costes calibrados realistas antes de producción.

**Entregable:** modelo de ejecución con costes realistas.

### Paso 4 — Testing y reproducibilidad
- [ ] Suite de tests: ingesta, conversión, labels, splits temporales, invariantes anti-leakage, costes, serialización, compatibilidad modelo/escaler/schema.
- [ ] Dependencias bloqueadas (lockfile) + entorno limpio que re-ejecute un experimento pequeño.

**Entregable:** suite de tests verde + lockfile.

### Paso 5 — Holdout de evaluación
- [ ] Definir umbrales antes de abrir el holdout, abrirlo una sola vez, resultado inmutable.
- [ ] Solo entonces la señal pasa de research-only a evidencia out-of-sample.

**Entregable:** holdout cerrado con resultado inmutable.

### Paso 6 — Métricas y monitor del paper
- [ ] Registrar curva de P&L (`history_paper_trading.csv`).
- [ ] Métricas: Sharpe, Sortino, Calmar, VaR, CVaR, turnover reportadas a diario.

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