# Auditoría SFM v8 — Los resultados de test son inválidos

> **Fecha:** 2026-10-26
> **Pipeline auditado:** `work/crypto/qlib_sfm_pipeline.v8.py`
> **Resultados en cuestión:** `sfm-v8-resultados.md` (Sharpe 2.74, equity 20.03x)
> **Veredicto:** 🔴 **NO son evidencia válida de rendimiento.** Tres leaks de
> futuro confirmados y cuantificados.

---

## 1. Resumen

`sfm-v8-resultados.md` reporta, para el mejor trial en test:

| Métrica | Valor reportado |
|---|---|
| Sharpe | **2.74** |
| Equity final | **20.03x** |
| Retorno anual | **+1.903%** |
| Direction Accuracy | 58.3% |

**Estos números están contaminados por fuga de información futura.** El modelo,
durante el test, tiene acceso a datos que en producción no tendría.

| Leak | Línea | Efecto medido |
|---|---|---|
| **L1** Denoising wavelet global | 240 | El suavizado de cada fecha usa fechas futuras |
| **L2** Inflado de la correlación feature-label | 240+242 | **+0.1424** de correlación artificial |
| **L3** `bfill()` hacia atrás | 221, 227 | Propaga el primer valor futuro a todo el pasado |

---

## 2. L1 — Denoising sobre toda la serie (línea 240)

```python
# L239-240
# Denoising wavelet ANTES de la label
market_matrix = denoise_market_matrix(market_matrix)
```

El denoising se aplica a la **matriz completa antes de cualquier split**. La
transformada wavelet calcula coeficientes **globales**: el coeficiente de
aproximación representa la tendencia de *toda* la serie. Por tanto, el valor
suavizado en la fecha `t` depende de fechas posteriores a `t`.

### Medición

Comparando el denoising global (como lo hace el pipeline) contra uno causal
(ventana que termina en `t`), sobre una serie sintética de 1.800 puntos:

| | Valor |
|---|---|
| Diferencia media | 2.2973 |
| Diferencia máxima | 9.5980 |
| Diferencia relativa media | **4.63% del precio** |

**Correlación entre el ajuste del denoising hoy y el retorno de mañana: `+0.2440`.**

Esa correlación es la prueba: si el denoising no usara información futura, no
podría anticipar el retorno del día siguiente. Un `+0.244` significa que el
suavizado "sabe" parcialmente lo que va a pasar.

> **Nota metodológica:** la medición se hizo con un sustituto de ventana
> centrada, porque `pywt` no está instalado en esta máquina. El sustituto
> **no es el wavelet real**, pero comparte la propiedad que causa el leak
> (usar fechas futuras). Con `pip install PyWavelets` el script usa el wavelet
> exacto. La dirección del hallazgo no cambia: el wavelet también es global.

---

## 3. L2 — El leak infla la señal (el dato más contundente)

Aquí está el efecto directo sobre lo que el modelo aprende:

| Feature `close` | Correlación con la label |
|---|---|
| Con denoising **GLOBAL** (actual) | **+0.1629** |
| Con denoising **CAUSAL** (correcto) | **−0.0205** |
| **Señal artificial** | **+0.1424** |

**Toda la señal aparente desaparece al eliminar el leak.** Con denoising causal
la correlación es `−0.02`: prácticamente cero, incluso ligeramente negativa.

Esto significa que **el modelo no está aprendiendo a predecir retornos** —
está explotando la fuga de información del preprocesado.

---

## 4. L3 — `bfill()` propaga el futuro (`fillna` hacia atrás)

```python
# L221
df_close_safe = df_close.replace(0, np.nan).ffill().bfill()
# L227
df_ma20_ratio = (df_ma20 / df_close_safe).replace(...).ffill().bfill().fillna(1.0)
```

`.bfill()` rellena hacia **atrás**, usando el siguiente valor disponible. En un
panel de criptomonedas con fechas de lanzamiento distintas (BTC desde 2015, SOL
desde 2020), esto rellena **todo el pasado de cada moneda con su primer precio
futuro**.

### Medición

Simulando una moneda que empieza en `t=100`:

```
valor real en t=100        : 86.4781
ffill deja en t=0..99      : 100 NaN   (correcto)
bfill pone en t=0..99      : 86.4781   ← el precio de 2020 en 2016
```

**El modelo ve, en 2016, el precio que esa moneda tendrá en 2020.**

Y hay un efecto secundario: con `bfill` el precio es constante en todo el tramo
previo, así que `pct_change()` da 0 y `ratio_5d` da 1.0 — features degeneradas
que el modelo puede usar como identificador de "moneda que aún no existía".

---

## 5. Hallazgo adicional — Inconsistencia feature-label

```python
# L242 — la label usa el precio CRUDO
labels_matrix = (df_close.shift(-fwd_days) / df_close - 1).fillna(0).values
```

La **feature** `close` va denoised (L240), pero la **label** se calcula sobre el
precio crudo. El modelo ve una serie suavizada y debe predecir sobre la serie
real.

