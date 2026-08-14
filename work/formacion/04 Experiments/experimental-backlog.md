# Backlog experimental

Este backlog recoge experimentos que merecen convertirse en runs reproducibles dentro del proyecto, priorizando preguntas que pueden cambiar decisiones reales sobre modelo, portfolio, datos o paso a operativa.

## Prioridad alta

### 1. Probar weighting / sizing sobre la señal tuned

**Motivación:**

- `top20` mejora retorno pero rompe robustez
- quizá el problema no es la selección, sino el reparto de pesos
- los materiales de formación refuerzan que concentración, turnover y sizing importan tanto como la señal

**Ideas concretas:**

- weighting uniforme vs concentración por score
- clipping de pesos
- límites por posición
- pequeña penalización por rotación implícita

**Salida esperada:**

- saber si la señal tuned puede acercarse al baseline en robustez sin perder toda su mejora de retorno

**Artefacto preparado:**

- `config/workflow_baseline_lightgbm_alpha158_csi300_tuned_softtopk20.yaml`

### 2. Comparar rachas, drawdowns y turnover entre baseline y tuned + top20

**Motivación:**

- ya sabemos que el drawdown empeora
- falta entender cómo y cuándo se deteriora la trayectoria
- `Conceptos Investment` sugiere mirar la rotación como parte central del coste real

**Salida esperada:**

- una explicación más fina del coste de la concentración
- cuantificación de si el mayor retorno viene acompañado de rotación excesiva

### 3. Revisar explícitamente el modelo de costes del proyecto

**Motivación:**

- en `formacion/` aparece la duda sobre `min_cost`, coste fijo por orden y round-trip efectivo
- esto puede cambiar la lectura de variantes concentradas o con más rotación

**Preguntas concretas:**

- ¿la documentación actual deja claro el efecto de `min_cost`?
- ¿qué diferencia produce usar el coste actual frente a una variante alternativa razonable?
- ¿cuánto del deterioro de ciertas variantes viene de señal mala y cuánto de fricción operativa?

**Salida esperada:**

- una nota metodológica clara sobre costes y su impacto experimental

### 4. Comparar labels / horizontes manteniendo el resto fijo

**Motivación:**

- `Temas Pendientes Qlib` y varios materiales apuntan a revisar 1 día vs 5 días
- ahora mismo la calidad de señal y la monetización no están perfectamente alineadas

**Diseño mínimo:**

- baseline actual
- variante con horizonte más largo
- misma familia de features
- mismo universo
- mismo portfolio inicial para aislar efecto

**Salida esperada:**

- saber si una label menos ruidosa mejora la transferibilidad de señal a PnL

**Artefacto preparado:**

- `config/workflow_baseline_lightgbm_alpha158_csi300_label5d.yaml`

## Prioridad media

### 5. Cambiar familia de features manteniendo `csi300`

**Motivación:**

- separar el efecto de features del efecto de portfolio
- el baseline actual ya sirve como referencia estable

**Candidatos:**

- otra familia manejable dentro de Qlib
- variante reducida de features enfocada a robustez

### 6. Revisar si otra estrategia de rotación mejora la tuned

**Motivación:**

- `n_drop` y `topk` ya mostraron sensibilidad
- puede haber una región intermedia mejor
- merece probar antes de cambiar de modelo completo

### 7. Explorar un modelo alternativo ligero frente a LightGBM

**Motivación:**

- en formación aparecen líneas tipo AutoGluon y modelos secuenciales
- no conviene saltar aún a una variante pesada sin una comparación mínima y limpia

**Regla:**

- solo abrir esta línea con una versión pequeña, reproducible y comparable contra el baseline

### 8. Contrastar selección por IC / Rank IC con monetización real

**Motivación:**

- ya vimos en resultados que mejor `IC` no implica mejor PnL
- esto merece convertirse en criterio explícito de selección de modelos

**Salida esperada:**

- una regla operativa para no promocionar modelos solo por métricas de señal

## Prioridad baja

### 9. Reabrir comparación de universos tras fijar una base más estable

**Motivación:**

- ahora mismo `csi300` domina
- aún no hay una capa de portfolio final suficientemente madura

### 10. Formalizar una vía research → paper trading → execution layer

**Motivación:**

- los materiales de Qlib insisten en separar research, scoring y ejecución
- es importante, pero hoy no es el cuello de botella principal del proyecto

**Salida esperada:**

- checklist mínimo para decidir cuándo una estrategia merece pasar de research a operativa diaria

## Regla del backlog

Antes de abrir muchos frentes, preferir:

1. cambiar una variable importante
2. correr el workflow completo
3. comparar en notebook
4. consolidar hallazgo en `docs/experimental-results.md`
5. si cambia criterio metodológico, promoverlo también a `wiki/research/methodological-decisions.md`

## Promociones sugeridas desde formación

Los materiales de `formacion/` sugieren estas promociones probables:

- **costes y turnover** → decisión metodológica
- **label 1 día vs 5 días** → experimento prioritario
- **IC / Rank IC / ICIR vs PnL** → criterio de selección de modelos
- **AutoGluon u otro modelo ligero** → experimento exploratorio controlado
