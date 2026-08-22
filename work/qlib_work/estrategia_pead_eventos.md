# ⚡ Estrategia de Eventos PEAD — Cómo operar el Earnings Momentum

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Base:** PEAD con alpha confirmado (IC Spearman 0.19-0.22, long-short +5-7% tras el anuncio)

---

## 1. Qué es operar "por eventos"

En lugar de tener una posición continua, una estrategia de **eventos PEAD** concentra la operativa **alrededor de los anuncios de resultados**:
1. Esperas a que una empresa **anuncie resultados** (4 veces al año por empresa)
2. Si la **sorpresa es positiva** (bate claramente al consenso) → **compras** tras el anuncio
3. Mantienes la posición de **20-60 días** (el "drift" o deriva post-anuncio)
4. Si la sorpresa es negativa → evitas/shorteas

**Clave:** aprovechas el *drift* documentado (la sorpresa no se incorpora toda de golpe, sigue "moviendo" el precio semanas después).

---

## 2. Cómo seleccionar las entradas

### La señal: SUE (Standardized Unexpected Earnings)
```
SUE = (EPS_real − EPS_consenso) / desviación histórica del error de estimación
```

Para simplificar con los datos que tenemos, usamos el **surprise%**:
```
surprise% = (EPS_real / EPS_estimado − 1) × 100
```

### Reglas de entrada (regla de oro del drift)
| Condición | Acción |
|---|---|
| **Sorpresa muy positiva** (> +5-10%) | **Comprar** tras el anuncio |
| Sorpresa positiva moderada (+1-5%) | Comprar con tamaño menor |
| Sorpresa ≈ 0 | No operar |
| Sorpresa negativa (< −1%) | Evitar / short (según apetito de riesgo) |

**Momentum del mercado:** como refuerzo, solo operar el lado largo si la acción ya tiene momentum de precio (combina bien con nuestra señal base).

---

## 3. Cuándo entrar y salir

| Fase | Timing | Acción |
|---|---|---|
| **Evento** | Día del anuncio (reporte) | Detectar la sorpresa del EPS |
| **Entrada** | 1-3 días tras el anuncio | Comprar si la sorpresa es positiva (la mejor señal ya ha salido) |
| **Mantenimiento** | 20-60 días | Aprovechar el drift (hemos medido +5% a 20d, +7% a 60d en alto surprise) |
| **Salida** | Antes del siguiente anuncio o al vencimiento del drift | Realizar la ganancia |

**Única trampa:** evitar operar en la **semana previa al siguiente anuncio** (volatilidad por expectativas).

---

## 4. Ejemplo concreto (con nuestros datos)

Imagina que **AAPL** anuncia un trimestre y:
- EPS real = $2.02 vs estimado $1.89 → **surprise +6.9%**

Según el estudio:
- **Alto surprise** → retorno post-anuncio medio **+4.8% en 20 días**
- Acción: comprar 1-3 días tras el anuncio, mantener 20-60 días, salir antes del próximo reporte

**Si la sorpresa es +6.9% pero la acción además tiene momentum 120d positivo** → señal doble, convicción alta.

---

## 5. Tamaño de posición (sizing)

- **Sorpresa muy alta** (> +10%) → tamaño pleno (convicción alta)
- **Sorpresa moderada** (+3-10%) → tamaño 50-70%
- **Sorpresa baja/negativa** → no operar el lado largo

**Gestión de riesgo:** cada posición es un evento limitado en el tiempo → riesgo acotado a esas 20-60 días. Usar un **stop** (ej. −5%) para cortar si el drift no se da.

---

## 6. Cómo encaja con la estrategia momentum

| Estrategia | Tipo | Horizonte |
|---|---|---|
| **Momentum 120d** | Continua (topk 30, semanal) | Medio plazo |
| **PEAD eventos** | Por éxito (alrededor de anuncios) | 20-60 días |

**Son complementarias:** el momentum te tiene **siempre posicionado** en tendencias; el PEAD captura **oportunidades puntuales** de alta convicción cuando una empresa sorprende. Combinadas no se pisan (señales distintas) y diversifican el alpha.

---

## 7. Plan de implementación en Qlib

**Fase B (integración real) — pasos concretos:**
1. Crear un **DataHandler** que aporte la columna `sue`/`surprise` por ticker-fecha
2. Calendario de anuncios: añadir la fecha del próximo reporte de cada ticker
3. Generar la señal: en cada fecha de anuncio, calcular surprise y marcar las entradas
4. Backtest con la estrategia: comprar tras anuncio positivo, mantener 20-60d
5. Validar con walk-forward (IC OOS > 0.02) y comparar vs momentum solo

**Fuentes ya resueltas:**
- `yahooquery` → earnings (actual, estimate, surprisePct, reportedDate)
- Qlib → precios para el drift

---

## 8. Criterio de éxito

Confirmar la estrategia PEAD *solo* y *combinada* mejora el **Sharpe** vs el momentum solo, con **walk-forward IC OOS > 0.02**.

---

## 9. Riesgos y honestidad

- El **PEAD es más débil en megacaps muy cubiertas** (el mercado ya sabe casi todo) — suele ser más fuerte en empresas menos seguidas.
- El **forward-fill** de la sorpresa entre trimestres aligera la señal (lo vimos en la Fase C) — por eso la estrategia de **eventos reales** (operar en el momento del anuncio) es más fiel.
- **Muestra limitada** (solo ~2 años de earnings en nuestros datos) — validar con más histórico.
- El drift es **más fuerte a corto plazo** (20d) que a largo — capturar pronto el efecto.

---

*Documento de referencia del proyecto Qlib Work. Complementa `pead_hallazgo.md` y `pead_faseC.md`.*
