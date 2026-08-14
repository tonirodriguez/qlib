# Instrucciones para crear el entorno crypto

## Objetivo

Crear un entorno Conda aislado para la línea de investigación crypto de Qlib.
Este entorno evita modificar `finance` y mantiene la combinación compatible de
NumPy y PyTorch requerida en macOS Intel.

El entorno utilizado y validado en este repositorio se llama `crypto` y usa:

- Python 3.11
- NumPy 1.26.4
- PyTorch 2.2.2
- Pandas 2.3.3
- CCXT 4.5.11
- Optuna 4.5.0
- PyWavelets 1.9.0
- Qlib instalado desde este checkout en modo editable
- MLflow Skinny 3.8.1, requerido por la inicialización de Qlib

## Requisitos previos

- Miniconda, Anaconda o una distribución compatible con Conda.
- Git.
- Acceso al repositorio Qlib.
- Terminal situada en la raíz del repositorio.
- Espacio suficiente para PyTorch, PyArrow y los datasets generados.

Comprobar Conda:

```bash
conda --version
```

Clonar el repositorio, si todavía no está disponible localmente:

```bash
git clone <URL-DEL-REPOSITORIO> qlib
cd qlib
```

## 1. Crear el entorno base

```bash
conda create -n crypto python=3.11 pip -y
conda activate crypto
```

Comprobar que se está usando el intérprete correcto:

```bash
python --version
python -c "import sys; print(sys.executable)"
```

La ruta mostrada debe pertenecer a un directorio similar a
`miniconda3/envs/crypto` o `anaconda3/envs/crypto`.

## 2. Actualizar las herramientas de instalación

```bash
python -m pip install --upgrade pip setuptools wheel
```

## 3. Consideración especial para macOS Intel

PyTorch 2.2.2 es el último wheel disponible para determinadas versiones de
macOS Intel (`osx-64`) y fue compilado contra la ABI de NumPy 1.x. Por ese
motivo este proyecto fija:

```text
numpy>=1.26,<2
torch==2.2.2
```

No se debe actualizar NumPy a 2.x dentro de este entorno mientras se utilice
ese wheel de PyTorch.

Instalar primero una versión de `cryptography` que disponga de wheel universal
para evitar compilar Rust y OpenSSL localmente:

```bash
python -m pip install cryptography==47.0.0
```

En Linux o macOS Apple Silicon puede haber wheels más recientes de PyTorch. No
se deben cambiar versiones sin volver a ejecutar todos los tests y el smoke
training.

## 4. Instalar las dependencias del proyecto crypto

Desde la raíz del repositorio:

```bash
python -m pip install \
  -r work/crypto/requirements.txt \
  torch==2.2.2 \
  pytest \
  pandas==2.3.3 \
  scipy \
  scikit-learn \
  matplotlib \
  pyyaml \
  filelock \
  redis \
  dill \
  fire \
  ruamel.yaml \
  python-redis-lock \
  tqdm \
  pymongo \
  loguru \
  lightgbm \
  gym \
  joblib \
  pyarrow \
  pydantic-settings \
  setuptools-scm
```

Este perfil instala lo necesario para:

- descarga OHLCV mediante CCXT;
- conversión y lectura del provider Qlib;
- preprocessing y modelo SFM;
- optimización con Optuna;
- gráficos;
- tests del proyecto crypto.

No instala deliberadamente CVXPY, MLflow completo, Jupyter ni el stack completo
de reinforcement learning porque no forman parte del flujo crypto actual y
pueden introducir restricciones incompatibles con NumPy 1.x. Sí instala
`mlflow-skinny`, ya que Qlib importa el módulo `mlflow` durante su
inicialización.

## 5. Instalar este checkout de Qlib

Registrar el repositorio en modo editable sin incorporar todas las dependencias
opcionales de Qlib:

```bash
python -m pip install -e . --no-deps
```

El modo editable permite que los cambios realizados en el código local se
utilicen inmediatamente sin reinstalar Qlib.

No usar para este entorno:

```bash
python -m pip install -e ".[dev,rl]"
```

Ese comando intenta instalar dependencias generales y de RL que no son
necesarias para el proyecto crypto y pueden entrar en conflicto con NumPy 1.x.

## 6. Verificar las versiones

```bash
python - <<'PY'
import ccxt
import numpy
import optuna
import pandas
import pywt
import qlib
import sklearn
import torch

print("numpy:", numpy.__version__)
print("torch:", torch.__version__)
print("pandas:", pandas.__version__)
print("qlib:", qlib.__version__)
print("ccxt:", ccxt.__version__)
print("optuna:", optuna.__version__)
print("tensor_numpy:", torch.tensor([1.0]).numpy().tolist())
PY
```

