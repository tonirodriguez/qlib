# 🧬 Purged Cross-Validation (Purged CV) — Guía completa

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work — formación en inversión cuantitativa
> **Nivel:** Intermedio-avanzado
> **Fuente base:** López de Prado, *Advances in Financial Machine Learning* (2018)

---

## 1. El problema: ¿por qué la validación normal falla en finanzas?

En ML clásico se usa **k-fold cross-validation**:
```
Datos: [A][B][C][D][E]  →  entrenar en 4, validar en 1, repetir 5 veces
```
Esto asume que las muestras son **independientes e idénticamente distribuidas (iid)**.

**Pero los datos financieros NO son iid:**
1. **Solapamiento de etiquetas (label overlap):** si la etiqueta es "retorno a los próximos 20 días", dos observaciones consecutivas comparten 19 días de la misma ventana. No son independientes.
2. **Autocorrelación:** los retornos de hoy se parecen a los de ayer.
3. **Características repetidas:** la misma información fluye a través de varias filas.

**El peligro:** en un k-fold clásico, información del conjunto de **validación se filtra al entrenamiento** (data leakage / look-ahead), especialmente con etiquetas solapadas. Esto infla el rendimiento "out-of-sample" → **sobreestimamos el alpha y luego el modelo falla en producción.**

---

## 2. La solución: purge (purga) + embargo

### 2.1 Purge (purga)
Para un conjunto de validación [A, B], las etiquetas **antes** de A se solapan con datos posteriores que entraron en el entrenamiento. Se **purguan** (eliminan) del entrenamiento las muestras cuyo *intervalo de etiqueta* se solape con el del conjunto de validación.

```
                ┌─ validación ─┐
Entrenamiento:  [·][·][·][·][·][A][B]...
                     ↑
              Se purgan estas (sus etiquetas se solapan con A/B)
```

### 2.2 Embargo (embargo / congelación)
Incluso tras purgar, el **efecto de la información** puede persistir unos días más que la etiqueta (p.ej. tras un anuncio). El embargo elimina además **una franja temporal extra** tras el \*intervalo de etiqueta\* del set de validación.

```
┌─ validación ─┐┌─ EMBARGO ─┐
[A][B].........[·][·][·]  ← también se quitan del entrenamiento
```

### La fórmula (PurgedKFold)
Para cada pliegue `k`:
1. **Determina el intervalo temporal** de cada muestra (por su etiqueta).
2. **Elimina del entrenamiento** toda muestra cuyo intervalo de etiqueta se **solape** con el del pliegue de validación (purga).
3. **Elimina además** las muestras dentro de la **ventana de embargo** (unos `h` días tras el intervalo de etiqueta del pliegue).

---

## 3. Cuándo usar purge vs embargo (lo que importa)

| Situación | ¿Purga? | ¿Embargo? |
|---|---|---|
| Etiquetas no solapadas (retorno a 1 día) | No crítica | No crítica |
| **Etiquetas solapadas** (retorno a 20-120 días) | **SÍ, imprescindible** | Sí, recomenda |
| Transitoriedad de la señal (fundamentals, momentum) | Sí | **Sí, crítica** |
| Eventos con cola de información (PEAD, announcements) | Sí | **Sí, útil** |

**En nuestro caso concreto (momentum 120d / PEAD):** las etiquetas están muy solapadas (retornos a 20-60 días) y hay cola de información (PEAD) → **purga + embargo son esenciales** para una validación honesta.

---

## 4. Implementación práctica (numpy/scikit-learn)

