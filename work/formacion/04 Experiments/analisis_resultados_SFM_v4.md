---
tags: [analysis, results, sfm, v4, crypto, failure-mode]
status: completed
date: 2026-06-03
---

# Análisis de Resultados: SFM v4 en Cripto

> **Veredicto: SFM v4 NO genera alpha en este mercado/periodo.**
> Resultados sistemáticamente negativos en todas las métricas, con degradación temporal y varianza entre trials inaceptablemente alta. El modelo no es operativo.

---

## 1. Datos de la ejecución

- **Script:** `scripts/crypto/qlib_sfm_pipeline.v4.py`
- **Activo:** Criptomoneda (pipeline SFM para cripto)
- **Optuna:** 100 trials, 7 HPs, TPESampler + MedianPruner
- **Top-K:** 5 mejores por validation loss, reentrenados y evaluados en test
- **Walk-Forward:** 3 ventanas secuenciales con train creciente
- **Archivos fuente:** `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md`

---

## 2. Resultados Top-K (5 mejores trials)

| Trial | val_loss | Sharpe | Equity final | vs Hold |
|-------|----------|--------|-------------|---------|
| #1 | 0.0010477 | −1.35 | 0.71x | −6.9% |
| #2 | 0.0010478 | −1.67 | 0.53x | −24.3% |
| **#3 🟢** | **0.0010508** | **+0.57** | **1.09x** | **+31.2%** |
| #4 | 0.0010585 | −1.54 | 0.60x | −17.3% |
| #5 | 0.0010627 | −1.37 | 0.66x | −11.7% |
| **Agregado** | — | **μ = −1.07 (σ = 0.83)** | **μ = 0.72x (σ = 0.19)** | **μ = −5.8%** |

**Ratio de acierto:** 1/5 trials con Sharpe positivo.

---

## 3. Resultados Walk-Forward (3 ventanas)

| Ventana | Sharpe SFM | Equity SFM | Tendencia |
|---------|-----------|------------|-----------|
| 1 (más temprana) | **−0.55** | 0.85x | — |
| 2 | **−1.48** | 0.48x | ⬇️ −0.93 |
| 3 (más reciente) | **−1.83** | 0.73x | ⬇️ −0.34 |
| **Agregado** | **μ = −1.29 (σ = 0.54)** | **μ = 0.68x (σ = 0.15)** | **⬇️ Pendiente: −0.64/ventana** |

Degradación **monótonamente decreciente**: el modelo rinde peor en cada ventana sucesiva.

---

## 4. Diagnóstico de hiperparámetros

Los 5 mejores trials muestran convergencia sospechosa:

| Parámetro | Rango de búsqueda | Top-5 values | ¿Variación? |
|-----------|-------------------|-------------|-------------|
| **batch_size** | 16 / 32 / 64 | 64, 64, 64, 64, 64 | ❌ Cero — todas a 64 |
| **lookback** | 15–50 | 35, 35, 35, 35, 35 | ❌ Cero — colapsó a 35 |
| **hidden_dim** | 32–128 | 80, 48, 80, 80, 80 | Casi todas 80 |
| **dropout** | 0.1–0.5 | 0.4, 0.2, 0.4, 0.4, 0.35 | Leve |
| **lr** | 1e-4 – 1e-2 | 0.0014 – 0.0007 | Moderada |
| **freq_components** | 4–20 | 9, 19, 15, 17, 10 | ✅ La única con variación real |
| **weight_decay** | 1e-5 – 1e-3 | 1.14e-5 – 1.57e-5 | Casi cero |

**Conclusión:** Optuna encontró un **mínimo local plano** y no exploró suficiente variedad. batch_size=64 dominó todas las runs, posiblemente por ser el valor por defecto más estable en validación.

---

## 5. Señales de alarma detectadas

### 5.1 El val_loss NO discrimina rendimiento real

- Diferencia entre mejor y peor val_loss de los top-5: solo **0.000015** (~1.4%)
- Pero la diferencia en Sharpe va de **−1.67 a +0.57**
- Correlación val_loss vs Sharpe: **r = −0.18** (prácticamente ruido)

> ⚠️ **Trial Rank Hazard (TRH):** El criterio de optimización (val_loss) no se correlaciona con la métrica objetivo (Sharpe en test). El mejor trial en validación es, con frecuencia, de los peores en test.

### 5.2 Degradación temporal sistemática

El walk-forward muestra una pendiente negativa consistente:

```
V1 → V2: −0.93 de Sharpe
V2 → V3: −0.34 de Sharpe
Tendencia: MONOTÓNICAMENTE DECRECIENTE
```

Esto descarta la hipótesis de "mala suerte en una ventana": el modelo pierde **sistemática y progresivamente** a medida que avanza el tiempo.

### 5.3 Varianza excesiva entre trials

