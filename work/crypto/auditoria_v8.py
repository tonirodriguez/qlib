"""auditoria_v8.py — Auditoria del pipeline SFM v8: cuantifica los leaks.

CONTEXTO
    `sfm-v8-resultados.md` reporta Sharpe 2.74 y equity 20.03x en test.
    Son numeros extraordinarios y exigen verificacion.

HALLAZGOS ESTATICOS (leidos del codigo)
    L240:  market_matrix = denoise_market_matrix(market_matrix)
           -> denoising wavelet aplicado a TODA la serie ANTES de cualquier
              split. La wavelet usa coeficientes globales, asi que el valor
              "denoised" de una fecha depende de fechas FUTURAS.

    L221/227: df_close.replace(0, np.nan).ffill().bfill()
           -> `.bfill()` rellena hacia ATRAS usando valores FUTUROS.

    L219:  df_pct = df_close.pct_change().fillna(0)
    L225:  df_vol = df_pct.rolling(20).std()
           -> estos son causales (solo miran al pasado). OK.

QUE MIDE ESTE SCRIPT
    1. Cuanto cambia el denoising el valor de una fecha concreta si se
       recalculan los datos SIN el futuro (comparacion directa del leak).
    2. Cuanto mejora artificialmente la "senal" por ese leak.
    3. Efecto del bfill.

NO necesita qlib: usa datos sinteticos con propiedades similares (crypto-like).

Uso:
    python work/crypto/auditoria_v8.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

# Reproducir EXACTAMENTE las funciones del pipeline
try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False


def wavelet_denoise_1d(signal, wavelet="db2", level=2, mode="soft"):
    """COPIA EXACTA de qlib_sfm_pipeline.v8.py L132-144."""
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    uthresh = sigma * np.sqrt(2 * np.log(len(signal)))
    coeffs_thresh = [coeffs[0]]
    for c in coeffs[1:]:
        coeffs_thresh.append(pywt.threshold(c, uthresh, mode=mode))
    return pywt.waverec(coeffs_thresh, wavelet)[:len(signal)]


def _moving_average_denoise(signal, win=31):
    """SUSTITUTO del wavelet cuando pywt no esta disponible.

    NO es wavelet, pero comparte la propiedad que causa el leak: el valor
    suavizado de una fecha se calcula con una ventana CENTRADA, que incluye
    fechas futuras. Sirve para DEMOSTRAR el mecanismo del leak.

    Con pywt instalado, el script usa el wavelet real y este sustituto no
    se ejecuta.
    """
    s = pd.Series(signal)
    # ventana centrada -> usa pasado Y futuro
    return s.rolling(win, center=True, min_periods=1).mean().to_numpy()


def denoise_1d(signal):
    """Denoising con wavelet si esta disponible; si no, sustituto centrado."""
    if HAS_PYWT:
        return wavelet_denoise_1d(signal)
    return _moving_average_denoise(signal)


def denoise_market_matrix(market_matrix):
    """COPIA de qlib_sfm_pipeline.v8.py L147-158 (con el sustituto si no hay pywt).

    LO IMPORTANTE: se aplica a la matriz ENTERA, sin split. Esa es la linea
    exacta del leak (L240 del pipeline).
    """
    denoised = np.zeros_like(market_matrix)
    for col in range(market_matrix.shape[1]):
        denoised[:, col] = denoise_1d(market_matrix[:, col])
    return denoised


def main() -> int:
    print("=" * 76)
    print(" AUDITORIA SFM v8 — CUANTIFICACION DE LEAKS")
    print("=" * 76)
    if HAS_PYWT:
        print("  metodo: wavelet db2 level2 (el REAL del pipeline)")
    else:
        print("  metodo: sustituto de ventana CENTRADA (pywt no disponible)")
        print("          NO es el wavelet real, pero comparte la propiedad que")
        print("          causa el leak: usar fechas futuras en el suavizado.")
        print("          Para el wavelet exacto: pip install PyWavelets")

    rng = np.random.default_rng(42)
    n = 1800
    # Serie tipo crypto: tendencia + volatilidad variable + ruido
    rets = rng.normal(0.0008, 0.035, n)
    price = 100 * np.cumprod(1 + rets)

    print(f"\n  serie sintetica: {n} puntos")

    # ------------------------------------------------------------------
    # LEAK 1: denoising global vs causal
    # ------------------------------------------------------------------
    print("\n" + "=" * 76)
    print(" LEAK 1 — Denoising wavelet sobre TODA la serie (L240)")
    print("=" * 76)

    full = denoise_market_matrix(price.reshape(-1, 1)).ravel()

    # Version causal: para cada fecha t, denoising usando SOLO datos <= t.
    # Se hace en una ventana rodante de tamano W (el wavelet necesita un
    # tamano minimo para descomponer a level=2).
    W = 256
    causal = np.full(n, np.nan)
    for t in range(W, n):
        window = price[t - W:t + 1]
        d = denoise_1d(window)
        causal[t] = d[-1]  # solo el valor de HOY

    valid = ~np.isnan(causal)
    diff = np.abs(full[valid] - causal[valid])
    rel = diff / np.abs(price[valid])

    print(f"  ventana causal: {W} puntos")
    print(f"  fechas comparadas: {valid.sum()}")
    print(f"\n  DIFERENCIA entre denoising global y causal:")
    print(f"    media  |diff| : {diff.mean():.6f}")
    print(f"    max    |diff| : {diff.max():.6f}")
    print(f"    media  relativa: {rel.mean()*100:.4f}%  (sobre el precio)")

    # El leak es informacion del futuro que entra en el presente
    # Correlacion entre el error y el retorno FUTURO: si el denoising
    # "sabe" lo que va a pasar, el error debe correlacionar con ello.
    fut_ret = np.full(n, np.nan)
    fut_ret[:-1] = price[1:] / price[:-1] - 1
    m = valid & ~np.isnan(fut_ret)
    err = (full - price)  # cuanto mueve el denoising el valor actual
    corr = np.corrcoef(err[m], fut_ret[m])[0, 1]

    print(f"\n  ¿el denoising 'sabe' el futuro?")
    print(f"    correlacion(ajuste_denoising_hoy, retorno_manana) = {corr:+.4f}")
    if abs(corr) > 0.05:
        print(f"    >>> LEAK CONFIRMADO: el denoising incorpora informacion futura")
    else:
        print(f"    correlacion baja: el leak existe pero no domina en esta serie")

    # ------------------------------------------------------------------
    # LEAK 2: efecto sobre la label
    # ------------------------------------------------------------------
    print("\n" + "=" * 76)
    print(" LEAK 2 — El denoising tambien contamina la LABEL")
    print("=" * 76)

    # En el pipeline, la label es (close.shift(-1)/close - 1) sobre el precio
    # CRUDO (L242-243), no sobre el denoised. Pero la FEATURE 'close' SI esta
    # denoised, asi que el modelo ve un close "suavizado" mientras la label
    # usa el crudo. Eso genera una inconsistencia.
    label = np.full(n, np.nan)
    label[:-1] = price[1:] / price[:-1] - 1

    # 'close' denoised como feature
    feat_den = full
    # correlacion entre el cambio del feature denoised y la label
    d_feat_full = np.diff(feat_den)
    d_feat_causal = np.diff(causal)
    lab = label[1:]

    m2 = ~np.isnan(d_feat_causal) & ~np.isnan(lab)
    c_full = np.corrcoef(d_feat_full[m2], lab[m2])[0, 1]
    c_causal = np.corrcoef(d_feat_causal[m2], lab[m2])[0, 1]

    print(f"  correlacion(feature_close, label) — como la ve el modelo:")
    print(f"    con denoising GLOBAL (actual) : {c_full:+.4f}")
    print(f"    con denoising CAUSAL          : {c_causal:+.4f}")
    print(f"    mejora artificial por el leak : {abs(c_full)-abs(c_causal):+.4f}")
    if abs(c_full) > abs(c_causal):
        print(f"    >>> El leak INFLA la correlacion feature-label")
        print(f"        (el modelo 've' mas senal de la que tendria en produccion)")

    # ------------------------------------------------------------------
    # LEAK 3: bfill
    # ------------------------------------------------------------------
    print("\n" + "=" * 76)
    print(" LEAK 3 — bfill() hacia atras (L221, L227)")
    print("=" * 76)

    # El caso real del pipeline: una moneda que EMPIEZA mas tarde que las
    # demas (p.ej. SOL empieza en 2020, BTC en 2015). Al combinarlas, las
    # fechas previas al lanzamiento quedan NaN al PRINCIPIO de su columna.
    #
    #   .ffill() -> no puede rellenar: no hay valor anterior. Deja NaN.
    #   .bfill() -> rellena con el PRIMER valor disponible, que es FUTURO
    #               respecto a esas fechas.
    #
    # Eso significa que en 2016 la columna de SOL contiene el precio de 2020:
    # el modelo "ve" el futuro de esa moneda.
    s = pd.Series(price)
    s_with_leading_nan = s.copy()
    s_with_leading_nan.iloc[0:100] = np.nan   # moneda que empieza en t=100

    ffill_only = s_with_leading_nan.ffill()
    with_bfill = s_with_leading_nan.ffill().bfill()

    print(f"  caso real: moneda que empieza en t=100 (NaN en t=0..99)")
    print(f"  valor en t=100 (primer dato real) : {s.iloc[100]:.4f}")
    print(f"  ffill deja NaN en t=0..99         : {ffill_only.iloc[0:100].isna().sum()} NaN")
    print(f"  bfill pone en t=0..99             : {with_bfill.iloc[0]:.4f}")
    print(f"  (el modelo ve en 2016 el precio de 2020)")
    if (ffill_only.iloc[0:100].isna().all()
            and abs(with_bfill.iloc[0] - s.iloc[100]) < 1e-9):
        print("  >>> CONFIRMADO: bfill propaga el PRIMER valor futuro al pasado")
        print("      Afecta a TODAS las fechas previas al lanzamiento de cada moneda.")

    # ------------------------------------------------------------------
    # RESUMEN
    # ------------------------------------------------------------------
    print("\n" + "=" * 76)
    print(" RESUMEN")
    print("=" * 76)
    print(f"  L1 denoising global  : diff media {diff.mean():.6f} ({rel.mean()*100:.4f}% del precio)")
    print(f"  L2 inflado de senal  : {abs(c_full)-abs(c_causal):+.4f} de correlacion")
    print(f"  L3 bfill             : propaga valores futuros (confirmado)")
    print()
    print("  Los tres afectan a la FEATURE. La label (L242) usa precio crudo,")
    print("  asi que hay ademas una INCONSISTENCIA feature-label.")
    print()
    print("  CONSECUENCIA: las metricas de test (Sharpe 2.74, equity 20x)")
    print("  NO son evidencia valida de rendimiento fuera de muestra.")
    print("=" * 76)
    return 0


if __name__ == "__main__":
    sys.exit(main())
