# 🪙 Proyecto Crypto — Estado y lectura (2026-09-01)

> **Proyecto:** Qlib Work (frente crypto)
> **Fecha:** 2026-09-01
> **Fuente:** `work/formacion/Estado Crypto.md` + salidas del piloto en `work/crypto/output/` + avances de infraestructura de datos del 2026-09-01.
> **Objetivo de este doc:** resumen accesible del estado del frente crypto y de los próximos pasos, alineado con el resto de `qlib_work/`.

---

## 📌 Qué es

Sistema de **investigación cuantitativa sobre criptomonedas** con Qlib + SFM (State Fusion Model) + Optuna. Universo: **BTC, ETH, SOL, XLM, ADA, XRP, DOGE, LINK, LTC**.

**Fase actual:** la **estrategia v8 ya está en paper trading** (estrategia ganadora, operativa desde 2026-09-01). La comparación de universos del piloto es investigación pasada/paralela. Todo el pipeline es **causal y trazable** (sin fuga temporal).

> 🧭 **Contexto de actores:** una parte del proyecto se centra en las **estrategias de acciones** (E1/E2/E3 en paper). Este documento es el **frente crypto, separado**. El frente crypto mantiene prioridad baja frente a la medición de estrategias de acciones.

---

## 🆕 Avances de infraestructura de datos (2026-09-01)

Hoy se hizo una mejora importante en la **cadena de datos** del frente crypto (es infraestructura, no resultado de investigación):

### 1. Carga inicial desde génesis — CryptoCompare ✅
- **`download_crypto_cryptocompare.py`**: histórico **COMPLETO desde el génesis real** de cada moneda (paginando con `toTs`).
- Génesis conseguida: **BTC 2010-07, LTC 2013, DOGE 2014, XLM 2014, ETH/XRP 2015, ADA/LINK 2017, SOL 2020**.
- Recorta el padding de ceros previo al listing real de cada coin.
- Requiere **API key** (en `.env`, gitignore). ⚠️ Rate-limit gratis: **100 llamadas/mes**. (Quedaban ~47 hoy; reservado para regenerar génesis puntualmente.)

### 2. Operativa diaria incremental — Coinbase (recomendado) ✅
- **`update_crypto_daily_coinbase.py`**: actualización diaria en **USD real** (`*-USD`), **pública sin límite**.
- Vía **recomendada** para el día a día (evita el tope de 100/mes de CryptoCompare).
- Verificado: rellena días pendientes de forma no destructiva (recuperó 11 días en test).

### 3. Alternativas diarias — Binance / CryptoCompare
- **`update_crypto_daily_binance.py`**: pares `*USDT` (stablecoin 1:1 USD), sin límite.
- **`update_crypto_daily_cryptocompare.py`**: CryptoCompare USD literal, pero tope 100/mes → uso puntual.

### 4. Moneda garantizada en dólares 💵
- CryptoCompare = **USD literal** (`tsym=USD`); Coinbase = **USD real** (`*-USD`); Binance = USDT (~1:1 USD).
- **Guarda automática `_assert_usd_plausible`** en los 3 scripts: aborta si el último close cae bajo el umbral USD por coin (evita corromper el histórico con una moneda equivocada).

### 5. Base Qlib consolidada (UNA sola) ✅
- Se **consolidó todo en `data/qlib`** (histórico génesis + incremental diario). Se **eliminó** la base temporal `data/qlib_cryptocompare`.
- **Fuente de verdad:** los CSV por coin en `scripts/crypto/csv_data/crypto_cryptocompare/ohlcv/{coin}.csv`.
- `data/qlib` es un **derivado** regenerable desde los CSV (`convert_crypto_qlib.py`).

### 6. Pipeline diario orquestado ✅
- **`run_daily_pipeline.sh`**: encadena 1) Coinbase incremental → 2) convertir a `data/qlib` → 3) señal diaria → 4) paper trading. Todo apuntando a **`data/qlib`**.
- Rutas portables vía ENV (`QLIB_PROJECT_DIR`, `QLIB_PYTHON`).

> 📓 **Notebook:** `work/crypto/notebooks/cargar_ohlcv_desde_qlib.ipynb` — carga OHLCV de las 9 coins desde Qlib en pandas y muestra head/tail (desde fecha real de inicio).

