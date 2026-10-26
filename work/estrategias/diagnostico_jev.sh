#!/usr/bin/env bash
# diagnostico_jev.sh — Comprueba el entorno ANTES de lanzar el backtest.
# Ejecutar en WSL desde work/estrategias:  bash diagnostico_jev.sh
# No llama a la API de pago. No modifica nada. Solo comprueba.

echo "===================================================================="
echo " DIAGNOSTICO PREVIO AL BACKTEST JEV"
echo "===================================================================="
FAIL=0

# --- 1) Python y version ---
echo ""
echo "[1] Python"
if command -v python3 >/dev/null 2>&1; then
    PY=python3
elif command -v python >/dev/null 2>&1; then
    PY=python
else
    echo "  FALLO: no hay python ni python3 en PATH"; FAIL=1; PY=""
fi
if [ -n "$PY" ]; then
    echo "  $($PY --version 2>&1)  (binario: $(command -v $PY))"
fi

# --- 2) Paquetes ---
echo ""
echo "[2] Paquetes Python"
for pkg in numpy pandas requests certifi; do
    if [ -n "$PY" ] && $PY -c "import $pkg" 2>/dev/null; then
        echo "  OK   $pkg"
    else
        echo "  FALTA $pkg  ->  pip install $pkg"; FAIL=1
    fi
done
if [ -n "$PY" ] && $PY -c "import qlib" 2>/dev/null; then
    echo "  OK   qlib"
else
    echo "  FALTA qlib  ->  pip install pyqlib"; FAIL=1
fi

# --- 3) Datos qlib ---
echo ""
echo "[3] Datos qlib"
QLIB_DIR="$HOME/.qlib/qlib_data/us_data"
if [ -d "$QLIB_DIR" ]; then
    echo "  OK   existe $QLIB_DIR"
    if [ -d "$QLIB_DIR/instruments" ]; then
        echo "  OK   instruments/"
        if [ -f "$QLIB_DIR/instruments/sp500_liquid.txt" ]; then
            N=$(wc -l < "$QLIB_DIR/instruments/sp500_liquid.txt")
            echo "  OK   sp500_liquid.txt ($N tickers)"
        else
            echo "  AVISO: no hay sp500_liquid.txt. Universos disponibles:"
            ls "$QLIB_DIR/instruments"/*.txt 2>/dev/null | head -5 | sed 's/^/         /'
            echo "         El backtest usara el primero que encuentre."
            echo "         Detalle completo: python3 inspeccionar_qlib_data.py"
        fi
    else
        echo "  FALLO: falta $QLIB_DIR/instruments"; FAIL=1
    fi
    if [ -d "$QLIB_DIR/features" ]; then
        echo "  OK   features/ ($(ls "$QLIB_DIR/features" | wc -l) entradas)"
    else
        echo "  AVISO: no hay features/ (revisa la ruta)"
    fi
else
    echo "  FALLO: no existe $QLIB_DIR"; FAIL=1
    echo "  Directorios similares:"
    ls -d "$HOME"/.qlib/*/ 2>/dev/null | head -5
fi

# --- 4) API key ---
echo ""
echo "[4] OpenRouter API key"
if [ -n "$OPENROUTER_API_KEY" ]; then
    LEN=${#OPENROUTER_API_KEY}
    echo "  OK   definida en el entorno (longitud $LEN)"
    case "$OPENROUTER_API_KEY" in
        sk-or-*) echo "  OK   prefijo sk-or-" ;;
        *) echo "  AVISO: no empieza por sk-or-" ;;
    esac
else
    if [ -f "../../.env" ]; then
        echo "  AVISO: no esta en el entorno; se leera de ../../.env"
    else
        echo "  FALLO: no definida y no hay .env"; FAIL=1
    fi
fi

# --- 5) Archivos del proyecto ---
echo ""
echo "[5] Archivos necesarios"
for f in jev_regime.py jev_backtest_ab.py vol_gate.py; do
    if [ -f "$f" ]; then echo "  OK   $f"; else echo "  FALLO: falta $f"; FAIL=1; fi
done

# --- 6) Conectividad TLS con OpenRouter (SIN gastar credito) ---
echo ""
echo "[6] Conectividad con OpenRouter (gratis, no consume credito)"
if [ -n "$PY" ]; then
    $PY - <<'EOF'
import sys
try:
    import requests, certifi
except Exception as e:
    print(f"  FALLO: faltan paquetes ({e})"); sys.exit(1)
try:
    r = requests.get("https://openrouter.ai/api/v1/models", timeout=25, verify=certifi.where())
    print(f"  OK   HTTP {r.status_code} ({len(r.content)} bytes)")
except Exception as e:
    msg = str(e)
    print(f"  FALLO: {msg[:200]}")
    if "CERTIFICATE" in msg.upper() or "SSL" in msg.upper():
        print("  -> Hay inspeccion TLS. Prueba con la CA local:")
        print("     KASPERSKY_CA_PATH=/ruta/al/cert.cer python3 jev_backtest_ab.py")
        sys.exit(2)
    sys.exit(1)
EOF
    RC=$?
    [ $RC -ne 0 ] && FAIL=1
fi

# --- 7) Test sintetico del motor ---
echo ""
echo "[7] Motor del backtest (sintetico, sin datos ni API)"
if [ -n "$PY" ] && [ -f "test_jev_backtest_sintetico.py" ]; then
    if $PY test_jev_backtest_sintetico.py >/tmp/_jevtest.log 2>&1; then
        OK=$(grep -c "OK" /tmp/_jevtest.log)
        echo "  OK   motor validado ($OK comprobaciones OK)"
    else
        echo "  FALLO: revisa el motor"; tail -20 /tmp/_jevtest.log; FAIL=1
    fi
fi

echo ""
echo "===================================================================="
if [ $FAIL -eq 0 ]; then
    echo " TODO LISTO. Lanza:  python3 jev_backtest_ab.py"
else
    echo " HAY PROBLEMAS. Resuelve los FALLO de arriba antes de lanzar."
fi
echo "===================================================================="
exit $FAIL
