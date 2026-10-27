# Auditoría — IC del momentum 120d

> **Fecha:** 2026-10-27
> **Script:** `work/estrategias/audit_momentum_ic.py`
> **Objeto:** el IC +0.066 que sostiene las 3 carteras vivas (E1/E2/E3)
> **Veredicto:** 🔴 **El 0.066 no existe. El IC real es +0.032 y NO es
> significativo. A 60 días es cero.**

---

## 1. Resumen

| Label | IC cross-sectional | t clásico | t honesto | n independiente |
|---|---:|---:|---:|---:|
| **120d** | **+0.0316** | +9.65 | **+0.9** | ~17 |
| **60d** | **−0.0007** | −0.18 | **−0.02** | ~34 |

**Conclusión:** hay una señal positiva a 120 días, coherente con la
literatura de momentum, pero **la muestra no permite demostrarla**. A 60 días
no hay señal, y ahí sí hay potencia estadística para afirmarlo.

---

## 2. Por qué el 0.066 no era válido

### El número no salía de ningún sitio

`momentum_backtest.py` **no calcula IC**. Solo ejecuta un backtest y reporta
Sharpe/IR/drawdown. El `+0.066` estaba escrito en su **docstring** (línea 3),
no en su salida.

### El único script que lo medía ya lo había invalidado

`momentum_purgedcv_resultado.md` (2026-08-22) dice literalmente:

> *"El momentum 120d **NO tiene un IC robusto y estable en el tiempo**. Con
> purged CV el IC medio es **ligeramente negativo**, muy por debajo del +0.066
> que recordábamos de la validación inicial."*

| Label | IC Spearman purged |
|---|---:|
| 60d | −0.062 |
| 120d | −0.036 |

**Y ese resultado llevaba dos meses en el repositorio** mientras ~15
documentos seguían citando el 0.066 como *"alpha validado"*.

### Ese purged CV tampoco era correcto

`momentum_purgedcv.py` dividía por **número de filas** (no por fecha) y **no
dejaba hueco de purga** entre pliegues. Con label de 120 días, las ventanas de
etiqueta de pliegues vecinos se solapan: el "out-of-sample" no era
out-of-sample.

Por eso su resultado (−0.036) tampoco era fiable, aunque apuntaba en la
dirección correcta.

---

## 3. Metodología del audit

El script mide **cuatro** cosas, porque el método cambia la respuesta:

| Sección | Qué mide | Para qué |
|---|---|---|
| **A** Pooled | Correlación sobre todas las muestras apiladas | El método del script viejo, para comparar |
| **B** Cross-sectional por fecha | Correlación de rango **entre tickers, cada día** | **El IC que decide el top-30** |
| **C** Purged CV por fecha | Pliegues temporales **con embargo real** | Variabilidad por régimen |
| **D** Significancia honesta | No solapado + Newey-West | Evitar el t inflado |

### El contraste clave: A vs B

| Método | 120d |
|---|---:|
| Pooled Pearson | +0.0378 |
| Pooled Spearman | **−0.0026** |
| Cross-sectional (B) | **+0.0316** |

El pooled Spearman es **cero** mientras el cross-sectional es **+0.032**. La
explicación: el momentum ordena bien *entre acciones el mismo día*, pero los
*periodos* de alto momentum no tienen mejores retornos. Para una estrategia
top-30 lo que importa es lo primero — **B es la métrica correcta**.

---

## 4. El problema del t inflado

El primer run dio **t = +9.65** y parecía concluyente. No lo era.

Con label de 120 días, cada IC diario comparte **119 días de ventana de
retorno** con el siguiente. Las 1.974 observaciones no son independientes.

| Corrección | t | n efectivo |
|---|---:|---:|
| Clásico (asume independencia) | **+9.65** | 1.974 |
| No solapado (1 de cada 120) | **~+0.9** | **~17** |
| Newey-West (lag 120) | conservador | — |

**En 8 años de datos con horizonte de 120 días solo caben ~17 observaciones
independientes.** Eso no da para establecer significancia, y no se arregla con
más análisis: haría falta más historia.

---

## 5. Variabilidad por régimen (label 120d)

| Pliegue | Periodo | IC medio |
|---|---|---:|
| 1 | 2018-06 → 2019-07 | **+0.047** |
| 2 | 2020-07 → 2021-02 | −0.019 |
| 3 | 2022-02 → 2022-09 | +0.010 |
| 4 | 2023-08 → 2024-04 | **+0.105** |
| 5 | 2025-03 → 2026-05 | **+0.068** |

