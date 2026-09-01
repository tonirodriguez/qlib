#!/bin/bash
# =====================================================================
# run_daily_pipeline.sh — Ejecuta el pipeline diario SFM v8
#
# Flujo:
#   1. Descarga datos frescos desde CoinGecko (CSV)
#   2. Convierte CSVs a formato Qlib binario (data/qlib/)
#   3. Genera señal diaria
#   4. Ejecuta paper trading
#   4. Guarda log con fecha
#
# Uso manual:
#   bash work/crypto/run_daily_pipeline.sh
#
# Cron (crontab -e):
#   0 9 * * * /mnt/c/Users/trodriguez/src/qlib/work/crypto/run_daily_pipeline.sh
# =====================================================================

set -e

# ── Configuración ──
PROJECT_DIR="/mnt/c/Users/trodriguez/src/qlib"
PYTHON="/home/toni/miniconda3/envs/qlib/bin/python"
LOG_DIR="${PROJECT_DIR}/work/crypto/output/sfm_v8/logs"
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
LOG_FILE="${LOG_DIR}/pipeline_${TIMESTAMP}.log"

# Crear directorio de logs si no existe
mkdir -p "$LOG_DIR"

echo "==========================================" | tee -a "$LOG_FILE"
echo "🔮 SFM v8 — Pipeline Diario" | tee -a "$LOG_FILE"
echo "   Fecha: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "==========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

cd "$PROJECT_DIR"

# ── Paso 1: Descargar datos ──
echo "[1/4] 📥 Descargando datos desde CoinGecko..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/download_crypto_coingecko.py >> "$LOG_FILE" 2>&1

END_TIME=$(date +%s)
echo "   ⏱️  $(($(($END_TIME - $START_TIME))/60)) min $(($(($END_TIME - $START_TIME)) % 60)) seg" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# ── Paso 2: Convertir a Qlib binario ──
echo "[2/4] 🔄 Convirtiendo CSVs a Qlib binario..." | tee -a "$LOG_FILE"
echo "      $(date '+%H:%M:%S')" | tee -a "$LOG_FILE"
START_TIME=$(date +%s)

$PYTHON work/crypto/dump_coingecko_to_qlib.py >> "$LOG_FILE" 2>&1

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