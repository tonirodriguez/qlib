"""
qlib_sfm_pipeline.v9_causal.py — SFM v9: v8 SIN LEAKS. Mide el rendimiento REAL.

POR QUE EXISTE (auditoria 2026-10-26, ver AUDITORIA_V8.md)
    El pipeline v8 tiene TRES fugas de informacion futura que inflan sus
    metricas:

      L1  L240  denoise_market_matrix() sobre TODA la matriz, antes del split.
                La wavelet usa coeficientes globales -> el valor suavizado de
                una fecha depende de fechas FUTURAS.
                Medido: correlacion(ajuste_hoy, retorno_manana) = +0.244

      L2  L240+242  la feature 'close' va denoised pero la label usa el precio
                crudo. Correlacion feature-label: +0.1629 (global) vs -0.0205
                (causal). TODA la senal aparente desaparece al quitar el leak.

      L3  L221/227  .ffill().bfill() rellena hacia ATRAS. Con monedas que
                empiezan en fechas distintas, propaga el primer precio FUTURO
                a todo el pasado de esa moneda.
                (El modelo ve en 2016 el precio de SOL de 2020.)

    Resultado: el Sharpe 2.74 y la equity 20.03x de v8 NO son evidencia valida.

QUE HACE v9
    Aplica las 3 correcciones y re-entrena con los mismos hiperparametros,
    para poder COMPARAR v8 vs v9 y cuantificar cuanto del rendimiento era leak.

    Correcciones:
      1. Denoising DENTRO del fold: se ajusta con train y se aplica a val/test.
         (Igual que ya hace bien el MinMaxScaler.)
      2. Sin bfill: se deja NaN y se enmascara. Las fechas previas al
         lanzamiento de una moneda NO tienen dato.
      3. Consistencia: la label se calcula sobre el precio CRUDO en ambos casos
         (ya era asi), pero la feature 'close' tambien se deja cruda para no
         mezclar representaciones. El denoising se aplica como una feature
         MAS, no sustituyendo.

MODO DE USO
    # Comparacion v8 vs v9 (recomendado)
    conda run -n qlib python work/crypto/qlib_sfm_pipeline.v9_causal.py --compare

    # Solo v9, mas trials
    conda run -n qlib python work/crypto/qlib_sfm_pipeline.v9_causal.py --trials 60

    # Prueba rapida
    conda run -n qlib python work/crypto/qlib_sfm_pipeline.v9_causal.py --trials 5 --epochs 30

SALIDA
    work/crypto/output/sfm_v9_causal/
        v9_results.json      metricas de v9
        comparison.json      v8 vs v9 lado a lado
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.preprocessing import MinMaxScaler
from torch.utils.data import DataLoader, TensorDataset

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

SEED = 42
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)

try:
    import pywt
    HAS_PYWT = True
except ImportError:
    HAS_PYWT = False
    print("AVISO: pywt no instalado. El denoising wavelet se omitira.")
    print("       pip install PyWavelets   (para reproducir v8 fielmente)")

try:
    import optuna
    from optuna.pruners import MedianPruner
    from optuna.samplers import TPESampler
    HAS_OPTUNA = True
except ImportError:
    HAS_OPTUNA = False

# IMPORTANTE: en data/qlib los instrumentos estan en MINUSCULAS
# (verificado 2026-10-26 en instruments/crypto.txt: ada, btc, doge, eth,
#  link, ltc, sol, xlm, xrp). El dataset cubre 2010-07-17 -> 2026-10-22.
CRYPTOS = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
START_DATE = "2015-01-01"
END_DATE = "2026-10-22"
FWD_DAYS = 1
LOOKBACK = 20

# Valores de v8 (documentados en sfm-v8-resultados.md), para comparar
V8_REPORTADO = {
    "sharpe_top5_mean": 2.17,
    "sharpe_best": 2.74,
    "equity_top5_mean": 10.49,
    "equity_best": 20.03,
    "diracc_mean": 0.581,
}


# =====================================================================
# DENOISING (la funcion del pipeline, sin cambios)
# =====================================================================
def wavelet_denoise_1d(signal, wavelet="db2", level=2, mode="soft"):
    """Denoising wavelet. OJO: usa coeficientes GLOBALES -> no es causal."""
    if not HAS_PYWT:
        return signal
    coeffs = pywt.wavedec(signal, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    uthresh = sigma * np.sqrt(2 * np.log(len(signal)))
    coeffs_thresh = [coeffs[0]]
    for c in coeffs[1:]:
        coeffs_thresh.append(pywt.threshold(c, uthresh, mode=mode))
    return pywt.waverec(coeffs_thresh, wavelet)[: len(signal)]


def denoise_columns(matrix: np.ndarray) -> np.ndarray:
    if not HAS_PYWT:
        return matrix
    out = np.zeros_like(matrix)
    for j in range(matrix.shape[1]):
        out[:, j] = wavelet_denoise_1d(matrix[:, j])
    return out


# =====================================================================
# CARGA DE DATOS — CORREGIDA
# =====================================================================
def load_close(start_date=START_DATE, end_date=END_DATE) -> pd.DataFrame:
    """Solo carga los precios. Ninguna transformacion (esas van por fold)."""
    import qlib
    from qlib.config import REG_US
    from qlib.data import D

    # MISMAS variables que usa el pipeline v8 y sfm_daily_signal.py:
    #   CRYPTO_QLIB_OUTPUT_DIR (default "data/qlib")
    candidates = [
        os.environ.get("CRYPTO_QLIB_OUTPUT_DIR"),
        "data/qlib",
        str(HERE / "data" / "qlib"),
        "work/crypto/data/qlib",
    ]
    uri = None
    for cand in candidates:
        if not cand:
            continue
        # una instalacion qlib valida tiene instruments/ y calendars/
        if (os.path.isdir(os.path.join(cand, "instruments"))
                or os.path.isdir(os.path.join(cand, "calendars"))):
            uri = cand
            break
    if uri is None:
        raise FileNotFoundError(
            "No encuentro los datos crypto de qlib.\n"
            "  Se probaron: " + ", ".join(str(c) for c in candidates if c) + "\n"
            "  Define la variable (igual que v8):\n"
            "      export CRYPTO_QLIB_OUTPUT_DIR=/ruta/a/data/qlib\n"
            "  Comprueba con:\n"
            "      ls data/qlib/instruments/"
        )
    print(f"  provider_uri: {uri}")
    qlib.init(provider_uri=uri, region=REG_US, kernels=int(os.getenv("QLIB_KERNELS", "1")))

    # Averiguar los nombres REALES de los instrumentos (pueden estar en
    # mayusculas o minusculas segun como se generara el dataset).
    insts: list[str] = []
    try:
        insts = D.list_instruments(D.instruments("all"), as_list=True)
    except Exception:  # noqa: BLE001
        pass
    lookup = {i.lower(): i for i in insts} if insts else {}

    start_ts = pd.Timestamp(start_date) - pd.DateOffset(days=120)
    end_date_ts = pd.Timestamp(end_date)
    close_dict = {}
    for c in CRYPTOS:
        # resolver el nombre real: exacto, o por coincidencia sin distinguir caso
        name = c if (not lookup or c in insts) else lookup.get(c.lower(), c)
        try:
            df = D.features([name], ["$close"], start_time=start_ts,
                            end_time=end_date_ts)
        except Exception as exc:  # noqa: BLE001
            print(f"  {c}: ERROR -> {str(exc)[:120]}")
            continue
        if df is None or df.empty:
            print(f"  {c}: SIN DATOS (probado como '{name}')")
            continue
        try:
            s = df.reset_index().pivot(index="datetime",
                                       columns="instrument",
                                       values="$close")[name]
        except KeyError:
            # el pivot puede devolver otra capitalizacion
            cols = list(df.reset_index()["instrument"].unique())
            if not cols:
                print(f"  {c}: sin columnas")
                continue
            s = df.reset_index().pivot(index="datetime",
                                       columns="instrument",
                                       values="$close")[cols[0]]
        close_dict[c] = s          # se guarda con la clave canonica (mayusculas)
        print(f"  {c}: {s.notna().sum()} valores "
              f"[{s.first_valid_index()} -> {s.last_valid_index()}]")
    if not close_dict:
        # diagnostico util: que instrumentos HAY de verdad
        try:
            insts = D.list_instruments(D.instruments("all"), as_list=True)
            print(f"\n  DIAGNOSTICO: el dataset tiene {len(insts)} instrumentos.")
            print(f"  Muestra: {insts[:20]}")
            print(f"  ¿Alguno de los esperados? "
                  f"{[c for c in CRYPTOS if c in insts]}")
        except Exception as exc:  # noqa: BLE001
            print(f"  No se pudo listar instrumentos: {str(exc)[:120]}")
        raise ValueError(
            "No se cargo ninguna cripto. Los nombres pueden diferir: revisa "
            "la lista de instrumentos de arriba y ajusta CRYPTOS en el script."
        )
    df = pd.DataFrame(close_dict).sort_index()
    df = df[df.index >= pd.Timestamp(start_date)]
    return df


def build_features(df_close: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Features. TODAS causales (solo miran al pasado).

    CORRECCION L3: SIN .bfill(). Las fechas previas al lanzamiento de una
    moneda quedan NaN, que es la verdad: ese dato no existia.
    """
    safe = df_close.replace(0, np.nan).ffill()          # <-- solo ffill

    return {
        # NOTA: 'close' se deja CRUDA para no mezclar representaciones con la
        # label (correccion L2). El denoising se anade como feature aparte.
        "close": df_close,
        "pct": df_close.pct_change(),
        "ratio_5d": (df_close.rolling(5).mean() / safe),
        "vol_20d": df_close.pct_change().rolling(20).std(),
        "ma20_ratio": (df_close.rolling(20).mean() / safe),
        "rango": df_close.pct_change().abs(),
    }


