"""vol_gate_validacion_v2.py — Validacion del vol-gate con el MECANISMO CORRECTO.

POR QUE EXISTE ESTE SCRIPT
==========================
La validacion original (`vol_gate_test.py`, agosto 2026) documentaba:
    mom puro     -> Sharpe 0.960, DD -19.3%
    mom+gate P75 -> Sharpe 1.136, DD -16.6%   <-- el numero que se uso para promover

Pero ese script aplicaba el gate asi:
    sig_gated = mom.multiply(gate_col, axis=0)

y `TopkDropoutStrategy` ORDENA la senal y compra el top-k. Multiplicar por un
escalar NO cambia el orden:
    gate=1.0 -> orden intacto
    gate=0.5 -> 0.5*x conserva el orden -> IDENTICO a 1.0
    gate=0.0 -> todos empatan a 0    -> indefinido
Por eso los 4 backtests daban resultados IDENTICOS (verificado: Sharpe 1.151
en los 4). La tabla de agosto es irreproducible con ese codigo, que ademas no
cambio entre commits (`git show cdd68576` -> mismo `multiply`).

MECANISMO CORRECTO
==================
El gate debe modular la EXPOSICION, no la escala de la senal. Se implementa
como una estrategia propia que ajusta el tamano de la cartera:

    gate = 1.0  -> topk = 30  (posicion completa)
    gate = 0.5  -> topk = 15  (media posicion)
    gate = 0.0  -> topk = 0   -> VENDER TODO -> 100% cash

Decision del usuario (2026-10-26): con gate=0, TODO A CASH.

Esto si reduce la exposicion real y es medible con el motor de qlib.

Uso (en WSL):
    conda run -n qlib python work/estrategias/vol_gate_validacion_v2.py
    conda run -n qlib python work/estrategias/vol_gate_validacion_v2.py --quick
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import vol_gate as vg  # noqa: E402

MOM_W = 120
TOPK = 30

# Costes IB (identicos al test original, para ser comparable)
IB = dict(open_cost=0.0004, close_cost=0.0006, min_cost=1.0,
          limit_threshold=0.095, deal_price="close")

# Guarda la ultima clase Gated creada, para leer sus contadores de diagnostico.
_LAST_GATED: list = [None]

# Referencia documentada en agosto (a contrastar)
AGOSTO = {
    "momentum puro": {"sharpe": 0.960, "maxdd": -0.193, "anual": 0.185},
    "gate P70": {"sharpe": 0.967, "maxdd": -0.150, "anual": 0.189},
    "gate P75": {"sharpe": 1.136, "maxdd": -0.166, "anual": 0.232},
    "gate P80": {"sharpe": 1.071, "maxdd": -0.177, "anual": 0.215},
}


# ---------------------------------------------------------------------------
# Estrategia con gate sobre la EXPOSICION
# ---------------------------------------------------------------------------

def make_gated_strategy(gate_series: pd.Series, base_topk: int = TOPK):
    """Crea una TopkDropoutStrategy cuyo topk varia con el gate.

    qlib no permite topk dinamico en la clase estandar, asi que se subclasea
    y se sobreescribe `generate_trade_decision` para ajustar `self.topk`
    segun el gate de la fecha actual.
    """
    from qlib.backtest.decision import Order, OrderDir
    from qlib.contrib.strategy import TopkDropoutStrategy

    class GatedTopkStrategy(TopkDropoutStrategy):
        """TopkDropout con topk modulado por el gate de volatilidad.

        Mecanismo:
            gate 1.0 -> topk = base_topk  (posicion completa)
            gate 0.5 -> topk = base//2    (media posicion)
            gate 0.0 -> VENDER TODO       (100% cash)

        Con gate=0 se intercepta la decision y se devuelve una lista de ordenes
        de VENTA de toda la cartera, en vez de delegar en la clase base.
        (Delegar con topk=0 no vende todo: la clase base calcula
         `buy = today[: len(sell) + topk - len(last)]` con n_drop fijo, que no
         garantiza vaciar la cartera.)
        """

        # Contadores de diagnostico (nivel de clase, para verlos al final)
        _dbg_calls = 0
        _dbg_levels = None
        _dbg_topks = None
        _dbg_sellall = 0

        def __init__(self, *args, gate=None, base_topk=30, **kwargs):
            super().__init__(*args, **kwargs)
            self._gate = gate
            self._base_topk = base_topk
            self._sold_all = False
            GatedTopkStrategy._dbg_levels = {}
            GatedTopkStrategy._dbg_topks = {}

        def _level_at(self, date) -> float:
            """Nivel de gate vigente en `date` (ultimo valor <= date)."""
            if self._gate is None:
                return 1.0
            try:
                sub = self._gate.loc[:date]
                if len(sub) == 0:
                    return 1.0
                v = float(sub.iloc[-1])
                return 1.0 if v != v else v  # NaN -> 1.0 (sin senal, no se recorta)
            except Exception:
                return 1.0

        def generate_trade_decision(self, execute_result=None):
            # Fecha de decision actual
            try:
                cur = self.trade_calendar.get_step_time()[0]
            except Exception:
                cur = None

            GatedTopkStrategy._dbg_calls += 1

            if cur is not None:
                lvl = self._level_at(pd.Timestamp(cur))
                new_topk = int(round(self._base_topk * lvl))
                GatedTopkStrategy._dbg_levels[lvl] = \
                    GatedTopkStrategy._dbg_levels.get(lvl, 0) + 1
                GatedTopkStrategy._dbg_topks[new_topk] = \
                    GatedTopkStrategy._dbg_topks.get(new_topk, 0) + 1

                if new_topk <= 0:
                    GatedTopkStrategy._dbg_sellall += 1
                    # --- GATE 0: VENDER TODO -> 100% cash ---
                    self._sold_all = True
                    try:
                        from qlib.backtest.decision import TradeDecisionWO
                        pos = self.trade_position
                        # start_time/end_time son opcionales: TradeDecisionWO
                        # los rellena con el rango del step.
                        sell_orders = [
                            Order(stock_id=code,
                                  amount=pos.get_stock_amount(code),
                                  direction=OrderDir.SELL)
                            for code in pos.get_stock_list()
                            if pos.get_stock_amount(code) > 0
                        ]
                        if sell_orders:
                            return TradeDecisionWO(sell_orders, self)
                    except Exception:
                        # Si algo falla, cae al comportamiento base (mejor que romper)
                        pass
                else:
                    self.topk = new_topk
                    self._sold_all = False

            return super().generate_trade_decision(execute_result)

    _LAST_GATED[0] = GatedTopkStrategy
    return GatedTopkStrategy


# ---------------------------------------------------------------------------
# Backtest
# ---------------------------------------------------------------------------

def run_backtest(signal, gate_series, name, bt_start, bt_end, benchmark,
                 base_topk=TOPK):
    """Backtest con gate sobre exposicion (o sin gate si gate_series es None)."""
    from qlib.backtest import backtest
    from qlib.contrib.strategy import TopkDropoutStrategy

    if gate_series is None:
        strategy = {
            "class": TopkDropoutStrategy,
            "kwargs": {"signal": signal, "topk": base_topk, "n_drop": 5,
                       "only_tradable": True, "hold_thresh": 20},
        }
    else:
        Gated = make_gated_strategy(gate_series, base_topk)
        strategy = {
            "class": Gated,
            "kwargs": {"signal": signal, "topk": base_topk, "n_drop": 5,
                       "only_tradable": True, "hold_thresh": 20,
                       "gate": gate_series, "base_topk": base_topk},
        }

    executor = {
        "class": "SimulatorExecutor",
        "module_path": "qlib.backtest.executor",
        "kwargs": {"time_per_step": "week", "generate_portfolio_metrics": True},
    }
    report, _ = backtest(
        start_time=bt_start, end_time=bt_end,
        strategy=strategy, executor=executor,
        benchmark=benchmark, account=100000, exchange_kwargs=IB,
    )
    freq_key = list(report.keys())[0]
    df = report[freq_key][0]
    pv = df["account"].values
    port_ret = pd.Series(pv).pct_change().dropna().values
    mean_ann = float(np.mean(port_ret)) * 52
    vol = float(np.std(port_ret)) * np.sqrt(52)
    sharpe = mean_ann / vol if vol else np.nan
    cum = np.cumprod(1 + port_ret)
    dd = cum / np.maximum.accumulate(cum) - 1
    return {
        "name": name,
        "sharpe": float(sharpe),
        "maxdd": float(dd.min()),
        "anual": float(mean_ann),
        "n_weeks": int(len(port_ret)),
        "final_value": float(pv[-1]) if len(pv) else np.nan,
    }


# ---------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default="2026-08-01")
    ap.add_argument("--bt-start", default="2022-01-01")
    ap.add_argument("--bt-end", default="2026-08-07")
    ap.add_argument("--benchmark", default="^NDX")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", default=str(HERE / "vol_gate_validacion_v2.json"))
    args = ap.parse_args()

    import qlib
    from qlib.data import D

    print("=" * 78)
    print(" VALIDACION v2 DEL VOL-GATE — gate sobre EXPOSICION (no sobre la senal)")
    print("=" * 78)
    print("  Mecanismo: gate 1.0 -> topk 30 | 0.5 -> topk 15 | 0.0 -> TODO A CASH")
    print(f"  Periodo  : {args.bt_start} -> {args.bt_end}  (benchmark {args.benchmark})")

    uri = os.environ.get("QLIB_US_DATA") or os.path.expanduser("~/.qlib/qlib_data/us_data")
    qlib.init(provider_uri=uri, region="us")

    inst_dir = os.path.join(uri, "instruments")
    universe = None
    for nm in ("sp500_liquid", "sp500"):
        if os.path.exists(os.path.join(inst_dir, nm + ".txt")):
            universe = nm
            break
    if universe is None:
        raise FileNotFoundError(f"Sin universo en {inst_dir}")
    print(f"  Universo : {universe}")

    tickers = D.list_instruments(D.instruments(universe), as_list=True)
    close = D.features(tickers, ["$close"], start_time=args.start,
                       end_time=args.end, freq="day")
    close = close["$close"].unstack(level=0).sort_index()
    print(f"  Precios  : {close.shape[0]} fechas x {close.shape[1]} tickers")

    mom = close / close.shift(MOM_W) - 1
    market = close.mean(axis=1)

    def to_qlib(sig_df):
        s = sig_df.stack().dropna()
        s = s.reset_index()
        s.columns = ["datetime", "instrument", "signal"]
        s["datetime"] = pd.to_datetime(s["datetime"])
        return s.set_index(["datetime", "instrument"])["signal"].sort_index()

    sig = to_qlib(mom)

    results = []
    print("\n  [1/4] momentum puro (sin gate)...")
    results.append(run_backtest(sig, None, "momentum puro",
                                args.bt_start, args.bt_end, args.benchmark))

    grid = [(0.75, 0.90)] if args.quick else [(0.70, 0.85), (0.75, 0.90), (0.80, 0.95)]
    for i, (p75, p90) in enumerate(grid, start=2):
        label = f"gate P{int(p75*100)}"
        print(f"  [{i}/4] {label}...")
        gate = vg.gate_series_gated(market, p75=p75, p90=p90)
        gate_col = gate.reindex(close.index).ffill().fillna(1.0)
        r = run_backtest(sig, gate_col, label,
                         args.bt_start, args.bt_end, args.benchmark)
        results.append(r)

        # --- DIAGNOSTICO: ¿se esta aplicando el gate de verdad? ---
        Gated = _LAST_GATED[0]
        if Gated is not None:
            print(f"      [diag] llamadas a generate_trade_decision: {Gated._dbg_calls}")
            print(f"      [diag] niveles de gate vistos : {Gated._dbg_levels}")
            print(f"      [diag] topk aplicados         : {Gated._dbg_topks}")
            print(f"      [diag] veces 'vender todo'    : {Gated._dbg_sellall}")
            if Gated._dbg_calls == 0:
                print("      [diag] >>> EL OVERRIDE NO SE ESTA LLAMANDO <<<")
            elif len(Gated._dbg_topks) <= 1:
                print("      [diag] >>> EL TOPK NUNCA CAMBIA <<<")

    # --- Tabla ---
    print("\n" + "=" * 78)
    print(" RESULTADOS (mecanismo CORRECTO: gate sobre exposicion)")
    print("=" * 78)
    print(f"  {'Estrategia':<18}{'Sharpe':>9}{'MaxDD':>10}{'Anual':>10}"
          f"{'Valor final':>14}")
    print("  " + "-" * 60)
    for r in results:
        print(f"  {r['name']:<18}{r['sharpe']:>9.3f}{r['maxdd']*100:>9.1f}%"
              f"{r['anual']*100:>9.1f}%{r['final_value']:>14,.0f}")

    # --- Comparacion con agosto ---
    print("\n" + "=" * 78)
    print(" vs VALIDACION DE AGOSTO (mecanismo INCORRECTO)")
    print("=" * 78)
    print(f"  {'Estrategia':<18}{'ago':>9}{'hoy':>9}{'nota':>34}")
    print("  " + "-" * 70)
    for r in results:
        old = AGOSTO.get(r["name"], {})
        so = old.get("sharpe")
        nota = ""
        if r["name"] == "momentum puro":
            nota = "comparable (sin gate)"
        else:
            nota = "NO comparable: agosto multiplicaba la senal"
        print(f"  {r['name']:<18}"
              f"{so if so is not None else float('nan'):>9.3f}"
              f"{r['sharpe']:>9.3f}  {nota}")

    # --- Veredicto ---
    print("\n" + "=" * 78)
    print(" VEREDICTO")
    print("=" * 78)
    base = results[0]
    gates = results[1:]
    mej = sum(1 for r in gates if r["sharpe"] > base["sharpe"])
    ddm = sum(1 for r in gates if r["maxdd"] >= base["maxdd"] * 0.80)

    print(f"  momentum puro : Sharpe {base['sharpe']:.3f}, DD {base['maxdd']:.1%}")
    for r in gates:
        print(f"  {r['name']:<14}: Sharpe {r['sharpe']:.3f} "
              f"({r['sharpe']-base['sharpe']:+.3f}), DD {r['maxdd']:.1%} "
              f"({(r['maxdd']-base['maxdd'])*100:+.1f}pp)")

    print(f"\n  Gates que mejoran Sharpe : {mej}/{len(gates)}")
    print(f"  Gates que mejoran DD >=20%: {ddm}/{len(gates)}")

    # Distinguir "identico" de "mejora"
    identical = all(abs(r["sharpe"] - base["sharpe"]) < 1e-6 for r in gates)
    if identical:
        print("\n  >> TODOS IDENTICOS: el gate NO esta afectando al backtest.")
        print("     Revisar que la estrategia GatedTopkStrategy reciba el gate.")
    elif mej == len(gates):
        print("\n  >> El gate MEJORA en todos los umbrales -> robusto.")
    elif mej > 0:
        print("\n  >> Mejora PARCIAL (no en todos los umbrales).")
    else:
        print("\n  >> El gate NO mejora el Sharpe con este mecanismo.")
        if ddm > 0:
            print("     Pero SI reduce el drawdown: util como control de riesgo,")
            print("     aunque el Sharpe no suba.")

    out = {
        "fecha": pd.Timestamp.now().isoformat(),
        "mecanismo": "gate sobre exposicion (topk dinamico, gate=0 -> todo a cash)",
        "periodo": [args.bt_start, args.bt_end],
        "benchmark": args.benchmark,
        "universe": universe,
        "resultados": results,
        "agosto_no_comparable": True,
    }
    Path(args.out).write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n  Guardado en: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
