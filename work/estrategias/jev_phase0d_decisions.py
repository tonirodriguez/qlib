#!/usr/bin/env python
"""
FASE 0d - Endpoint nativo de decisiones.

La Fase 0 revelo que `~typesafe/jev-latest` NO funciona en /chat/completions:
    HTTP 400: "is a decisions model and cannot be used with the chat/completions
               endpoint. Use the /api/alpha/decisions endpoint instead."

Es decir: el endpoint nativo de Jev es /api/alpha/decisions y sigue en ALPHA.
Aqui se sondea su forma: probamos variantes de payload para descubrir el
contrato, SIN gastar mas de lo necesario.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import requests

from jev_phase0_probe import ca_bundle, get_key, headers, load_env_file, OUT_DIR

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"

# El error de validacion revelo el contrato real:
#   path ["state"]     -> string | record | array   (el contexto/observacion)
#   path ["questions"] -> record                     (las preguntas a decidir)
# Se construye un payload conforme a ese contrato.
STATE_TEXT = (
    "Fecha: 2026-03-15. S&P500: volatilidad realizada 20d = 41% (percentil 97 "
    "historico). Drawdown desde maximos de 52 semanas = -28%. Breadth = 12% de "
    "valores sobre su media de 200d. Correlacion media entre acciones = 0.78. "
    "Curva 10y-2y invertida en -0.45."
)

# Contrato completo descubierto por inferencia de errores de validacion:
#   state                      -> string | record | array
#   questions.<id>.type        -> 'noul' | 'choice' | 'score' | 'box'
#   questions.<id>.instructions-> string | record | array
#   questions.<id>.criteria    -> record
VARIANTS: list[tuple[str, dict]] = [
    ("choice_full", {
        "model": "~typesafe/jev-latest",
        "state": STATE_TEXT,
        "questions": {
            "regimen": {
                "type": "choice",
                "instructions": "Clasifica el regimen de mercado segun los datos del estado.",
                "criteria": {
                    "risk_on": "Volatilidad baja, breadth amplio, sin drawdown relevante.",
                    "neutral": "Senales mixtas, sin estres ni euforia.",
                    "risk_off": "Volatilidad elevada o drawdown moderado, breadth deteriorado.",
                    "crisis": "Volatilidad extrema y drawdown severo con correlaciones altas.",
                },
            }
        },
    }),
    ("choice_full_opts", {
        "model": "~typesafe/jev-latest",
        "state": STATE_TEXT,
        "questions": {
            "regimen": {
                "type": "choice",
                "instructions": "Clasifica el regimen de mercado.",
                "criteria": {
                    "options": ["risk_on", "neutral", "risk_off", "crisis"],
                    "risk_on": "Volatilidad baja y breadth amplio.",
                    "crisis": "Volatilidad extrema y drawdown severo.",
                },
            }
        },
    }),
]


def main() -> None:
    load_env_file()
    key = get_key()
    if not key:
        print("Falta OPENROUTER_API_KEY")
        return

    print("=" * 74)
    print("FASE 0d - ENDPOINT NATIVO /api/alpha/decisions")
    print("=" * 74)

    out: dict = {}
    for name, body in VARIANTS:
        print(f"\n--- variante: {name} ---")
        print(f"    payload keys: {list(body.keys())}")
        try:
            r = requests.post(DECISIONS_URL, headers=headers(key), json=body,
                              timeout=90, verify=ca_bundle())
            try:
                payload = r.json()
            except Exception:  # noqa: BLE001
                payload = {"_raw": r.text[:800]}
            out[name] = {"http": r.status_code, "response": payload}
            print(f"    HTTP {r.status_code}")
            txt = json.dumps(payload, ensure_ascii=False)
            print(f"    {txt[:700]}")
        except Exception as exc:  # noqa: BLE001
            out[name] = {"error": str(exc)}
            print(f"    [ERROR] {exc}")

    dest = OUT_DIR / "decisions_endpoint_probe.json"
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado en: {dest}")

    print("\n" + "=" * 74)
    print("LECTURA")
    print("=" * 74)
    ok = [k for k, v in out.items() if v.get("http") == 200]
    if ok:
        print(f"  Variantes aceptadas (HTTP 200): {ok}")
        print("  -> El contrato esta en la primera que funcione.")
    else:
        codes = {k: v.get("http", v.get("error")) for k, v in out.items()}
        print(f"  Ninguna variante dio 200: {codes}")
        print("  -> Puede requerir un formato especifico o acceso alpha restringido.")


if __name__ == "__main__":
    main()