La última línea debe mostrar `tensor_numpy: [1.0]`. Si aparece `Numpy is not
available` o un aviso sobre `_ARRAY_API`, comprobar que NumPy sigue siendo
1.26.x.

## 7. Ejecutar los tests crypto

```bash
python -m pytest -q tests/crypto
```

El resultado esperado en el estado actual del proyecto es:

```text
7 passed
```

## 8. Configuración recomendada

El proyecto funciona con variables de entorno. Se pueden exportar en la
terminal o definir en un archivo `.env` local que nunca debe subirse al
repositorio.

Ejemplo:

```bash
export CRYPTO_INSTRUMENTS="BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"
export CRYPTO_OHLCV_DIR="scripts/crypto/csv_data/crypto/ohlcv"
export CRYPTO_QLIB_OUTPUT_DIR="data/qlib_crypto"
export CRYPTO_UNIVERSE="crypto"
export QLIB_KERNELS="1"
```

`QLIB_KERNELS=1` evita problemas de multiproceso en algunos entornos macOS y
facilita ejecuciones reproducibles.

## 9. Ejecutar la ruta canónica

### Descargar OHLCV

```bash
python work/crypto/download_crypto.py
```

La descarga utiliza mercados spot públicos de Binance mediante CCXT. No
requiere claves privadas ni credenciales de trading.

### Convertir los datos a Qlib

```bash
CRYPTO_OHLCV_DIR=scripts/crypto/csv_data/crypto/ohlcv \
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto \
python work/crypto/convert_crypto_qlib.py
```

### Validar el provider

```bash
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto \
QLIB_KERNELS=1 \
python work/crypto/use_crypto.py
```

El universo esperado es:

```text
ada, btc, doge, eth, link, ltc, sol, xlm, xrp
```

## 10. Ejecutar un smoke training

El smoke training valida el circuito técnico con un solo trial y una sola
época. Sus métricas no constituyen evidencia financiera.

```bash
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto \
QLIB_KERNELS=1 \
CRYPTO_OPTUNA_TRIALS=1 \
CRYPTO_TRIAL_EPOCHS=1 \
CRYPTO_FINAL_EPOCHS=1 \
CRYPTO_FINAL_PATIENCE=1 \
CRYPTO_TOP_K=1 \
CRYPTO_MODEL_OUTPUT_DIR=work/crypto/output/optuna_sfm_v4_causal_smoke_local \
python work/crypto/qlib_sfm_pipeline.v4.py
```

No ejecutar un entrenamiento grande hasta completar nested walk-forward,
dataset atómico, backtest realista y holdout final.

## 11. Exportar el entorno

Para registrar exactamente el entorno local:

```bash
conda env export -n crypto --no-builds > crypto-environment-lock.yml
```

El archivo exportado puede contener rutas o paquetes específicos del sistema.
Debe revisarse antes de incorporarlo al repositorio.

Para generar una lista de paquetes Python:

```bash
python -m pip freeze > crypto-requirements-lock.txt
```

## 12. Activar y desactivar el entorno

Activar:

```bash
conda activate crypto
```

Desactivar:

```bash
conda deactivate
```

Comprobar siempre el entorno antes de instalar o ejecutar:

```bash
echo "$CONDA_DEFAULT_ENV"
which python
```

## 13. Actualizaciones

No ejecutar actualizaciones globales como `pip install -U numpy torch` sin una
validación específica. Para actualizar una dependencia:

1. crear un entorno temporal;
2. instalar la nueva combinación;
3. ejecutar todos los tests crypto;
4. validar Qlib y la conversión tensor–NumPy;
5. ejecutar un smoke training;
6. actualizar el lockfile y esta documentación.

## 14. Solución de problemas

### `RuntimeError: Numpy is not available`

```bash
python -m pip install --force-reinstall "numpy>=1.26,<2" "torch==2.2.2"
```

### Fallo compilando `cryptography`, Rust u OpenSSL

```bash
python -m pip install cryptography==47.0.0
```

Después, repetir la instalación de las dependencias crypto.

### Qlib se bloquea o crea demasiados procesos

```bash
export QLIB_KERNELS=1
```

### El intérprete pertenece a otro entorno

```bash
conda deactivate
conda activate crypto
python -c "import sys; print(sys.executable)"
```

### Recrear el entorno desde cero

Esta operación elimina el entorno y debe utilizarse solo si no contiene trabajo
no reproducible:

```bash
conda deactivate
conda env remove -n crypto
conda create -n crypto python=3.11 pip -y
conda activate crypto
```

Después se deben repetir los pasos de instalación y verificación de este
documento.
