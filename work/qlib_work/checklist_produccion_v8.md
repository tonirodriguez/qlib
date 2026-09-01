# 🚀 Checklist — Llevar la estrategia v8 a producción real

> **Frente:** crypto (SFM v8)
> **Fecha:** 2026-09-01
> **Estado actual:** v8 en **paper trading** (desde 2026-09-01) — estrategia ganadora operando
> con $10k ficticios, señal diaria, modelo `sfm_top3.pth`.
> **Objetivo de este doc:** lista de temas pendientes para pasar de paper trading a
> **capital real**, alineada con los gates de producción que exige el repo
> (`work/crypto/README.md → "Required gates before any real-world use"`).

---

## 🧭 Dónde estamos: v8 en paper trading (hoy)

- Modelo: `sfm_top3.pth` (ensemble Top-K de v8), label 1d, walk-forward.
- Señal diaria: `signal_YYYY-MM-DD.json` (COMPRA mejor score si confianza ALTA).
- Paper trading: `state_paper_trading.json`, $10k, coste 0.1%, máx. 2 posiciones.
- Pipeline diario: `run_daily_pipeline.sh` (Coinbase incremental → data/qlib → señal → paper).

> Los gates del README exigen que, antes de tocar capital real, se cierren:
> causalidad, evaluación (holdout), modelo de ejecución, calidad de datos,
> reproducibilidad, testing, control de riesgos y revisión.

---

## 🔴 Checklist de temas pendientes para producción real

Priorizado **P1** (imprescindible) → **P2** (importante) → **P3** (recomendado).

### P1 — Imprescindible antes de capital real

#### 1. ⚠️ Cerrar los "risk controls" que el paper trading aún NO tiene
El README exige, antes de producción, que el sistema de trading tenga:
- [ ] **Reconciliation**: comparar la cartera simulada vs los datos reales de mercado cada día (cash, posiciones, valor).
- [ ] **Exposure limits**: límite de exposición por moneda y total (hoy solo `MAX_POSITIONS=2`; falta cap por % de cartera por activo).
- [ ] **Drawdown limits**: límite máximo de drawdown que detiene el sistema (**hoy no existe**).
- [ ] **Stale-data protection**: no operar si la señal es de ayer o el precio no está fresco.
- [ ] **Kill-switch** testeado: interruptor manual/automático para detener toda operación.
- [ ] **Alertas**: notificaciones ante anomalías (drawdown, stale, error de API).

#### 2. 🔁 Reconectar / re-entrenar el modelo al dataset de génesis
- [ ] `sfm_top3.pth` se entrenó sobre el dataset **antiguo** (2017→hoy). Ahora `data/qlib` tiene **génesis** (2010+).
- [ ] Decidir: **re-entrenar v8** sobre génesis y re-evaluar en walk-forward, **versus** mantener el modelo actual.
- [ ] Documentar qué versión de dataset/modelo se usa (trazabilidad).

#### 3. 📦 Modelo de ejecución y costes reales
- [ ] Costes: hoy solo `0.1%`. Falta **slippage, liquidez, funding/borrow, latencia** y el **calendario 24/7 cripto** (lo exige el repo; `execution_costs_v2.py` pendiente de datos reales).
- [ ] Backtest con **costes calibrados** realistas antes de pasar a producción.

#### 4. 🧪 Testing y reproducibilidad
- [ ] Tests offline: ingesta, conversión, labels, splits temporales, invariantes anti-leakage, costes, serialización, compatibilidad modelo/escaler/schema.
- [ ] **Dependencias bloqueadas** (lockfile) + entorno limpio que re-ejecute un experimento pequeño.

#### 5. 🔍 Holdout sin tocar (evaluación)
- [ ] Definir umbrales **antes** de abrir el holdout, abrirlo **una sola vez**, resultado **inmutable**.
- [ ] Solo entonces la señal pasa de "research-only" a evidencia out-of-sample.

---

### P2 — Importante (para operar de forma robusta)

#### 6. 📉 Drawdown / métricas de rendimiento en monitor
- [ ] Registrar curva de P&L del paper trading (revisar que `history_paper_trading.csv` se complete).
- [ ] Métricas: Sharpe, Sortino, Calmar, VaR, CVaR, turnover (el backtest v4 las calcula; el paper actual no las reporta al día).

#### 7. 🔐 Gestión de credenciales (si se va a capital real)
- [ ] Si se integra a un exchange: credenciales **least-privilege** y con retiros desactivados (exige el README). Nunca hardcodear.

#### 8. 🔔 Notificación y alertas diarias
- [ ] Avisos cuando el pipeline se detiene, falta data, la señal es anómala o el drawdown supera umbral.

---

### P3 — Recomendado / pulido

#### 9. 📊 Calidad y frescura de datos (ya mejorada hoy)
- [ ] Confirmar que el diario (Coinbase) mantiene `data/qlib` fresco; alertas de gap/missing (deuda del repo).
- [ ] Rate-limit de CryptoCompare reservado para regeneración de génesis (no tocarlo en el día a día).

#### 10. 🧹 Sacar `v5` (S&P) fuera de `work/crypto` — deuda conocida.

#### 11. ⚙️ Universo point-in-time y lockfile multiplataforma + CI.

---

## 🗓️ Orden de ejecución recomendado

```
1. Re-entrenar/evaluar v8 sobre génesis + cerrar holdout (puntos 5 + 2)  → ¿sigue ganadora?
2. Añadir risk controls al paper (drawdown, stale, kill-switch, alertas) → punto 1
   (esto acerca el paper a producción)
3. Modelo de ejecución con costes realistas                             → punto 3
4. Testing + reproducibilidad + lockfile                                → punto 4
5. Métricas en monitor del paper                                        → punto 6
6. Solo con todo lo anterior: preparar el paso a capital real (P2/P3)   → credenciales, notificación
```

**Regla de oro (del README):** hasta que todos los gates pasen, los outputs siguen
siendo **research-only** y **no válidos como evidencia out-of-sample**. El paper
trading es el ensayo; producción real no se toca hasta cerrar los P1.

---

## Resumen: dónde estamos vs dónde ir

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

*Checklist de producción para la estrategia SFM v8. Complementa `work/crypto/README.md` (gates) y `estado_proyecto_crypto.md`.*