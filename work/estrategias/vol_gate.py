"""vol_gate.py — Regla de vol-gating simple para el libro táctico (momentum).

Según el plan de Quinn (Semana 5): prototipo de vol-gating NO-HMM.
Métrica: percentil de la vol realizada 20d del mercado (SP500/proxy).
Regla con histéresis para evitar churn (apagar/encender cada día).

La idea: cuando la vol del mercado está alta, el momentum falla (confirmado
en regimen_test.py, IC -0.18 en estrés). Reducir/pausar el momentum en ese
estado captura el beneficio de evitar el momentum-crash.

Uso como módulo: from vol_gate import get_gate_level
"""
import numpy as np
import pandas as pd


def realized_vol(close, win=20):
    """Volatilidad realizada anualizada (ventana rolante de retornos diarios)."""
    s = close / close.shift(1) - 1
    return s.rolling(win).std() * np.sqrt(252)


def vol_percentile(close, vol_win=20, hist_win=252):
    """Percentil CAUSAL de la vol realizada (valor de hoy vs su historia pasada).

    CORREGIDO 2026-10-17 (dos bugs reales detectados en producción):

    1. **Rama equivocada con historia corta.** Antes, si `len(vol) <= hist_win` se usaba
       `vol / vol.max()`, que NO es un percentil sino "fracción de la vol máxima". Como
       `prices_live.csv` tiene 160 filas (< 252), la simulación en vivo ejecutaba esa rama
       mientras la validación (con años de historia Qlib) ejecutaba el percentil → **el gate
       validado y el gate desplegado eran reglas distintas**. Ahora la ventana se ESCALA a la
       historia disponible: `win = min(hist_win, n)`, conservando la semántica de percentil.
    2. **Look-ahead.** `vol.max()` es una estadística de toda la muestra (incluye el futuro).
       Eliminado: el percentil se calcula solo con el pasado (`x.iloc[:-1]`).
    """
    vol = realized_vol(close, vol_win)
    n = int(len(vol))
    if n == 0:
        return vol, vol
    win = int(min(hist_win, n)) if hist_win else n
    if win < 10:
        # Sin historia suficiente no hay percentil posible: devolvemos NaN (no una regla falsa).
        return vol, pd.Series(np.nan, index=vol.index)
    minp = max(10, min(win // 2, 60))
    # percentil causal: fracción de valores PASADOS por debajo del de hoy
    pct = vol.rolling(win, min_periods=minp).apply(
        lambda x: (x.iloc[-1] > x.iloc[:-1]).mean(), raw=False
    )
    return vol, pct


def gate_level_from_pct(pct, p75=0.75, p90=0.90):
    """Nivel de gate (0..1) según el percentil de vol, con 3 estados."""
    if pct < p75:
        return 1.0
    elif pct < p90:
        return 0.5
    else:
        return 0.0


def gate_series_gated(close, p75=0.75, p90=0.90, hysteresis_days=5,
                      vol_win=20, hist_win=252):
    """Serie temporal de niveles de gate con histéresis.

    La histéresis evita churn: una vez que baja de estado, se mantiene N días
    antes de volver a subir (no apaga/enciende cada día).
    """
    vol, pct = vol_percentile(close, vol_win, hist_win)
    raw = pct.apply(lambda x: gate_level_from_pct(x, p75, p90) if pd.notna(x) else 1.0)
    raw = raw.fillna(1.0)
    return _apply_hysteresis(raw, hysteresis_days)


def _apply_hysteresis(gate, hyst_days):
    """Aplana: si gate < 1.0, se mantiene así durante hyst_days antes de subir."""
    g = gate.copy()
    v = g.values
    n = len(v)
    out = np.ones(n)
    i = 0
    while i < n:
        if v[i] < 1.0:
            # mantener este nivel (o menor) durante hyst_days
            level = v[i]
            for j in range(i, min(i + hyst_days, n)):
                out[j] = min(level, v[j]) if v[j] >= 0 else level
            i += hyst_days
        else:
            out[i] = v[i]
            i += 1
    return pd.Series(out, index=gate.index)
