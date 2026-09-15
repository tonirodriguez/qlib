#!/usr/bin/env bash
set -euo pipefail

# Resincronización periódica del dataset US.
#
# Re-descarga y vuelve a volcar desde el día 1 del mes anterior hasta hoy, para corregir
# revisiones de Yahoo (splits, dividendos, cierres ajustados a posteriori) y huecos que
# haya dejado el update incremental diario.
#
# IMPORTANTE: esto NO es un clean rebuild. Usa update_data_to_bin (DumpDataUpdate), que
# sobrescribe solo el rango indicado y conserva el histórico desde 1999. El clean rebuild
# completo (rebuild_data_to_bin + DumpDataAll) reconstruye el dataset desde cero con los
# datos descargados: lanzarlo con una fecha de inicio reciente DESTRUIRÍA el histórico.
# Para un clean rebuild completo, usar --full (descarga desde REBUILD_START_DATE, ~19 h).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "${1:-}" = "--full" ]; then
  shift
  echo "⚠️  Clean rebuild COMPLETO desde ${REBUILD_START_DATE:-1999-12-31} (varias horas)."
  exec "$SCRIPT_DIR/update_us_qlib_daily.sh" --clean-rebuild \
    --universe_data "${REBUILD_UNIVERSE_DIR:-$HOME/.qlib/qlib_data/us_data/}" "$@"
fi

# Día 1 del mes anterior (ej.: el 2026-09-15 -> 2026-08-01)
RESYNC_START="${RESYNC_START:-$(date -d "$(date +%Y-%m-01) -1 month" +%F)}"

echo "➡️ Resincronizando datos Qlib US desde $RESYNC_START (día 1 del mes anterior) ..."
START_DATE="$RESYNC_START" exec "$SCRIPT_DIR/update_us_qlib_daily.sh" "$@"