```python
import numpy as np
import pandas as pd

def purged_kfold_index(times, label_end, n_splits=5, embargo_days=10):
    """Genera índices purged+embargo para CV temporal.

    times      : Series/array con el timestamp (inicio) de cada muestra
    label_end  : Series/array con el timestamp de FIN del intervalo de la etiqueta
                 (inicio + horizonte del retorno)
    """

    times = pd.Series(np.asarray(times))
    label_end = pd.Series(np.asarray(label_end))
    n = len(times)

    # puntos de corte temporal (split de los pliegues)
    split_points = np.linspace(times.min(), times.max(), n_splits + 1)[1:-1]

    folds = []
    # construir cada pliegue: test = un tramo temporal, train = lo demás (purged+embargo)
    for i in range(n_splits):
        test_start = split_points[i] if i > 0 else times.min()
        test_end = split_points[i + 1] if i < n_splits - 1 else times.max()

        test_idx = np.where(
            (times >= test_start) & (times <= test_end)
        )[0]

        # Purga: eliminar del train muestras cuyo label_end > test_start
        #         (su etiqueta se solapa con el test) o label_end < test_start - embargo
        train_idx = np.arange(n)
        train_idx = train_idx[
            (label_end < (test_start - np.timedelta64(embargo_days, "D"))) |
            (label_end < test_start) &
            (times < test_start)
        ]

        # Embargo: no usar muestras cuya etiqueta termine dentro de la ventana tras el test
        # (ya está cubierto por la condición label_end < test_start - embargo)
        folds.append((train_idx, test_idx))

    return folds
```

> ⚠️ **Nota:** la implementación de arriba es didáctica. Para producción usa `mlfinlab` (PurgedKFold) o una versión validada con tests. La clave es el **concepto**, no el código exacto.

---

## 5. Cómo se vería en Qlib (enfoque práctico)

Qlib no trae purged CV de serie, pero puedes hacer la validación **con walk-forward purgado manual**:

```python
# En lugar de: train_period, valid_period fijos (que asumen independencia)
# Haz: walk-forward con purga

train = {"start": "2018-01-01", "end": "2022-06-01"}
valid = {"start": "2022-06-01", "end": "2022-12-31"}

# PERO, por purga, elimina del train las filas cuya etiqueta (retorno a 60d)
# se solape con el inicio del valid (2022-06-01):
#   train_filtrado = train[train.fecha <= valid.start - 60_dias]
```

**Regla práctica para nuestro stack:**
```
train_end_efectivo = valid_start − (horizonte_de_la_etiqueta + embargo)
```
Es decir, cuando validas con etiquetas a 60 días, el train debe **terminar 60 días antes** (purga) **+ unos días más** (embargo) del start del valid.

---

## 6. Por qué esto importa en TU proyecto (lección concreta)

### El caso que ya vivimos
Cuando probamos el **backtest combinado momentum + PEAD**, tuvimos "éxito" con datos parciales de earnings (IC 0.19) y luego el resultado no se sostuvo (Sharpe 0.57-0.87 vs 1.0 del momentum puro). **Una parte de esa sobreestimación inicial era data leakage por solapamiento de etiquetas.**

- El PEAD se midió con retorno post-anuncio a 20-60 días → **etiquetas muy solapadas**
- Conviene re-validar el IC del PEAD con **purged CV** para saber si el alpha 0.19 es real o inflado por el solapamiento

### Lo que debes validar con purged CV
1. El **IC del momentum 120d** (¿sigue en 0.066 con purga? Era walk-forward estándar)
2. El **IC del PEAD** (¿sigue en 0.19 con purga de las etiquetas de 20-60 días?)
3. Cualquier **combinación de factores** futura

---

## 7. Resumen de buenas prácticas de validación

| Práctica | Para qué |
|---|---|
| **Walk-forward (rolador)** | Validación temporal realista (ya lo usas ✅) |
| **Purga** | Eliminar solapamiento de etiquetas entre train y valid |
| **Embargo** | Eliminar la cola de información tras cada evento |
| **Purged CV** | Combinación robusta de ambas para etiquetas solapadas |
| **Test de datos nuevos** | Confirmar que el modelo generaliza (retiene el mejor modelo) |
| **Combinación de caminos** | Probar varias semillas para no sobreajustar al azar (ya lo usas en cripto ✅) |

---

## 8. Recursos y siguiente paso

- **Libro:** *Advances in Financial Machine Learning* — Marcos López de Prado (cap. 7: Cross-Validation)
- **Lib:** `mlfinlab` (PurgedKFold, CombinatorialPurgedKFold) — la implementación de referencia
- **Librería Qlib:** no trae purged CV nativo; se implementa manualmente o vía mlfinlab

**Acción recomendada:** aplicar purged CV para **re-validar el IC del PEAD** (nuestro alpha de 0.19), para confirmar si es real o estaba inflado por el solapamiento de etiquetas de 20-60 días.

---

*Documento de formación del proyecto Qlib Work. Basado en López de Prado (2018).*
