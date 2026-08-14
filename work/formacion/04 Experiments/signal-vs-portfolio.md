# Señal vs portfolio

_Generado automáticamente desde `mlruns/`._

## Aprendizaje principal

En este proyecto ya apareció una lección importante:

> una señal puede mejorar métricas predictivas y aun así empeorar el resultado de la estrategia.

## Caso observado

La variante **Alpha158 + csi300 (tuned LGBM)**:

- mejora `IC` de `0.0760` a `0.0589`
- mejora `Rank IC` de `0.0793` a `0.0495`
- pero empeora el retorno anualizado con costes de `0.1620` a `0.0753`
- y empeora el drawdown con costes de `-0.0780` a `-0.1051`

## Interpretación

Eso sugiere que hay dos problemas distintos:

1. **calidad de señal**
2. **cómo se monetiza esa señal**

No conviene mezclar ambos al interpretar resultados.

## Qué mostró la capa de portfolio

Al concentrar cartera sobre la misma señal tuned:

- **Alpha158 + csi300 (tuned LGBM, top20/n_drop2)** alcanza `ann_ret_cost` = `0.1264`, `IR` = `0.9463` y `max drawdown` = `-0.1590`
- **Alpha158 + csi300 (tuned LGBM, top30/n_drop3)** alcanza `ann_ret_cost` = `0.1070`, `IR` = `0.9480` y `max drawdown` = `-0.1186`
- **Alpha158 + csi300 (tuned LGBM, softtopk20)** alcanza `ann_ret_cost` = `0.0329`, `IR` = `0.2635` y `max drawdown` = `-0.2433`

## Conclusión operativa

La señal tuned **sí parece contener edge**, pero:

- necesita una cartera más adecuada para extraerlo
- demasiada concentración introduce fragilidad

## Mejor variante tuned por retorno

- **Variante:** `Alpha158 + csi300 (tuned LGBM, top20/n_drop2)`
- **Annualized return with cost:** `0.1264`
- **IR with cost:** `0.9463`
- **Max drawdown with cost:** `-0.1590`

## Regla de trabajo futura

Cuando cambie el modelo o los features:

- revisar primero señal
- revisar después portfolio
- no declarar ganador un modelo solo por IC

## Fuente canónica

- `docs/analysis-why-tuned-underperformed.md`
- `docs/experimental-results.md`
- `wiki/research/dashboard.md`
