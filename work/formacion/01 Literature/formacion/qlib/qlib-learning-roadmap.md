# Hoja de ruta: Aprender Qlib practicando

> Estrategia de aprendizaje basada en experimentos reales sobre el proyecto, no teoría abstracta.

---

## Fase 0 — Lo que ya tienes ✅

- Proyecto qlib funcionando con baseline CN
- Wiki operativa (MkDocs + Obsidian)
- Pipeline de experimentos (`prepare` / `train`)
- Configs US preparadas
- `mlruns/` con varios experimentos registrados

---

## Fase 1 — US Market Baseline

**Qué aprenderás:**
- Cómo se estructura un dataset en Qlib (binario, calendario, instrumentos)
- Diferencia entre regiones (`cn` vs `us`)
- Cómo se define un universo, benchmark, proveedor de datos
- Cómo se interpreta el output de `--mode prepare`

**Qué hacer:**
1. Descargar dataset US → `~/.qlib/qlib_data/us_data` (ver [[download-us-market-data.md]])
2. Ejecutar `--mode prepare` con `sp500_us.yaml`
3. Ejecutar `--mode train`
4. Mirar resultados en la wiki (dashboard, baselines, runs-index)

**Pregúntate:**
- ¿Qué features tiene Alpha158?
- ¿Qué hace exactamente el handler?
- ¿Cómo se divide train/valid/test?

---

## Fase 2 — Jugar con configs

**Qué aprenderás:**
- Formato YAML de Qlib (`qlib_init`, `task`, `dataset`, `model`, `port_analysis`)
- Cómo cambiar parámetros del modelo, fechas, topk, costes
- Cómo crear configs propios

**Qué hacer:**
1. Coge el config US y haz cambios pequeños:
   - Cambia `topk` (20, 50, 100)
   - Cambia entre `label 5d` y `label 1d`
   - Cambia fechas de backtest
   - Varía costes de transacción
2. Ejecuta y compara resultados en la wiki
3. Crea tu propio config: `config/mi_primer_experimento.yaml`

**Pregúntate:**
- ¿Cambia el ranking de runs al tocar topk?
- ¿Qué métrica mejora y cuál empeora con cada cambio?

---

## Fase 3 — Features: Alpha158 y más allá

**Qué aprenderás:**
- Cómo se calculan los features (Alpha158 = 158 features técnicas)
- Qué informa cada grupo (precio, volumen, volatilidad, etc.)
- Cómo añadir features propios

**Qué hacer:**
1. Leer el código de `Alpha158` en `vendor/microsoft-qlib/qlib/contrib/data/handler.py`
2. Crear una variante `Alpha158_simple` que use solo 20 features
3. Comparar si empeora mucho con menos features
4. (Avanzado) Añadir un feature nuevo (RSI, indicador propio)

**Pregúntate:**
- ¿Qué features tienen más correlación con el target?
- ¿El modelo funciona igual con menos features?

---

## Fase 4 — Modelos: más allá de LightGBM

**Qué aprenderás:**
- Cómo Qlib abstrae los modelos (`LGBModel`, `XGBModel`, `GRUModel`)
- Diferencia entre modelos tree y redes neuronales
- Impacto de hiperparámetros

**Qué hacer:**
1. Instalar e integrar `xgboost`: cambiar a `XGBModel` en un config
2. Variar parámetros de LightGBM (learning_rate, num_leaves, subsample)
3. Comparar resultados en la wiki
4. (Avanzado) Probar `GRUModel` de Qlib o un modelo PyTorch propio

**Pregúntate:**
- ¿XGBoost da resultados distintos a LightGBM en el mismo dataset?
- ¿Más complejidad de modelo se traduce en mejor backtest?

---

## Fase 5 — Portfolio: de la señal a la cartera

**Qué aprenderás:**
- Diferencia entre señal (signal) y cartera (portfolio)
- Estrategias de Qlib: `TopkDropoutStrategy`, `WeightStrategyBase`
- Cómo modelar costes de transacción
- Interpretación de métricas con costes vs sin costes

**Qué hacer:**
1. Cambiar la estrategia de portfolio a `WeightStrategyBase`
2. Variar costes (open_cost, close_cost) y ver impacto en el ranking
3. Comparar drawdown entre estrategias concentradas y diversificadas

**Pregúntate:**
- ¿Cuándo una señal buena no se traduce en PnL?
- ¿A partir de qué nivel de costes el backtest deja de ser viable?

---

## Fase 6 — Paper trading

**Qué aprenderás:**
- Pipeline de producción vs pipeline de investigación
- Generar señales fuera de backtest
- Persistencia y logging de decisiones diarias
- Monitorización de degradación del modelo

**Qué hacer:**
1. Escribir un script que cargue el modelo entrenado
2. Genere predicciones para el día actual
3. Genere una cartera objetivo
4. Persista todo en un log diario
5. Comparar señales en tiempo real vs backtest histórico

**Pregúntate:**
- ¿El modelo se degrada con el tiempo?
- ¿Las señales en vivo se parecen a las del backtest?

---

## Resumen visual

```
Fase 1 ──► US Market Baseline      (ya)
Fase 2 ──► Jugar con configs       (días)
Fase 3 ──► Features                (semana)
Fase 4 ──► Modelos                 (semana +)
Fase 5 ──► Portfolio               (semana +)
Fase 6 ──► Paper trading           (cuando domines lo anterior)
```

Cada fase es un experimento real que queda registrado en `mlruns/` y visible en la wiki. **No hay teoría sin práctica.**

---

## Referencias útiles

- `vendor/microsoft-qlib/qlib/contrib/data/handler.py` — código de Alpha158
- `vendor/microsoft-qlib/qlib/contrib/model/gbdt.py` — LGBModel
- `vendor/microsoft-qlib/examples/` — ejemplos oficiales
- `docs/experimental-results.md` — historial de resultados
- `wiki/research/runs-index.md` — índice plano de todos los runs
