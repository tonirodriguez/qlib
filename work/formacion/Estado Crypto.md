# Estado Crypto

## Propósito del documento

Este documento registra el estado operativo del proyecto crypto: qué se ha
hecho, qué evidencia existe, qué queda pendiente y qué condiciones deben
cumplirse para avanzar. Complementa `Planificación Crypto.md`, que define el
roadmap completo.

Fecha de actualización: 2026-08-15 (tarde; piloto completo y gates evaluados).

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
| Modelo de costes | Superado (offline); v2 disponible | Proxies train-only + módulo `execution_costs_v2.py` (maker/taker + order book), pendiente de integrar |
| Comparación de universos | Piloto completo; gates rechazan | 6/6 combinaciones; `holdout_may_be_opened: false`; ninguna variante supera los gates |
| Holdout final | Bloqueado | 2026-03-02 a 2026-08-13, 165 fechas; `evaluated: false` en las 6 |
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

Estado al actualizar este documento (2026-08-15, tarde): **piloto completo**, las
seis combinaciones han terminado sus tres folds y escrito `nested_results.json`.
Se regeneró `comparison.json` y se evaluaron los gates. El proceso no consulta el
holdout final: todas las combinaciones registran `final_holdout.evaluated: false`.

Sharpe neto por fold con costes calibrados (train-only, nocional 10.000):

| Combinación | Fold 1 | Fold 2 | Fold 3 | Media | Folds+ | Peor drawdown |
|---|---:|---:|---:|---:|---:|---:|
| original_5, seed 42 | -0,84 | 0,92 | -2,56 | -0,83 | 1/3 | -51% |
| original_5, seed 43 | 1,07 | 1,51 | -2,38 | 0,07 | 2/3 | -56% |
| full_9, seed 42 | -0,65 | -1,07 | -2,78 | -1,50 | 0/3 | -54% |
| full_9, seed 43 | -0,87 | 0,95 | -2,95 | -0,96 | 1/3 | -52% |
| reduced_8 sin XLM, seed 42 | -0,29 | 0,14 | -2,17 | -0,77 | 1/3 | -46% |
| reduced_8 sin XLM, seed 43 | 0,94 | -0,85 | -3,20 | -1,03 | 1/3 | -59% |

Agregado por universo (los seis folds de ambos seeds combinados):

| Universo | n folds | Sharpe medio | Mediana | Desv. típica | Mín | Máx | Folds positivos |
|---|---:|---:|---:|---:|---:|---:|---:|
| Original 5 | 6 | -0,379 | 0,040 | 1,65 | -2,56 | 1,51 | 3/6 |
| Completo 9 | 6 | -1,229 | -0,969 | 1,33 | -2,95 | 0,95 | 1/6 |
| Reducido 8 sin XLM | 6 | -0,904 | -0,567 | 1,40 | -3,20 | 0,94 | 2/6 |

Lectura: ningún universo alcanza un Sharpe medio positivo con el piloto
completo. La dispersión sigue siendo enorme (desviación 1,3-1,7 frente a medias
negativas) y el tercer fold es sistemáticamente el peor: las seis combinaciones lo
cierran por debajo de -2, y la 6ª combinación lo hace en -3,20. El original de
cinco es la variante menos mala (única con mediana ≥ 0 y la mitad de folds en
positivo), seguido del reducido de ocho y, en último lugar, el completo de nueve.
El piloto confirma inestabilidad, no rentabilidad; no autoriza abrir el holdout ni
tomar ninguna decisión de selección. Estos valores corresponden al presupuesto
piloto (cinco trials por fold, dos seeds) y no al experimento formal.

### Evaluación de gates del piloto

Ejecutado `evaluate_experiment_gates.py` sobre `comparison.json`. Resultado:
`holdout_may_be_opened: false`. Ninguna variante supera los gates predeclarados
en `experiment_protocol.json`.

