# Temas Pendientes Qlib

1. Caracterizar bien las comisiones: min_cost: 0.0035
2. Entender cómo se normalizan los datos.
3. Entender los resultados de los experimentos. Cómo seleccionar el mejor modelo.
4. ~~Aplicar Optuna según las métricas del punto anterior.~~ ✅ Hecho en `scripts/crypto/qlib_sfm_pipeline.v3.py` — 30 trials, 7 hiperparámetros, MedianPruner, análisis de importancia.
5. Aplicar la salida del día siguiente y la de los 5 días siguientes. Entender cual es la label cuando utilizamos Alpha158

---

6. **Modelar SFM con Cryptos y Stocks** — Explorar la viabilidad de aplicar Stochastic Factor Models (SFM) al universo combinado de criptomonedas y acciones, evaluando si el framework de Qlib soporta esta heterogeneidad de activos.

---

## Operaciones / Infraestructura

7. **Ajustar docker-compose.yml** — Revisar y actualizar la configuración de docker-compose del proyecto para que refleje correctamente las necesidades actuales (volúmenes, redes, dependencias).

8. **Incorporar el directorio de datos de Qlib al proyecto** — El directorio `data/qlib/` con los datasets debe estar correctamente integrado en la estructura del proyecto y en el sistema de backups.

9. **Backup del workspace** — Establecer un sistema de backup periódico del workspace de OpenClaw para no perder configuraciones, experimentos ni documentación.

10. **Wiki de PhD** — Mantener actualizada la wiki del PhD (mkdocs) con la documentación del proyecto, resultados y decisiones metodológicas.