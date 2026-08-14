#!/usr/bin/env python3
"""Portfolio Momentum Dashboard - Toni's QuantInvest Portfolio

Usage:
    python scripts/portfolio_momentum.py                     # saves to portfolio_momentum.png
    python scripts/portfolio_momentum.py output_chart.png    # custom filename

All calculations use today's date as the end date automatically.
"""

import yfinance as yf
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
from matplotlib.ticker import FuncFormatter
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import sys

# ── Today's Date (dynamic) ────────────────────────────────────────
TODAY = datetime.now().strftime('%Y-%m-%d')
CURRENT_DATE = datetime.now()

# ── Portfolio Config ──────────────────────────────────────────────
PORTFOLIO = {
    'NVO':   {'shares': 8,  'buy_price': 39.79,  'buy_date': '2026-03-10'},
    'AAPL':  {'shares': 8,  'buy_price': 275.10, 'buy_date': '2026-02-05'},
    'GOOGL': {'shares': 10, 'buy_price': 316.30, 'buy_date': '2026-01-05'},
    'MSFT':  {'shares': 13, 'buy_price': 411.98, 'buy_date': '2026-02-09'},
    'META':  {'shares': 3,  'buy_price': 664.00, 'buy_date': '2026-02-05'},
}

OUTPUT_FILE = sys.argv[1] if len(sys.argv) > 1 else 'portfolio_momentum.png'
START_DATE = '2025-12-01'  # a bit before first purchase for context

# ── Fetch Data ────────────────────────────────────────────────────
print(f"📡 Fetching price data (end date: {TODAY})...")
tickers = list(PORTFOLIO.keys())
df_raw = yf.download(tickers, start=START_DATE, end=TODAY, progress=False, auto_adjust=True)

# Handle both old and new yfinance formats
if isinstance(df_raw.columns, pd.MultiIndex):
    df_close = df_raw['Close']
else:
    df_close = df_raw

# Ensure we have all tickers
for t in tickers:
    if t not in df_close.columns:
        print(f"  Warning: {t} not found in columns: {list(df_close.columns)[:10]}...")
        df_close[t] = np.nan

df_close = df_close[tickers].ffill()
print(f"  → {len(df_close)} trading days loaded")

# ── Calculate Portfolio Value ─────────────────────────────────────
portfolio_value = pd.DataFrame(index=df_close.index)
total_value = pd.Series(0.0, index=df_close.index)

for sym, info in PORTFOLIO.items():
    shares = info['shares']
    col = f"{sym}_value"
    portfolio_value[col] = df_close[sym] * shares
    total_value += portfolio_value[col]

portfolio_value['Total'] = total_value

# Daily returns
portfolio_value['Daily_Return'] = portfolio_value['Total'].pct_change() * 100
portfolio_value['Cumulative_Return'] = (portfolio_value['Total'] / portfolio_value['Total'].iloc[0] - 1) * 100

# Rolling momentum (20-day return = ~1 month trading)
portfolio_value['Momentum_20d'] = portfolio_value['Total'].pct_change(20) * 100

# Individual momentum & RSI per ticker
mom_20d_per_ticker = pd.DataFrame(index=df_close.index)
rsi_14d_per_ticker = pd.DataFrame(index=df_close.index)

for sym in tickers:
    # Momentum 20d
    mom_20d_per_ticker[sym] = df_close[sym].pct_change(20) * 100
    # RSI 14d
    delta_sym = df_close[sym].diff()
    gain_sym = delta_sym.clip(lower=0)
    loss_sym = -delta_sym.clip(upper=0)
    avg_gain_sym = gain_sym.rolling(window=14).mean()
    avg_loss_sym = loss_sym.rolling(window=14).mean()
    rs_sym = avg_gain_sym / avg_loss_sym.replace(0, np.nan)
    rsi_14d_per_ticker[sym] = 100 - (100 / (1 + rs_sym))

# RSI (14-day) for portfolio total
delta = portfolio_value['Total'].diff()
gain = delta.clip(lower=0)
loss = -delta.clip(upper=0)
avg_gain = gain.rolling(window=14).mean()
avg_loss = loss.rolling(window=14).mean()
rs = avg_gain / avg_loss.replace(0, np.nan)
portfolio_value['RSI_14'] = 100 - (100 / (1 + rs))

# Individual performance since purchase
perf_since_buy = pd.DataFrame(index=df_close.index)
for sym, info in PORTFOLIO.items():
    buy_price = info['buy_price']
    perf_since_buy[sym] = (df_close[sym] / buy_price - 1) * 100

# ── Current Snapshot ──────────────────────────────────────────────
latest = df_close.iloc[-1]
latest_date = df_close.index[-1]
print(f"\n📊 Portfolio snapshot ({latest_date.date()} / today={TODAY}):")
total_cost = sum(v['shares'] * v['buy_price'] for v in PORTFOLIO.values())
total_now = sum(v['shares'] * latest[sym] for sym, v in PORTFOLIO.items())

