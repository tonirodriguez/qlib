"""rutas_entorno.py — Resolucion de rutas y universo para los simuladores.

POR QUE EXISTE
    Los simuladores (simulate.py, simulate_pead.py, simulate_pead_core.py)
    tienen las rutas HARDCODEADAS a otra maquina:

        QLIB_URI = "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data"
        UNIVERSE_FILE = os.path.join(QLIB_URI, "instruments/sp500_liquid.txt")

    Verificado el 2026-10-26:
      - `/opt/data/...`  -> NO existe en esta maquina
      - `sp500_liquid.txt` -> NO existe (el dataset tiene `sp500.txt`)
      - `prices_live.csv`  -> NO existe

    Este modulo resuelve ambas cosas SIN tocar los simuladores originales:
    se importa y se usa en su lugar.

QUE HACE
    1. Encuentra el directorio `qlib_data` probando varias rutas y validando
       que sea una instalacion qlib real (con instruments/ y calendars/).
    2. Encuentra el fichero de universo, aceptando los nombres disponibles y
       permitiendo filtrar los tickers LIQUIDOS (que es lo que pretendia
       `sp500_liquid`: ~390 tickers liquidos del S&P 500).

USO
    from rutas_entorno import get_qlib_uri, get_universe, get_universe_file

    uri = get_qlib_uri()
    tickers = get_universe(min_dollar_vol=...)   # liquidez opcional
"""
from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent

# Rutas candidatas, en orden de preferencia.
#
# OJO: `data/qlib` (el dataset CRYPTO) tambien es una instalacion qlib valida.
# Si se colara aqui, una estrategia de acciones US leeria precios de cripto.
# Por eso se valida ademas que el universo sea de ACCIONES (ver _es_us_equity).
CANDIDATAS = [
    os.environ.get("QLIB_US_DATA"),
    "/opt/data/profiles/investments/home/.qlib/qlib_data/us_data",
    os.path.expanduser("~/.qlib/qlib_data/us_data"),
    str(HERE.parents[2] / "data" / "qlib"),          # crypto: ultimo recurso
]

# Marcadores de dataset de cripto (nombres de instrumento en minuscula)
_CRYPTO_MARKERS = {"btc", "eth", "sol", "xrp", "doge", "ada", "ltc", "xlm", "link"}

# Nombres de universo, en orden de preferencia.
# `sp500_liquid.txt` primero (el original); si no, `sp500.txt`.
UNIVERSOS = ["sp500_liquid.txt", "sp500.txt", "csi300.txt"]


def _es_qlib_dir(p: str | None) -> bool:
    """Una instalacion qlib valida tiene instruments/ o calendars/."""
    if not p:
        return False
    if not os.path.isdir(p):
        return False
    return (os.path.isdir(os.path.join(p, "instruments"))
            or os.path.isdir(os.path.join(p, "calendars")))


def _parece_crypto(uri: str) -> bool:
    """Heuristica: ¿este dataset qlib es de CRIPTO?

    Se mira `instruments/`: si los tickers son minusculas conocidas
    (btc, eth, ...) es cripto. Un dataset de acciones US tiene tickers
    en MAYUSCULAS (AAPL, MSFT).
    """
    inst_dir = os.path.join(uri, "instruments")
    if not os.path.isdir(inst_dir):
        return False
    try:
        for fn in os.listdir(inst_dir):
            if not fn.endswith(".txt"):
                continue
            with open(os.path.join(inst_dir, fn)) as f:
                for i, line in enumerate(f):
                    if i >= 20:
                        break
                    t = line.split("\t")[0].strip()
                    if t and t.isupper():
                        return False        # hay tickers en mayuscula -> acciones
                    if t.lower() in _CRYPTO_MARKERS:
                        return True
    except OSError:
        pass
    return False


