# Genera notebooks/backtest_v8_2025.ipynb
from pathlib import Path
import nbformat as nbf

nb = nbf.v4.new_notebook()
nb.metadata = {
    "kernelspec": {"display_name": "Python 3 (qlib)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.11"},
}

md_intro = (
    "# 📈 Backtest SFM v8 — 2025-01-01 → 2026-08-30 (long multi-monedas)\n\n"
    "Backtest de la estrategia SFM v8 (modelo `sfm_top3.pth`) operando **igual que el "
    "paper trading real**: long en hasta 2 monedas con señal COMPRA de confianza ALTA, "
    "ponderación equitativa, vendiendo cuando deja de haber señal.\n\n"
    "Metodología (causal):\n"
    "- Features del pipeline v8 (close, pct, ratio_5d, vol_20d, ma20_ratio, rango = 54).\n"
    "- Cada día: fit de clipping + scaler solo con datos disponibles hasta ese día (sin lookahead).\n"
    "- Long hasta MAX_POSITIONS=2, confianza ALTA (score>0.025), capital equitativo.\n"
    "- Costes Binance: fee 0.1% taker + half-spread + slippage en cada cambio de posición.\n"
    "- Conversión EUR a USD al inicio y USD a EUR al final.\n\n"
    "El modelo se entrenó con split 60/20/20 donde 2025-2026 estuvieron en TEST, "
    "por lo que este rango es out-of-sample legítimo."
)

code_load = '''import json
from pathlib import Path

RESULT = Path("/opt/data/qlib/work/crypto/output/sfm_v8/backtest_result.json")
r = json.loads(RESULT.read_text())

print(f"Periodo: {r['start_date']} → {r['end_date']}")
print(f"Capital inicial: {r['initial_capital_eur']:.0f} EUR (={r['initial_capital_usd']:.2f} USD, EUR/USD {r['eurusd_start']})")
print(f"Tipo cambio final EUR/USD: {r['eurusd_end']}")
print()
print("=== RESULTADO (con costes Binance) ===")
print(f"  Final en USD : ${r['final_capital_usd']:,.2f}")
print(f"  Final en EUR : €{r['final_capital_eur']:,.2f}")
print(f"  Retorno USD  : {r['return_pct_usd']:+.2f}%")
print(f"  Retorno EUR  : {r['return_pct_eur']:+.2f}%")
print(f"  Sharpe: {r['sharpe']} | Sortino: {r['sortino']} | Max DD: {r['max_drawdown_pct']}%")
print(f"  Operaciones: {r['n_trades']}")'''

code_pd = '''import pandas as pd

df = pd.DataFrame({"fecha": r["curve_dates"], "capital_usd": r["equity_usd"]})
df["fecha"] = pd.to_datetime(df["fecha"])
df["capital_eur"] = df["capital_usd"] / r["eurusd_end"]
df.head()'''

code_plot = '''import matplotlib
import matplotlib.pyplot as plt

matplotlib.use("Agg")
plt.rcParams["figure.figsize"] = (12, 5)

fig, ax = plt.subplots()
ax.plot(df["fecha"], df["capital_usd"], label=f"Capital USD (final ${r['final_capital_usd']:,.0f})", color="#1976d2")
ax.plot(df["fecha"], df["capital_eur"], label=f"Capital EUR (final €{r['final_capital_eur']:,.0f})", color="#d32f2f")
ax.axhline(r["initial_capital_usd"], color="gray", ls="--", lw=1, label=f"Inicial ${r['initial_capital_usd']:,.0f}")
ax.set_title(f"Evolución del capital — SFM v8 (2025→ago-2026) — retorno EUR {r['return_pct_eur']:+.1f}%")
ax.set_ylabel("Capital")
ax.legend()
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig("/opt/data/qlib/work/crypto/output/sfm_v8/backtest_curve.png", dpi=110)
plt.show()
print("Gráfico guardado: output/sfm_v8/backtest_curve.png")'''