| Gate | Umbral | Original 5 | Completo 9 | Reducido 8 |
|---|---|:--:|:--:|:--:|
| Nº mínimo de seeds (≥3) | 3 | ✗ (2) | ✗ (2) | ✗ (2) |
| Folds externos por seed (≥3) | 3 | ✓ | ✓ | ✓ |
| Mediana Sharpe calibrado ≥ 0 | 0,0 | ✓ (0,040) | ✗ | ✗ |
| Fracción de folds positivos ≥ 0,667 | 0,667 | ✗ (0,50) | ✗ (0,17) | ✗ (0,33) |
| Drawdown peor fold ≥ -0,5 | -0,5 | ✗ (-0,558) | ✗ (-0,544) | ✗ (-0,594) |
| Sharpe medio adverso ≥ 0 | 0,0 | ✗ (-0,354) | ✗ (-1,319) | ✗ (-0,946) |
| Supera benchmark ≥ 50% folds | 0,5 | ✗ (0,33) | ✗ (0,17) | ✗ (0,33) |
| **Resultado** | | **Rechazado** | **Rechazado** | **Rechazado** |

El único gate que aprueba alguna variante es la mediana de Sharpe del original de
cinco (0,040), marginal. El fallo del recuento de seeds es esperado: el piloto
tiene dos y el protocolo exige tres. Aunque se ignorase, el original de cinco
seguiría fallando por proporción de folds positivos, drawdown, escenario adverso
y benchmark. Conclusión: el piloto valida el flujo y el coste computacional, pero
no selecciona universo ni abre el holdout.

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

Estado actual: tests crypto aprobados, incluidos los módulos nuevos B2 y B3
(`test_execution_costs_v2.py`, `test_baselines.py`).

Principales artefactos:

- `data/qlib_crypto/manifest.json`
- `work/crypto/output/universe_analysis/`
- `work/crypto/output/cost_calibration/`
- `work/crypto/output/nested_walk_forward_smoke/`
- `work/crypto/output/nested_walk_forward_cost_smoke/`
- `work/crypto/output/universe_comparison_pilot/plan.json`
- `work/crypto/output/universe_comparison_pilot/comparison.json`
- `work/crypto/output/universe_comparison_pilot/gate_evaluation.json`
- `work/crypto/output/universe_comparison_pilot/<universo>_seed_<n>/nested_results.json` (6)
- `work/crypto/experiment_protocol.json`
- `work/crypto/execution_costs_v2.py` (B2, modelo de costes realista)
- `work/crypto/baselines.py` (B3, baselines + bootstrap/PSR/DSR)

## Módulos nuevos (2026-08-15)

- **B2 — `execution_costs_v2.py`.** Modelo de costes microestructural: tiers
  maker/taker configurables mezclados por fracción taker, half-spread desde
  bid/ask reales o proxy etiquetado, impacto raíz cuadrada `k·σ·√(Q/L)` con `L`
  = profundidad de order book o ADV proxy, tope de participación con rechazo de
  órdenes y timing t+1. Emite un vector de coste por activo compatible con
  `top1_long_returns(one_way_costs=...)`. Pendiente: alimentar el fee schedule y
  los datos reales de bid/ask/profundidad e integrarlo en cada fold del nested.
- **B3 — `baselines.py`.** Baselines t+1 (cash, equal-weight, buy-and-hold,
  momentum sin look-ahead), bootstrap por bloques del Sharpe, PSR y DSR
  (multiple testing). Pendiente: conectar `compare_to_baselines(...)` a la salida
  del experimento formal con `n_trials` = universos × seeds.

## Siguiente acción

El piloto está completo y sus gates rechazan las tres variantes; el holdout
sigue bloqueado. Los próximos pasos, en orden, son:

1. Integrar el modelo de costes v2 (B2) en `run_nested_walk_forward.py` y la
   comparación con baselines (B3) en la evaluación por fold.
2. Ejecutar el experimento formal predeclarado (tres seeds, 30 trials/fold, 60
   épocas) con los umbrales congelados y sin observar el holdout.
3. Aplicar bootstrap por bloques y DSR a los resultados formales.
4. Solo si alguna variante supera todos los gates de forma estable, congelarla,
   generar el manifest de decisión y abrir el holdout una única vez.

El detalle operativo de cada paso, con comandos, está en la sección
«Plan accionable».

