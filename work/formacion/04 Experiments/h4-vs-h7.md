# H4 vs H7 (2026-05-10)

Resumen corto:

- **H4** ya quedó arreglada y ejecutada completa.
- **H7** sigue ganando claramente y dio el mejor resultado observado hasta ahora en este repo.

## H4

- config: `config/workflow_baseline_lightgbm_alpha158_csi300_tuned_softtopk20.yaml`
- experimento: `645493182688106959`
- run: `3b121593ab2b45cea2bd85467a6302fc`
- `IC`: `0.0589`
- `Rank IC`: `0.0495`
- `Ann. Return (with cost)`: `0.0329`
- `IR (with cost)`: `0.2635`
- `Max Drawdown (with cost)`: `-0.2433`
- estado: **evaluada**, pero con resultado flojo

## H7

- config: `config/workflow_baseline_lightgbm_alpha158_csi300_label5d.yaml`
- experimento: `641902479728835995`
- run: `942aed50889d44f493a0d98ebda0c38f`
- `IC`: `0.0760`
- `Rank IC`: `0.0793`
- `Ann. Return (with cost)`: `0.1620`
- `IR (with cost)`: `2.1507`
- `Max Drawdown (with cost)`: `-0.0780`

## Lectura

La evidencia de hoy favorece claramente **H7**:

- mejora señal
- mejora monetización
- mejora robustez frente al baseline anterior

H4 ya no es un problema de infraestructura: ahora sabemos que esta variante concreta de `softtopk20` monetiza mal la señal en este setup.

## Documento largo

- [Comparación completa](h4-vs-h7-detalle.md)
