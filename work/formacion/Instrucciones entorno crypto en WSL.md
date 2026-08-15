# Instrucciones para crear el entorno crypto en WSL

Adaptación a WSL2 (Ubuntu) del documento `Instrucciones para crear el entorno
crypto.md`. Mantiene la misma combinación validada de versiones (Python 3.11,
NumPy 1.26.x, PyTorch 2.2.2) para reproducir los resultados del proyecto. En
Linux existen wheels más recientes de PyTorch, pero **no se deben cambiar las
versiones sin volver a pasar todos los tests y el smoke training**.

## 0. Requisitos previos en WSL

Comprobar que usas WSL2 (desde PowerShell en Windows):

```powershell
wsl --status          # debe indicar "Versión predeterminada: 2"
wsl --list --verbose  # la distro Ubuntu debe estar en VERSION 2
```

Dentro de Ubuntu (WSL), actualizar el sistema e instalar utilidades base:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl build-essential
```

El entrenamiento es intensivo (~3 h por combinación) y usa mucha RAM. Conviene
dar recursos a WSL creando en Windows el fichero `C:\Users\<tu-usuario>\.wslconfig`:

```ini
[wsl2]
memory=16GB
processors=8
swap=8GB
```

Después, en PowerShell: `wsl --shutdown` y vuelve a abrir Ubuntu.

## 1. Colocar el repositorio dentro del sistema de archivos de WSL

**Importante para el rendimiento:** trabajar sobre `/mnt/d/...` (el disco de
Windows) es lento y da problemas de permisos con Conda y PyArrow. Copia o clona
el repo en el sistema de archivos nativo de Linux (`~/src`).

Opción A — copiar tu repo actual desde `D:\src\qlib` (incluye datos y outputs):

```bash
mkdir -p ~/src
cp -r /mnt/d/src/qlib ~/src/qlib
cd ~/src/qlib
```

Opción B — clonar limpio (tendrás que regenerar el provider de datos):

```bash
mkdir -p ~/src && cd ~/src
git clone <URL-DEL-REPOSITORIO> qlib
cd ~/src/qlib
```

Si clonas limpio, necesitarás `data/qlib_crypto/` (el provider). O lo copias
desde tu repo Windows:

```bash
cp -r /mnt/d/src/qlib/data/qlib_crypto ~/src/qlib/data/
```

o lo regeneras con la ruta canónica del paso 9.

## 2. Instalar Miniconda (Linux)

```bash
curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o ~/miniconda.sh
bash ~/miniconda.sh -b -p ~/miniconda
~/miniconda/bin/conda init bash
exec bash            # recarga la shell para activar conda
conda --version
```

## 3. Crear y activar el entorno

```bash
cd ~/src/qlib
conda create -n crypto python=3.11 pip -y
conda activate crypto
python --version
python -c "import sys; print(sys.executable)"   # debe apuntar a envs/crypto
```

## 4. Actualizar herramientas de instalación

```bash
python -m pip install --upgrade pip setuptools wheel
```

## 5. Instalar las dependencias del proyecto crypto

Se mantiene el pin `numpy>=1.26,<2` + `torch==2.2.2` por compatibilidad de ABI.
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

En Linux, `torch==2.2.2` instala por defecto el wheel **CPU**. Si tienes GPU
NVIDIA con soporte CUDA en WSL y quieres acelerarlo, instala en su lugar el
wheel CUDA (opcional, cambia el entorno respecto al validado):

```bash
# opcional, solo con GPU NVIDIA + CUDA en WSL
python -m pip install torch==2.2.2 --index-url https://download.pytorch.org/whl/cu121
```

No se instala CVXPY, MLflow completo ni Jupyter para no arrastrar restricciones
incompatibles con NumPy 1.x. Sí se instala `mlflow-skinny` porque Qlib importa
`mlflow` durante `qlib.init`.

## 6. Instalar este checkout de Qlib en modo editable

```bash
python -m pip install -e . --no-deps
```

No usar `pip install -e ".[dev,rl]"`: arrastra dependencias de RL que chocan con
NumPy 1.x.

## 7. Verificar versiones y la conversión tensor–NumPy

```bash
python - <<'PY'
import ccxt, numpy, optuna, pandas, pywt, qlib, sklearn, torch
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
available` o un aviso sobre `_ARRAY_API`, NumPy se ha ido a 2.x: corrige con

```bash
python -m pip install --force-reinstall "numpy>=1.26,<2" "torch==2.2.2"
```

## 8. Ejecutar los tests crypto

```bash
python -m pytest -q tests/crypto
```

Deben salir todos en verde (incluye los módulos nuevos B2/B3:
`test_execution_costs_v2.py` y `test_baselines.py`).

## 9. Configuración recomendada (.env o export)

```bash
export CRYPTO_INSTRUMENTS="BTC,ETH,SOL,XLM,ADA,XRP,DOGE,LINK,LTC"
export CRYPTO_OHLCV_DIR="scripts/crypto/csv_data/crypto/ohlcv"
export CRYPTO_QLIB_OUTPUT_DIR="data/qlib_crypto"
export CRYPTO_UNIVERSE="crypto"
export QLIB_KERNELS="1"
```

`QLIB_KERNELS=1` evita problemas de multiproceso y facilita reproducibilidad.

## 10. Ruta canónica de datos (solo si no copiaste `data/qlib_crypto`)

```bash
# 1) descargar OHLCV (spot público de Binance vía CCXT; sin credenciales)
python work/crypto/download_crypto.py

