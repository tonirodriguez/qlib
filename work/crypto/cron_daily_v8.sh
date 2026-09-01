#!/bin/bash
# =====================================================================
# cron_daily_v8.sh — Wrapper para el cronjob diario del paper trading v8.
#
# Ejecuta run_daily_pipeline.sh a las 9:00 (horario del server). El pipeline
# ya actualiza datos, genera señal, ejecuta el paper y notifica por Telegram
# a @oscarbot_toni_bot (resumen + métricas).
#
# Este wrapper:
#   - Lanza el pipeline y captura el exit code.
#   - Si falla, emite un mensaje de ERROR por stdout (-> alerta del cron).
#   - Si OK, emite un resumen breve.
#   - Nunca corta por fallos menores de las notificaciones.
# =====================================================================

set -uo pipefail

PROJECT_DIR="${QLIB_PROJECT_DIR:-/opt/data/qlib}"

echo "🚀 SFM v8 cron diario — $(date '+%Y-%m-%d %H:%M:%S')"

cd "$PROJECT_DIR" || { echo "ERROR: no existe $PROJECT_DIR"; exit 1; }

# Lanzar pipeline (proporciona su propio log por fecha)
if ! bash work/crypto/run_daily_pipeline.sh >> /tmp/cron_daily_v8_out.log 2>&1; then
    echo "❌ ERROR en el pipeline diario de v8 — revisa logs en output/sfm_v8/logs/"
    exit 1
fi

# Resumen de la señal/paper más reciente
echo ""
echo "── Última señal / paper ──"
latest_signal=$(ls -t output/sfm_v8/signal_*.json 2>/dev/null | head -1)
if [ -n "$latest_signal" ]; then
    echo "Señal: $latest_signal"
fi
if [ -f output/sfm_v8/state_paper_trading.json ]; then
    echo "Estado paper: output/sfm_v8/state_paper_trading.json"
fi

echo "✅ Pipeline diario completado."