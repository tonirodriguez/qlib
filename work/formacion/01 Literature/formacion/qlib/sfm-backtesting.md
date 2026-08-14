# SFM — Evaluación y Backtesting

## Estrategia de trading: Top-1

La estrategia selecciona cada día el activo con mayor retorno predicho según el modelo SFM:

```python
best_asset_idx = np.argmax(predicted_returns, axis=1)
strategy_daily_returns = np.array([real_returns[t, best_asset_idx[t]]
                                   for t in range(len(best_asset_idx))])
strategy_daily_returns -= 0.001  # comisión 0.1%
```

## Benchmark

El benchmark es un **hold equitativo** (promedio simple de retornos de todos los activos):

```python
benchmark_returns = np.mean(real_returns, axis=1)
```

## Curva de Equity

```python
equity_strategy = np.cumprod(1 + strategy_daily_returns)
equity_benchmark = np.cumprod(1 + benchmark_returns)
```

## Métricas

### Precisión direccional

```python
accuracy = np.mean((preds > 0) == (real_returns > 0))
```

Mide el % de veces que el modelo acierta la dirección (sube/baja), independientemente de la magnitud.

### Sharpe Ratio (aproximado)

```python
sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252)
```

### MAPE

```python
from sklearn.metrics import mean_absolute_percentage_error
mape = mean_absolute_percentage_error(real_prices, predicted_prices)
```

El MAPE es la métrica recomendada para comparar multivariable vs univariable porque evita el sesgo de escala.

## Backtesting con Gestión de Riesgo (SL/TP)

Versión avanzada que evalúa velas completas (open, high, low, close):

| Parámetro | Valor típico |
|-----------|-------------|
| Stop Loss | −3% |
| Take Profit | +6% |
| Comisión | 0.1% por orden |

## Backtesting con Qlib (métricas institucionales)

```python
from qlib.contrib.strategy import TopkDropoutStrategy
from qlib.contrib.evaluate import backtest, risk_analysis

strategy = TopkDropoutStrategy(signal=predictions, topk=2, n_drop=1)
portfolio, benchmark = backtest(
    strategy=strategy,
    start_time="2025-07-01",
    end_time="2026-06-01",
    account=1000000,
    freq="day",
    open_cost=0.001,
    close_cost=0.001
)

report = risk_analysis(portfolio, benchmark)
```

Métricas que produce:

| Métrica | Descripción |
|---------|-------------|
| **Retorno anualizado** | Rendimiento compuesto anual |
| **Volatilidad anualizada** | Desviación estándar anual de retornos |
| **Sharpe Ratio** | Retorno por unidad de riesgo (>1.5 excelente) |
| **Information Ratio** | Exceso sobre benchmark (>0.5 consistente) |
| **Max Drawdown** | Peor caída desde máximo histórico |

## Interpretación

- **Sharpe > 1.5**: el SFM extrae ganancias sólidas compensando la volatilidad crypto
- **Sharpe < 1.0**: el modelo asume demasiado riesgo por unidad de beneficio
- **IR alto**: la transformada de Fourier interna captura frecuencias cíclicas reales
- **Drawdown controlado**: la diversificación (top-K) reduce caídas vs activos individuales

## Archivos relacionados

- `scripts/crypto/qlib_sfm_pipeline_grafica.py`
- `scripts/crypto/rendimiento_modelo_sfm.png`
