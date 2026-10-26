# Auditoría — Resultados CSI300

> **Fecha:** 2026-10-26
> **Objeto:** los resultados de LightGBM + alpha158 sobre CSI300 que respaldan
> el trabajo inicial del proyecto (14.73% – 31.40% anual)
> **Veredicto:** 🔴 **No verificables + contradicción interna documentada.**

---

## 1. Resumen

| Hallazgo | Gravedad |
|---|---|
| **Los experimentos MLflow no existen** en el repositorio | 🔴 No verificable |
| **Contradicción directa** sobre SoftTopk20: 3.29% vs 31.40% | 🔴 Dos números para el mismo run |
| La base MLflow está **vacía** (0 runs) | 🔴 |

**Los números de CSI300 no se pueden reproducir ni comprobar desde este
repositorio.** Y hay dos documentos que afirman cosas incompatibles.

---

## 2. Hallazgo 1 — Los experimentos no están

`baselines.md` cita 7 experimentos con sus `experiment_id` y `run_id`:

```
641902479728835995   641902479728835995  ...
413470885701369270   ...
645493182688106959   ...
```

**Ninguno existe.** Verificado:

| Comprobación | Resultado |
|---|---|
| `mlruns/` del repo | Solo `0/` y `418986570876607566` (el SP500 de hoy) |
| `experiment_id` de CSI300 en `mlruns/` | ❌ Ninguno |
| `toni/mlruns/mlflow.db` (528 KB) | **0 runs**, 1 experimento ("Default") |
| `docs/experimental-results.md` | ❌ No existe |
| `wiki/research/dashboard.md` | ❌ No existe `wiki/` |

`baselines.md` dice *"Generado automáticamente desde `mlruns/`"*, pero los
registros que cita **no están en ningún `mlruns/` del repositorio**.

**Conclusión:** los resultados se generaron en otra máquina (probablemente la
de `/opt/data/`) y solo se copiaron los documentos, no los datos.

---

## 3. Hallazgo 2 — Contradicción sobre SoftTopk20

Este es el hallazgo más grave, y es **independiente** del anterior.

### Los dos números

| Documento | SoftTopk20 | Cita `run_id`? |
|---|---|---|
| `baselines.md` | **0.0329 (3.29%)** | ✅ `3b121593ab2b45cea2bd85467a6302fc` |
| `dashboard.md` | **0.0329** | — |
| `hypotheses.md` | **0.0329** | ✅ mismo run_id |
| `signal-vs-portfolio.md` | **0.0329** | — |
| `ROADMAP TRABAJO.md` | **31.40%** | ❌ no |
| `Cambios_Qlib.md` | **31.40%** | ❌ no |
| `Estado_Proyecto_Quantitativo.md` | **31.40%** | ❌ no |

### Por qué importa

Los documentos que dan **0.0329** son los que **citan el run_id concreto** y
están generados desde MLflow:

> `hypotheses.md`: *"la variante `tuned_softtopk20` ya pudo ejecutarse completa
> (`run 3b121593ab2b45cea2bd85467a6302fc`) tras corregir fallos de
> strategy/backtest, pero el resultado fue flojo: `Ann. Return with cost
> 0.0329`, `IR 0.2635`, `Max Drawdown -0.2433`"*

Y `signal-vs-portfolio.md` lo trata como un hallazgo **negativo**:

> *"alpha158 + csi300 (tuned LGBM, softtopk20) alcanza `ann_ret_cost` = `0.0329`,
> `IR` = `0.2635` y `max drawdown` = `-0.2433`"*

Mientras, `Estado_Proyecto_Quantitativo.md` (el informe de estado del proyecto)
lo presenta como **el mejor resultado del proyecto**:

> *"SoftTopk20 alcanza **31.40% anual** (la mejor hasta ahora)"*
> *"El proyecto ha completado con éxito la fase de prototipado en mercado chino
> (CSI300) con resultados sólidos (~31% anual con SoftTopk)"*

### La discrepancia es ~10x

3.29% vs 31.40%. No es un redondeo ni una diferencia de métrica: **es un orden
de magnitud**.

