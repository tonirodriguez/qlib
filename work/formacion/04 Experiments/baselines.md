# Baselines y runs

_Generado automáticamente desde `mlruns/`._

## Baseline de referencia actual

**Alpha158 + csi300 (label 5d)** es el baseline de referencia porque mantiene el mejor equilibrio general entre:

- señal
- retorno neto
- information ratio
- drawdown

## Tabla resumen

| Variante | Experiment ID | Run ID | IC | Rank IC | Ann. Return | IR | Max DD | Lectura rápida |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Alpha158 + csi300 (label 5d) | `641902479728835995` | `f47322850f1b4db3b0fedaf66738ecb5` | 0.0760 | 0.0793 | 0.1620 | 2.1507 | -0.0780 | Mejor equilibrio general por ahora |
| Alpha158 + csi300 | `413470885701369270` | `c429e2f1f0e14adf872673cb585cbb5a` | 0.0470 | 0.0487 | 0.1106 | 1.3051 | -0.0858 | Run comparable registrado en mlruns |
| Alpha158 + csi300 (tuned LGBM, top20/n_drop2) | `209993374317524872` | `0a03ad2f33d94bd494163acbce8ae517` | 0.0589 | 0.0495 | 0.1264 | 0.9463 | -0.1590 | Más retorno, pero drawdown claramente peor |
| Alpha158 + csi300 (tuned LGBM, top30/n_drop3) | `437384314645360487` | `cfc884bfd1484e4db5aac5dc62ead9fc` | 0.0589 | 0.0495 | 0.1070 | 0.9480 | -0.1186 | Monetiza mejor la señal tuned, pero aún no supera al baseline |
| Alpha158 + csi500 | `434003243921075867` | `83b9429344a345f4b08ceb41ae798e19` | 0.0357 | 0.0459 | 0.0949 | 1.1844 | -0.1262 | Peor que csi300 en este setup |
| Alpha158 + csi300 (tuned LGBM) | `154367763693815271` | `85c9211a243147a0badea2b5361dc351` | 0.0589 | 0.0495 | 0.0753 | 0.8284 | -0.1051 | Mejor señal, pero peor resultado neto |
| Alpha158 + csi300 (tuned LGBM, softtopk20) | `645493182688106959` | `3b121593ab2b45cea2bd85467a6302fc` | 0.0589 | 0.0495 | 0.0329 | 0.2635 | -0.2433 | Sizing suave probado; señal buena pero monetización débil con costes |

## Runs importantes

### Alpha158 + csi300 (label 5d)

- experiment id: `641902479728835995`
- run id: `f47322850f1b4db3b0fedaf66738ecb5`
- IC: `0.0760`
- Rank IC: `0.0793`
- annualized return with cost: `0.1620`
- IR with cost: `2.1507`
- max drawdown with cost: `-0.0780`
- lectura: Mejor equilibrio general por ahora

### Alpha158 + csi300

- experiment id: `413470885701369270`
- run id: `c429e2f1f0e14adf872673cb585cbb5a`
- IC: `0.0470`
- Rank IC: `0.0487`
- annualized return with cost: `0.1106`
- IR with cost: `1.3051`
- max drawdown with cost: `-0.0858`
- lectura: Run comparable registrado en mlruns

### Alpha158 + csi300 (tuned LGBM, top20/n_drop2)

- experiment id: `209993374317524872`
- run id: `0a03ad2f33d94bd494163acbce8ae517`
- IC: `0.0589`
- Rank IC: `0.0495`
- annualized return with cost: `0.1264`
- IR with cost: `0.9463`
- max drawdown with cost: `-0.1590`
- lectura: Más retorno, pero drawdown claramente peor

### Alpha158 + csi300 (tuned LGBM, top30/n_drop3)

- experiment id: `437384314645360487`
- run id: `cfc884bfd1484e4db5aac5dc62ead9fc`
- IC: `0.0589`
- Rank IC: `0.0495`
- annualized return with cost: `0.1070`
- IR with cost: `0.9480`
- max drawdown with cost: `-0.1186`
- lectura: Monetiza mejor la señal tuned, pero aún no supera al baseline

### Alpha158 + csi500

- experiment id: `434003243921075867`
- run id: `83b9429344a345f4b08ceb41ae798e19`
- IC: `0.0357`
- Rank IC: `0.0459`
- annualized return with cost: `0.0949`
- IR with cost: `1.1844`
- max drawdown with cost: `-0.1262`
- lectura: Peor que csi300 en este setup

### Alpha158 + csi300 (tuned LGBM)

- experiment id: `154367763693815271`
- run id: `85c9211a243147a0badea2b5361dc351`
- IC: `0.0589`
- Rank IC: `0.0495`
- annualized return with cost: `0.0753`
- IR with cost: `0.8284`
- max drawdown with cost: `-0.1051`
- lectura: Mejor señal, pero peor resultado neto

### Alpha158 + csi300 (tuned LGBM, softtopk20)

- experiment id: `645493182688106959`
- run id: `3b121593ab2b45cea2bd85467a6302fc`
- IC: `0.0589`
- Rank IC: `0.0495`
- annualized return with cost: `0.0329`
- IR with cost: `0.2635`
- max drawdown with cost: `-0.2433`
- lectura: Sizing suave probado; señal buena pero monetización débil con costes

## Reglas de lectura

- baseline ganador actual ≠ mejor retorno absoluto en cualquier variante
- una variante más agresiva puede subir retorno y empeorar robustez
- `IR` y drawdown importan tanto como `ann_ret_cost`
- mejor `IC` no implica automáticamente mejor resultado de portfolio

## Fuente canónica

Para el detalle completo, usar:

- `docs/experimental-results.md`
- `wiki/research/dashboard.md`
