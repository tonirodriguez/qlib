#!/bin/bash
# =====================================================================
# run_daily_pipeline.sh — Ejecuta el pipeline diario SFM v8
#
# Flujo:
#   1. Actualiza datos incrementales desde Coinbase (USD real, sin límite)
#   2. Convierte CSVs a formato Qlib binario (data/qlib)
#   3. Genera señal diaria
#   4. Ejecuta paper trading
#   Guarda log con fecha
#
# IMPORTANTE:
#   - Se usa Coinbase (no CoinGecko) para el incremental diario en USD real.
#   - El dataset Qlib objetivo es data/qlib (UNO SOLO, consolidado desde genesis
#     CryptoCompare + incremental Coinbase). Se exporta CRYPTO_QLIB_OUTPUT_DIR.
#
# Uso manual:
#   bash work/crypto/run_daily_pipeline.sh
#
# Cron (server):
#   0 9 * * * /opt/data/qlib/work/crypto/run_daily_pipeline.sh
# Cron (Mac local):
#   0 9 * * * /path/to/src/qlib/work/crypto/run_daily_pipeline.sh
# =====================================================================

set -e

# ── Configuración (portable: permite override vía ENV) ──
PROJECT_DIR="${QLIB_PROJECT_DIR:-/opt/data/qlib}"
PYTHON="${QLIB_PYTHON:-/opt/data/qlib-venv/bin/python}"
LOG_DIR="${PROJECT_DIR}/work/crypto/output/sfm_v8/logs"

# Dataset Qlib objetivo: UNO SOLO en data/qlib (consolidado desde genesis).
export CRYPTO_QLIB_OUTPUT_DIR="${CRYPTO_QLIB_OUTPUT_DIR:-data/qlib}"
# Directorio de CSVs por coin (fuente de verdad) para el conversor
export CRYPTO_OHLCV_DIR="scripts/crypto/csv_data/crypto_cryptocompare/ohlcv"
export CRYPTO_OHLCV_FILE_PATTERN="{instrument_lower}.csv"
# Costes reales de Binance (punto 3): el paper trading usa la fee del schedule
export CRYPTO_FEE_SCHEDULE_JSON="${CRYPTO_FEE_SCHEDULE_JSON:-work/crypto/config/binance_fee_schedule.json}"

TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/pipeline_${TIMESTAMP}.log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

echo "==========================================" | tee -a "$LOG_FILE"
echo "🔮 SFM v8 — Pipeline Diario" | tee -a "$LOG_FILE"
echo "   Fecha: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "   Dataset Qlib: $CRYPTO_QLIB_OUTPUT_DIR" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR"

# ── Paso 1: Actualizar datos (Coinbase, USD real, incremental) ──
echo "[1/4] 📥 Actualizando datos desde Coinbase (USD)..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/update_crypto_daily_coinbase.py >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME))/60)) min $(($(($END_TIME - $START_TIME)) % 60)) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Paso 2: Convertir a Qlib binario ──
echo "[2/4] 🔄 Convirtiendo CSVs a Qlib binario..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/convert_crypto_qlib.py >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME)))) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Paso 3: Generar señal ──
echo "[3/4] 📊 Generando señal diaria..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/sfm_daily_signal.py >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME)))) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Paso 4: Paper trading ──
echo "[4/4] 💰 Ejecutando paper trading..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/sfm_paper_trading.py >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME))/60)) min $(($(($END_TIME - $START_TIME)) % 60)) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Paso 5: Metricas y monitor del paper (Paso 6 de produccion) ──
echo "[5/5] 📊 Calculando metricas del paper (Sharpe, Sortino, Calmar, VaR, drawdown)..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/paper_metrics.py --csv "${PROJECT_DIR}/work/crypto/output/sfm_v8/history_paper_trading.csv" >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME)))) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Resumen ──
echo "==========================================" | tee -a "$LOG_FILE"
echo "✅ Pipeline completado" | tee -a "$LOG_FILE"
echo "   Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "   Hora: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"

# Mostrar resumen de la señal al final (para salida rápida)
echo ""
echo "═══════════════════════════════════════════"
echo "  Últimas líneas de la señal:"
echo "═══════════════════════════════════════════"
grep -A 20 "SEÑAL DIARIA SFM" "$LOG_FILE" | head -20
echo ""
echo "  📋 Log completo: $LOG_FILE"
echo "═══════════════════════════════════════════"