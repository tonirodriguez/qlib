---
tags: [literature, review, alpha-decay, quant-strategies, ml]
status: draft
---

# Alpha Decay in Quantitative Strategies — Revisión de Literatura

## Definición

El **alpha decay** (o erosión de alpha) es la pérdida progresiva de poder predictivo y rentabilidad de una estrategia cuantitativa a medida que:
- Más participantes la adoptan (crowding)
- El régimen de mercado cambia (non-stationarity)
- El modelo sobreajusta a patrones históricos que no se repiten

## Literatura clave

### 1. NBER W35273 (2026) — "The Growth and Performance of AI in Asset Management"
- **Hallazgo central**: El outperformance de hedge funds IA declinó con el tiempo.
- **Mecanismo**: Adopción generalizada → commoditización de señales → erosión de alpha.
- **Dato sorprendente**: Aun así, los fondos IA no están correlacionados entre sí.

### 2. Fan (2025) — "The Rise of AI Quantitative Investment Funds" (SSRN)
- Documenta cómo los fondos cuantitativos aplican deep learning y ML.
- Señala explícitamente el fenómeno de *alpha decay* como desafío central.
- **Cita textual**: "se volvieron ineficaces (conocido como 'Alpha decay')".

### 3. Jiang et al. (2025) — "Alpha-R1: Alpha Screening with LLM Reasoning via Reinforcement Learning"
- Aborda **signal decay** y **regime shifts** como desafíos recurrentes.
- Propuesta: usar razonamiento de LLMs + RL para factor screening, en lugar de depender solo de correlaciones históricas.
- **Relevancia**: Representa la siguiente ola — IA generativa + RL aplicada a descubrimiento de factores.

### 4. Makinde (2026) — "T-KAN for High-Frequency LOB Forecasting"
- T-KAN (Temporal Kolmogorov-Arnold Networks) para forecasting de limit order book.
- Aborda alpha decay explícitamente: "el alpha decay representa un desafío significativo, con modelos tradicionales como DeepLOB perdiendo poder predictivo a medida que el horizonte temporal (k) aumenta".
- Resultados: +19.1% F1, +132.48% return en backtests con costes.

### 5. Benhenda (2026) — "Look-Ahead-Bench"
- Benchmark para look-ahead bias en LLMs financieros.
- Distingue capacidad predictiva genuina de rendimiento basado en memorización.
- Crucial para entender si los LLMs realmente generalizan o solo memorizan patrones.

## Mecanismos de Alpha Decay

| Mecanismo | Descripción | Referencia |
|---|---|---|
| **Crowding** | Demasiados actores usando la misma señal | NBER 35273, Fan (2025) |
| **Non-stationarity** | El régimen de mercado cambia | Alpha-R1 (2025) |
| **Model degradation** | El poder predictivo decae con el horizonte temporal | T-KAN (2026) |
| **Look-ahead bias** | Sobreestimación del rendimiento por sesgo de futuros | Look-Ahead-Bench (2026) |
| **Overfitting** | El modelo captura ruido en lugar de señal | Literatura clásica |

## Implicaciones para qlib

- Los factores de alpha158 pueden estar sufriendo crowding/decay
- Estrategias de **ensemble dinámico** y **weight decay adaptativo** como posibles mitigaciones
- Incorporar detección de regime shifts en el pipeline
- Explorar RL + LLM para descubrimiento de factores (ej. Alpha-R1)
- Validar contra look-ahead bias sistemáticamente

## Pendiente

- [ ] Buscar papers sobre crowding measures en estrategias cuantitativas
- [ ] Literature sobre dynamic factor selection
- [ ] Papers de regime-switching models aplicados a ML para trading
