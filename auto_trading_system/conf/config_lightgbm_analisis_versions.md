# Comparativa LightGBM

Este documento resume los resultados de las cuatro configuraciones probadas:

- [config_lightgbm.yaml](/mnt/c/Users/toni/src/qlib/auto_trading_system/conf/config_lightgbm.yaml)
- [config_lightgbm_v2.yaml](/mnt/c/Users/toni/src/qlib/auto_trading_system/conf/config_lightgbm_v2.yaml)
- [config_lightgbm_improved.yaml](/mnt/c/Users/toni/src/qlib/auto_trading_system/conf/config_lightgbm_improved.yaml)
- [config_lightgbm_improved_v2.yaml](/mnt/c/Users/toni/src/qlib/auto_trading_system/conf/config_lightgbm_improved_v2.yaml)

Runs analizadas:

- base: [3c428c3c49d34ff89e84a6e1ea693e2f](/mnt/c/Users/toni/src/qlib/auto_trading_system/mlruns/172799653875555946/3c428c3c49d34ff89e84a6e1ea693e2f/meta.yaml)
- v2 actual: [2908b156afbc44f8bb7b1cce0b683843](/mnt/c/Users/toni/src/qlib/auto_trading_system/mlruns/172799653875555946/2908b156afbc44f8bb7b1cce0b683843/meta.yaml)
- improved: [c1109a58540d47e4937d2b1ad0aa8d1b](/mnt/c/Users/toni/src/qlib/auto_trading_system/mlruns/390309113018558731/c1109a58540d47e4937d2b1ad0aa8d1b/meta.yaml)
- improved_v2: [28d3429dddfb4af0b0acaa0c2ad2e538](/mnt/c/Users/toni/src/qlib/auto_trading_system/mlruns/133289539944255561/28d3429dddfb4af0b0acaa0c2ad2e538/meta.yaml)

**Veredicto**
Orden final:

1. `config_lightgbm_improved_v2`
2. `config_lightgbm_improved`
3. `config_lightgbm_v2`
4. `config_lightgbm`

Si el objetivo es seguir iterando o pasar a paper trading, la mejor base ahora mismo es `config_lightgbm_improved_v2.yaml`.

**Señal**
| Modelo | IC | ICIR | Rank IC | Rank ICIR | Corr(score,label) | Top10 mean | Top10 hit | Top30 mean | Bottom10 mean | Long-short 10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `config_lightgbm` | -0.000816 | -0.008901 | 0.001967 | 0.022249 | 0.002219 | -0.000121 | 0.5081 | 0.000622 | 0.001238 | -0.001359 |
| `config_lightgbm_v2` | 0.004182 | 0.048099 | 0.001804 | 0.023433 | 0.008923 | 0.000654 | 0.4984 | 0.000738 | 0.000388 | 0.000266 |
| `improved` | 0.006815 | 0.076099 | 0.008371 | 0.112996 | 0.013618 | 0.000740 | 0.5168 | 0.000692 | 0.000045 | 0.000695 |
| `improved_v2` | 0.006111 | 0.046904 | 0.008139 | 0.073004 | 0.010490 | 0.001640 | 0.5323 | 0.001212 | 0.001058 | 0.000582 |

Lectura rápida:

- `config_lightgbm` tiene una señal casi nula y un top 10 peor que el universo.
- `config_lightgbm_v2` mejora claramente a la base, pero sigue lejos de las versiones `improved` en calidad de ranking y consistencia del top 10.
- `improved` mejora claramente la calidad del ranking.
- `improved_v2` pierde algo de pureza estadística frente a `improved`, pero mejora la parte más operativa: mejor top 10 y mejor tasa de acierto.

**Backtest**
Solo `improved` y `improved_v2` incluyen `PortAnaRecord`.

| Modelo | Retorno anual sin costes | IR sin costes | MDD sin costes | Retorno anual con costes | IR con costes | MDD con costes | Long-Short Ann Return | Long-Short Ann Sharpe |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `improved` | 0.083567 | 0.780077 | -0.117431 | -0.064480 | -0.601645 | -0.197359 | 0.044806 | 1.346110 |
| `improved_v2` | 0.171977 | 1.333898 | -0.083366 | 0.122439 | 0.948367 | -0.117533 | 0.004256 | 0.081521 |

Lectura rápida:

- `improved` parece razonable sin costes, pero al meter costes pasa a negativo.
- `improved_v2` es la primera que conserva edge neto tras costes.
- `improved_v2` también reduce drawdown frente a `improved`.
- `config_lightgbm_v2` no tiene backtest en este run, así que hoy solo puede compararse por calidad de señal.

**Overfitting**
Comportamiento de `l2.valid`:

- `config_lightgbm`: mejor valor en el paso `0`
- `config_lightgbm_v2`: mejor valor en el paso `0`
- `improved`: mejor valor en el paso `0`
- `improved_v2`: mejor valor en el paso `31`

Eso refuerza que `improved_v2` está menos sobreajustada que el resto, mientras que `config_lightgbm_v2` todavía se comporta más como la base que como la mejor versión.

**Conclusión**

- `config_lightgbm` queda descartada.
- `config_lightgbm_v2` es un paso adelante frente a la base, pero no aporta una mejora suficiente como para desbancar a `config_lightgbm_improved`.
- `config_lightgbm_improved` sirve para demostrar mejora de señal, pero no sobrevive a costes.
- `config_lightgbm_improved_v2` es la mejor combinación actual entre señal, robustez y resultados netos.