## Plan accionable

Convención: cada tarea es una casilla `[ ]`. Todos los comandos asumen que se
ejecutan desde la raíz del repositorio con el entorno Conda `crypto` activo:

```bash
conda activate crypto
cd <RAIZ_DEL_REPO>   # el directorio que contiene work/, data/, qlib/
```

El entrenamiento (nested walk-forward con Optuna + PyTorch) es intensivo: en el
piloto cada combinación tardó del orden de tres horas. Ejecútalo en una máquina
con el entorno preparado, no en un sandbox efímero. La interfaz de
`run_nested_walk_forward.py` se controla íntegramente por variables de entorno
(`CRYPTO_*`); no tiene argumentos de línea de comandos.

### Bloqueante B1 — Cerrar la 6ª combinación del piloto — COMPLETADO (2026-08-15)

Ejecutado. `reduced_8_no_xlm` seed 43 dio folds `[0,94, -0,85, -3,20]` (media
-1,03), holdout `evaluated: false`. Se regeneró `comparison.json` y
`gate_evaluation.json`: `holdout_may_be_opened: false`, las tres variantes
rechazadas. Detalle en «Ejecución del piloto» y «Evaluación de gates del piloto».

- [x] Ejecutar `reduced_8_no_xlm`, seed 43:

```bash
CRYPTO_INSTRUMENTS="BTC,ETH,SOL,ADA,XRP,DOGE,LINK,LTC" \
CRYPTO_SEED=43 \
CRYPTO_NESTED_OUTPUT_DIR=work/crypto/output/universe_comparison_pilot/reduced_8_no_xlm_seed_43 \
CRYPTO_NESTED_FOLDS=3 \
CRYPTO_NESTED_TRIALS=5 \
CRYPTO_NESTED_FINAL_EPOCHS=15 \
CRYPTO_NESTED_PATIENCE=5 \
CRYPTO_ORDER_NOTIONAL=10000 \
python work/crypto/run_nested_walk_forward.py 2>&1 \
  | tee work/crypto/output/universe_comparison_pilot/reduced_8_no_xlm_seed_43/run.log
```

- [x] Comprobar que se escribió el reporte y que el holdout sigue cerrado:

```bash
python - <<'PY'
import json
p="work/crypto/output/universe_comparison_pilot/reduced_8_no_xlm_seed_43/nested_results.json"
d=json.load(open(p))
print("holdout evaluated:", d["final_holdout"]["evaluated"])
print("folds sharpe:", [round(f["calibrated_cost_metrics"]["sharpe"],2) for f in d["folds"]])
PY
```

- [x] Reconstruir el agregado del piloto (lee los 6 `nested_results.json`, no
  reentrena) y evaluar los gates predeclarados:

```bash
CRYPTO_COMPARISON_SEEDS=42,43 \
CRYPTO_COMPARISON_OUTPUT_DIR=work/crypto/output/universe_comparison_pilot \
CRYPTO_COMPARISON_REBUILD_ONLY=true \
python work/crypto/run_universe_comparison.py

CRYPTO_COMPARISON_RESULT=work/crypto/output/universe_comparison_pilot/comparison.json \
python work/crypto/evaluate_experiment_gates.py
```

Resultado esperado del gate: rechazo (`holdout_may_be_opened: false`) porque el
piloto solo tiene dos seeds y el mínimo son tres. Sirve para validar el flujo,
no para decidir.

### Bloqueante B2 — Modelo de costes realista

Módulo implementado: `work/crypto/execution_costs_v2.py` (tests en
`tests/crypto/test_execution_costs_v2.py`). Sustituye los proxies de
`calibrate_execution_costs.py` por un modelo microestructural configurable:
tiers maker/taker mezclados por fracción taker, half-spread desde bid/ask reales
(o proxy etiquetado), impacto raíz cuadrada `k·σ·√(Q/L)` con `L` = profundidad
de order book (o ADV proxy), tope de participación con rechazo de órdenes y
timing t+1. Cada componente registra su `source` ("orderbook" o "proxy").

