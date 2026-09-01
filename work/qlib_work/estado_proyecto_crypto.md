# 🪙 Proyecto Crypto — Estado y lectura (2026-09-01)

> **Proyecto:** Qlib Work (frente crypto)
> **Fecha:** 2026-09-01
> **Fuente:** `work/formacion/Estado Crypto.md` + salidas del piloto en `work/crypto/output/` + avances de infraestructura de datos del 2026-09-01.
> **Objetivo de este doc:** resumen accesible del estado del frente crypto y de los próximos pasos, alineado con el resto de `qlib_work/`.

---

## 📌 Qué es

Sistema de **investigación cuantitativa sobre criptomonedas** con Qlib + SFM (State Fusion Model) + Optuna. Universo: **BTC, ETH, SOL, XLM, ADA, XRP, DOGE, LINK, LTC**.

**Fase:** exclusivamente **investigación** (sin paper-trading ni capital real). Todo el pipeline es **causal y trazable** (sin fuga temporal): provider atómico, datos cerrados con manifests/hashes, nested walk-forward, escenarios de costes.

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

## 🚦 Estado de los gates

| Gate | Estado | Evidencia |
|---|---|---|
| Contención de prototipos antiguos (con fuga) | ✅ Superado | salidas separadas, `research-only` |
| Causalidad del preprocessing | ✅ Superado | tests anti-leakage; clipping/scaler por train |
| Datos cerrados y trazables | ✅ Superado | manifests SHA-256 |
| Nested walk-forward | ✅ Técnicamente | smoke 2 folds; holdout no evaluado |
| Modelo de costes v2 | ✅ En módulo | `execution_costs_v2.py`; falta alimentar datos reales |
| **Comparación de universos** | ⚠️ **Piloto completo → gates RECHAZAN** | 6/6 combos; `holdout_may_be_opened: false` |
| **Holdout final** | 🔒 Bloqueado | 2026-03-02 → 2026-08-13, 165 fechas; `evaluated: false` |
| **Paper trading** | 🔒 Bloqueado | depende de todos los gates anteriores |

---

## 📊 Resultado del piloto (dato clave)

Sharpe neto medio por universo (6 folds, costes calibrados train-only, nocional $10k):

| Universo | Sharpe medio | Mediana | Desv. | Folds positivos | Peor DD |
|---|---:|---:|---:|---:|---:|
| Original 5 | **−0.379** | 0.040 | 1.65 | 3/6 | −51% |
| Completo 9 | −1.229 | −0.969 | 1.33 | 1/6 | −54% |
| Reducido 8 (sin XLM) | −0.904 | −0.567 | 1.40 | 2/6 | −59% |

**Lectura honesta:** el piloto **confirma inestabilidad, no rentabilidad**. Dispersión enorme y el **fold 3 (2025-08 → 2026-03) es el peor en las 6 combinaciones**. Ninguno supera los gates predeclarados → **el holdout sigue correctamente cerrado**.

---

## 🔴 Próximos pasos (en orden)

1. **B2 — Alimentar el modelo de costes v2 con datos reales.** Implementado ✅; faltan: fee schedule, bid/ask, profundidad (mientras no existan → degrada a proxy).
2. **B3 — Conectar baselines + DSR al experimento formal.** `baselines.py` implementado ✅; falta conectarlo con `n_trials` = universos × seeds.
3. **D1 — Experimento formal (Fase 4).** 3 universos × 3 seeds (42,43,44), 30 trials/fold, 60 épocas. Empieza con **dry-run**. **Largo:** el piloto tardó ~3h/combo.
   - Si ninguna variante supera gates estables → decisión correcta: no seleccionar ni abrir el holdout.
4. **D2 — Holdout final** (solo si D1 pasa gates).
5. **D3 — Paper trading** (solo si holdout aprueba).

**Deuda no bloqueante:** lockfile multiplataforma + CI, mover `v5` (S&P) fuera de `work/crypto`, alertas freshness/gaps, universo point-in-time.

---

## 💡 Valoración (lectura de hoy)

- La **infraestructura de datos está ahora sólida** (génesis + incremental, USD garantizado, UNA base Qlib, pipeline orquestado). Es un avance de **fundación** que quita trabas de datos para cuando se retome la investigación.
- **La investigación sigue honestamente parada**: el piloto no dio rentabilidad estable, y el sistema correctamente **no avanza** hacia holdout/paper hasta que un experimento formal justifique abrirlo.
- El histórico de génesis es **valioso para un futuro re-entrenamiento** (más datos de train), pero **no cambia por sí solo el veredicto** de investigación del frente crypto.

---

*Documento de referencia del frente crypto. Complementa `work/formacion/Estado Crypto.md` y `work/crypto/`. Actualizado 2026-09-01 con los avances de infraestructura de datos.*