# 💵 Decisión — Histórico de earnings: fuentes gratuitas vs pago

> **Fecha:** 2026-08-23
> **Proyecto:** Qlib Work
> **Contexto:** Prioridad 1 de Quinn (quinn_ahora.md) — extender historia de earnings para robustecer la validación del PEAD-núcleo (E3).

---

## 1. El problema

El **PEAD necesita por trimestre**: (1) EPS real, (2) EPS estimado/consenso, (3) **fecha de anuncio** (crítica para point-in-time y medir el retorno post-anuncio).

**Las fuentes gratuitas no cubren los 3 con profundidad histórica:**

| Fuente | EPS real | EPS est. | Fecha anuncio | Histórico |
|---|---|---|---|---|
| **yahooquery** | ✅ | ✅ | ✅ | ❌ solo ~1 año (4 trimestres) |
| **stockanalysis** (financials) | ✅ | ❌ | ❌ | ✅ varios años, pero incompleto |
| **stockanalysis** (earnings) | ❌ | solo próximo | ❌ | ❌ solo próximo anuncio |

**Conclusión:** ampliar el histórico de earnings **de forma point-in-time limpia** (con fecha de anuncio + sorpresa) **no es viable con fuentes gratuitas** — las que lo dan son APIs de pago.

## 2. Coste de las opciones de pago

| Proveedor | Plan mín. | Precio/mes | Histórico earnings |
|---|---|---|---|
| **FMP** (fundamentals-first) | Starter | **$29/mes** (~$14-20/mes anual) | ✅ 10+ años |
| **Alpha Vantage** | Premium | **$49.99/mes** | ✅ amplio |
| **Polygon** | Starter | **$29/mes** | ✅ amplio |
| **TIingo** | — | ~$25-49/mes | ✅ amplio |
| **Twelve Data** | Grow | **$79/mes** | ✅ amplio |

*Precios orientativos 2026. La más adecuada para earnings/fundamentals es FMP ($29/mes).*

## 3. DECISIÓN (tomada 23-08-2026)

**NO contratar fuente de pago ahora.**

**Razones:**
1. **La validación actual es suficiente** para el paper-trading y la S8: PEAD-núcleo validado con ~1 año real (yahooquery) y **el purged CV ya confirmó que se sostiene** (IC +0.085 a +0.130).
2. **La S8** (en ~2 meses) dará dato REAL de si el PEAD-núcleo funciona en vivo — no necesitamos pagar para saberlo.
3. Coherente con la disciplina de Quinn: **no gastar en fuentes de datos antes de que la señal se valide** en el lab/paper.

**Cuándo SÍ valdría pagar (FMP $29/mes):**
- Si en la **S8 el PEAD se confirma en vivo**, y
- Estás considerando **escalar a capital real**
- → entonces el histórico largo de earnings justifica el coste para robustecer la validación ANTES de arriesgar dinero real.

## 4. Riesgo residual aceptado

El PEAD-núcleo reposa en ~1 año real de anuncios de earnings. Con el purged CV que lo sostiene es aceptable para paper. **El riesgo se cubre con disciplina**: E3 en paper, y la S8 lo confirmará con dato real. Si en la S8 el PEAD se degrada, se actuará entonces (no antes, no con gasto).

---

*Documento de decisión del proyecto Qlib Work. Complementa `quinn_ahora.md` (Prioridad 1).*