- [x] Estructura de tiers maker/taker configurable (`FeeTier`, `select_fee_tier`,
  `blended_fee`).
- [x] Half-spread desde bid/ask reales con fallback a proxy etiquetado.
- [x] Impacto de mercado por profundidad/participación y rechazo de órdenes.
- [x] Timing t+1 y vector de costes por activo compatible con
  `top1_long_returns(one_way_costs=...)`.
- [x] Integrar el vector v2 en cada fold del nested (paso 3, automatizado): flag
  `CRYPTO_COST_MODEL=v2` en `run_nested_walk_forward.py`, train-only por fold.
- [x] Carga automática de fee schedule y de quotes/depth reales (paso 4,
  automatizado): variables `CRYPTO_FEE_SCHEDULE_JSON`, `CRYPTO_QUOTES_DIR`,
  `CRYPTO_DEPTH_DIR`; si están, las fuentes pasan de `proxy` a `orderbook` sin
  tocar código.
- [ ] Aportar los **datos reales** (valores del fee schedule del venue y ficheros
  de bid/ask y profundidad); la fontanería ya está lista, faltan los datos.
- [ ] Ejecutar el nested con `v2` y confirmar que el escenario adverso se separa de
  forma material del calibrado.

#### Cómo ejecutar B2 — instrucciones exactas

Requisitos previos (una vez por sesión):

```bash
conda activate crypto
cd <RAIZ_DEL_REPO>   # el directorio que contiene work/, data/, qlib/
```

Variables de entorno que acepta `execution_costs_v2.py` (todas opcionales; se
muestran con su valor por defecto):

| Variable | Defecto | Significado |
|---|---|---|
| `CRYPTO_OHLCV_DIR` | `scripts/crypto/csv_data/crypto/ohlcv` | Carpeta con `<ACTIVO>.csv` OHLCV |
| `CRYPTO_INSTRUMENTS` | universo de 9 | Activos y su orden (define el esquema) |
| `CRYPTO_ORDER_NOTIONALS` | `1000,10000,100000` | Nocionales a calibrar (USD) |
| `CRYPTO_FINAL_HOLDOUT_FRACTION` | `0.15` | Fracción final reservada (no se usa) |
| `CRYPTO_THIRTY_DAY_VOLUME_USD` | `0` | Volumen 30d de la cuenta → elige tier de fees |
| `CRYPTO_TAKER_FRACTION` | `1.0` | Fracción de fills a taker (0=todo maker, 1=todo taker) |
| `CRYPTO_IMPACT_COEFFICIENT` | `1.0` | Coeficiente `k` del impacto raíz cuadrada |
| `CRYPTO_MAX_PARTICIPATION` | `0.1` | Tope de participación; por encima, orden rechazada |
| `CRYPTO_COST_CALIBRATION_V2_DIR` | `work/crypto/output/cost_calibration_v2` | Carpeta de salida |

Paso 1 — calibración autónoma (verificado; sin quotes/depth reales degrada a
proxy etiquetado):

```bash
CRYPTO_INSTRUMENTS="BTC,ETH,SOL,ADA,XRP,DOGE,LINK,LTC" \
CRYPTO_ORDER_NOTIONALS="1000,10000,100000" \
CRYPTO_THIRTY_DAY_VOLUME_USD=0 \
CRYPTO_TAKER_FRACTION=1.0 \
CRYPTO_IMPACT_COEFFICIENT=1.0 \
CRYPTO_MAX_PARTICIPATION=0.1 \
python work/crypto/execution_costs_v2.py
```

Escribe dos ficheros en `work/crypto/output/cost_calibration_v2/`:
`asset_costs_v2.csv` (desglose fee / half_spread / market_impact / participation /
rejected / source por activo y nocional) y `summary.json`. Salida verificada para
nocional 10.000 (universo de 8, muestra de decisión hasta 2026-03-02): coste medio
por lado 0,266%, más caro LINK (0,320%) y ADA (0,307%), más barato BTC (0,186%),
ningún activo rechazado.

Paso 2 — tests del módulo:

```bash
python -m pytest tests/crypto/test_execution_costs_v2.py -q   # 12 passed
```