---

## 🚦 Estado actual

| Frente | Estado | Nota |
|---|---|---|
| **Estrategia v8 (SFM)** | ✅ **En paper trading** (desde 2026-09-01) | Modelo `sfm_top3.pth`; señal diaria COMPRA en BTC / VENTA en otras. $10k, 1 trade inicial (BTC a 77.689). **Estrategia ganadora operativa.** |
| Comparación de universos (piloto) | ⚠️ Rechazado | Investigación pasada; ninguno superó gates predeclarados. No es la vía actual. |
| Holdout final del piloto | 🔒 Cerrado | Solo aplicable al experimento formal de universos (no bloquea a v8). |
| **Datos** | ✅ Génesis + incremental | Consolidados en `data/qlib` (CryptoCompare génesis + Coinbase diario, USD garantizado, ver sección siguiente). |
| Pipeline diario | ✅ Orquestado + automatizado | `run_daily_pipeline.sh` (Coinbase→convert→señal→paper→métricas→notif) sobre `data/qlib`. Cronjob **9:00** (paper v8) + **9:30** (watchdog salud). |

---

## 📈 Estado del paper trading v8 (2026-09-01)

- **Modelo:** `sfm_top3.pth` (del ensemble Top-K de v8).
- **Señal de hoy:** 🟢 **COMPRA BTC** (confianza ALTA, retorno esp. +2.94%); las 7 monedas con score negativo → **VENTA**; ETH → ESPERAR.
- **Cartera paper:** capital $10k, cash $6.663,33, posición BTC (0.0429 BTC @ 77.689), 1 trade, fees $3.33. Recién iniciada (día 1).

> El paper trading de v8 es la **estrategia activa** del frente crypto. El `run_daily_pipeline.sh` la alimenta cada día.

---

## 🤖 Automatización diaria y notificaciones (2026-09-01)

La operativa de paper v8 quedó **automatizada y vigilada** con cronjobs Hermes:

| Cronjob Hermes | Horario | Función |
|---|---|---|
| **Papel trading v8 diario** | **9:00** | `cron_daily_v8.sh` → `run_daily_pipeline.sh`: Coinbase incremental → convert Qlib → señal → paper → métricas → notifica resumen + métricas a @oscarbot_toni_bot |
| **Healthcheck v8 (watchdog)** | **9:30** | `watchdog_v8.sh` → `watchdog_v8.py`: comprueba que el pipeline haya corrido (<27h) y que los datos estén al día (≤2 días). Notifica a @oscarbot_toni_bot **solo si hay problema**; silencioso si OK. 30 min después del principal para detectar fallos silenciosos. |

**Notificaciones Telegram** (bot **@oscarbot_toni_bot**, token/chat en `/opt/data/qlib/.env` gitignored):
- **Resumen diario** del paper (capital, P&L, posiciones) — cada ejecución del pipeline.
- **Alertas de riesgo** (drawdown, stale, kill-switch, exposición) — si algo bloquea.
- **Monitor de métricas** (Sharpe, Sortino, Calmar, VaR, drawdown) — fin de pipeline.
- **Healthcheck** — alerta de pipeline detenido / datos obsoletos, o informe `--report`.

> **Paso 7 casi cerrado:** solo queda pendiente la **credencial de exchange (Binance)**,
> que es intencionalmente para cuando se decida capital real (no es necesaria para paper).

---

## 🔍 Conclusiones del Backtest y Validación (2026-09-01) — ⚠️ Cautela para producción

Backtest completo (2025→ago-2026, multi-moneda, costes Binance + yield cash USDT) +
sensibilidad + mini-holdout. Detalle completo en **`checklist_produccion_v8.md`**
(sección "Conclusiones del Backtest"). Resumen:

| Métrica | Valor |
|---|---|
| Retorno USD (todo el periodo) | +4,3% |
| Retorno EUR (todo el periodo) | **-6,9%** (por FX) |
| Mejor config en 2026 aislado (holdout real) | **+9,6% USD** (BASE actual) |
| Max drawdown | -34% |