**Nota:** `31.40%` coincide sospechosamente con `0.0329` leído con el punto
decimal desplazado. No puedo confirmarlo, pero es la hipótesis más simple.

---

## 4. Qué es verificable y qué no

### ✅ Verificable (existe en el repo)

- Las **configs** de Qlib: `examples/benchmarks/LightGBM/workflow_config_lightgbm_Alpha158.yaml`
  y variantes `_csi500`. Son las plantillas oficiales de Microsoft.
- La **metodología**: LightGBM + alpha158 + TopkDropout es el setup estándar.
- El **software** para reproducirlo (qlib está en el repo).

### ❌ No verificable

- Los **resultados concretos** (14.73%, 20.52%, 31.40%, IC 0.0487...).
- Los **experimentos MLflow** (no están).
- Cuál de los dos números de SoftTopk20 es el correcto.

### ⚠️ El problema de fondo

Los números de CSI300 son la **base del proyecto**: el `Estado_Proyecto` afirma
que llevan a *"resultados sólidos"* que justifican expandirse a US y crypto.

Si el número real es 3.29% (con IC 0.0589 y DD −24%), la lectura cambia por
completo: **la estrategia no monetiza la señal**. Eso es exactamente lo que dice
`signal-vs-portfolio.md` y contradice al informe de estado.

---

## 5. Por qué esto es distinto de los otros hallazgos

Los cinco artefactos anteriores tenían fallos **técnicos** (config inexistente,
leak, mecanismo inerte, import roto). Este es un fallo de **consistencia
documental**:

- No hay ningún leak ni bug de código.
- Hay **dos conjuntos de documentos que se contradicen**.
- Y no hay forma de resolverlo desde el repositorio, porque los datos que
  zanjarían la cuestión (los runs de MLflow) no están.

Es el fallo más difícil de detectar, porque **cada documento por separado
parece correcto**.

---

## 6. Recomendaciones

### Inmediatas

1. 🔴 **Reconciliar los números.** Decidir cuál es correcto y corregir los
   documentos que discrepen. Los que citan `run_id` tienen más credibilidad.
2. 🔴 **Marcar `Estado_Proyecto_Quantitativo.md`** como no verificado en su
   sección de CSI300 hasta resolverlo.
3. 🟡 **Actualizar `baselines.md`**: dice "generado desde `mlruns/`" pero esos
   runs no están. Añadir una nota de origen.

### Para verificar de verdad

4. 🟡 **Re-ejecutar el baseline CSI300** en esta máquina. Requiere datos
   chinos (`~/.qlib/qlib_data/cn_data`), que **probablemente no estén** (aquí
   solo hay `us_data` y crypto). Sin datos, no hay verificación posible.

### De fondo

5. 🔴 **Adoptar la práctica de citar siempre `run_id`.** Los documentos que lo
   hacen (`baselines.md`, `hypotheses.md`) son los únicos en los que se puede
   confiar — y en este caso son los que revelan la contradicción.
6. 🟡 **Copia de seguridad de `mlruns/`.** Si los experimentos viven solo en
   `/opt/data/`, cualquier pérdida de esa máquina borra la evidencia.

---

## 7. Balance del proyecto tras 7 auditorías

| # | Artefacto | Tipo de fallo |
|---|---|---|
| 1 | Config SP500 | No existía |
| 2 | `vol_pct` (mi aviso) | Falso positivo — era causal |
| 3 | Entorno qlib | xgboost roto |
| 4 | `vol_gate` | Mecanismo inerte |
| 5 | SFM v8 | 3 leaks de futuro |
| 6 | `momentum_vt` | Import roto |
| 7 | **CSI300** | **Contradicción documental** |

**Patrón dominante: la documentación describe un estado que no coincide con la
realidad del repositorio.**

Ninguno de los 7 fallos se habría detectado leyendo los documentos — todos
requirieron **ir a comprobar**.

---

*Auditoría realizada el 2026-10-26. Script de comprobación:
`work/qlib_work/_inspeccionar_mlflow.py`.*