Paso 3 (AUTOMATIZADO) — ejecutar el nested con el modelo de costes v2. Ya no hay
que editar código: `run_nested_walk_forward.py` acepta `CRYPTO_COST_MODEL=v2` y
usa `fold_cost_vector_v2(...)` con **solo el train de cada fold**. Con `proxy`
(por defecto) el comportamiento es el original. Ejemplo para una combinación:

```bash
CRYPTO_COST_MODEL=v2 \
CRYPTO_INSTRUMENTS="BTC,ETH,SOL,ADA,XRP,DOGE,LINK,LTC" \
CRYPTO_SEED=43 \
CRYPTO_NESTED_OUTPUT_DIR=work/crypto/output/nested_v2_demo \
CRYPTO_NESTED_FOLDS=3 CRYPTO_NESTED_TRIALS=5 CRYPTO_NESTED_FINAL_EPOCHS=15 \
CRYPTO_NESTED_PATIENCE=5 CRYPTO_ORDER_NOTIONAL=10000 \
CRYPTO_TAKER_FRACTION=1.0 CRYPTO_IMPACT_COEFFICIENT=1.0 CRYPTO_MAX_PARTICIPATION=0.1 \
python work/crypto/run_nested_walk_forward.py
```

El `nested_results.json` resultante registra `"cost_model": "v2"` y, en cada fold,
`cost_calibration.model = "v2_maker_taker_orderbook"`, el `source` de cada
componente y los `rejected_assets`.

Para el experimento formal de comparación con costes v2, basta con exportar el
flag y lanzar el orquestador habitual (lo hereda por el entorno):

```bash
export CRYPTO_COST_MODEL=v2
CRYPTO_COMPARISON_SEEDS=42,43,44 \
CRYPTO_COMPARISON_OUTPUT_DIR=work/crypto/output/universe_comparison_formal_v2 \
CRYPTO_NESTED_FOLDS=3 CRYPTO_NESTED_TRIALS=30 CRYPTO_NESTED_FINAL_EPOCHS=60 \
CRYPTO_NESTED_PATIENCE=10 CRYPTO_ORDER_NOTIONAL=10000 \
python work/crypto/run_universe_comparison.py
```

Paso 4 (AUTOMATIZADO) — datos reales de microestructura. Cuando dispongas de
ellos, se activan solo con variables de entorno, sin tocar código:

```bash
export CRYPTO_FEE_SCHEDULE_JSON=work/crypto/config/fee_schedule.json
export CRYPTO_QUOTES_DIR=scripts/crypto/csv_data/crypto/quotes
export CRYPTO_DEPTH_DIR=scripts/crypto/csv_data/crypto/depth
```

Formatos esperados:

- `fee_schedule.json`: lista de objetos
  `{"min_thirty_day_volume_usd": <float>, "maker": <float>, "taker": <float>}`.
- `CRYPTO_QUOTES_DIR/<ACTIVO>.csv`: columnas `date, bid, ask`.
- `CRYPTO_DEPTH_DIR/<ACTIVO>.csv`: columnas `date, depth_notional`.

Todo se lee train-only por fold. En cuanto existan estos ficheros, el `source` de
cada componente pasa de `proxy` a `orderbook` automáticamente; mientras no
existan, se degrada al proxy etiquetado. Si no defines `CRYPTO_FEE_SCHEDULE_JSON`
se usa `DEFAULT_FEE_SCHEDULE` (placeholder que debes sustituir por el real).

### Bloqueante B3 — Rigor estadístico y baselines

Módulo implementado: `work/crypto/baselines.py` (tests en
`tests/crypto/test_baselines.py`). Todo en numpy (normal CDF/inversa locales).

- [x] Baselines t+1 sobre la misma matriz de retornos y costes: `cash`,
  `equal_weight` (rebalanceo diario), `buy_and_hold` (sin rebalanceo) y
  `momentum` (top-1 por retorno acumulado, sin look-ahead).
- [x] Bootstrap por bloques circular del Sharpe (`block_bootstrap_sharpe`): CI y
  `p(Sharpe>0)` preservando autocorrelación.
