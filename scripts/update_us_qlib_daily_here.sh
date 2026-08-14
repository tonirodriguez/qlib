#!/usr/bin/env bash
# Actualización incremental de los datos US de Qlib desde Yahoo Finance.
# Adaptado a las rutas de ESTA máquina (HOME del perfil investments).
# Es el modo "update" (incremental): trae solo los días nuevos hasta hoy.
# Rápido — adecuado para ejecución semanal programada.
#
# Uso: bash scripts/update_us_qlib_daily_here.sh [START_DATE]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QLIB_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

# === RUTAS DE ESTA MÁQUINA ===
DATA_DIR="/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
PYTHON_BIN="/opt/data/qlib-venv/bin/python"
QLIB_US_WORK_DIR="${DATA_DIR%/us_data}/yahoo_data"

# Fecha de inicio del update incremental (datos desde aquí los recoge)
START_DATE="${1:-2026-05-31}"
TODAY=$(date +%F)

echo "ℹ️  Actualización incremental de datos Qlib US"
echo "   Repo:      $QLIB_REPO"
echo "   Datos:     $DATA_DIR"
echo "   Python:    $PYTHON_BIN"
echo "   Desde:     $START_DATE hasta $TODAY"

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
export QLIB_REPO
export QLIB_MAX_WORKERS="${MAX_WORKERS:-4}"
export QLIB_NORMALIZE_MAX_WORKERS="${NORMALIZE_MAX_WORKERS:-5}"
export DATA_DIR
export QLIB_US_WORK_DIR

if [ ! -d "$DATA_DIR" ]; then
  echo "❌ No existe el directorio de datos: $DATA_DIR"
  exit 1
fi

echo "➡️  Ejecutando update_data_to_bin ..."
"$PYTHON_BIN" scripts/update_us_all.py update_data_to_bin \
  --qlib_data_1d_dir "$DATA_DIR" \
  --trading_date "$START_DATE" \
  --end_date "$TODAY" \
  --delay "${DELAY:-0.1}" \
  --region US

echo "✅ Datos Qlib US actualizados hasta $TODAY"
