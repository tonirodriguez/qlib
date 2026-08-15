# Estado Crypto

## Propósito del documento

Este documento registra el estado operativo del proyecto crypto: qué se ha
hecho, qué evidencia existe, qué queda pendiente y qué condiciones deben
cumplirse para avanzar. Complementa `Planificación Crypto.md`, que define el
roadmap completo.

Fecha de actualización: 2026-08-15.

## Resumen ejecutivo

El proyecto ha pasado de ser un conjunto de prototipos con fuga temporal a un
flujo de investigación causal con datos trazables, provider atómico, universo
de nueve activos, nested walk-forward y escenarios básicos de costes.

El sistema sigue siendo exclusivamente de investigación. El holdout final de
165 días no ha sido evaluado y no existe autorización para paper trading ni
trading real.

Estado de los gates principales:

| Gate | Estado | Evidencia |
|---|---|---|
| Contención de resultados antiguos | Superado | Avisos `research-only` y outputs separados |
| Causalidad del preprocessing | Superado en el pipeline actual | Tests anti-leakage; clipping/scaler por train |
| Datos cerrados y trazables | Superado | 1.099 velas cerradas, manifests y hashes |
| Publicación segura del provider | Superado | Staging, validación y sustitución recuperable |
| Nested walk-forward | Superado técnicamente | Smoke de dos folds; holdout no evaluado |
| Modelo de costes | Superado para investigación offline | Costes train-only por activo/nocional; falta order book para operación |
| Comparación de universos | Piloto en curso | Smoke con costes terminado; protocolo y gates predeclarados |
| Holdout final | Bloqueado | 2026-03-02 a 2026-08-13, 165 fechas |
| Paper trading | Bloqueado | Depende de todos los gates anteriores |

## Entorno de ejecución

### Realizado

- Creado el entorno Conda aislado `crypto` con Python 3.11.
- Fijados NumPy 1.26.4 y PyTorch 2.2.2 para compatibilidad con macOS Intel.
- Instalados CCXT, Optuna, PyWavelets, Pandas, SciPy, scikit-learn,
  Matplotlib y dependencias de Qlib-data.
- Instalado Qlib desde el checkout actual en modo editable.
- Instalado `mlflow-skinny`, necesario porque Qlib importa `mlflow` durante
  `qlib.init`, sin incorporar el stack completo de MLflow.
- Validada la conversión tensor–NumPy y la carga de Qlib.

### Pendiente

- Generar y revisar un lockfile multiplataforma o locks separados para macOS
  Intel, Apple Silicon y Linux.
- Resolver las advertencias de metadata de la instalación editable de Qlib:
  el paquete general declara dependencias como CVXPY/Jupyter/MLflow completo,
  aunque el perfil crypto no las utiliza.
- Incorporar la creación del entorno a CI.

### Criterio de salida

Un entorno limpio debe instalarse siguiendo el documento de instrucciones,
ejecutar todos los tests crypto, leer el provider y completar un smoke nested.

## Fase 0. Contención

### Realizado

- Marcados v2, v3 y v4 originales como resultados no válidos fuera de muestra.
- Identificado v5 como experimento S&P 500, no crypto.
- Separadas las salidas nuevas de los directorios antiguos.
- Bloqueada la generación diaria de señales por ausencia de artefacto validado.
- Documentada la prohibición de usar los prototipos para trading real.

### Pendiente

- Mover físicamente v5 y sus outputs fuera de `work/crypto` cuando se realice
  la consolidación de estructura.
- Decidir una política de retención o archivo para checkpoints invalidados.

### Criterio de salida

Superado. Cualquier output nuevo debe conservar manifest y etiqueta de estado.

## Fase 1. Causalidad y validación temporal

### Realizado

- Desactivado el wavelet global que incorporaba observaciones futuras.
- Eliminado el clipping global previo al split.
- Clipping y scaler se ajustan solo con train.
- Implementados tests que protegen las transformaciones causales.
- Implementadas primitivas temporales que:
  - reservan el holdout final;
  - crean folds nested con train expansivo;
  - colocan validación inmediatamente antes del test externo;
  - generan tests externos contiguos y disjuntos;
  - terminan exactamente antes del holdout.