def get_qlib_uri(solo_acciones: bool = True) -> str:
    """Directorio de datos qlib.

    Parameters
    ----------
    solo_acciones : bool
        Si True (por defecto), DESCARTAR los datasets de cripto. Evita que
        una estrategia de acciones US lea precios de cripto por accidente
        (el error seria silencioso y grave: momentum sobre BTC en vez de AAPL).
    """
    descartadas: list[str] = []
    for c in CANDIDATAS:
        if not _es_qlib_dir(c):
            continue
        if solo_acciones and _parece_crypto(c):
            descartadas.append(str(c))
            continue
        return str(c)
    msg = ("No encuentro qlib_data de ACCIONES US. Rutas probadas:\n  "
           + "\n  ".join(str(c) for c in CANDIDATAS if c))
    if descartadas:
        msg += ("\n\nDescartadas por ser de CRIPTO (tickers en minuscula):\n  "
                + "\n  ".join(descartadas)
                + "\n\nSi querias el dataset crypto, usa get_qlib_uri(solo_acciones=False)")
    msg += "\n\nDefine QLIB_US_DATA=/ruta/a/qlib_data/us_data"
    raise FileNotFoundError(msg)


def get_universe_file() -> str:
    """Fichero de instrumentos. Avisa si no es el original."""
    uri = get_qlib_uri()
    inst_dir = os.path.join(uri, "instruments")
    for nm in UNIVERSOS:
        p = os.path.join(inst_dir, nm)
        if os.path.exists(p):
            return p
    # ultimo recurso: cualquier .txt que no sea 'all' (15k tickers)
    if os.path.isdir(inst_dir):
        cands = sorted(f for f in os.listdir(inst_dir)
                       if f.endswith(".txt") and "all" not in f.lower())
        if cands:
            return os.path.join(inst_dir, cands[0])
    raise FileNotFoundError(f"Sin universo en {inst_dir}")


def get_universe(min_dollar_vol: float | None = None,
                 max_tickers: int | None = None,
                 verbose: bool = True) -> list[str]:
    """Lista de tickers del universo.

    Parameters
    ----------
    min_dollar_vol : float, optional
        Si se indica, filtra por liquidez media (precio x volumen, 60d).
        Sirve para reproducir el espiritu de `sp500_liquid` (~390 tickers
        liquidos) cuando solo hay `sp500.txt` (1.180 tickers historicos).
    max_tickers : int, optional
        Recorta a N tickers (muestreo uniforme, no alfabetico).
    """
    uf = get_universe_file()
    nombre = os.path.basename(uf)
    tickers: list[str] = []
    with open(uf) as f:
        for line in f:
            t = line.split("\t")[0].strip()
            if t and not t.startswith("#"):
                tickers.append(t)

    if verbose:
        print(f"   universo: {nombre} ({len(tickers)} tickers)")
        if nombre != "sp500_liquid.txt":
            print(f"   NOTA: '{nombre}' no es el original 'sp500_liquid.txt'")
            print(f"         (aquel no existe en esta maquina).")
            print(f"         sp500.txt incluye composicion historica -> evita")
            print(f"         sesgo de supervivencia, pero tiene ~1.180 tickers")

    # --- filtro de liquidez ---
    if min_dollar_vol is not None and tickers:
        try:
            import numpy as np
            import qlib
            from qlib.data import D
            qlib.init(provider_uri=get_qlib_uri(), region="us",
                      kernels=int(os.environ.get("QLIB_KERNELS", "1")))
            d = D.features(tickers, ["$volume", "$factor"],
                           start_time="2025-01-01", end_time="2100-12-31",
                           freq="day")
            vol = d["$volume"].unstack(level=0).sort_index()
            fac = d["$factor"].unstack(level=0).sort_index()
            # volumen ajustado medio (proxy de liquidez)
            adv = vol.mul(fac).tail(60).mean()
            keep = adv[adv >= min_dollar_vol].index.tolist()
            if verbose:
                print(f"   liquidez: {len(keep)}/{len(tickers)} tickers con "
                      f"volumen ajustado medio >= {min_dollar_vol:,.0f} (60d)")
            if keep:
                tickers = [t for t in tickers if t in set(keep)]
        except Exception as exc:  # noqa: BLE001
            if verbose:
                print(f"   AVISO: no se pudo filtrar por liquidez "
                      f"({str(exc)[:80]}); se usa el universo completo")

    # --- recorte ---
    if max_tickers and len(tickers) > max_tickers:
        import numpy as np
        idx = np.linspace(0, len(tickers) - 1, max_tickers).astype(int)
        tickers = [tickers[i] for i in idx]
        if verbose:
            print(f"   recorte: {max_tickers} tickers (muestreo uniforme)")

    return tickers


def get_prices_live() -> str | None:
    """Ruta de prices_live.csv si existe (datos frescos externos)."""
    p = HERE / "prices_live.csv"
    return str(p) if p.exists() else None
