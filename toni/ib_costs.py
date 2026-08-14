"""
Costes de transacción reales de INTERACTIVE BROKERS para España (acciones EE. UU.).

Fuente: interactivebrokers.com pricing (acciones US), estructura por niveles (tiered).

CONVERSIÓN a % (para exchange_kwargs de Qlib):
- Qlib models open_cost / close_cost como fracción del valor negociado.
- IB cobra POR ACCIÓN, no por valor. Con precio medio del universo tech_giants ~$350:
    comisión $0.0035/acc => ~0.001% del valor
    SEC fee ~0.0033% (ventas)
    TAF ~0.0001%

VALORES CONSERVADORES incorporados (incluyen slippage no modelado por Qlib):
- open_cost:  0.0004  (0.04%)  -> comisión + slippage de entrada + SEC
- close_cost: 0.0006  (0.06%)  -> comisión + slippage + SEC/TAF de salida (mayor)
- min_cost:   1.00             -> mínimo $1 por orden (estructura fija IB)
- round-trip: ~0.10%           -> conservador, ~2x la comisión pura de IB como margen

Nota: los valores por defecto de Qlib (0.0005 open + 0.0015 close = 0.20% round-trip)
SOBREESTIMAN ~2-5x lo que tocaría con IB en megacaps. Estos son más fieles.
"""
IB_US_COSTS = {
    "open_cost": 0.0004,    # 0.04%
    "close_cost": 0.0006,   # 0.06%
    "min_cost": 1.0,        # $1 mínimo por orden
    "limit_threshold": 0.095,
    "deal_price": "close",
}