- Implementado `run_nested_walk_forward.py`.
- Cada fold crea su propio estudio Optuna, preprocessing y checkpoint.
- El seed es configurable y queda registrado.

### Evidencia

Smoke nested con dos folds y una época:

| Fold | Periodo test | Sharpe | Equity | Drawdown máximo |
|---|---|---:|---:|---:|
| 1 | 2025-02-21 a 2025-08-26 | 2,04 | 1,585 | -21,99% |
| 2 | 2025-08-27 a 2026-03-01 | -2,16 | 0,434 | -61,84% |

Media de Sharpe: -0,06. Desviación: 2,10.

Estos valores no evalúan la estrategia; el smoke usa un trial y una época.
La dispersión demuestra que una única ventana puede producir una conclusión
engañosa.

### Pendiente

- Ejecutar tres o más folds con el presupuesto formal de trials y epochs.
- Ejecutar múltiples seeds.
- Congelar la configuración después del nested y antes de abrir el holdout.
- Añadir purging/embargo si se incorporan labels con horizontes superiores a
  un día o features que solapen ventanas.

### Criterio de salida

El nested formal debe completar todos los folds/seeds sin tocar el holdout y
mostrar estabilidad suficiente bajo costes adversos.

## Fase 2. Datos e ingesta

### Realizado

- Universo actual: BTC, ETH, SOL, XLM, ADA, XRP, DOGE, LINK y LTC.
- Descarga mediante CCXT/Binance con UTC, timeout, retries y backoff.
- Límites de paginación y control de monotonía.
- Validación de timestamps, nulos, precios positivos, volumen y consistencia
  `low/open/close/high`.
- Exclusión de la vela diaria actual mientras permanezca abierta.
- Actualización incremental con siete días de solapamiento configurable.
- Escritura CSV mediante temporal y reemplazo.
- Manifest de descarga con hashes SHA-256.
- Construcción del provider en staging.
- Validación de calendario, universo y todos los binarios antes de publicar.
- Sustitución recuperable del provider completo.
- Preservación del provider activo cuando un build falla.
- Manifest Qlib con 93 ficheros hasheados.

### Estado del dataset

- 1.099 velas cerradas por activo.
- Inicio: 2023-08-11.
- Fin: 2026-08-13.
- Nueve instrumentos.
- Diez campos Qlib por instrumento.
- Provider: `data/qlib_crypto`.

### Pendiente

- Guardar histórico de manifests y versiones del provider.
- Automatizar alertas de freshness, gaps y fallos de actualización.
- Añadir una segunda fuente para reconciliación y riesgo de venue.
- Implementar un universo point-in-time con listings/delistings históricos.

### Criterio de salida

Superado para investigación offline. Las alertas y reconciliación multi-venue
son obligatorias antes de paper trading.

## Análisis del universo

### Realizado

- Reservado el 15% final antes de calcular estadísticas.
- Analizadas 934 fechas hasta 2026-03-01.
- Calculadas correlaciones Pearson, Spearman y rolling de 90 días.
- Ejecutado clustering con distancia `1 - abs(correlación)` y linkage medio.
- Calculadas volatilidad anualizada y mediana de volumen quote por activo.

### Hallazgos

- XRP/XLM: Pearson 0,754; Spearman 0,846; correlación rolling mediana 0,843.
  Existe redundancia clara.
- LTC/BTC: Pearson 0,604; rolling mediana 0,674. LTC formó un cluster propio.
- BTC, ETH, SOL, ADA, DOGE y LINK formaron un cluster amplio con el umbral
  configurado.
- XLM presenta menor liquidez mediana que XRP en la muestra de decisión.

### Decisión provisional

Comparar:

1. universo original de cinco;
2. universo completo de nueve;
3. universo reducido de ocho sin XLM, conservando XRP.

La decisión no es definitiva y no utiliza el holdout.

### Pendiente

- Ejecutar ablaciones sin XRP y sin XLM.
- Medir contribución marginal por activo y estabilidad entre folds.
- Repetir clustering por regímenes de mercado.

## Fase 3. Backtest y costes

### Realizado

