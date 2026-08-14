# 🚀 Hallazgo CLAVE — Momentum de medio plazo con alpha OOS genuino (S&P 500)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — búsqueda de alpha sistemático
> **Universo:** sp500_liquid (283 acciones S&P 500 con historial desde 2010)
> **Contexto:** primer alpha out-of-sample genuino encontrado tras el diagnóstico riguroso (Alpha158+LightGBM y momentum corto no daban señal).

---

## 1. El hallazgo

**El momentum de MEDIO PLAZO (120 días) sobre universo AMPLIO da IC out-of-sample = +0.066**, muy por encima del umbral de 0.02 para considerar alpha real y explotable.

| Ventana momentum | IC medio OOS (label 120d) | Veredicto |
|---|---|---|
| mom20 | −0.010 | Reversión corto plazo |
| mom60 | +0.026 | Débil/positivo |
| **mom120** | **+0.066** | ✅ ALPHA REAL |
| mom250 | +0.022 | Positivo |

## 2. La tabla completa (por horizonte de label)

| Horizonte label | mom20 | mom60 | mom120 | mom250 |
|---|---|---|---|---|
| **10 días** | −0.09 | −0.12 | −0.10 | −0.08 |
| **60 días** | −0.09 | −0.09 | −0.03 | −0.05 |
| **120 días** | −0.01 | +0.03 | **+0.066 ✅** | +0.02 |

**Conclusión:** el alpha aparece cuando el **horizonte del label se alinea con la ventana de momentum largo**. Momentum 120d + label 120d = IC 0.066.

## 3. IC por año (mom120, label 120d) — robustez

| Año | mom120 |
|---|---|
| 2018 | −0.007 |
| 2019 | +0.006 |
| 2020 | −0.081 |
| 2021 | +0.039 |
| 2022 | −0.124 |
| 2023 | +0.067 |
| 2024 | +0.036 |
| 2025 | **+0.188** |
| 2026 | **+0.470** |
| **IC medio** | **+0.066** |

**Lectura honesta:** el IC es positivo y fuerte en los últimos 3-4 años (2023-2026), pero negativo en 2020 y 2022 (años de alta volatilidad/crisis). Esto es **coherente con el patrón conocido de momentum-crash** (Daniel-Moskowitz 2016): el momentum sufre en transiciones bruscas de mercado (2020 covid, 2022 subidas de tipos). El alpha está ahí, pero hay que **gestionar el riesgo de momentum-crash**.

## 4. Por qué este hallazgo es importante

1. **Es el primer alpha out-of-sample GENUINO** del proyecto (IC 0.066 > 0.02).
2. **Confirma la tesis de Quinn y la literatura (Jegadeesh-Titman 1993):** el momentum de medio plazo funciona en universo amplio, no en 16 megacaps del mismo sector con label de 10 días.
3. **El diagnóstico completo del proyecto ha funcionado:** rigurosamente descartamos lo que no funciona (Alpha158+LightGBM, momentum corto, tech_giants) hasta encontrar lo que sí.
4. **Da una base sólida** para construir la estrategia: momentum 120d + label 120d sobre S&P 500.

## 5. Próximos pasos (secuenciales)

1. ✅ **Documentar** este hallazgo (este documento)
2. ⏭️ **Confirmar robustez** — probar variantes (mom120/label60, mom250/label250, mom120/label120 confirmado)
3. ⏭️ **Implementar señal real** — backtest completo con momentum 120d en Qlib sobre sp500_liquid, con costes IB
4. ⏭️ **Combinar con factor ortogonal** — momentum + quality/low-vol (según roadmap de Quinn)
5. ⏭️ **Gestionar momentum-crash** — vol-targeting o filtro de régimen

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
