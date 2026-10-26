"""Verifica que v9 encuentra y lee los datos crypto correctamente.

Ejecutar en WSL:  conda run -n qlib python work/crypto/_verificar_datos.py

Comprueba, en este orden:
  1. Que data/qlib existe y tiene la estructura qlib.
  2. Que qlib.init funciona con esa ruta.
  3. Los nombres REALES de los instrumentos.
  4. Que D.features devuelve datos para cada moneda.
"""
import os
import sys

print("=" * 74)
print(" VERIFICACION DE DATOS CRYPTO")
print("=" * 74)

# --- 1) estructura en disco ---
cand = [os.environ.get("CRYPTO_QLIB_OUTPUT_DIR"), "data/qlib",
        "work/crypto/data/qlib"]
uri = None
print("\n[1] Buscando el dataset")
for c in cand:
    if not c:
        continue
    ok = os.path.isdir(os.path.join(c, "instruments")) or \
        os.path.isdir(os.path.join(c, "calendars"))
    print(f"    {c:<28} {'OK' if ok else 'no'}")
    if ok and uri is None:
        uri = c
if uri is None:
    print("\n  FALLO: no se encontro el dataset.")
    print("  Define: export CRYPTO_QLIB_OUTPUT_DIR=/ruta/a/data/qlib")
    sys.exit(1)
print(f"  -> usando: {uri}")

for sub in ("instruments", "features", "calendars"):
    p = os.path.join(uri, sub)
    print(f"    {sub:<12} {'OK' if os.path.isdir(p) else 'FALTA'}")

# --- 2) qlib.init ---
print("\n[2] Inicializando qlib")
try:
    import qlib
    from qlib.config import REG_US
    from qlib.data import D
    qlib.init(provider_uri=uri, region=REG_US, kernels=1)
    print("    OK")
except Exception as exc:
    print(f"    FALLO: {str(exc)[:200]}")
    sys.exit(1)

# --- 3) instrumentos reales ---
print("\n[3] Instrumentos disponibles")
try:
    insts = D.list_instruments(D.instruments("all"), as_list=True)
    print(f"    total: {len(insts)}")
    print(f"    nombres: {insts}")
except Exception as exc:
    print(f"    FALLO: {str(exc)[:200]}")
    insts = []

# --- 4) features por moneda ---
print("\n[4] Lectura de precios por moneda")
esperadas = ["btc", "eth", "sol", "xlm", "ada", "xrp", "doge", "link", "ltc"]
lookup = {i.lower(): i for i in insts}
ok_count = 0
for c in esperadas:
    name = c if c in insts else lookup.get(c.lower(), c)
    try:
        df = D.features([name], ["$close"], start_time="2015-01-01",
                        end_time="2026-10-22")
        if df is None or df.empty:
            print(f"    {c:>5s} -> SIN DATOS (como '{name}')")
            continue
        s = df["$close"]
        n = int(s.notna().sum())
        print(f"    {c:>5s} -> {n:>5d} valores  [{s.first_valid_index()} -> "
              f"{s.last_valid_index()}]  (nombre real: '{name}')")
        if n > 100:
            ok_count += 1
    except Exception as exc:
        print(f"    {c:>5s} -> ERROR: {str(exc)[:100]}")

print("\n" + "=" * 74)
if ok_count >= 8:
    print(f" TODO CORRECTO: {ok_count}/9 monedas con datos.")
    print(" Ejecuta:")
    print("   conda run -n qlib python work/crypto/qlib_sfm_pipeline.v9_causal.py \\")
    print("       --compare --trials 30 --epochs 80")
else:
    print(f" PROBLEMA: solo {ok_count}/9 monedas con datos.")
    print(" Revisa la lista de instrumentos de arriba.")
print("=" * 74)
