# ⚡ Estrategia de Eventos PEAD — Resultado validación (2026-08-22)

## Configuración del test
- Entrada: 2 días tras el anuncio
- Hold: 20 días
- Umbral sorpresa: ≥ +5%
- Fuente: yahooquery (earnings) + Qlib (precios)

## Resultado (61 operaciones)

| Métrica | Valor |
|---|---|
| Retorno medio | +1.02% |
| Retorno mediano | −0.47% |
| % positivas | 49.2% |
| Sharpe (evento) | 0.10 |
| Mejor operación | +46.2% |
| Peor operación | −21.7% |
| IC Spearman (dentro de entradas) | +0.15 |

## Interpretación honesta

**Resultado MIXTO:**

1. **Positivo pero frágil:** retorno medio +1.02% impulsado por **pocas operaciones grandes** (+46%), no por consistencia (mediana negativa, 49% acierto).
2. **El IC de ranking persiste (+0.15)** — la sorpresa sigue siendo informativa entre las entradas.
3. **Typical del PEAD en megacaps:** mucha varianza, cola negativa real (−21%), y el retorno medio se reduce con costes.

## Conclusión

**La señal PEAD es REAL (IC 0.15-0.22 positivo), pero como estrategia de eventos binaria (comprar toda sorpresa >5%) es solo marginalmente rentable** (+1% por evento, 49% acierto).

**El valor real está en USARLA COMO REFUERZO, no como señal única:**
- Combinar con momentum (entrar solo cuando hay alto surprise Y buen momentum)
- Ponderar por la magnitud de la sorpresa (más tamaño en sorpresas muy altas)
- Mejorar con más histórico y gestión de riesgo de cola

*Script: `work/estrategias/pead_eventos.py`*