**Patrón claro:** los pliegues recientes (2023-2026) son los fuertes. Eso
explica por qué las carteras pasaron de −2% a +0.2%/+0.9%/+3.7%.

Pero es **régimen favorable, no ventaja demostrada**: los pliegues 1-3
(2018-2023) están en ruido alrededor de cero.

---

## 6. Qué documentos se corrigieron

**34 afirmaciones en 14 ficheros.** Todos citaban el 0.066 como válido.

| Fichero | Afirmación corregida |
|---|---|
| `Estado_Proyecto_Quantitativo.md` | 3 (incluida "valida la señal base") |
| `work/qlib_work/momentum_largo_alpha.md` | 7 (**la tesis entera del doc**) |
| `work/qlib_work/backtest_momentum.md` | 4 |
| `work/qlib_work/documentacion_momentum.md` | 3 |
| `work/qlib_work/Estrategia_Momentum_120.md` | 3 |
| `work/qlib_work/lowvol_diagnostico.md` | 2 |
| `work/qlib_work/plan_post_paper_pead.md` | 2 |
| `work/qlib_work/quinn_planteamiento_estrategias.md` | 2 |
| `work/qlib_work/README.md` | 2 |
| `work/crypto/ic_short_term_sp500.py` | 2 |
| `work/estrategias/momentum_backtest.py` | 1 (docstring falso) |
| `work/estrategias/momentum_purgedcv.py` | 1 (docstring) |
| `work/qlib_work/cambio_pead_filtro_a_nucleo.md` | 1 (cita + nota) |
| `work/qlib_work/evolucion_E1_E2_E3.md` | 1 |
| `work/qlib_work/quinn_paper_combinado.md` | 1 |
| `work/estrategias/JEV_GUIA.md` | 2 (error mío, corregido antes) |

**No se tocó** `examples/benchmarks/README.md`: su `0.0667` es de la tabla
oficial de benchmarks de Microsoft, sin relación con este proyecto.

---

## 7. Qué significa para las carteras vivas

La estrategia **no está rota**, pero su ventaja es más frágil de lo documentado:

| Documentado | Real |
|---|---|
| IC 0.066 "alpha validado" | IC 0.032, **no significativo** |
| "primer alpha GENUINO del proyecto" | Evidencia **preliminar** |
| Alpha sólido y genuino | Señal débil, solo a 120d |

El dato más sólido que queda es el **Sharpe ~1.0 del backtest** y el perfil de
drawdown. Pero descansa sobre un IC cuya significancia no se puede establecer.

**Implicación práctica:** la decisión de mantener las estrategias debe apoyarse
en criterio económico (momentum es un fenómeno con 60 años de literatura) y en
el comportamiento en vivo, **no** en un IC de 0.066 que no existe.

---

## 8. Siguiente paso

Medir el IC **al horizonte real de la operativa**, no al teórico:

```bash
conda run -n qlib python work/estrategias/audit_momentum_ic.py --grid
```

Barre labels de 5 a 120 días. Responde dos preguntas:

1. **¿Dónde vive la señal?** (a 60d es cero; a 120d es +0.032)
2. **¿Dónde se puede demostrar?** A horizontes cortos hay más observaciones
   independientes y por tanto más potencia estadística.

Si la señal es significativa a ~30 días (el horizonte real: rebalanceo
semanal, rotación 5/30 → posición media ~6 semanas), entonces el edge está
respaldado **donde de verdad importa**.

---

## 9. Lección

Este es el **noveno** artefacto del proyecto que no resiste una comprobación, y
el patrón se repite con una variante nueva: **un número que el propio proyecto
ya había invalidado siguió circulando en 14 documentos durante dos meses.**

Los otros ocho fallos fueron técnicos (leaks, imports rotos, mecanismos
inertes). Este es de **propagación documental**: nadie leyó
`momentum_purgedcv_resultado.md`, que estaba en el repositorio con la
respuesta correcta.

**Regla que se deriva:** cuando un documento invalida un número, hay que
**buscar todos los sitios donde aparece** y corregirlos el mismo día. Si no, el
número sobrevive a su propia refutación.

---

*Auditoría realizada el 2026-10-27. Script: `work/estrategias/audit_momentum_ic.py`.
Corrección masiva: 34 reemplazos verificados uno a uno.*