def make_matrix(feats: dict[str, pd.DataFrame], cols: list[str]) -> np.ndarray:
    return np.hstack([feats[k][cols].to_numpy() for k in feats])


# =====================================================================
# NORMALIZACION + DENOISING DENTRO DEL FOLD  (correcciones L1 y L2)
# =====================================================================
def fit_transform_fold(matrix: np.ndarray, i_train_end: int,
                       i_val_end: int, use_denoise: bool = True):
    """Ajusta scaler (y denoising) SOLO con train; aplica a todo.

    Devuelve (train_s, val_s, test_s). El denoising se ajusta con el tramo
    de train y se aplica a val/test — NO se recalcula sobre ellos, para no
    introducir informacion futura.

    NOTA: el denoising wavelet no tiene "parametros" que ajustar; el leak
    venia de aplicarlo a la serie COMPLETA. Aqui se aplica por tramos, de
    modo que el valor de una fecha de test solo usa datos de ese tramo.
    """
    tr = matrix[:i_train_end]
    va = matrix[i_train_end:i_val_end]
    te = matrix[i_val_end:]

    # scaler ajustado SOLO con train
    scaler = MinMaxScaler(feature_range=(-1, 1))
    # NaN -> se imputan con la mediana de TRAIN (no del total)
    med = np.nanmedian(tr, axis=0)
    med = np.where(np.isfinite(med), med, 0.0)

    def prep(a):
        a = np.where(np.isfinite(a), a, med)
        return a

    tr, va, te = prep(tr), prep(va), prep(te)

    if use_denoise:
        # denoising por tramo (no sobre la serie entera)
        tr = denoise_columns(tr)
        va = denoise_columns(va)
        te = denoise_columns(te)

    tr_s = scaler.fit_transform(tr)
    va_s = scaler.transform(va)
    te_s = scaler.transform(te)

    # --- CONTROL DE CALIDAD: detectar NaN en cada etapa ---
    # Si queda NaN aqui, entra al modelo y torch lo propaga a TODA la salida
    # (predicciones = NaN), que es el sintoma observado.
    for nm, arr in (("train", tr_s), ("val", va_s), ("test", te_s)):
        n = int(np.isnan(arr).sum())
        if n:
            bad_cols = np.where(np.isnan(arr).any(axis=0))[0]
            print(f"    [QA] {nm}: {n} NaN en {len(bad_cols)} columnas "
                  f"{list(bad_cols[:10])}")
            # intentar arreglarlo: imputar los NaN residuales con 0
            arr[np.isnan(arr)] = 0.0
    for nm, arr in (("train", tr_s), ("val", va_s), ("test", te_s)):
        n_inf = int(np.isinf(arr).sum())
        if n_inf:
            print(f"    [QA] {nm}: {n_inf} inf -> recortados a +-1e6")
            arr[np.isinf(arr)] = np.sign(arr[np.isinf(arr)]) * 1e6

    return tr_s, va_s, te_s


