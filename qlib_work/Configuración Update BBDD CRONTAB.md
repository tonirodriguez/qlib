# Configuración CRONTAB para cargas diarias

Con la siguiente configuración, haremos una carga diaria y una carga Rebuild el sabado para actualizar la BBDD

1 1 * * 2-5 /home/toni/src/qlib/scripts/update_us_qlib_daily.sh >>  /home/toni/src/qlib/scripts/logs/run_daily_$(date +\%Y\%m\%d) 2>&1
1 1 * * 6 /home/toni/src/qlib/scripts/update_us_qlib_rebuild.sh >>  /home/toni/src/qlib/scripts/logs/run_rebuild_$(date +\%Y\%m\%d) 2>&1
