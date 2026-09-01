"""decision_s8_alarmas.py — Prioridad 3: infraestructura MÍNIMA para la decisión S8.

SCRIPT READ-ONLY (no toca simuladores ni estados):
- Lee los 3 estados (E1/E2/E3) + precios actuales.
- Calcula P&L acumulado, valor, y métricas básicas en vivo.
- Flaggea los umbrales de alarma §5.2 del plan (E3 degradado, vol-gate, DD).
- Emite un MEMO markdown con el comparativo para decidir en la S8.

Uso: python work/estrategias/decision_s8_alarmas.py
"""
import os, sys, json, datetime
import numpy as np
import pandas as pd

SIM = os.path.dirname(os.path.abspath(__file__)) + "/simulation"
sys.path.insert(0, SIM)   # para importar sim_utils desde simulation/
import sim_utils as su

# Umbrales de alarma (de plan_E3_quinn_futuro.md §5.2)
ALARMA_E3_NEG_SOSTENIDO_WEEKS = 3      # semanas de P&L E3 negativo sostenido
ALARMA_DD_MAX = 0.25                   # 25% drawdown desde inicio de E1 (backtest DD ~-19%)

# Estado del portfolio
PORTFOLIO = {
    "NVO": {"shares": 8, "cost": 39.79},
    "AAPL": {"shares": 8, "cost": 275.10},
    "GOOGL": {"shares": 10, "cost": 316.30},
    "MSFT": {"shares": 13, "cost": 411.98},
    "META": {"shares": 3, "cost": 664.00},
}


def load_price(ticker):
    """Precio actual de un ticker (desde prices_live.csv si existe)."""
    csv = os.path.join(SIM, "prices_live.csv")
    if os.path.exists(csv):
        df = pd.read_csv(csv, index_col=0, parse_dates=True)
        if ticker in df.columns:
            s = df[ticker].dropna()
            if len(s):
                return float(s.iloc[-1])
    return None


def estrategia_value(state):
    """Valor de una estrategia = cash + posiciones valoradas (cost como fallback)."""
    val = float(state.get("cash_usd", 0))
    for t, pos in state["positions"].items():
        px = load_price(t)
        if px:
            val += float(pos["shares"]) * px
        else:
            val += float(pos["cost_usd"])
    return val


def main():
    # Leer estados
    estados = {}
    for name, f in [("E1 momentum", "state.json"),
                    ("E2 mom+PEAD", "state_pead.json"),
                    ("E3 PEAD-núcleo", "state_pead_core.json")]:
        path = os.path.join(SIM, f)
        if os.path.exists(path):
            estados[name] = su.load_state(path)

    print("="*62)
    print("📊 DECISIÓN S8 — Comparativo y alarmas (%s)" % datetime.date.today())
    print("="*62)

    # Tabla de estrategias
    rows = []
    alertas = []
    for name, s in estados.items():
        start = float(s["start_capital_usd"])
        val = estrategia_value(s)
        pnl = (val / start - 1) * 100
        rows.append({"estrategia": name, "start": start, "valor": val, "pnl_pct": pnl})
        if "gate" in s:
            rows[-1]["gate"] = float(s["gate"])
        print(f"  {name:20} | start ${start:,.0f} | valor ${val:,.0f} | P&L {pnl:+.2f}%")

    # ALARMAS (flag umbrales §5.2)

    # 1. E3 degradado (PEAD-núcleo P&L negativo sostenido)
    if "E3 PEAD-núcleo" in estados:
        e3 = estados["E3 PEAD-núcleo"]
        e3_pnl = (estrategia_value(e3) / float(e3["start_capital_usd"]) - 1) * 100
        if e3_pnl < -5:
            alertas.append(f"🔴 E3 PEAD-núcleo en P&L {e3_pnl:+.1f}% (negativo acusado) — evaluar si la señal PEAD se degrada")
        elif e3_pnl < 0:
            alertas.append(f"🟡 E3 PEAD-núcleo en {e3_pnl:+.1f}% (negativo) — vigilar si se sostiene (> {ALARMA_E3_NEG_SOSTENIDO_WEEKS} semanas)")

    # 2. Vol-gate: ¿está funcionando? (comparar DD E1 vs E3 con gate)
    if "E1 momentum" in estados and "E3 PEAD-núcleo" in estados:
        e1 = estados["E1 momentum"]
        e1_pnl = (estrategia_value(e1) / float(e1["start_capital_usd"]) - 1) * 100
        # si E1 cae mucho más que E3, el gate está protegiendo
        diff = e1_pnl - (estrategia_value(estados["E3 PEAD-núcleo"]) / float(estados["E3 PEAD-núcleo"]["start_capital_usd"]) - 1) * 100
        if diff > 0 and e1_pnl < -3:
            alertas.append(f"🟢 El vol-gate de E3 parece proteger (E1 {e1_pnl:+.1f}% vs E3 {e3_pnl:+.1f}%)")

    # 3. Drawdown desde inicio
    for name, s in estados.items():
        start = float(s["start_capital_usd"])
        val = estrategia_value(s)
        dd = (val / start - 1)
        if dd < -ALARMA_DD_MAX:
            alertas.append(f"🔴 {name}: drawdown {dd*100:.1f}% supera umbral ({ALARMA_DD_MAX*100:.0f}%)")

    # 4. Verificar que las 3 corren (fechas recientes)
    hoy = datetime.date.today()
    for name, s in estados.items():
        d = s.get("date")
        if d:
            try:
                dias = (hoy - datetime.date.fromisoformat(d)).days
                if dias > 20:
                    alertas.append(f"🟠 {name}: estado hace {dias} días ({d}) — ¿sigue corriendo el cronjob?")
            except ValueError:
                pass

    # Referencia: portfolio real
    print("\n--- CARTERA REAL (referencia) ---")
    val_real = 0
    cost_real = 0
    for t, pos in PORTFOLIO.items():
        px = load_price(t)
        if px:
            v = px * pos["shares"]
            c = pos["cost"] * pos["shares"]
            val_real += v
            cost_real += c
    if val_real:
        print(f"  Valor cartera real: ${val_real:,.0f} | P&L {(val_real/cost_real-1)*100:+.2f}%")

    # Emitir memo
    print("\n" + "="*62)
    print("⚠️ ALARMAS §5.2")
    print("="*62)
    if alertas:
        for a in alertas:
            print(f"  {a}")
    else:
        print("  ✅ Sin alarmas activas — evolución dentro de lo esperado.")

    # Guardar memo
    out = f"/opt/data/qlib/work/qlib_work/decision_s8_memo_{datetime.date.today().isoformat()}.md"
    with open(out, "w") as f:
        f.write(f"# 📊 Memo Decisión S8 — {datetime.date.today()}\n\n")
        f.write("| Estrategia | Start $ | Valor $ | P&L % |\n|---|---|---|---|\n")
        for r in rows:
            f.write(f"| {r['estrategia']} | {r['start']:,.0f} | {r['valor']:,.0f} | {r['pnl_pct']:+.2f}% |\n")
        f.write("\n## Alarmas\n")
        if alertas:
            for a in alertas:
                f.write(f"- {a}\n")
        else:
            f.write("- Sin alarmas activas\n")
    print(f"\n✅ Memo guardado en {out}")


if __name__ == "__main__":
    main()
