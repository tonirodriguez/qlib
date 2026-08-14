# 🎯 Plan Post-Paper-Trading + PEAD (Earnings Momentum) + Datos Fundamentales

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — progresión de la estrategia momentum 120d
> **Contexto:** el momentum 120d sobre sp500_liquid ya superó el backtest (IC OOS +0.066, +21.7% anual, Sharpe 1.07) y está en simulación paper-trading con €20,000 ficticios (rebalanceo semanal vía cronjobs del sábado).

---

## 1. Plan Post-Paper-Trading (progresión del momentum)

**Principio de Quinn:** la estrategia solo es "real" si lo que se observa en vivo **confirma lo que el backtest predecía** (falsabilidad). El paper-trading es la fase intermedia que valida el edge antes de tocar dinero real.

### 1.1 Durante el paper-trading (meses 1-2) — acumular evidencia
Cada semana (el cronjob del sábado 15:00 ya lo hace), registrar:
- **IC / long-short en vivo** vs el IC OOS esperado (0.066)
- **Retorno y drawdown en vivo** vs backtest (+21.7% anual, DD −18.6%)
- **Costes reales** (IB ~0.1% round-trip) — ¿se comen el alpha o no?

### 1.2 Mes 2 — comparar paper vs backtest
| Pregunta | Si confirma | Si degrada |
|---|---|---|
| ¿El IC en vivo se sostiene (~0.05-0.07)? | → Avanzar | → Volver a investigación |
| ¿El drawdown estuvo contenido (<25%)? | → Avanzar | → Revisar gestión de riesgo |
| ¿Los costes no destruyen el edge? | → Avanzar | → Reducir rotación |

**Regla de oro:** NO pasar a dinero real hasta que el paper-trading confirme el backtest durante al menos 2 ciclos.

### 1.3 Si el paper confirma — escalado gradual (DISCIPLINADO)
1. **Empezar pequeño** — fracción del capital (10-20%), NO todo
2. **Monitorizar "thesis breakers"** — si IC cae sostenidamente hacia 0 o drawdown supera lo esperado → **reducir/parar**
3. **Respetar el límite de breadth** — Quinn: esperar IR 0.5-0.7, NO >1 sostenido en universo concentrado

### 1.4 Si el paper degrada — vuelta a investigación
- Revisar si el edge era overfitting del periodo 2023-2026
- Probar universos más amplios, otros horizontes, otras señales
- Opción final honesta: **cartera de índice/calidad + gestión de riesgo**

### 1.5 Mejora de segundo grado (mientras paper valida o tras confirmar)
- **Añadir PEAD/Earnings revision** como señal ortogonal (sube IC/Sharpe)
- **Quality/profitability como filtro** (evita "momentum de la peor empresa")
- **Low-vol/beta como escala de riesgo** (ya tenemos vol-targeting)

---

## 2. PEAD (Post-Earnings Announcement Drift) — Descripción

### 2.1 Qué es
> Cuando una empresa anuncia resultados **sorprendentemente** buenos o malos, el precio sigue "derivando" (drifting) en esa dirección durante semanas/meses después del anuncio.

Si una empresa supera el EPS esperado, la acción no sube todo de golpe el día del anuncio — sigue subiendo gradualmente 60-90 días. Ese arrastre es el PEAD, explotable comprando tras un anuncio positivo.

### 2.2 Evidencia
- **Bernard & Thomas (1989)** — paper fundacional; el PEAD persiste y es difícil de arbitrar.
- **Chan, Jegadeesh & Lakonishok (1996)** — conectan PEAD con el momentum general.

### 2.3 La medida clave: SUE (Standardized Unexpected Earnings)
```
SUE = (EPS_real − EPS_consenso) / desviación histórica del error
```
- **SUE alto (+)** = resultados mucho mejores de lo esperado → drift alcista
- **SUE bajo (−)** = peores → drift bajista

