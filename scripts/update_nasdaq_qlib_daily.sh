#!/usr/bin/env bash
set -euo pipefail

# === CONFIG ===
QLIB_REPO="${QLIB_REPO:-/mnt/c/Users/toni/src/qlib}"         # ruta donde clonaste qlib
DATA_DIR="${DATA_DIR:-$HOME/.qlib/qlib_data/us_data}"
PYTHON_BIN="${PYTHON_BIN:-python}"
SOURCE_DIR="${SOURCE_DIR:-$QLIB_REPO/scripts/data_collector/yahoo/source_nasdaq100}"
NORMALIZE_DIR="${NORMALIZE_DIR:-$QLIB_REPO/scripts/data_collector/yahoo/normalize_nasdaq100}"
DELAY="${DELAY:-0.1}"
START_DATE="2026-03-31"
TODAY=$(date +%F)

# === CHECKS ===
if [ ! -d "$QLIB_REPO/scripts/data_collector/yahoo" ]; then
  echo "❌ No encuentro el repo qlib en: $QLIB_REPO"
  exit 1
fi

echo "➡️ Actualizando datos Qlib (Solo Nasdaq 100) desde $START_DATE hasta $TODAY ..."
echo "   DATA_DIR=$DATA_DIR"
echo "   SOURCE_DIR=$SOURCE_DIR"
echo "   NORMALIZE_DIR=$NORMALIZE_DIR"
echo "   DELAY=$DELAY"

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

# Ejecutamos el script de python personalizado que filtra las acciones
$PYTHON_BIN scripts/update_nasdaq100.py update_data_to_bin \
  --qlib_data_1d_dir "$DATA_DIR" \
  --source_dir "$SOURCE_DIR" \
  --normalize_dir "$NORMALIZE_DIR" \
  --trading_date "$START_DATE" \
  --end_date "$TODAY" \
  --delay "$DELAY" \
  --region US

echo "✅ Update completado para Nasdaq 100 desde $START_DATE hasta $TODAY."