- Anualización diaria con 365 periodos.
- Costes aplicados solo cuando existe operación.
- Un cambio directo de activo cuenta como salida y entrada.
- Escenarios optimista, base y adverso.
- Componentes separados de comisión, half-spread, slippage y carry.
- Métricas: equity, retorno anualizado, Sharpe, Sortino, Calmar, drawdown,
  turnover, VaR 95% y CVaR 95%.
- Tests que exigen deterioro monótono de equity al incrementar costes.
- Creado `calibrate_execution_costs.py`.
- Calibrados proxies por activo para nocionales de 1.000, 10.000 y 100.000.
- Integrados costes distintos por activo en cada operación.
- Cada fold nested recalibra los costes usando exclusivamente su train y
  registra fecha de corte, nocional y vector de costes.

### Calibración actual

Coste estimado por lado, usando exclusivamente la muestra de decisión:

| Nocional | Optimista | Base | Adverso | Activo más costoso |
|---:|---:|---:|---:|---|
| 1.000 | 0,225% | 0,260% | 0,268% | LINK |
| 10.000 | 0,244% | 0,280% | 0,329% | XLM |
| 100.000 | 0,302% | 0,377% | 0,503% | XLM |

Estos valores son proxies construidos con rango diario, volatilidad y volumen
quote. No son spreads históricos ni replay de order book y deben etiquetarse
como tales.

El smoke nested con nocional 10.000 confirmó que los costes se recalibran por
fold. Por ejemplo, XLM pasó de 0,360% por lado en el primer train a 0,388% en el
segundo; BTC se mantuvo alrededor de 0,191%. El resultado neto calibrado fue
Sharpe 2,03 en el primer fold y -2,26 en el segundo. La conclusión sigue siendo
inestabilidad, no rentabilidad.

### Pendiente

- Ampliar la calibración por fold a una serie temporal de costes por fecha; el
  estado actual usa un vector fijo por activo ajustado con el train.
- Sustituir el fee genérico por el tier maker/taker real definido para el caso
  de uso.
- Incorporar snapshots o datos históricos de bid/ask y profundidad.
- Modelar límite de participación sobre volumen y rechazo de órdenes.
- Añadir exposición por activo, hit rate y reconciliación de ejecución `t+1`.
- Incorporar funding/borrow solo si se aprueba una estrategia con derivados o
  cortos.

### Criterio de salida

La estrategia debe conservar resultados aceptables bajo el escenario adverso,
con costes dependientes de activo/tamaño y sin superar participación permitida.

El gate se considera superado únicamente para continuar la investigación
offline: los proxies actuales no autorizan paper trading. Antes de operar debe
completarse la parte de microestructura indicada en «Pendiente».

## Fase 4. Comparación formal

### Realizado

- Creado `run_universe_comparison.py`.
- Definidos tres universos comparables: 5, 9 y 8 sin XLM.
- El runner aplica las mismas semillas y configuración nested a todos.
- Cada ejecución se realiza en un proceso independiente.
- Se guardan logs, checkpoints, resultados nested y plan de ejecución.
- El runner aborta si algún reporte indica que el holdout fue evaluado.
- Preparado un dry-run verificable para revisar la matriz antes de consumir
  cómputo.
- Creado `experiment_protocol.json` antes del run formal. Declara universos,
  presupuestos piloto/formal, nocional, métricas, gates y política del holdout.
- Integrados en la comparación el Sharpe neto con costes calibrados por fold,
  el escenario adverso, drawdown y comparación con benchmark.
- Creado `evaluate_experiment_gates.py`, que aplica los umbrales declarados y
  mantiene el holdout cerrado incluso si una ejecución preliminar parece buena.
- Ejecutado el smoke comparativo completo con costes y evaluados sus gates.

### Pendiente

- Ejecutar el piloto predeclarado: dos seeds, tres folds, cinco trials por fold,
  diez épocas de búsqueda y quince épocas para el modelo final del fold.
- Ejecutar el experimento formal con presupuesto aprobado.
- Comparar distribución por folds/seeds, no solo medias.
- Aplicar bootstrap por bloques y corrección por multiple testing.
- Congelar la variante final y generar manifest de decisión.
- Revisar y aprobar el protocolo propuesto antes del piloto. Los umbrales son
  conservadores iniciales y no deben cambiarse después de observar resultados.