- σ = 0.83 en Sharpe del Top-K
- El trial #3 da +0.57, pero el #2 da −1.67 con val_loss casi idéntico
- **Resultados no reproducibles** incluso entre trials del mismo estudio

---

## 6. Hipótesis sobre las causas

| # | Hipótesis | Evidencia | Prioridad |
|---|-----------|-----------|-----------|
| 1 | **Overfitting clásico** | val_loss minúsculo (0.001) pero test Sharpe negativo; val_loss no correlaciona con test | 🔴 Alta |
| 2 | **Cambio de régimen de mercado** | Walk-forward empeora monótonamente → el modelo se entrena en un régimen y testea en otro | 🔴 Alta |
| 3 | **batch_size demasiado grande** | batch=64 domina; batch grande → mínimos más agudos, peor generalización | 🔴 Alta |
| 4 | **Arquitectura SFM inadecuada para este activo** | SFM (State Frequency Memory) asume estructura espectral que el cripto puede no tener | 🟡 Media |
| 5 | **Look-ahead bias residual** | El split es cronológico, pero puede haber fuga en denoising (wavelet) o normalización | 🟡 Media |
| 6 | **Mercado bajista, SFM amplifica pérdidas** | Equity Hold también negativa; SFM pierde más que Hold en lugar de cubrir | 🟢 Baja |

---

## 7. Recomendaciones

| Prioridad | Acción | Fundamento |
|-----------|--------|------------|
| 🔴 Alta | Probar con equity US (SP500) | Determinar si el problema es SFM o el activo cripto |
| 🔴 Alta | Reducir batch_size (forzar 16 o 32) | batch=64 es sospechosamente dominante en top-5 |
| 🟡 Media | Añadir Transformer/LSTM como baseline | Para saber si el problema es SFM o ML en general para este activo |
| 🟡 Media | Calcular Sharpe de Hold en el periodo de test | Verificar si el mercado fue bajista y cuantificar la magnitud del underperformance |
| 🟡 Media | Forzar exploración de Optuna (aumentar n_trials o usar RandomSampler primero) | El espacio efectivo explorado fue pequeño |
| 🟢 Baja | Aumentar dropout range (0.3–0.7) | Más regularización para combatir overfitting |
| 🟢 Baja | weight_decay más alto (1e-4 – 1e-2) | Ídem |
| 🟢 Baja | Probar sin wavelet denoising | El denoising puede estar eliminando señal relevante |

---

## 8. Correcciones aplicadas post-análisis

Tras detectar los problemas anteriores, se aplicaron estos cambios a la v4:

| Cambio | Código | Motivo |
|--------|--------|--------|
| **Gradient clipping** | `clip_grad_norm_(max_norm=1.0)` en train_trial y train_final | Evita que combinaciones agresivas de HP (lr alto + dropout bajo + hidden_dim grande) produzcan gradientes explosivos → loss Inf |
| **batch_size** | Se eliminó 64 del espacio de búsqueda → solo [16, 32] | batch=64 dominaba artificialmente todos los Top-5 por ser más estable en validación, pero daba peor generalización en test |
| **n_startup_trials** | 5 → **10** | Los primeros trials solían divergir (Inf), corrompiendo la mediana del MedianPruner y desactivando el prune para el resto de la ejecución |

**Efecto esperado:**
- El clipping elimina los `Inf` → el pruner funciona correctamente desde el inicio
- Sin batch=64, Optuna explora tamaños de batch más pequeños que generalizan mejor
- Con n_startup_trials=10, aunque haya trials inestables, la mediana no se contamina

## 9. Valor del pipeline de diagnóstico

Aunque el resultado es negativo, el pipeline de validación (Top-K + Walk-Forward) **funcionó correctamente** y demostró su utilidad:

- ✔️ **Top-K** reveló que solo 1/5 trials funciona → problema no es un mal seed
- ✔️ **Walk-Forward** reveló degradación temporal → problema no es una mala partición
- ✔️ **Agregación estadística** evitó caer en p-hacking

**Con una sola partición test tradicional, estos problemas habrían pasado desapercibidos.**

---

## 9. Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline.v4.py` — script ejecutado
- `scripts/crypto/output/optuna_sfm_v4/top_k_results.json` — resultados Top-K
- `scripts/crypto/output/optuna_sfm_v4/walk_forward_results.json` — resultados Walk-Forward
- `obsidian/01 Literature/formacion/qlib/sfm-v4-caracteristicas.md` — nota técnica de la v4
- `obsidian/01 Literature/formacion/qlib/sfm-comparativa-scripts.md` — comparativa de versiones
- `obsidian/01 Literature/formacion/qlib/img/top_k_v4_real.png` — gráfica Top-K
- `obsidian/01 Literature/formacion/qlib/img/walk_forward_v4_real.png` — gráfica Walk-Forward
