# Mapa del proyecto

## Objetivo

Proyecto de investigación cuantitativa basado en **Microsoft Qlib** para:

- ingeniería de features
- entrenamiento de modelos
- evaluación reproducible
- backtesting
- documentación de decisiones experimentales

## Estructura principal

- `src/qlib_project/` → código Python propio
- `config/` → workflows y configuración
- `scripts/` → setup, validación y ejecución
- `docs/` → documentación tradicional del proyecto
- `wiki/` → capa de wiki navegable para humanos/LLMs
- `notebooks/` → análisis exploratorio y comparación de runs
- `research/` → notas de investigación
- `strategies/` → ideas y diseños de estrategia
- `backtests/` → material relacionado con evaluación/backtesting
- `vendor/microsoft-qlib/` → clon oficial de Qlib
- `mlruns/` → artefactos de experimentos locales
- `data/qlib/` → dataset demo preparado

## Piezas críticas

### Entorno

- `.venv/` contiene el entorno Python del proyecto
- Qlib se instala desde el repo clonado, no desde PyPI

### Código propio relevante

- `src/qlib_project/bootstrap.py`
  - inicializa Qlib
  - valida entorno
  - resume el proyecto

- `src/qlib_project/config.py`
  - acceso a configuración del proyecto

### Configuraciones clave

- `config/project.yaml`
- `config/workflow_baseline_lightgbm_alpha158.yaml`
- `config/workflow_baseline_lightgbm_alpha158_csi500.yaml`
- `config/workflow_baseline_lightgbm_alpha158_csi300_tuned.yaml`
- variantes `tuned_top30` y `tuned_top20`

## Lectura rápida sugerida

- si quieres **entender el repo**: `README.md`
- si quieres **ponerlo a funcionar**: `docs/setup.md`
- si quieres **ejecutar el baseline**: `docs/instrucciones-uso-baseline.md`
- si quieres **ver resultados**: `docs/experimental-results.md`