- [x] Probabilistic Sharpe Ratio (`probabilistic_sharpe_ratio`) corrigiendo por
  longitud, skew y kurtosis.
- [x] Deflated Sharpe Ratio (`deflated_sharpe_ratio` + `expected_max_sharpe`) para
  corregir multiple testing al comparar universos × seeds.
- [x] Informe combinado `compare_to_baselines(...)` (métricas + bootstrap + PSR
  por serie, y flags de si la estrategia bate cada baseline).
- [ ] Conectar `compare_to_baselines(...)` a la salida del experimento formal y
  aplicar DSR con `n_trials` = nº de universos × seeds y la varianza observada de
  los Sharpes por fold.
- [ ] Regla previa: no interpretar diferencias entre universos dentro de ±1σ
  como señal.

#### Cómo ejecutar B3 — instrucciones exactas

`baselines.py` es una biblioteca (no tiene CLI); se usa desde Python o se conecta
al experimento formal. Requisitos previos:

```bash
conda activate crypto
cd <RAIZ_DEL_REPO>
```

Funciones principales (todas en `work/crypto/baselines.py`):

| Función | Qué devuelve |
|---|---|
| `baseline_returns(realized, momentum_lookback, one_way_costs)` | dict con series t+1: `cash`, `equal_weight`, `buy_and_hold`, `momentum` |
| `block_bootstrap_sharpe(returns, block_size, n_boot, seed)` | Sharpe anualizado con CI y `prob_sharpe_gt_0` |
| `probabilistic_sharpe_ratio(returns, benchmark_sharpe_per_period)` | PSR (corrige longitud, skew, kurtosis) |
| `expected_max_sharpe(var_trial_sharpes, n_trials)` | Sharpe esperado máximo de N trials |
| `deflated_sharpe_ratio(returns, var_trial_sharpes, n_trials)` | DSR (PSR contra el máximo esperado) |
| `compare_to_baselines(strategy_returns, realized, ...)` | informe completo: métricas + bootstrap + PSR por serie y flags de si la estrategia bate cada baseline |

Uso mínimo verificado (calcula baselines sobre los retornos del universo y
compara una serie de estrategia). Guarda esto como `work/crypto/run_baselines_demo.py`
y ejecútalo, o pégalo en un intérprete:

```python
import numpy as np, pandas as pd
from work.crypto.baselines import compare_to_baselines, deflated_sharpe_ratio

instr = ["BTC","ETH","SOL","ADA","XRP","DOGE","LINK","LTC"]
base = "scripts/crypto/csv_data/crypto/ohlcv"
cols = {}
for a in instr:
    df = pd.read_csv(f"{base}/{a}.csv")
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df = df.sort_values("date").drop_duplicates("date", keep="last").set_index("date")
    cols[a] = df["close"].pct_change()
prices = pd.DataFrame(cols).dropna()
n = int(len(prices) * 0.85)                 # ventana de decisión (reserva 15% holdout)
realized = prices.iloc[:n].to_numpy()
strategy = realized[:, :2].mean(axis=1)     # sustituir por la serie neta del modelo

report = compare_to_baselines(strategy, realized, momentum_lookback=30, n_boot=2000, seed=42)
for name in ["strategy","cash","equal_weight","buy_and_hold","momentum"]:
    m, b = report[name]["metrics"], report[name]["bootstrap"]
    print(name, round(m["sharpe"],3), [round(b["ci_low"],2), round(b["ci_high"],2)], b["prob_sharpe_gt_0"])
print(report["strategy_beats_baseline"])
```

```bash
python work/crypto/run_baselines_demo.py
```

Ejecución verificada sobre la ventana de decisión (estrategia de ejemplo =
media BTC/ETH): Sharpe estrategia +0,646 (CI [-0,48, +1,87], p>0 = 0,85);
equal_weight +0,686; buy_and_hold +0,627; momentum +0,928; cash 0. La estrategia
de ejemplo bate a cash y buy_and_hold pero no a equal_weight ni momentum — que es
justamente el tipo de comparación que faltaba.

Tests del módulo:

