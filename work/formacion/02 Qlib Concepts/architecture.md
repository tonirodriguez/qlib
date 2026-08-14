# Arquitectura

## Capas

### 1. Framework base: Microsoft Qlib

El proyecto usa Qlib como framework principal para:

- datasets y handlers
- modelos
- workflow experimental
- backtesting
- tracking de artefactos

La fuente local está en:

- `vendor/microsoft-qlib/`

## 2. Capa propia del proyecto

El código propio vive en:

- `src/qlib_project/`

La decisión importante es que el paquete interno se llama `qlib_project` y no `qlib`, para evitar colisiones con la librería oficial.

## 3. Capa de ejecución

Los puntos de entrada más importantes están en `scripts/`:

- `setup_venv.sh`
- `check_qlib_setup.py`
- `validate_qlib_workflow.py`
- `run_baseline_workflow.py`

## 4. Capa analítica

- `notebooks/01_qlib_smoke_test.ipynb`
- `notebooks/02_baseline_analysis.ipynb`
- `notebooks/03_compare_runs.ipynb`

## 5. Capa documental

Dos capas complementarias:

- `docs/` → documentación más estable y explicativa
- `wiki/` → navegación rápida, contexto enlazado y síntesis útil para iteración

## Flujo mental del proyecto

1. preparar entorno
2. validar instalación de Qlib
3. preparar dataset
4. ejecutar baseline
5. comparar runs
6. documentar qué funcionó y qué no

## Artefactos experimentales

Los resultados locales viven en:

- `mlruns/`

Ahí quedan:

- métricas
- parámetros
- predicciones
- análisis de señal
- análisis de portfolio

## Principio de trabajo

No optimizar solo señal (`IC`, `Rank IC`).

Siempre contrastar también:

- retorno con costes
- information ratio
- max drawdown
- comportamiento de portfolio
