#!/bin/bash
# 1. Cargar el perfil de conda (ajusta la ruta a tu instalación)
source /home/toni/miniconda3/etc/profile.d/conda.sh

# 2. Activar el entorno
conda activate qlib

# 3. Ejecutar el script
set -euo pipefail

/mnt/c/Users/toni/src/qlib/scripts/update_sp500_qlib_daily.sh
/mnt/c/Users/toni/src/qlib/scripts/update_nasdaq_qlib_daily.sh
/mnt/c/Users/toni/src/qlib/scripts/backup_qlib_us_data.sh
mv /home/toni/.qlib/backups/us_data_backup_*.zip "/mnt/c/Users/toni/OneDrive - Laietana de Llibreteria S.L/qlib_backups/"