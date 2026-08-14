---
tags: [literature, hedge-funds, strategies, quant, macro]
status: draft
---

# Estrategias de Hedge Funds (2025–2026)

## Panorama general

Basado en observaciones de mercado, informes sectoriales y literatura reciente.

## Principales estrategias en uso

### 1. Multi-Strategy / Multi-Manager
- **Descripción**: Plataformas que agrupan múltiples estrategias ( equity long/short, macro, systematic, event-driven) bajo un mismo paraguas.
- **Ejemplos**: Citadel, Millennium, D.E. Shaw, Point72.
- **Tendencia**: Siguen dominando en captación de capital. Los inversores buscan diversificación de riesgos.

### 2. Quant Equity / Statistical Arbitrage
- **Tradicional**: Factor investing (value, momentum, carry, low vol) con models ML para weighting dinámico.
- **Nueva ola**: Uso de **datos alternativos** (satélite, web scraping, transacciones con tarjetas, sentimiento de redes sociales).
- **Problema**: Los factores clásicos están comprimidos (crowding). Los fondos compiten por datos propietarios.

### 3. AI / Machine Learning Systematic
- Uso extensivo de deep learning (transformers, LSTM, GNNs) para:
  - Forecasting de retornos a corto plazo
  - Procesamiento de LOB (limit order book)
  - Análisis de sentimiento con NLP
- **Novedad 2025-2026**: Incorporación de **LLMs** y **reinforcement learning** para:
  - Descubrimiento de factores (Alpha-R1)
  - Toma de decisiones contextual (razonamiento macro + señales técnicas)
- **Advertencia**: Según NBER W35273, la ventaja de los fondos IA se ha erosionado significativamente.

### 4. Global Macro (Discrecional + Sistemático)
- **Discrecional**: Estrategias basadas en opinión fundamental sobre tipos, divisas, materias primas.
- **Sistemático**: Modelos trend-following (CTA clásicos) con ML para detectar regímenes.
- **Contexto 2026**: Alta volatilidad geopolítica (EEUU-Irán, fragmentación comercial) está beneficiando a macro funds.

### 5. Event-Driven / Special Situations
- M&A arbitrage, distressed debt, activism.
- **2025-2026**: Aumento de actividad en M&A tecnológico.

### 6. Alternative Risk Premia (Factor Investing 2.0)
- Versión avanzada de risk premia con weighting dinámico y machine learning para:
  - Timing de factores
  - Combinación óptima (risk parity + ML)
- **Problema**: La "solución del 6%" (alpha fácil con factor timing IA) ha desaparecido (MarketWatch, Jun 2026).

## ¿Qué está funcionando?

Según reports de HFRI, Preqin y observaciones de mercado:

| Estrategia | Performance relativa 2025-2026 | Notas |
|---|---|---|
| Multi-strat | ✅ Alto, estable | Los mega-funds siguen capturando la mayor parte del capital |
| CTA / Macro sistemático | ✅ Alto | Beneficiado por volatilidad geopolítica y tendencias |
| Quant equity (alt data) | ✅ Medio-alto | Depende de calidad de datos propietarios |
| Quant equity (factores clásicos) | ⚠️ Medio-bajo | Erosión por crowding |
| AI/ML systematic | ⚠️ Declinante | El alpha ML se ha commoditizado (NBER 35273) |
| Event-driven | ✅ Medio | Depende de pipeline de M&A |

## Innovaciones emergentes

1. **LLMs + RL para descubrimiento de factores** (Alpha-R1, Jiang et al. 2025)
2. **Temporal KAN para forecasting de LOB** (Makinde 2026)
3. **Point-in-time benchmarks** para evitar look-ahead bias (Look-Ahead-Bench, Benhenda 2026)
4. **Fondos que usan proprietary LLMs** entrenados con sus propios datos de trading
5. **Estrategias híbridas** (combinan señales de ML con razonamiento macro de LLMs)

## Implicaciones para qlib

- **No depender solo de factores alfa158 clásicos** — pueden estar sufriendo crowding
- Explorar **dynamic factor selection** con detección de régimen
- Considerar **modelos temporales avanzados** (T-KAN, transformers) para forecasting
- **Validación rigurosa contra look-ahead bias** usando principios de point-in-time
- Las **estrategias multi-estrategia** (combinar varios modelos/features) parecen más robustas

## Pendiente

- [ ] Buscar datos concretos de AUM por estrategia 2025-2026 (Preqin, HFRI)
- [ ] Investigar crowding measures para el universo de factores chinos (CSI300)
- [ ] Analizar estrategias de market-making algorítmico
