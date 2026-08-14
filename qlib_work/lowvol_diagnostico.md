# 📉 Factor Low-Volatility — Resultado (no mejora en mercado alcista)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — combinación de factores ortogonales para el momentum
> **Contexto:** tras validar el momentum 120d (IC OOS +0.066), probamos combinar con un factor ortogonal. El candidato sin datos fundamentales era **low-volatility** (Frazzini-Pedersen 2014). Resultado: no mejoró en este régimen de mercado.
> **Script:** `toni/lowvol_walkforward.py`

---

## 1. Resultado

**IC medio de vol: +0.126 (positivo)** → las de ALTA volatilidad sobre-performan, lo contrario del factor low-vol clásico.

| Año | IC vol→fwd | L/S (low-vol vs high-vol) | Lectura |
|---|---|---|---|
| 2018 | −0.151 | +8.47% | Low-vol funcionó |
| 2019 | +0.016 | +1.80% | Neutral |
| 2020 | +0.406 | **−25.86%** | ⚠️ High-vol CRASH (low-vol defendió) |
| 2021 | +0.155 | −2.03% | High-vol gana |
| 2022 | +0.158 | −3.18% | High-vol gana |
| 2023 | +0.100 | −8.73% | High-vol gana |
| 2024 | −0.084 | +4.45% | Low-vol funcionó |
| 2025 | +0.307 | −17.49% | High-vol gana fuerte |
| 2026 | +0.226 | −9.03% | High-vol gana |
| **IC medio** | **+0.126** | | **High-vol sobre-performa** |

## 2. Interpretación honesta

- El **low-vol/defensivo funciona como SEGURO EN CAÍDAS**: en 2020 (crash covid), el high-vol cayó −26% mientras las defensas sobrevivieron.
- Pero en **mercados alcistas como 2023-2026**, el high-vol/growth sobre-performa de forma contundente (+0.10 a +0.31 de IC).
- **Conclusión:** usar low-vol como **factor de selección** NO mejora el momentum en este régimen alcista — el mercado premia al crecimiento.

## 3. Lección para el proyecto

El low-vol NO se usa como **señal de selección** (ique no aporta aquí). Pero la evidencia del 2020 (−26% para high-vol) refuerza la necesidad de **gestión de riesgo**, no de selección:
- En vez de "comprar low-vol", usamos la volatilidad como **control de exposición** (vol-targeting) sobre la cartera de momentum.
- Eso nos lleva al paso 5: **gestionar el momentum-crash reduciendo exposición cuando sube la volatilidad.**

## 4. Plan actualizado

| Paso | Estado | Resultado |
|---|---|---|
| 1. Hallazgo momentum | ✅ | IC OOS +0.066 |
| 2. Robustez | ✅ | Label-120 óptimo |
| 3. Backtest momentum | ✅ | +18.5%, Sharpe 0.96 |
| 4. Low-vol como selección | ❌ | No mejora en alcista |
| 5. **Gestión de riesgo (vol-targeting)** | ⏭️ | Siguiente: controlar exposición del momentum |

*Conclusión: no forzamos low-vol como señal. Pasamos a control de riesgo.*
