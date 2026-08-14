# 💰 Comisiones de Interactive Brokers (España) y su caracterización en Qlib

> **Fecha:** 2026-08-14
> **Ámbito:** Acciones de EE. UU. (Nasdaq/pet S&P 500) operadas desde España con Interactive Brokers (IBKR)
> **Proyecto:** Qlib Work — inversión cuantitativa US/cripto

---

## 1. Estructura de comisiones de Interactive Brokers (acciones US)

IB ofrece dos estructuras para acciones de EE. UU. en IBKR Pro:

### 1.1 Estructura por niveles (tiered) — recomendada para coste bajo
| Volumen mensual (acciones) | Comisión por acción |
|---|---|
| ≤ 300,000 | **$0.0035/acción** |
| 300,001 – 3,000,000 | $0.0020/acción |
| 3,000,001 – 20,000,000 | $0.0015/acción |
| > 20,000,000 | $0.0010/acción |
| **Mínimo por orden** | **$0.35** |

### 1.2 Estructura fija (fixed)
| Concepto | Valor |
|---|---|
| Comisión por acción | **$0.005/acción** |
| **Mínimo por orden** | **$1.00** |

### 1.3 Cargos regulatorios adicionales (sobre la comisión del broker)
| Cargo | Aprox. | Cuándo |
|---|---|---|
| **SEC transaction fee** | ~$33.10 por $1M (~0.0033% del valor) | Operaciones de venta |
| **TAF (FINRA Trading Activity Fee)** | ~$0.0001–0.0002/acción | Operaciones de venta |

*Nota: en España no aplica impuesto a las transacciones financieras (ITF) sobre acciones US/Nasdaq de megacaps para inversor retail; el ITF español solo afecta a ciertas acciones españolas/BME.*

---

## 2. Conversión de comisiones por acción → porcentaje (para Qlib)

**Qlib modela los costes como fracción del valor negociado** (`open_cost` / `close_cost` en `exchange_kwargs`), **no por acción**. Como IB cobra **por acción**, hay que convertir.

### Método de conversión
```
Precio medio del universo (tech_giants): ~$350
Comisión $0.0035/acción  →  0.0035 / 350 = 0.00001 (0.001%) del valor
SEC fee (~0.0033%)       →  ~0.000033
TAF (~0.0001%)           →  ~0.000001
```
En megacaps de precio alto, la comisión por acción en % es **muy pequeña**. El coste dominante pasa a ser el **slippage** (no modelado nativamente por Qlib).

---

## 3. Cómo caracterizar las comisiones en un modelo de Qlib

### 3.1 Valores recomendados (conservadores) — `exchange_kwargs`

| Parámetro Qlib | Valor | Justificación |
|---|---|---|
| **`open_cost`** | **0.0004** (0.04%) | Comisión IB tiered + slippage entrada + SEC |
| **`close_cost`** | **0.0006** (0.06%) | Comisión + slippage salida + SEC/TAF (mayor en ventas) |
| **`min_cost`** | **1.0** | Mínimo por orden IB (estructura fija = $1; tiered = $0.35 → usamos $1 conservador) |
| **`deal_price`** | `close` | Ejecución estimada al cierre |
| **`limit_threshold`** | `0.095` | Límite de variación de precio (stop de ejecución) |
| **Round-trip total** | **~0.10%** | Conservador, ~2x la comisión pura de IB como margen para slippage |

### 3.2 Principios de caracterización
1. **Incluir slippage como margen** — Qlib **no modela slippage** ni impacto de mercado. Como no se puede modelar directamente, se añade un **margen sobre la comisión pura** (≈2x) en `open_cost`/`close_cost` para ser conservador.
2. **`open` vs `close` costes asimétricos** — en US, la venta (close) tiene más cargos regulatorios (SEC/TAF) → `close_cost` > `open_cost`.
3. **`min_cost` acorde al broker** — usar el mínimo real de IB ($1 fixed / $0.35 tiered). Para universos de megacaps el mínimo casi nunca aplica, pero es correcto incluirlo.
4. **Ajustar por precio del universo** — la comisión por acción convierte a % según el precio medio. Si el universo cambia (p.ej. criptos con precios bajos o spreads altos), recalcular la conversión.
5. **Conservadurismo** — es mejor sobre-estimar ligeramente los costes que obtener un backtest demasiado optimista. Un modelo que sobrevive con costes conservadores es más robusto en operativa real.

### 3.3 Costes en cripto (futuro)
Para el futuro módulo de **criptos**, los costes son distintos y suelen ser más altos:
- Spread bid-ask en exchanges (a menudo 5-10 bps) — dominante
- Comisiones del exchange (taker/maker): ~5-20 bps según exchange
- **No hay** cargos SEC/TAF, pero hay **spread amplio** en pares menos líquidos
- Recomendación: modelar `open_cost`/`close_cost` ~0.05–0.1% y considerar `deal_price` más conservador

---

## 4. Comparativa: Qlib default vs. IB real

| Parámetro | Qlib default | **IB España (recomendado)** |
|---|---|---|
| open_cost | 0.0005 (0.05%) | **0.0004 (0.04%)** |
| close_cost | 0.0015 (0.15%) | **0.0006 (0.06%)** |
| min_cost | 5 | **1.0** |
| Round-trip | ~0.20% | **~0.10%** |

**Conclusión:** el default de Qlib (0.20% round-trip) **sobreestima ~2-5x** lo que pagarías con IB en megacaps tech. Usar los valores reales hace que los resultados "con costes" sean más fieles a tu operativa real.

---

## 5. Implementación práctica

Los costes IB se centralizan en **`toni/ib_costs.py`** y se aplican a cada experimento en el `exchange_kwargs` de su yml:

```yaml
exchange_kwargs:
    limit_threshold: 0.095
    deal_price: close
    open_cost: 0.0004    # IB tiered + slippage (0.04%)
    close_cost: 0.0006   # IB tiered + slippage + SEC/TAF (0.06%)
    min_cost: 1.0        # mínimo por orden IB
```

Para incorporar en el backtest de Qlib:

```python
exchange_kwargs = {
    "open_cost": 0.0004,
    "close_cost": 0.0006,
    "min_cost": 1.0,
    "limit_threshold": 0.095,
    "deal_price": "close",
}
```

---

*Documento de referencia del proyecto Qlib Work. Fuente de comisiones: interactivebrokers.com (pricing acciones US). Se actualizará cuando cambien tarifas o se añada el módulo de cripto.*