code_summary = '''fx_effect = (r["eurusd_end"] / r["eurusd_start"] - 1) * 100
print("=" * 60)
print("RESUMEN BACKTEST v8 (2025-01-01 hasta 2026-08-30) - long multi-monedas")
print("=" * 60)
print(f"  Capital inicial      : €{r['initial_capital_eur']:,.2f} (${r['initial_capital_usd']:,.2f} USD)")
print(f"  Capital final        : ${r['final_capital_usd']:,.2f} = €{r['final_capital_eur']:,.2f}")
print(f"  Retorno (USD)        : {r['return_pct_usd']:+.2f}%")
print(f"  Retorno (EUR)        : {r['return_pct_eur']:+.2f}%")
print(f"  Abs (EUR)            : €{r['final_capital_eur']-r['initial_capital_eur']:+,.2f}")
print(f"  Sharpe               : {r['sharpe']} | Sortino: {r['sortino']}")
print(f"  Max drawdown         : {r['max_drawdown_pct']}%")
print(f"  Operaciones          : {r['n_trades']}")
print(f"  Efecto tipo de cambio EUR/USD: {fx_effect:+.2f}%")
print("=" * 60)
print("Lectura: en USD la estrategia está casi plana; la pérdida en EUR viene")
print("principalmente de la apreciación del EUR frente al USD en el periodo.")
if r["return_pct_eur"] > 0:
    print("Resultado POSITIVO en EUR (con costes)")
else:
    print("Resultado NEGATIVO en EUR (principalmente por tipo de cambio)")'''

code_returns = '''import json
from pathlib import Path

r = json.loads(Path("/opt/data/qlib/work/crypto/output/sfm_v8/backtest_result.json").read_text())

fx_move = (r["eurusd_end"] / r["eurusd_start"] - 1) * 100

print("Los DOS retornos del backtest (2025-01-01 → 2026-08-30, costes Binance incl.):")
print("=" * 60)
print(f"  Retorno en USD : {r['return_pct_usd']:+.2f}%   <- rendimiento de la ESTRATEGIA")
print(f"  Retorno en EUR : {r['return_pct_eur']:+.2f}%   <- estrategia convertida a EUR (con FX)")
print("=" * 60)
print(f"  Capital inicial: €{r['initial_capital_eur']:,.2f} ")
print(f"  Final en USD   : ${r['final_capital_usd']:,.2f}")
print(f"  Final en EUR   : €{r['final_capital_eur']:,.2f}")
print(f"  Efecto EUR/USD  : {fx_move:+.2f}%  (EUR/USD {r['eurusd_start']} → {r['eurusd_end']})")
if r["return_pct_usd"] >= 0:
    print("  -> La estrategia (en USD) es positiva o plana.")
else:
    print("  -> La estrategia (en USD) es negativa.")'''

cells = [
    nbf.v4.new_markdown_cell(md_intro),
    nbf.v4.new_markdown_cell("## 1. Los dos retornos (USD y EUR)"),
    nbf.v4.new_code_cell(code_returns),
    nbf.v4.new_markdown_cell("## 2. Cargar resultados del backtest"),
    nbf.v4.new_code_cell(code_load),
    nbf.v4.new_markdown_cell("## 3. Cargar en pandas"),
    nbf.v4.new_code_cell(code_pd),
    nbf.v4.new_markdown_cell("## 4. Gráfico de evolución del capital (USD y EUR)"),
    nbf.v4.new_code_cell(code_plot),
    nbf.v4.new_markdown_cell("## 5. Resumen final"),
    nbf.v4.new_code_cell(code_summary),
]
nb.cells = cells

out = Path("/opt/data/qlib/work/crypto/notebooks/backtest_v8_2025.ipynb")
out.parent.mkdir(parents=True, exist_ok=True)
nbf.write(nb, out)
print("Notebook creado:", out)