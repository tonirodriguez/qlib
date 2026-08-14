# US market trading plan

Esta es la versión navegable en la wiki del plan técnico para extender `qlib` a mercado US.

## Secuencia recomendada

1. dataset US diario reproducible,
2. baseline `sp500 + Alpha158`,
3. variante `label 5d`,
4. validación de costes y turnover,
5. paper trading,
6. solo después, live muy controlado.

## Decisión práctica

- usar `sp500` como universo inicial,
- tratar `~/.qlib/qlib_data/us_data` como dataset maestro,
- no saltar a live sin varias semanas de paper trading.

## Canonical source

El documento fuente completo está en `qlib/docs/us-market-trading-plan.md`.
