# 📊 Los 3 KPI de Estado de Mercado (regimones)

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Script fuente:** `extract_estados.py`
> **Salida:** `estados_mercado.csv`
> **Propósito:** Medir el régimen de mercado para luego demostrar (o descartar) la dependencia de régimen del momentum.

---

## 🎯 Por qué 3 KPI

Tras el purged CV (momentum NO robusto, régimen-dependiente) necesitamos **medir el régimen de mercado de forma objetiva** para:

1. **Condicionar el IC del momentum por estado** (¿funciona en "calma" pero no en "estrés"?)
2. **Demostrar la dependencia de régimen con rigor** (semana 3-4 del plan)
3. **Alimentar un posible vol-gating** (semana 5-6)

Los 3 KPI capturan aspectos **complementarios** del régimen: volatilidad, tendencia y reversión extremo.

---

## KPI 1 — `vol_pct` (Percentil de volatilidad)

**Qué mide:** en qué percentil está la **volatilidad realizada a 20 días** del mercado (desv. anualizada de retornos diarios) respecto a su propia historia rolante de 252 días.

**Fórmula:**
```
vol_20d = std(retornos diarios, ventana 20d) × √252   (anualizada)
vol_pct = percentil de vol_20d dentro de la ventana de 252 días
```

**Interpretación:**
| vol_pct | Régimen |
|---|---|
| < 0.25 | Calma (vol baja) |
| 0.25 - 0.75 | Normal |
| 0.75 - 0.90 | Tensión (vol alta) |
| > 0.90 | Estrés (vol muy alta) |

**Clave:** la volatilidad es un **proxy de estrés sin lag de estado** (contemporánea) → el mejor "detector" simple de régimen. Es la base del vol-gating.

---

## KPI 2 — `drawdown120` (Mercado en drawdown)

**Qué mide:** si el mercado está en **tendencia bajista de 120 días** (retorno del índice a 120 días < 0).

**Fórmula:**
```
ret_120d = precio_hoy / precio_hace_120_días − 1
drawdown120 = 1 si ret_120d < 0, si no 0
```

**Interpretación:**
- `drawdown120 = 1` → mercado en drawdown (fase bajista/corrección)
- `drawdown120 = 0` → mercado en alza

**Clave:** captura el **régimen de tendencia** (complementa a la vol). El momentum crash clásico ocurre en mercados bajistas.

---

## KPI 3 — `mom_crash` (Indicador de momentum-crash)

**Qué mide:** si los **perdedores** (decil inferior por momentum) rinden **más** que los **ganadores** (decil superior) — la firma del momentum-crash (Daniel-Moskowitz).

**Fórmula:**
```
cross_ret = retorno a 120 días de cada ticker del universo
por fecha:
  perdedores = media de retorno del decil inferior (pct ≤ 0.1)
  ganadores  = media de retorno del decil superior (pct ≥ 0.9)
  mom_crash  = 1 si perdedores > ganadores, si no 0
```

**Interpretación:**
- `mom_crash = 1` → el momentum está fallando bruscamente (los que caen rebotan más que los ganadores)
- `mom_crash = 0` → el momentum funciona normalmente

---

## 📍 Hallazgo honesto (2026-08-22)

| KPI | Estado | Valor |
|---|---|---|
| `vol_pct` | ✅ Operativo | 0.17-0.75 típico (percentil) |
| `drawdown120` | ✅ Operativo | 510 días en drawdown (1,506 en alza) |
| `mom_crash` | ⚠️ Raro | Todo 0 en sp500_liquid a 120d |

**`mom_crash` casi nunca se activa** en sp500_liquid con retornos a 120 días (incluso en 2020-2022 los perdedores caen más que rebotan los ganadores). **No es un bug**: es una condición de reversión profunda infrecuente en este universo. Para el análisis de régimen, **`vol_pct` y `drawdown120` son la base principal**; `mom_crash` se mantiene como señal de alarma extrema (cuando se active, atención).

---

## 🎯 Cómo se usarán los 3 KPI

En `regimen_test.py` (semana 3-4):
- **IC del momentum condicionado por estado**: IC dentro de cada valor de los KPI (ej. IC cuando `vol_pct > 0.75` vs `vol_pct < 0.75`), con CI bootstrap.
- **Regresión de interacción**: `IC_momentum ~ mercado + I(vol alta) + mom_crash` para ver si el estado modula el IC significativamente.
- **Contraste régimen vs decaimiento**: separar si el IC cae por el régimen (KPI) o por el tiempo (decaimiento secular).

---

*Documento de referencia del proyecto Qlib Work. Complementa `plan_E3_quinn_futuro.md` (Semana 2).*