def make_windows(m: np.ndarray, y: np.ndarray, lookback: int,
                 valid: np.ndarray | None = None):
    """Ventanas deslizantes. MISMA forma que v8 (L264-269).

    v8:  X.append(market_matrix[i:i+lookback, :])   -> (lookback, n_feats)
         y.append(labels_matrix[i+lookback, :])     -> (n_monedas,)

    El modelo predice las N MONEDAS A LA VEZ (salida de dimension n_monedas).

    `valid` (opcional): mascara (T, n_coins) de labels reales. Las monedas
    sin label valida en una fecha se marcan como NaN en Y, y el MSE las
    ignora (ver `masked_mse`). Sin esto, los NaN de `shift(-1)` entran al
    target y contaminan toda la red.
    """
    X, Y = [], []
    for i in range(len(m) - lookback - 1):
        j = i + lookback
        if j >= len(y):
            break
        X.append(m[i:j, :])
        row = y[j, :].astype(np.float32).copy()
        if valid is not None and j < len(valid):
            row = np.where(valid[j], row, np.nan)
        Y.append(row)
    return np.asarray(X, dtype=np.float32), np.asarray(Y, dtype=np.float32)


def masked_mse(pred, target):
    """MSE ignorando las posiciones con target NaN.

    Necesario porque las monedas que aun no cotizaban no tienen label.
    Un MSE normal con NaN contagia toda la red.
    """
    import torch
    mask = torch.isfinite(target)
    if mask.sum() == 0:
        return torch.tensor(0.0, requires_grad=True, device=pred.device)
    diff2 = (pred - torch.nan_to_num(target, nan=0.0)) ** 2
    return diff2[mask].mean()