### 2.4 Por qué es ORTOGONAL al momentum (valioso)
| Señal | Capta | Correlación |
|---|---|---|
| Momentum (tu actual) | Tendencia de precio | — |
| **PEAD** | Información fundamental (EPS) | **Baja** → ortogonal ✓ |

Combinar z(momentum) + λ·z(PEAD) sube IC y Sharpe, porque son señales casi independientes (Chan-Jegadeesh-Lakonishok 1996).

### 2.5 Matiz honesto (megacaps)
En empresas **muy cubiertas** (como las del S&P500), el PEAD puro es **más débil** — el mercado ya sabe casi todo. Lo que SÍ es potente en grandes empresas es el **Earnings Revision**: cuando los analistas **suben/bajan estimaciones** futuras. Esa señal precede al movimiento.

---

## 3. Cómo conseguir los datos fundamentales (para Qlib)

### 3.1 Qué datos necesitas
Para PEAD/SUE necesitas:
1. **EPS real** (por trimestre)
2. **Consenso de EPS** (lo que esperan los analistas)
3. **Fecha del anuncio** (para el día del "evento")
4. **(Recomendado)** Revisiones de estimaciones de analistas
5. **(Opcional para quality)** ROE, gross margin, book value

### 3.2 Fuentes posibles
| Fuente | Qué da | Coste | Notas |
|---|---|---|---|
| **Yahoo Finance API** | EPS, earnings dates | Gratis | Rate-limit (ya lo vimos); peticiones puntuales |
| **Interactive Brokers API** | EPS est, datos fundamentales | Requiere cuenta/API | El broker que ya usas; paper trading disponible |
| **yfinance / yahooquery** (pip) | Earnings calendar, EPS | Gratis | Limitado por rate-limit de Yahoo |
| **stockanalysis.com** | EPS por trimestre | Gratis | Via web scraping (frágil) |
| **FMP / Alpha Vantage / Polygon** | Datos fundamentales completos | API key | Servicios de pago con buenos datos |

### 3.3 Cómo integrarlo en Qlib (el método correcto)
Qlib/Alpha158 **solo trabaja con OHLCV**. Los datos fundamentales se añaden como **columnas nuevas**:

1. **Conseguir los datos**: descargar EPS real, consenso, y fechas de anuncio por ticker (de la fuente elegida)
2. **Preparar los CSV**: añadir columnas `eps`, `eps_consensus`, `sue`, `earnings_date` al CSV junto con OHLCV
3. **Re-dump a formato Qlib**: usar `scripts/dump_bin.py` para convertir el CSV enriquecido al formato binario de Qlib
4. **Calcular SUE** como `factor`: `(eps − eps_consensus) / std_error` en el handler
5. **Usar la señal** en el ranking, junto al momentum

**Alternativa rápida para testear:** usar `DataHandlerLP` con expresiones `factor` propias o field expressions, sin re-dump completo.

### 3.4 Pasos prácticos recomendados (para TI)
**Fase A (test rápido, sin integración):** conseguir EPS/consenso de ~30 tickers del topk actual, calcular SUE, y ver su IC contra retorno futuro. Si el IC es positivo → vale la pena integrarlo.
**Fase B (integración completa):** añadir las columnas al CSV y re-dump a Qlib para usarlo en el backtest/walk-forward.

---

## 4. Resumen de decisión

| Fase | Cuándo | Acción |
|---|---|---|
| 1. Paper-trading | Ahora (2 meses) | Registrar si el edge se sostiene en vivo |
| 2. Fase A PEAD (test IC) | Tras validar momentum | EPS/consenso de ~30 tickers → IC de SUE |
| 3. Integración Qlib | Si el IC de SUE es positivo | Añadir columnas y re-dump |
| 4. Combinar momentum+PEAD | Confirmado | z(momentum)+λ·z(SUE) → walk-forward |

**Regla de oro:** NO implementar PEAD antes de que el paper-trading valide la señal principal (momentum). Es una mejora de segundo grado sobre una base que primero hay que confirmar.

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada avance.*
