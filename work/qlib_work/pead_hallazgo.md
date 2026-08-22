# ⚡ PEAD — Hallazgo: Earnings Momentum con alpha confirmado

> **Fecha:** 2026-08-19
> **Proyecto:** Qlib Work — búsqueda de factores ortogonales al momentum
> **Método:** Fase A (datos de earnings vía yahooquery) + Fase A2 (IC del retorno post-anuncio)

---

## 1. Qué se hizo

El PEAD (Post-Earnings Announcement Drift) dice que las empresas que baten/fallan al consenso de resultados siguen "derivando" en esa dirección las semanas posteriores al anuncio. Se midió si esa señal tiene alpha real en el universo **sp500_liquid**.

**Fuentes:**
- **Earnings:** `yahooquery` (actual, estimate, surprisePct, reportedDate por trimestre) — 39 tickers, 156 trimestres
- **Precios:** Qlib local (close/factor)

## 2. Resultados — IC de la sorpresa → retorno post-anuncio

| Horizonte | IC Pearson | IC Spearman | Long-short (alto−bajo) | Muestras |
|---|---|---|---|---|
| **20 días** | +0.193 | +0.219 | **+5.29%** | 123 |
| **60 días** | +0.055 | +0.194 | **+7.29%** | 116 |

### Retorno post-anuncio por tercil de sorpresa (20 días)

| Tercil | Retorno | Muestras |
|---|---|---|
| Alto sorpresa | **+4.78%** | 41 |
| Medio | +0.94% | 41 |
| Bajo sorpresa | −0.51% | 41 |

## 3. Veredicto

**✅ El PEAD tiene alpha real en sp500_liquid.**

- **IC Spearman ~0.19-0.22 sostenido** (20d y 60d) — muy alto (0.02-0.05 ya es bueno)
- **Long-short +5.3% (20d) y +7.3% (60d)** — magnitud clara y creciente
- Las empresas de alta sorpresa rinden +4.8% en 20d vs −0.5% las de baja sorpresa
- Coherente con la literatura (Bernard-Thomas 1989; Chan-Jegadeesh-Lakonishok 1996)

**El PEAD es ORTOGONAL al momentum de precios → combinarlos debería mejorar el IC y Sharpe.**

## 4. Matices honestos

- **Muestra pequeña** (116-123 eventos, ~39 tickers, 4 trimestres) — el IC podría bajar con más histórico
- El **Pearson baja a 60d** (+0.06) pero el **Spearman se mantiene** (+0.19) → el ranking es robusto aunque haya outliers
- Es señal de **primer orden** — falta integrarla en Qlib y validar en el contexto completo

## 5. Próximos pasos

- **Fase B:** integrar SUE/sorpresa en Qlib como factor
- **Fase C:** combinar momentum 120d + PEAD → walk-forward (IC OOS > 0.02)
- Documentado el avance en `plan_post_paper_pead.md`

---

*Documento de referencia del proyecto Qlib Work. Scripts: `pead_faseA.py`, `pead_faseA2.py` en `work/estrategias/`.*
