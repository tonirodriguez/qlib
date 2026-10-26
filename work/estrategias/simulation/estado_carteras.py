"""Muestra el estado REAL de las 4 carteras de paper-trading."""
import json
from pathlib import Path

SIM = Path(__file__).resolve().parent

ESTADOS = [
    ("state.json", "E1 Momentum puro"),
    ("state_pead.json", "E2 Momentum + PEAD"),
    ("state_pead_core.json", "E3 PEAD-nucleo + tactico"),
    ("state_backup_20260905.json", "backup E1 (2026-08-29)"),
]

print("=" * 78)
print(" ESTADO REAL DE LAS CARTERAS DE PAPER-TRADING")
print("=" * 78)

for fn, nombre in ESTADOS:
    p = SIM / fn
    if not p.exists():
        print(f"\n--- {nombre} --- NO EXISTE")
        continue
    s = json.loads(p.read_text(encoding="utf-8"))
    pos = s.get("positions", {})

    # valorar
    cash = float(s.get("cash_usd", 0) or 0)
    start = float(s.get("start_capital_usd", 0) or 0)
    cost = sum(float(v.get("cost_usd", 0) or 0) for v in pos.values())
    total = cash + cost
    pnl = (total - start) if start else float("nan")
    pnl_pct = (pnl / start * 100) if start else float("nan")

    print(f"\n--- {nombre} --- ({fn})")
    print(f"    fecha        : {s.get('date')}  (datos {s.get('data_date')})")
    print(f"    creado       : {s.get('created')}")
    print(f"    capital start: ${start:,.2f}")
    print(f"    cash         : ${cash:,.2f}")
    print(f"    coste pos.   : ${cost:,.2f}")
    print(f"    VALOR TOTAL  : ${total:,.2f}")
    print(f"    P&L          : ${pnl:+,.2f}  ({pnl_pct:+.2f}%)")
    print(f"    posiciones   : {len(pos)}")

    # libros si los hay
    books = {}
    for t, v in pos.items():
        b = v.get("book", "-")
        books[b] = books.get(b, 0) + 1
    if len(books) > 1 or "-" not in books:
        print(f"    por libro    : {books}")

    if s.get("gate") is not None:
        print(f"    gate         : {s.get('gate')}")
    if s.get("total_trades") is not None:
        print(f"    operaciones  : {s.get('total_trades')} "
              f"(W:{s.get('wins',0)} L:{s.get('losses',0)})")

    # tickers (primeros 8)
    tick = list(pos.keys())
    print(f"    tickers      : {tick[:8]}{' ...' if len(tick) > 8 else ''}")

print("\n" + "=" * 78)
print(" ORDENADAS POR FECHA (la mas reciente primero)")
print("=" * 78)
rows = []
for fn, nombre in ESTADOS:
    p = SIM / fn
    if p.exists():
        s = json.loads(p.read_text(encoding="utf-8"))
        rows.append((s.get("date", ""), nombre, fn, len(s.get("positions", {}))))
for d, nm, fn, n in sorted(rows, reverse=True):
    print(f"  {d}  {nm:<30} {n} posiciones")