for sym, info in PORTFOLIO.items():
    price = latest[sym]
    change_pct = (price / info['buy_price'] - 1) * 100
    value = price * info['shares']
    weight = value / total_now * 100
    rsi_val = rsi_14d_per_ticker[sym].iloc[-1]
    mom_val = mom_20d_per_ticker[sym].iloc[-1]
    rsi_label = ""
    if not np.isnan(rsi_val):
        if rsi_val > 70:
            rsi_label = " ⚠️ SOBRECOMPRA"
        elif rsi_val < 30:
            rsi_label = " ⚠️ SOBREVENDIDO"
    print(f"  {sym:6s} | ${price:>7.2f} | {change_pct:>+6.1f}% | ${value:>7.2f} ({weight:.0f}%) | RSI {rsi_val:5.1f}{rsi_label} | Mom20d {mom_val:+.1f}%")

print(f"\n  Total cost : ${total_cost:,.2f}")
print(f"  Total value: ${total_now:,.2f}")
print(f"  P&L        : ${total_now - total_cost:+,.2f} ({(total_now/total_cost - 1)*100:+.1f}%)")

# ══════════════════════════════════════════════════════════════════
# ── Plot ──────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════
print("\n🎨 Generating chart...")
fig = plt.figure(figsize=(16, 14))
plt.style.use('seaborn-v0_8-darkgrid')

# Colors
COLORS = {'NVO': '#27AE60', 'AAPL': '#8E44AD', 'GOOGL': '#E74C3C', 
           'MSFT': '#F39C12', 'META': '#2980B9'}
BUY_DATES = {sym: info['buy_date'] for sym, info in PORTFOLIO.items()}

def fmt_dollar(x, _):
    return f'${x:,.0f}'

def fmt_pct(x, _):
    return f'{x:.0f}%'

def plot_buy_markers(ax, sym, bd_str, color, label=True):
    """Draw a vertical line at the buy date with optional label."""
    bd = pd.Timestamp(bd_str)
    if bd in df_close.index:
        y_min, y_max = ax.get_ylim()
        ax.axvline(x=bd, color=color, alpha=0.4, linestyle='--', linewidth=1.0, zorder=1)
        if label:
            ax.annotate(sym, xy=(bd, y_max), fontsize=7, fontweight='bold',
                        color=color, ha='left', va='top',
                        xytext=(2, -2), textcoords='offset points',
                        alpha=0.8)

# ── Panel 1: Portfolio Total Value ────────────────────────────────
ax1 = fig.add_subplot(4, 2, (1, 2))
ax1.fill_between(portfolio_value.index, portfolio_value['Total'], alpha=0.15, color='#2563EB')
ax1.plot(portfolio_value.index, portfolio_value['Total'], color='#2563EB', linewidth=2.5, label='Portfolio Value')

# Mark buy dates
for sym, bd_str in BUY_DATES.items():
    plot_buy_markers(ax1, sym, bd_str, COLORS[sym])

ax1.yaxis.set_major_formatter(FuncFormatter(fmt_dollar))
ax1.set_title('Valor Total del Portfolio', fontsize=14, fontweight='bold', pad=10)
ax1.set_ylabel('Valor ($)')
ax1.legend(['Valor Total'], loc='upper left')
ax1.grid(True, alpha=0.3)
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# Add latest value annotation
latest_val = portfolio_value['Total'].iloc[-1]
cost_total = sum(v['shares'] * v['buy_price'] for v in PORTFOLIO.values())
pct_total = (latest_val / cost_total - 1) * 100
ax1.annotate(f'${latest_val:,.0f}\n({pct_total:+.1f}%)',
             xy=(portfolio_value.index[-1], latest_val),
             xytext=(-80, 20), textcoords='offset points',
             fontsize=11, fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.3', facecolor='#2563EB', alpha=0.15),
             arrowprops=dict(arrowstyle='->', color='#2563EB'))

# ── Panel 2: Individual Position Value (Stacked Area) ────────────
ax2 = fig.add_subplot(4, 2, (3, 4))
stack_data = []
labels = []
colors_ordered = []
for sym, info in PORTFOLIO.items():
    stack_data.append(df_close[sym] * info['shares'])
    labels.append(f"{sym} ({info['shares']} sh)")
    colors_ordered.append(COLORS[sym])

ax2.stackplot(df_close.index, stack_data, labels=labels, colors=colors_ordered, alpha=0.85)
ax2.yaxis.set_major_formatter(FuncFormatter(fmt_dollar))
ax2.set_title('Desglose por Posicion', fontsize=14, fontweight='bold', pad=10)
ax2.set_ylabel('Valor ($)')
ax2.legend(loc='upper left', framealpha=0.9)
ax2.grid(True, alpha=0.3)
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# ── Panel 3: Momentum 20d por ticker ─────────────────────────────
ax3 = fig.add_subplot(4, 2, 5)
for sym in tickers:
    serie = mom_20d_per_ticker[sym].dropna()
    ax3.plot(serie.index, serie.values, color=COLORS[sym], linewidth=1.8, 
             label=sym, alpha=0.85)

# Add total portfolio momentum as dashed line
mom_total = portfolio_value['Momentum_20d'].dropna()
ax3.plot(mom_total.index, mom_total.values, color='#333', linewidth=2.2, 
         linestyle='--', label='Portfolio', alpha=0.7)

