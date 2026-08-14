# Research dashboard

Vista rápida del estado experimental y metodológico del proyecto `qlib`.

## Baseline actual

### Referencia principal

- **Variante:** `Alpha158 + csi300 (label 5d)`
- **Experiment ID:** `641902479728835995`
- **Run ID:** `f47322850f1b4db3b0fedaf66738ecb5`
- **Ann. return with cost:** `0.1620`
- **IR with cost:** `2.1507`
- **Max drawdown with cost:** `-0.0780`

### Por qué sigue siendo la referencia

- mejor equilibrio entre retorno, `IR` y drawdown según el ranking compuesto
- punto de comparación limpio para nuevas pruebas
- evita elegir ganador solo por una métrica aislada

## Mejor variante por retorno anualizado con costes

- **Variante:** `Alpha158 + csi300 (label 5d)`
- **Experiment ID:** `641902479728835995`
- **Run ID:** `f47322850f1b4db3b0fedaf66738ecb5`
- **Annualized return with cost:** `0.1620`
- **IR with cost:** `2.1507`
- **Max drawdown with cost:** `-0.0780`

## Tradeoff principal detectado

> el mejor run actual también es el más equilibrado; merece la pena explorar mejoras pequeñas y controladas.

## Hipótesis mejor apoyadas ahora mismo

- mejorar `IC` no implica automáticamente mejor PnL
- la capa de portfolio puede desbloquear edge latente
- más concentración puede aumentar retorno y empeorar robustez

## Próximo foco recomendado

### Prioridad 1

**Explorar weighting / sizing sobre la señal tuned**.

Motivo:

- ya vimos sensibilidad real a la capa de portfolio
- sigue faltando un punto medio convincente entre retorno y robustez

## Backlog corto

1. probar weighting / sizing sobre la tuned
2. comparar drawdowns y rachas entre baseline y la variante de mayor retorno
3. evaluar si conviene abrir otra familia de features

## Resumen rápido de runs

| Variante | Ann. Return | IR | Max DD | IC |
| --- | ---: | ---: | ---: | ---: |
| Alpha158 + csi300 (label 5d) | 0.1620 | 2.1507 | -0.0780 | 0.0760 |
| Alpha158 + csi300 | 0.1106 | 1.3051 | -0.0858 | 0.0470 |
| Alpha158 + csi300 (tuned LGBM, top20/n_drop2) | 0.1264 | 0.9463 | -0.1590 | 0.0589 |
| Alpha158 + csi300 (tuned LGBM, top30/n_drop3) | 0.1070 | 0.9480 | -0.1186 | 0.0589 |
| Alpha158 + csi500 | 0.0949 | 1.1844 | -0.1262 | 0.0357 |
| Alpha158 + csi300 (tuned LGBM) | 0.0753 | 0.8284 | -0.1051 | 0.0589 |
| Alpha158 + csi300 (tuned LGBM, softtopk20) | 0.0329 | 0.2635 | -0.2433 | 0.0589 |

## Preguntas abiertas más importantes

- ¿qué esquema de pesos conserva retorno sin disparar drawdown?
- ¿el deterioro de las variantes más concentradas viene de pocas rachas muy malas?
- ¿qué criterio usaremos para declarar una nueva baseline candidata?

## Enlaces rápidos

- [Baselines y runs](../experiments/baselines.md)
- [Señal vs portfolio](../experiments/signal-vs-portfolio.md)
- [Hipótesis](hypotheses.md)
- [Backlog experimental](experimental-backlog.md)
- [Decisiones metodológicas](methodological-decisions.md)
- [Preguntas abiertas](open-questions.md)

_Generado automáticamente desde `mlruns/`._