# =====================================================================
# MODELO (simplificado; el objetivo es medir el leak, no la arquitectura)
# =====================================================================
class SFMSmall(nn.Module):
    """MLP que predice las N MONEDAS a la vez.

    Entrada: (batch, lookback, n_features) -> se aplana a
             (batch, lookback * n_features)
    Salida : (batch, n_coins)  -- un retorno esperado por moneda

    NOTA: v8 usa `SFMCellRefined` con componentes de frecuencia. Aqui se usa
    un MLP porque el objetivo es aislar el efecto del LEAK, no replicar la
    arquitectura. Los deltas vs v8 son comparables; los niveles absolutos no.
    """

    def __init__(self, n_in, n_out, hidden=96, dropout=0.3):
        super().__init__()
        self.n_out = n_out
        self.net = nn.Sequential(
            nn.Flatten(),                       # (B, lookback*n_feats)
            nn.Linear(n_in, hidden), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden, hidden // 2), nn.ReLU(), nn.Dropout(dropout),
            nn.Linear(hidden // 2, n_out),      # <- n_coins salidas
        )

    def forward(self, x):
        return self.net(x)


def train_eval(Xtr, ytr, Xva, yva, Xte, yte, hidden=96, dropout=0.3,
               lr=1e-3, wd=1e-4, epochs=60, bs=16, patience=10):
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # n_in = lookback * n_features (Xtr tiene forma (N, lookback, n_feats))
    n_in = int(np.prod(Xtr.shape[1:]))
    n_out = int(ytr.shape[1]) if ytr.ndim > 1 else 1
    model = SFMSmall(n_in, n_out, hidden, dropout).to(dev)
    opt = optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    lossf = masked_mse          # ignora targets NaN (monedas sin cotizar)

    # Los NaN en el target se conservan (el masked_mse los ignora).
    # Se comprueba que la ENTRADA no tenga NaN: si los tiene, torch propaga
    # NaN por toda la red y las predicciones salen NaN (el sintoma que vimos).
    for nm, arr in (("Xtr", Xtr), ("Xva", Xva), ("Xte", Xte)):
        n = int(np.isnan(arr).sum())
        if n:
            print(f"    [BUG] {nm} tiene {n} NaN -> se imputan a 0")
            arr[np.isnan(arr)] = 0.0

    tr_ld = DataLoader(TensorDataset(torch.from_numpy(Xtr), torch.from_numpy(ytr)),
                       batch_size=bs, shuffle=True)
    va_x = torch.from_numpy(Xva).to(dev)
    va_y = torch.from_numpy(yva).to(dev)

    best, best_state, bad = np.inf, None, 0
    for ep in range(epochs):
        model.train()
        for xb, yb in tr_ld:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad()
            loss = lossf(model(xb), yb)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = lossf(model(va_x), va_y).item()
        if vl < best - 1e-6:
            best, best_state, bad = vl, deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= patience:
                break
    if best_state:
        model.load_state_dict(best_state)

    model.eval()
    with torch.no_grad():
        pv = model(torch.from_numpy(Xva).to(dev)).cpu().numpy()
        pt = model(torch.from_numpy(Xte).to(dev)).cpu().numpy()
    return pv, pt


def metrics(preds: np.ndarray, real: np.ndarray, periods: int = 365) -> dict:
    """Metricas cross-sectional sobre N monedas por fecha.

    preds/real tienen forma (T, n_coins): una prediccion y un retorno por
    moneda y fecha. Se replica la logica de v8:

      - dir_acc  : acierto direccional sobre TODAS las observaciones
      - estrategia: long la mejor moneda de cada fecha (top-1), solo si su
                    retorno esperado es positivo. Si no, esa fecha va a cash.
      - Sharpe   : anualizado con `periods`

    Se usa top-1 (no la media) porque es lo que hace v8 en su evaluacion.
    """
    preds = np.asarray(preds, dtype=float)
    real = np.asarray(real, dtype=float)
    if preds.ndim == 1:
        preds = preds.reshape(-1, 1)
        real = real.reshape(-1, 1)

    mask = np.isfinite(preds) & np.isfinite(real)
    if mask.sum() < 10:
        return {"sharpe": float("nan"), "equity": float("nan"),
                "dir_acc": float("nan"), "n": int(mask.sum()),
                "_why": f"pocos datos validos ({int(mask.sum())})"}

    dir_acc = float(np.mean(np.sign(preds[mask]) == np.sign(real[mask])))

    # long la mejor moneda de cada fecha, solo si la prediccion es positiva
    rets = []
    for t in range(preds.shape[0]):
        p = preds[t]
        r = real[t]
        ok = np.isfinite(p) & np.isfinite(r)
        if not ok.any():
            continue
        p_ok = np.where(ok, p, -np.inf)
        j = int(np.argmax(p_ok))
        rets.append(r[j] if p_ok[j] > 0 else 0.0)   # cash si no hay senal positiva
    rets = np.asarray(rets, dtype=float)
    rets = rets[np.isfinite(rets)]
    if len(rets) < 10:
        return {"sharpe": float("nan"), "equity": float("nan"),
                "dir_acc": dir_acc, "n": int(len(rets)),
                "_why": f"solo {len(rets)} fechas con retorno"}
    if rets.std() == 0:
        n_pos = int((rets != 0).sum())
        return {"sharpe": float("nan"), "equity": float("nan"),
                "dir_acc": dir_acc, "n": int(len(rets)),
                "_why": (f"desviacion cero: la estrategia nunca tomo posicion "
                         f"({n_pos}/{len(rets)} fechas con retorno != 0). "
                         f"Probablemente todas las predicciones son <= 0.")}
    sharpe = float(rets.mean() / rets.std() * np.sqrt(periods))
    equity = float(np.cumprod(1 + rets)[-1])
    return {"sharpe": sharpe, "equity": equity, "dir_acc": dir_acc,
            "n": int(len(rets))}


# =====================================================================
# MAIN
# =====================================================================
def run(use_denoise: bool, trials: int, epochs: int, label: str) -> dict:
    print("\n" + "=" * 76)
    print(f" {label}")
    print("=" * 76)
    print(f"  denoising: {'SI (por tramos)' if use_denoise else 'NO'}")
    print(f"  trials: {trials} | epochs: {epochs}")

    df_close = load_close()
    print(f"  datos: {df_close.shape[0]} fechas x {df_close.shape[1]} monedas")
    print(f"  rango: {df_close.index[0].date()} -> {df_close.index[-1].date()}")

    feats = build_features(df_close)
    cols = list(df_close.columns)
    matrix = make_matrix(feats, cols)
    labels = (df_close.shift(-FWD_DAYS) / df_close - 1).to_numpy()

    # --- LIMPIEZA DE LABELS (causa del NaN en las predicciones) ---
    # `shift(-1)` deja NaN en la ULTIMA fecha de cada moneda, y hay NaN en
    # todas las fechas previas a su lanzamiento. Si esos NaN llegan al MSE,
    # torch propaga NaN por TODA la red -> predicciones = NaN -> Sharpe NaN.
    #
    # Se marcan (no se imputan) y se filtran al construir las ventanas.
    n_nan_lab = int(np.isnan(labels).sum())
    if n_nan_lab:
        print(f"  labels: {n_nan_lab} NaN "
              f"({100*n_nan_lab/labels.size:.1f}%) -> se excluyen del target")
    labels = np.nan_to_num(labels, nan=0.0, posinf=0.0, neginf=0.0)
    # mascara de validez: 1 donde la label era real
    label_valid = np.isfinite(
        (df_close.shift(-FWD_DAYS) / df_close - 1).to_numpy())

    n = len(matrix)
    i_tr = int(n * 0.6)
    i_va = int(n * 0.8)
    print(f"  split: train 0-{i_tr} | val {i_tr}-{i_va} | test {i_va}-{n}")

    if use_denoise and not HAS_PYWT:
        print("  AVISO: pywt ausente -> denoising OMITIDO")

    tr_s, va_s, te_s = fit_transform_fold(matrix, i_tr, i_va, use_denoise)

    Xtr, ytr = make_windows(tr_s, labels[:i_tr], LOOKBACK, label_valid[:i_tr])
    Xva, yva = make_windows(va_s, labels[i_tr:i_va], LOOKBACK,
                            label_valid[i_tr:i_va])
    Xte, yte = make_windows(te_s, labels[i_va:], LOOKBACK, label_valid[i_va:])
    print(f"  ventanas: train {Xtr.shape} | val {Xva.shape} | test {Xte.shape}")

    # Busqueda de hiperparametros (o un unico modelo si no hay optuna)
    results = []
    _diag: dict = {}
    if HAS_OPTUNA and trials > 1:
        def obj(t):
            hid = t.suggest_categorical("hidden", [32, 64, 96, 112])
            drop = t.suggest_float("dropout", 0.1, 0.5)
            lr = t.suggest_float("lr", 1e-4, 3e-3, log=True)
            wd = t.suggest_float("wd", 1e-6, 1e-3, log=True)
            pv, _ = train_eval(Xtr, ytr, Xva, yva, Xte, yte, hid, drop, lr, wd,
                               epochs=max(20, epochs // 3))
            m = metrics(pv, yva)
            # direction="minimize" -> devolvemos -Sharpe (menor = mejor).
            # Si el Sharpe no es finito, devolvemos un PENALIZADOR GRANDE
            # POSITIVO (= malo), no +10 (que seria "bueno" al minimizar).
            # El bug anterior devolvia -(-10)=+10, y Optuna lo veia como el
            # mejor valor posible -> todos los trials empataban en 10.0.
            if not np.isfinite(m["sharpe"]):
                _diag["n_nan"] = _diag.get("n_nan", 0) + 1
                return 1e6
            return -float(m["sharpe"])

        study = optuna.create_study(direction="minimize",
                                    sampler=TPESampler(seed=SEED),
                                    pruner=MedianPruner())
        study.optimize(obj, n_trials=trials, show_progress_bar=False)

        # --- AVISO si la optimizacion no encontro nada util ---
        n_nan = _diag.get("n_nan", 0)
        if n_nan:
            print(f"\n  AVISO: {n_nan}/{trials} trials dieron Sharpe NO FINITO.")
        finished = [t for t in study.trials if t.value is not None]
        all_failed = bool(finished) and all(abs(t.value - 1e6) < 1.0
                                            for t in finished)
        if all_failed:
            print("\n  " + "!" * 68)
            print("  TODOS los trials fallaron (Sharpe no finito).")
            print("  La optimizacion NO es valida. Diagnostico probable:")
            print("    - la estrategia nunca toma posicion (predicciones <= 0)")
            print("    - o los retornos son todos cero")
            print("  Revisa la seccion de diagnostico de abajo.")
            print("  " + "!" * 68)
        if finished:
            vals = [t.value for t in finished]
            print(f"\n  Optuna: {len(finished)} trials | "
                  f"mejor={min(vals):.4f} | peor={max(vals):.4f}")

        # evaluar top-5 en test
        top = sorted(study.trials, key=lambda t: t.value if t.value is not None else 1e9)[:5]
        for t in top:
            p = t.params
            pv, pt = train_eval(Xtr, ytr, Xva, yva, Xte, yte,
                                p["hidden"], p["dropout"], p["lr"], p["wd"],
                                epochs=epochs)
            m = metrics(pt, yte)
            m["params"] = p
            results.append(m)
    else:
        pv, pt = train_eval(Xtr, ytr, Xva, yva, Xte, yte, epochs=epochs)
        m = metrics(pt, yte)
        m["params"] = {"hidden": 96, "dropout": 0.3, "lr": 1e-3, "wd": 1e-4}
        results.append(m)

    sharpes = [m["sharpe"] for m in results if np.isfinite(m["sharpe"])]
    eqs = [m["equity"] for m in results if np.isfinite(m["equity"])]
    das = [m["dir_acc"] for m in results if np.isfinite(m["dir_acc"])]

    agg = {
        "sharpe_mean": float(np.mean(sharpes)) if sharpes else float("nan"),
        "sharpe_best": float(np.max(sharpes)) if sharpes else float("nan"),
        "equity_mean": float(np.mean(eqs)) if eqs else float("nan"),
        "equity_best": float(np.max(eqs)) if eqs else float("nan"),
        "diracc_mean": float(np.mean(das)) if das else float("nan"),
        "n_models": len(results),
    }

    print("\n" + "-" * 76)
    print(f"  RESULTADOS {label}")
    print("-" * 76)
    for i, m in enumerate(results, 1):
        sh = m["sharpe"]
        eq = m["equity"]
        da = m["dir_acc"]
        print(f"   #{i}: Sharpe={sh:>7.3f} Equity={eq:>8.3f} "
              f"DirAcc={da*100:>5.1f}%")
        if not np.isfinite(sh) and m.get("_why"):
            print(f"        causa: {m['_why']}")

    # --- Diagnostico de las predicciones (por que el Sharpe puede ser NaN) ---
    if not np.isfinite(agg_sharpe := (np.mean([m["sharpe"] for m in results
                                               if np.isfinite(m["sharpe"])])
                                      if any(np.isfinite(m["sharpe"])
                                             for m in results) else float("nan"))):
        print("\n  " + "-" * 72)
        print("  DIAGNOSTICO: ninguna metrica valida en test")
        print("  " + "-" * 72)
        print(f"    predicciones test: media={np.nanmean(pt):+.6f} "
              f"std={np.nanstd(pt):.6f} "
              f"min={np.nanmin(pt):+.4f} max={np.nanmax(pt):+.4f}")
        print(f"    retornos test    : media={np.nanmean(yte):+.6f} "
              f"std={np.nanstd(yte):.6f}")
        pct_pos = 100 * np.nanmean(pt > 0)
        print(f"    % predicciones > 0 : {pct_pos:.1f}%")
        if pct_pos < 5:
            print("    >>> CASI NINGUNA prediccion positiva: la estrategia long")
            print("        nunca entra en mercado -> retornos cero -> Sharpe NaN.")
            print("        El modelo predice ~0 para todo (no aprendio senal).")
        print("\n    Nota: esto es un RESULTADO, no un bug. Significa que sin el")
        print("    leak el modelo NO encuentra senal explotable en test.")
    print(f"\n  media: Sharpe={agg['sharpe_mean']:.3f} "
          f"Equity={agg['equity_mean']:.3f} DirAcc={agg['diracc_mean']*100:.1f}%")
    return {"aggregate": agg, "models": results}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true",
                    help="Ejecuta v9 con y sin denoising, y compara con v8")
    ap.add_argument("--trials", type=int, default=30)
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--out", default=str(HERE / "output/sfm_v9_causal"))
    args = ap.parse_args()

    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    report = {"fecha": pd.Timestamp.now().isoformat(),
              "correcciones": ["L1 denoising por fold", "L2 close cruda",
                               "L3 sin bfill"],
              "v8_reportado": V8_REPORTADO}

    try:
        r_den = run(True, args.trials, args.epochs, "v9 CON denoising (por tramos)")
        report["v9_con_denoising"] = r_den
    except Exception as exc:  # noqa: BLE001
        print(f"\n  FALLO con denoising: {str(exc)[:200]}")
        report["v9_con_denoising"] = {"error": str(exc)[:300]}

    if args.compare:
        try:
            r_nod = run(False, args.trials, args.epochs, "v9 SIN denoising")
            report["v9_sin_denoising"] = r_nod
        except Exception as exc:  # noqa: BLE001
            print(f"\n  FALLO sin denoising: {str(exc)[:200]}")

    # --- Comparacion final ---
    print("\n" + "=" * 76)
    print(" COMPARACION: v8 (reportado) vs v9 (sin leaks)")
    print("=" * 76)
    print(f"  {'':<26}{'Sharpe':>10}{'Equity':>10}{'DirAcc':>10}")
    print("  " + "-" * 56)
    print(f"  {'v8 reportado (CON leak)':<26}"
          f"{V8_REPORTADO['sharpe_top5_mean']:>10.3f}"
          f"{V8_REPORTADO['equity_top5_mean']:>10.2f}"
          f"{V8_REPORTADO['diracc_mean']*100:>9.1f}%")

    for key, nm in (("v9_con_denoising", "v9 (por tramos)"),
                    ("v9_sin_denoising", "v9 sin denoising")):
        r = report.get(key, {})
        a = r.get("aggregate")
        if a and np.isfinite(a.get("sharpe_mean", np.nan)):
            print(f"  {nm:<26}{a['sharpe_mean']:>10.3f}"
                  f"{a['equity_mean']:>10.2f}{a['diracc_mean']*100:>9.1f}%")

    print("\n" + "=" * 76)
    print(" LECTURA")
    print("=" * 76)
    a = report.get("v9_con_denoising", {}).get("aggregate", {})
    if a and np.isfinite(a.get("sharpe_mean", np.nan)):
        delta = a["sharpe_mean"] - V8_REPORTADO["sharpe_top5_mean"]
        print(f"  delta Sharpe vs v8: {delta:+.3f}")
        if delta < -0.5:
            print("  >> CAIDA GRANDE: confirma que la mayor parte del rendimiento")
            print("     de v8 venia de la fuga de informacion, no de la senal.")
        elif delta < 0:
            print("  >> Caida moderada: parte del rendimiento era leak.")
        else:
            print("  >> v9 iguala o mejora a v8: la senal SOBREVIVE sin el leak.")
        if a["sharpe_mean"] > 0.5:
            print(f"  >> Sharpe v9 = {a['sharpe_mean']:.2f} > 0.5: hay senal real.")
        else:
            print(f"  >> Sharpe v9 = {a['sharpe_mean']:.2f}: senal DEBIL o nula.")
    else:
        print("  No se pudo completar v9. Revisa los errores de arriba.")

    (outdir / "v9_results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=float),
        encoding="utf-8")
    print(f"\n  Guardado en: {outdir/'v9_results.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