# 2) convertir a provider Qlib
CRYPTO_OHLCV_DIR=scripts/crypto/csv_data/crypto/ohlcv \
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto \
python work/crypto/convert_crypto_qlib.py

# 3) validar el provider (universo esperado: ada, btc, doge, eth, link, ltc, sol, xlm, xrp)
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto QLIB_KERNELS=1 \
python work/crypto/use_crypto.py
```

## 11. Smoke training (valida el circuito, no es evidencia financiera)

```bash
CRYPTO_QLIB_OUTPUT_DIR=data/qlib_crypto \
QLIB_KERNELS=1 \
CRYPTO_OPTUNA_TRIALS=1 CRYPTO_TRIAL_EPOCHS=1 CRYPTO_FINAL_EPOCHS=1 \
CRYPTO_FINAL_PATIENCE=1 CRYPTO_TOP_K=1 \
CRYPTO_MODEL_OUTPUT_DIR=work/crypto/output/optuna_sfm_v4_causal_smoke_wsl \
python work/crypto/qlib_sfm_pipeline.v4.py
```

## 12. Lanzar B1 (cerrar la 6ª combinación del piloto)

Con el entorno ya verificado, desde `~/src/qlib`:

```bash
CRYPTO_INSTRUMENTS="BTC,ETH,SOL,ADA,XRP,DOGE,LINK,LTC" \
CRYPTO_SEED=43 \
CRYPTO_NESTED_OUTPUT_DIR=work/crypto/output/universe_comparison_pilot/reduced_8_no_xlm_seed_43 \
CRYPTO_NESTED_FOLDS=3 CRYPTO_NESTED_TRIALS=5 CRYPTO_NESTED_FINAL_EPOCHS=15 \
CRYPTO_NESTED_PATIENCE=5 CRYPTO_ORDER_NOTIONAL=10000 \
python work/crypto/run_nested_walk_forward.py 2>&1 \
  | tee work/crypto/output/universe_comparison_pilot/reduced_8_no_xlm_seed_43/run.log
```

## 13. Exportar el lockfile del entorno

```bash
conda env export -n crypto --no-builds > work/formacion/crypto-environment-wsl-lock.yml
python -m pip freeze > work/formacion/crypto-requirements-wsl-lock.txt
```

## 14. Solución de problemas específicos de WSL

- **Todo va muy lento / permisos raros:** estás trabajando en `/mnt/d/...`. Mueve
  el repo a `~/src/qlib` (paso 1).
- **`Killed` durante el entrenamiento:** WSL se quedó sin RAM. Sube `memory` en
  `.wslconfig` y `wsl --shutdown`.
- **`RuntimeError: Numpy is not available`:** reinstala el par
  `"numpy>=1.26,<2"` + `"torch==2.2.2"` (paso 7).
- **Qlib crea demasiados procesos o se bloquea:** `export QLIB_KERNELS=1`.
- **Intérprete equivocado:** `conda deactivate && conda activate crypto` y
  comprobar `which python`.
