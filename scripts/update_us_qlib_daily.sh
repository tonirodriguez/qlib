#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_QLIB_REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

# === CONFIG ===
QLIB_REPO="${QLIB_REPO:-$DEFAULT_QLIB_REPO}"         # repo detectado desde la ubicación del script
DATA_DIR="${DATA_DIR:-$HOME/.qlib/qlib_data/us_data}"
PYTHON_BIN="${PYTHON_BIN:-python}"
START_DATE="${START_DATE:-2026-03-31}"
REBUILD_START_DATE="${REBUILD_START_DATE:-1999-12-31}"
MAX_WORKERS="${MAX_WORKERS:-4}"
NORMALIZE_MAX_WORKERS="${NORMALIZE_MAX_WORKERS:-5}"
DELAY="${DELAY:-0.1}"
TODAY=$(date +%F)
MODE="update"
REBUILD_UNIVERSE_DIR="${REBUILD_UNIVERSE_DIR:-}"

if [ "${1:-}" = "--clean-rebuild" ]; then
  MODE="rebuild"
  shift
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --universe_data|--universe_data_dir)
      if [ $# -lt 2 ]; then
        echo "❌ Falta el valor para $1"
        exit 1
      fi
      REBUILD_UNIVERSE_DIR="$2"
      shift 2
      ;;
    *)
      echo "❌ Opción no soportada: $1"
      echo "   Usa --clean-rebuild [--universe_data DIR] o ajusta REBUILD_UNIVERSE_DIR."
      exit 1
      ;;
  esac
done

# === CHECKS ===
if [ ! -d "$QLIB_REPO/scripts/data_collector/yahoo" ]; then
  echo "❌ No encuentro el repo qlib en: $QLIB_REPO"
  echo "   Clona qlib primero si no lo has hecho o ajusta la variable QLIB_REPO."
  exit 1
fi

if [ ! -d "$DATA_DIR" ] && [ "$MODE" = "update" ]; then
  echo "⚠️  No encuentro el dataset Qlib US en: $DATA_DIR"
  echo "   Asegúrate de haber inicializado los datos primero o el collector lo hará."
fi

cd "$QLIB_REPO"
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
export QLIB_REPO
export QLIB_MAX_WORKERS="$MAX_WORKERS"
if [ -n "$NORMALIZE_MAX_WORKERS" ]; then
  export QLIB_NORMALIZE_MAX_WORKERS="$NORMALIZE_MAX_WORKERS"
fi

if [ "$MODE" = "rebuild" ]; then
  echo "ℹ️  Usando QLIB_MAX_WORKERS=$QLIB_MAX_WORKERS"
  if [ -n "${QLIB_NORMALIZE_MAX_WORKERS:-}" ]; then
    echo "ℹ️  Usando QLIB_NORMALIZE_MAX_WORKERS=$QLIB_NORMALIZE_MAX_WORKERS"
  fi
  echo "ℹ️  Usando DELAY=$DELAY"
  if [ -z "$REBUILD_UNIVERSE_DIR" ]; then
    if [ -s "$DATA_DIR/instruments/all.txt" ] && [ -s "$DATA_DIR/calendars/day.txt" ]; then
      REBUILD_UNIVERSE_DIR="$DATA_DIR"
    else
      for candidate in $(find "$(dirname "$DATA_DIR")" -maxdepth 1 -type d -name "$(basename "$DATA_DIR")_backup_*" | sort -r); do
        if [ -s "$candidate/instruments/all.txt" ] && [ -s "$candidate/calendars/day.txt" ]; then
          REBUILD_UNIVERSE_DIR="$candidate"
          break
        fi
      done
    fi
  fi

  if [ -z "$REBUILD_UNIVERSE_DIR" ]; then
    echo "❌ No encuentro una fuente de universo válida para el clean rebuild."
    echo "   Ajusta REBUILD_UNIVERSE_DIR o restaura un backup sano en $DATA_DIR."
    exit 1
  fi

  echo "➡️ Reconstruyendo datos Qlib US desde $REBUILD_START_DATE hasta $TODAY ..."
  $PYTHON_BIN scripts/update_us_all.py rebuild_data_to_bin \
    --qlib_data_1d_dir "$DATA_DIR" \
    --universe_data_dir "$REBUILD_UNIVERSE_DIR" \
    --start_date "$REBUILD_START_DATE" \
    --end_date "$TODAY" \
    --delay "$DELAY" \
    --backup_existing True \
    --region US
  echo "✅ Reconstrucción completada desde $REBUILD_START_DATE hasta $TODAY."
else
  echo "ℹ️  Usando QLIB_MAX_WORKERS=$QLIB_MAX_WORKERS"
  if [ -n "${QLIB_NORMALIZE_MAX_WORKERS:-}" ]; then
    echo "ℹ️  Usando QLIB_NORMALIZE_MAX_WORKERS=$QLIB_NORMALIZE_MAX_WORKERS"
  fi
  echo "ℹ️  Usando DELAY=$DELAY"
  update_args=(
    update_data_to_bin
    --qlib_data_1d_dir "$DATA_DIR"
    --end_date "$TODAY"
    --delay "$DELAY"
    --region US
  )

  if [ -n "$START_DATE" ]; then
    echo "➡️ Actualizando datos Qlib US desde $START_DATE hasta $TODAY ..."
    echo "ℹ️  Forzando trading_date=$START_DATE"
    update_args+=(--trading_date "$START_DATE")
  else
    echo "➡️ Actualizando datos Qlib US en modo incremental automático hasta $TODAY ..."
  fi

  $PYTHON_BIN scripts/update_us_all.py "${update_args[@]}"
  echo "✅ Update completado hasta $TODAY."
fi