```bash
python -m pytest tests/crypto/test_baselines.py -q   # 9 passed
```

Integración (pendiente) con el experimento formal: tras el run formal, para cada
universo tomar la serie de retornos netos del modelo por fold, pasarla por
`compare_to_baselines(...)` (mismos costes y fechas), y aplicar DSR con
`n_trials` = nº de universos × seeds y `variance_of_trial_sharpes` = varianza de
los Sharpes por fold observados:

```python
from work.crypto.baselines import deflated_sharpe_ratio
dsr = deflated_sharpe_ratio(
    model_net_returns,                 # serie concatenada de folds del universo
    variance_of_trial_sharpes=var_sr, # var. de los Sharpes por fold/seed
    n_trials=n_universos * n_seeds,
)
# abrir el holdout solo si dsr["dsr"] es alto Y se superan los gates del protocolo
```

### Deseable D1 — Experimento formal (Fase 4)

Solo tras B1–B3. Presupuesto formal ya declarado en `experiment_protocol.json`
(seeds 42, 43, 44; 30 trials/fold; 60 épocas). Congelar umbrales antes de mirar.

- [ ] Dry-run para revisar la matriz de ejecución sin consumir cómputo:

```bash
CRYPTO_COMPARISON_SEEDS=42,43,44 \
CRYPTO_COMPARISON_OUTPUT_DIR=work/crypto/output/universe_comparison_formal \
CRYPTO_COMPARISON_DRY_RUN=true \
python work/crypto/run_universe_comparison.py
```

- [ ] Ejecutar el run formal completo (3 universos × 3 seeds; largo):

```bash
CRYPTO_COMPARISON_SEEDS=42,43,44 \
CRYPTO_COMPARISON_OUTPUT_DIR=work/crypto/output/universe_comparison_formal \
CRYPTO_NESTED_FOLDS=3 \
CRYPTO_NESTED_TRIALS=30 \
CRYPTO_NESTED_FINAL_EPOCHS=60 \
CRYPTO_NESTED_PATIENCE=10 \
CRYPTO_ORDER_NOTIONAL=10000 \
python work/crypto/run_universe_comparison.py 2>&1 \
  | tee work/crypto/output/universe_comparison_formal/run.log
```

- [ ] Evaluar gates del run formal:

```bash
CRYPTO_COMPARISON_RESULT=work/crypto/output/universe_comparison_formal/comparison.json \
python work/crypto/evaluate_experiment_gates.py
```

- [ ] Analizar distribución por folds/seeds (no solo medias), contribución
  marginal por activo y por qué el fold 3 es sistemáticamente el peor (¿régimen
  de mercado?).
- [ ] Si alguna variante supera todos los gates de forma estable, congelarla y
  generar el manifest de decisión. Si ninguna, la decisión correcta es
  no seleccionar y no abrir el holdout.

### Deseable D2 — Holdout final (Fase 5, solo si D1 pasa los gates)

- [ ] Definir los gates cuantitativos del holdout antes de mirarlo.
- [ ] Abrirlo una sola vez y generar un informe inmutable.
- [ ] Empaquetar el artefacto reproducible: pesos, arquitectura,
  hiperparámetros, scaler, clipping, orden de activos/features, esquema, hash del
  dataset, commit y versiones.

### Deseable D3 — Paper trading (Fase 5, solo si el holdout aprueba)

- [ ] Controles de stale data, exposición, concentración, drawdown y kill switch
  probado.
- [ ] Reconciliación diaria de señales contra datos posteriores y precios
  ejecutables.
- [ ] Ejecutar un mínimo de 30 días en simulación antes de cualquier decisión.

### Deuda de ingeniería / datos (no bloqueante)

- [ ] Generar lockfile multiplataforma y configurar CI que levante el entorno y
  corra los 21 tests crypto.
- [ ] Mover v5 (experimento S&P 500) y sus outputs fuera de `work/crypto`.
- [ ] Añadir alertas de freshness/gaps y una segunda fuente para reconciliación.
- [ ] Implementar universo point-in-time con listings/delistings (riesgo de
  supervivencia).