ax3.axhline(y=0, color='#666', linewidth=0.8)
ax3.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
ax3.set_title('Momentum 20d por Valor (%)', fontsize=13, fontweight='bold', pad=8)
ax3.set_ylabel('Retorno %')
ax3.legend(loc='upper left', ncol=3, fontsize=8)
ax3.grid(True, alpha=0.3)
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# Mark buy dates on momentum panel
for sym, bd_str in BUY_DATES.items():
    plot_buy_markers(ax3, sym, bd_str, COLORS[sym], label=True)

# ── Panel 4: RSI 14d por ticker ──────────────────────────────────
ax4 = fig.add_subplot(4, 2, 6)
for sym in tickers:
    rsi_serie = rsi_14d_per_ticker[sym].dropna()
    ax4.plot(rsi_serie.index, rsi_serie.values, color=COLORS[sym], linewidth=1.8, 
             label=sym, alpha=0.85)

# Add total portfolio RSI as dashed line
rsi_total = portfolio_value['RSI_14'].dropna()
ax4.plot(rsi_total.index, rsi_total.values, color='#333', linewidth=2.2, 
         linestyle='--', label='Portfolio', alpha=0.7)

ax4.axhline(y=70, color='#E74C3C', linestyle='--', alpha=0.5, linewidth=1)
ax4.axhline(y=30, color='#2ECC71', linestyle='--', alpha=0.5, linewidth=1)
ax4.axhline(y=50, color='#999', linestyle=':', alpha=0.4, linewidth=0.8)
ax4.fill_between(rsi_total.index, 70, 100, color='#E74C3C', alpha=0.08)
ax4.fill_between(rsi_total.index, 0, 30, color='#2ECC71', alpha=0.08)
ax4.set_ylim(10, 90)
ax4.set_title('RSI 14d por Valor', fontsize=13, fontweight='bold', pad=8)
ax4.set_ylabel('RSI')
ax4.legend(loc='upper left', ncol=3, fontsize=8)
ax4.grid(True, alpha=0.3)
ax4.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# Mark buy dates on RSI panel
for sym, bd_str in BUY_DATES.items():
    plot_buy_markers(ax4, sym, bd_str, COLORS[sym], label=True)

# ── Panel 5: Individual Performance Since Buy ─────────────────────
ax5 = fig.add_subplot(4, 2, (7, 8))
for sym in tickers:
    info = PORTFOLIO[sym]
    buy_date = pd.Timestamp(info['buy_date'])
    serie = perf_since_buy[sym].loc[buy_date:]
    serie.plot(ax=ax5, color=COLORS[sym], linewidth=2, label=sym, alpha=0.85)
    # Mark the buy point with a dot
    if buy_date in perf_since_buy.index:
        ax5.scatter(buy_date, 0, color=COLORS[sym], s=50, zorder=5, edgecolors='white', linewidth=0.8)

ax5.axhline(y=0, color='#333', linewidth=0.8, linestyle='-', alpha=0.5)
ax5.yaxis.set_major_formatter(FuncFormatter(fmt_pct))
ax5.set_title('Rendimiento desde Compra (%)', fontsize=14, fontweight='bold', pad=10)
ax5.set_ylabel('Retorno %')
ax5.legend(loc='upper left', framealpha=0.9)
ax5.grid(True, alpha=0.3)
ax5.xaxis.set_major_formatter(mdates.DateFormatter('%b %d'))

# Add final values
for sym in tickers:
    final_pct = perf_since_buy[sym].iloc[-1]
    ax5.annotate(f'{final_pct:+.1f}%',
                 xy=(perf_since_buy.index[-1], final_pct),
                 fontsize=9, fontweight='bold', color=COLORS[sym],
                 ha='left', va='center')

# ── Title & Footer ────────────────────────────────────────────────
latest_data_str = latest_date.strftime('%Y-%m-%d')
if latest_data_str == TODAY:
    subtitle = f'Datos: cierre de hoy {TODAY}'
else:
    subtitle = f'Datos: cierre del {latest_data_str} — objetivo {TODAY} (aún sin actualizar)⚠️'

fig.suptitle(f'QuantInvest - Momentum del Portfolio\n{subtitle}',
             fontsize=16, fontweight='bold', y=0.98)

fig.text(0.5, 0.01, 
         f'Coste: ${cost_total:,.0f} | Valor actual: ${latest_val:,.0f} | P&L: ${latest_val-cost_total:+,.0f} ({(latest_val/cost_total-1)*100:+.1f}%)',
         ha='center', fontsize=11, fontweight='bold',
         bbox=dict(boxstyle='round,pad=0.4', facecolor='#F0F0F0', alpha=0.8))

plt.tight_layout(rect=[0, 0.03, 1, 0.95])
plt.savefig(OUTPUT_FILE, dpi=150, bbox_inches='tight')
plt.close()

print(f"\n✅ Chart saved to: {OUTPUT_FILE}")
print(f"   File size: {os.path.getsize(OUTPUT_FILE)/1024:.0f} KB")
