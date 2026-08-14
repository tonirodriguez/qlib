# 🗺️ Qlib — Direcciones de Aprendizaje (Roadmap)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — inversión cuantitativa sistemática
> **Contexto:** tras el diagnóstico riguroso (walk-forward, IC OOS) concluimos que el universo tech_giants (16 megacaps del mismo sector) NO ofrece alpha transversal explotable. Estas son las direcciones para seguir aprendiendo y avanzando.

---

## Conclusión base (por qué giramos)

- **Alpha158 + LightGBM** (tech_giants): IC OOS 0.0078 → sin alpha (ruido)
- **Momentum 20-250d** (tech_giants): IC negativo → invertido/inexistente por concentración
- **Momentum 20d** (S&P 500): IC −0.09 → reversión de corto plazo
- **Momentum 120-250d** (S&P 500): IC +0.02 a +0.32 en últimos años → momentum largo aparece pero inestable

**Lección clave:** el alpha en Qlib viene de **universos amplios** (muchos tickers de distintos sectores) + **factores ortogonales con base teórica**, no de 158 factores técnicos sobre pocas acciones correlacionadas.

---

## Direcciones de aprendizaje (para explorar en sesiones futuras)

### A. Ampliar universo + momentum largo ⭐ (EN CURSO)
- Probar momentum 120/250d (el que dio IC positivo en 2025-26) sobre `sp500_liquid`
- Implementar el factor momentum como señal real en un backtest completo
- Comparar IC OOS del momentum largo en universo amplio vs tech_giants
- **Estado:** ejecutando walk-forward con label a 60d; probar también label a 120d/250d

### B. Factor mining / RD-Agent
- Explorar cómo Microsoft hace factor mining automático (RD-Agent)
- Entender por qué Alpha158 (158 factores) sobreajusta vs pocos factores ortogonales
- Probar selección de factores (feature selection) antes del modelo

### C. Estrategia "beta de calidad + gestión de riesgo"
- Usar vol-targeting, rebalanceo y costes (ya montados) para una cartera Qlib sobre sp500_liquid
- Plantilla de cartera indexada con gestión de riesgo como referencia honesta

### D. Datos fundamentales (para PEAD / quality)
- Añadir EPS/SUE a Qlib (para post-earnings announcement drift)
- Añadir factores fundamentales (ROE, profitability de Novy-Marx)
- Permite quality-at-a-reasonable-price y earnings momentum

### E. Otras técnicas de validación
- Purged/embargoed CV (López de Prado) para evitar fuga de datos
- Combinación de factores ortogonales (momentum + quality + low-vol)
- Gestión del momentum-crash (Daniel-Moskowitz)

---

## Criterio de éxito (regla fija)
Un modelo solo es "listo" si pasa **walk-forward con IC agregado OOS > 0.02** sostenido, además del backtest. Si no, es overfitting/beta.

---

*Documento vivo del proyecto Qlib Work. Se actualiza con cada avance.*