No es un leak en sí, pero es un **defecto de diseño**: entrena con una
representación del mundo y se evalúa contra otra. Introduce un sesgo cuya
dirección es difícil de acotar.

---

## 6. Qué NO está afectado

Para ser justo con lo que sí está bien construido:

| Componente | Estado |
|---|---|
| `MinMaxScaler` ajustado solo con train (L572-575, 831-834) | ✅ Correcto |
| `df_pct` (pct_change), `df_vol` (rolling std) | ✅ Causales |
| `df_ma20`, `df_mean_5` (rolling mean hacia atrás) | ✅ Causales |
| Penalización anti-overfitting en el objetivo de Optuna | ✅ Buena idea |
| Top-K en vez de mejor trial (evita p-hacking) | ✅ Buena práctica |
| Walk-forward | ⚠️ Bien planteado, pero **no salva el leak**: el denoising es global respecto a toda la matriz, así que la ventana de test también está contaminada |

El pipeline tiene decisiones metodológicas **acertadas**. El problema es que
el preprocesado se hace antes del split.

---

## 7. Consecuencias

### Sobre los números

- ❌ **Sharpe 2.74 y equity 20.03x no son evidencia de rendimiento real.**
- ❌ El "Direction Accuracy 58%" probablemente también está inflado.
- ❌ **No usar estos números** para decidir sobre producción.
- ⚠️ El *paper trading* en marcha usa `sfm_top3.pth`, entrenado con este
  pipeline. Sus resultados en vivo serán la primera medición honesta.

### Sobre el paper-trading activo

El cronjob diario (`run_daily_pipeline.sh`) ejecuta `sfm_daily_signal.py` con
el modelo entrenado. **El modelo aprendió sobre features contaminadas**, así que
su comportamiento en vivo puede diferir del backtest.

**Esto no significa que el modelo no sirva**, sino que su rendimiento real es
**desconocido**. La hipótesis a favor: el paper-trading en vivo **no tiene el
leak** (las features se calculan con datos hasta hoy), así que sus resultados
serán válidos — para bien o para mal.

---

## 8. Cómo arreglarlo

### Corrección mínima (3 cambios)

```python
# 1. L221/227: eliminar el bfill
df_close_safe = df_close.replace(0, np.nan).ffill()        # sin .bfill()
# y en las features, dejar NaN y enmascarar en el dataset

# 2. L240: mover el denoising DENTRO del bucle de entrenamiento,
#    aplicándolo SOLO a la ventana de train de cada fold.

# 3. Consistencia: o denoisear también la label, o no denoisear la feature.
#    Lo más simple: no denoisear 'close' como feature.
```

### Corrección correcta (recomendada)

Replantear el preprocesado con la regla: **todo cálculo que agregue información
(fitting, suavizado, clipping, normalización) debe hacerse dentro del fold de
entrenamiento y aplicarse con `.transform()` a validación y test.**

El propio código tiene la estructura correcta para el `MinMaxScaler`
(L572-575): fitea con train y transforma val/test. **El denoising debería
seguir el mismo patrón.**

### Después de arreglar

1. **Re-ejecutar el pipeline** y comparar. Esperar una caída grande del Sharpe
   (de >2 a algo como 0-0.5, si la señal es débil).
2. **Si el Sharpe corregido es positivo**, entonces sí hay señal real.
3. **Si es ~0 o negativo**, el modelo no aporta y conviene saberlo.

---

## 9. Lección metodológica

Este es el **quinto** artefacto del proyecto que no resiste una comprobación
(hoy: config SP500 inexistente, leak de `vol_pct` falso positivo, xgboost roto,
validación del vol_gate inerte, y ahora SFM v8).

**El patrón común: el preprocesado antes del split.** Es el error más frecuente
y más difícil de detectar, porque:

- No produce ningún error.
- Los resultados salen **mejores** de lo esperado, no peores.
- Un Sharpe alto se interpreta como éxito, no como alarma.

**Regla práctica:** cuando un backtest da un resultado extraordinario, la
primera hipótesis debe ser **fuga de información**, no habilidad del modelo.

### Comprobación rápida para cualquier pipeline

```python
# Test del "futuro ausente": re-ejecutar el preprocesado con los datos
# TRUNCADOS en la fecha t y comparar el valor de la feature en t.
# Si cambia, hay leak.
feat_full = preprocess(data[:])          # con todo
feat_trunc = preprocess(data[:t+1])      # solo hasta t
assert np.allclose(feat_full[t], feat_trunc[t]), "LEAK: la feature en t usa el futuro"
```

Esa comprobación habría detectado los tres leaks en segundos.

---

## 10. Ficheros

| Fichero | Qué es |
|---|---|
| `auditoria_v8.py` | Script que cuantifica los leaks |
| `qlib_sfm_pipeline.v8.py` | Pipeline auditado (no modificado) |
| `../formacion/.../sfm-v8-resultados.md` | Resultados invalidados |

---

*Auditoría realizada el 2026-10-26. El pipeline NO se ha modificado: la
corrección requiere decisión sobre cómo reentrenar.*
