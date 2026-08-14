# SFM — State-Frequency Memory: Fundamentos Teóricos

## ¿Qué es SFM?

State-Frequency Memory (SFM) es una arquitectura de red neuronal recurrente que extiende las LSTM clásicas incorporando **descomposición en frecuencias** mediante una Transformada de Fourier interna. En lugar de mantener un único estado oculto, SFM descompone la dinámica temporal en $K$ componentes de frecuencia independientes, cada uno capturando un patrón de mercado subyacente (tendencias a largo plazo vs oscilaciones de alta frecuencia).

Es particularmente efectiva para series temporales financieras porque:
- La volatilidad financiera tiene estructura multiescala (intradía, diaria, semanal, mensual)
- SFM puede capturar patrones latentes de fluctuación en diferentes horizontes simultáneamente
- La descomposición frecuencial es más interpretable que un estado oculto LSTM opaco

## Motivación para Criptomonedas

Las criptomonedas presentan dinámicas de frecuencia muy distintas entre sí. Los activos seleccionados se agrupan en tres perfiles:

| Perfil | Activos | Comportamiento |
|--------|---------|----------------|
| **Alta capitalización** | Bitcoin, Ethereum | Frecuencias bajas dominantes (tendencias macro), menor ruido relativo |
| **Capas 1 rápidas** | Solana, Cardano | Frecuencias medias, reacción rápida a eventos técnicos |
| **Utilidad/pagos** | Stellar (XLM) | Correlación alta con BTC pero ráfagas de alta frecuencia aisladas |

## Componentes de Frecuencia ($K$)

El hiperparámetro clave del SFM es $K$, el número de componentes de frecuencia:

- **$K$ bajo** (4-8): captura tendencias macro pero omite micro-movimientos
- **$K$ medio** (10-16): balance recomendado para velas diarias
- **$K$ alto** (16+): riesgo de sobreajuste (overfitting) capturando ruido blanco

## Referencias

- [arXiV: AI-Driven Portfolio Optimization with Bitcoin](https://arxiv.org/html/2509.15040v1)
- [ResearchGate: Bitcoin price forecasting](https://www.researchgate.net/publication/355337221_Bitcoin_price_forecasting_A_perspective_of_underlying_blockchain_transactions)
- [MDPI: Mathematics of crypto forecasting](https://www.mdpi.com/2227-7390/14/10/1615)
- [UPM: Transformer vs LSTM en cripto](https://oa.upm.es/82874/)