**Lectura clave para producción:**
1. El **"Sharpe 2.74" del training era top-1 SIN costes** → espejismo. Con costes reales, el top-1 colapsa a -49%.
2. La **v8 actual (BASE)** es **"plana pero estable" en USD**; en **EUR es negativa** por el tipo de cambio. El edge del modelo, neto de costes, es **débil**.
3. La config "optimizada" (+28,6%) **no superó la validación** (mini-holdout): sobreajuste a 2025. La **BASE es la más robusta**.
4. **El yield del cash USDT (~4,5% APY)** es el componente de valor más fiable y accesible.
5. ⚠️ **Recomendación: NO producir v8 con capital real todavía**; seguir en paper con la BASE + yield hasta pasar el **holdout final inmutable** (requiere re-entrenar en génesis, Paso 2/GPU).

---

## 🆕 Avances de infraestructura de datos (2026-09-01)

## 📊 Resultado del piloto (contexto histórico)

El que sigue fue el resultado del **experimento de comparación de universos** (piloto), que es **investigación pasada / paralela**. No refleja el estado actual: la **v8 ya es la estrategia ganadora en paper trading** y este piloto no la bloquea.

Sharpe neto medio por universo (6 folds, costes calibrados train-only, nocional $10k):

| Universo | Sharpe medio | Mediana | Desv. | Folds positivos | Peor DD |
|---|---:|---:|---:|---:|---:|
| Original 5 | **−0.379** | 0.040 | 1.65 | 3/6 | −51% |
| Completo 9 | −1.229 | −0.969 | 1.33 | 1/6 | −54% |
| Reducido 8 (sin XLM) | −0.904 | −0.567 | 1.40 | 2/6 | −59% |

**Lectura:** este piloto no dio rentabilidad estable y el holdout quedó cerrado, por lo que la vía de "comparación de universos" no prosperó. La estrategia que sí avanzó es la **v8**, ahora en paper trading.

---

## 🔴 Próximos pasos

> El foco actual está en **operar/monitorizar la estrategia v8 en paper trading** y
> en **producir la v8 SOLO si pasa el holdout final**. Las conclusiones del backtest
> (2026-09-01) recomiendan **cautela**: la v8 es "plana" en USD y negativa en EUR,
> con edge neto débil; el valor más fiable es el **yield del cash USDT**.
> Ver **`checklist_produccion_v8.md`** (sección "Conclusiones del Backtest").

Además, en paralelo:
- **Validar la cadena de datos diaria.** Confirmar que `data/qlib` se mantiene actualizado y que los 3 scripts de descarga (Coinbase/Binance/CryptoCompare) siguen el formato USD.
- **Deuda técnica de investigación (menor prioridad):** B2 (costes con datos reales), B3 (baselines + DSR), D1 (experimento de universos).

**Deuda no bloqueante:** lockfile multiplataforma + CI, mover `v5` (S&P) fuera de `work/crypto`, universo point-in-time. *(Las **alertas freshness/gaps** ya quedaron implementadas con el watchdog del Paso 7.)*

> 📌 Para el plan detallado de producción de v8, ver **`checklist_produccion_v8.md`** (documento único).

---

## 💡 Valoración (lectura de hoy)

- **La estrategia v8 es la ganadora y está en paper trading** (arrancó 2026-09-01): señal COMPRA en BTC, cartera $10k, 1 trade inicial. Es el activo principal del frente crypto, no una investigación en pausa.
- La **infraestructura de datos quedó sólida** hoy (génesis + incremental Coinbase, USD garantizado, UNA base Qlib, pipeline orquestado). Es la base que **sostiene la operativa diaria de v8**.
- La **operativa quedó automatizada y vigilada** (cron 9:00 + watchdog 9:30, notificaciones a @oscarbot_toni_bot). El Paso 7 está casi cerrado (solo falta credencial de exchange para capital real).
- El **histórico de génesis** abre la puerta a **re-entrenar v8 con más datos**, una mejora concreta a evaluar.
- La investigación de universos (piloto) fue una línea que **no prosperó**; el frente no está parado, está operando v8.

---

*Documento de referencia del frente crypto. Complementa `work/formacion/Estado Crypto.md` y `work/crypto/`. Actualizado 2026-09-01: **v8 en paper trading** + **backtest/validación (cautela para producción)** + **operativa automatizada y vigilada (cron 9:00 + watchdog 9:30)** + avances de infraestructura de datos.*