### Ejecución del piloto

Iniciada el 2026-08-15 en el entorno Conda `crypto`, con la configuración
predeclarada y nocional 10.000. La matriz contiene tres universos por dos seeds;
cada combinación ejecuta tres folds, cinco trials por fold y un entrenamiento
final. El directorio de trabajo es
`work/crypto/output/universe_comparison_pilot/`.

Estado al actualizar este documento: ejecución en curso; generado el primer
checkpoint de `original_5`, seed 42. No existen aún métricas completas del
piloto y, por tanto, no se toma ninguna decisión. El proceso no consulta el
holdout final.

### Resultado del smoke comparativo con costes

Se ejecutó una seed, dos folds, un trial por fold y una época. El objetivo fue
validar el orquestador, no seleccionar universo.

| Universo | Sharpe calibrado medio | Adverso medio | Folds positivos | Peor drawdown |
|---|---:|---:|---:|---:|
| Original 5 | 0,170 | 0,178 | 50% | -65,36% |
| Completo 9 | -0,113 | -0,108 | 50% | -62,89% |
| Reducido 8 sin XLM | -0,541 | -0,575 | 50% | -67,63% |

Las tres variantes muestran dispersión extrema y cambios de signo entre folds.
No se puede concluir que el universo de cinco sea superior: el presupuesto del
smoke es deliberadamente insuficiente y existe una sola seed. El resultado
válido de esta ejecución es que los tres universos se procesan bajo el mismo
protocolo, los costes se recalibran únicamente con el train de cada fold y el
holdout permanece sin evaluar.

La evaluación automática rechazó los tres universos. El original de cinco
superó en este smoke los umbrales puntuales de Sharpe mediano, escenario
adverso y benchmark, pero falló por número de seeds/folds, proporción de folds
positivos y drawdown. Los otros dos también fallaron los umbrales de retorno.
Por tanto, `holdout_may_be_opened` es `false`.

### Criterio de salida

Una variante solo puede seleccionarse si mejora de forma estable frente a
baselines y alternativas bajo varios folds, seeds y escenarios de costes. Si
ninguna es estable, la decisión correcta es no abrir el holdout.

## Fase 5. Holdout y paper trading

### Realizado

- Holdout definido entre 2026-03-02 y 2026-08-13.
- Todos los reportes nested indican `evaluated: false`.
- Generación de señales operativas bloqueada.

### Pendiente

- Completar comparación formal y congelar configuración.
- Abrir el holdout una sola vez y generar un informe inmutable.
- Definir gates cuantitativos antes de observar el resultado.
- Preparar artefacto completo con modelo, scaler, clipping, esquema, universo,
  dataset hash, commit y versiones.
- Diseñar controles de stale data, exposición, drawdown y kill switch.
- Ejecutar al menos 30 días de paper trading si todos los gates se superan.

### Criterio de salida

No existe salida automática hacia trading real. Cualquier paso posterior exige
una revisión y autorización independientes.

## Tests y evidencia reproducible

Estado actual: 21 tests crypto aprobados.

Principales artefactos:

- `data/qlib_crypto/manifest.json`
- `work/crypto/output/universe_analysis/`
- `work/crypto/output/cost_calibration/`
- `work/crypto/output/nested_walk_forward_smoke/`
- `work/crypto/output/nested_walk_forward_cost_smoke/`
- `work/crypto/output/universe_comparison/plan.json`
- `work/crypto/output/universe_comparison_smoke/comparison.json`
- `work/crypto/output/universe_comparison_cost_smoke/comparison.json`
- `work/crypto/output/universe_comparison_cost_smoke/gate_evaluation.json`
- `work/crypto/experiment_protocol.json`

## Siguiente acción

Ejecutar el piloto predeclarado de comparación de universos. Su función es
medir estabilidad, estimar el coste computacional y detectar defectos antes del
run formal; no puede abrir el holdout porque los gates formales exigen tres
seeds. Tras revisar el piloto se ejecutará el presupuesto formal sin cambiar
los umbrales a la vista de los resultados. El holdout continuará bloqueado.
