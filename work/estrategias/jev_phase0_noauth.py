#!/usr/bin/env python
"""
FASE 0b - Sondeo SIN autenticacion.

Objetivo: distinguir "Jev no es enrutable" de "Jev necesita auth",
sin disponer todavia de API key.

Si el error es 401 -> el modelo EXISTE en la ruta y solo falta la key.
Si el error es 404 -> no hay endpoint que lo sirva (unroutable), con o sin key.

Compara contra un modelo de control que sabemos que SI es servible.
"""
import json
import time
from pathlib import Path

import requests

from jev_phase0_probe import CHAT_URL, ca_bundle

PROMPT = "Responde solo con la palabra: ok"

# Modelo de control: si este tambien da 401, la ruta funciona y el test es valido.
TARGETS = [
    "typesafe/jev-router",
    "~typesafe/jev-latest",
    "deepseek/deepseek-v4.1-flash-1017",  # control (sabemos que se sirve)
]


def main() -> None:
    print("=" * 72)
    print("FASE 0b - SONDEO SIN API KEY")
    print("=" * 72)
    print("Interpretacion: 401 => existe, solo falta key | 404 => no enrutable\n")

    out = {}
    for model in TARGETS:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 16,
        }
        try:
            r = requests.post(CHAT_URL, json=body, timeout=60, verify=ca_bundle())
            try:
                payload = r.json()
            except Exception:  # noqa: BLE001
                payload = {"_raw": r.text[:500]}
            err = payload.get("error") if isinstance(payload, dict) else None
            msg = (err or {}).get("message") if isinstance(err, dict) else None
            code = (err or {}).get("code") if isinstance(err, dict) else None
            out[model] = {"http": r.status_code, "code": code, "message": msg}
            print(f"  {model}")
            print(f"     HTTP {r.status_code}  code={code}")
            print(f"     {msg}\n")
        except Exception as exc:  # noqa: BLE001
            out[model] = {"error": str(exc)}
            print(f"  {model}\n     [ERROR] {exc}\n")

    dest = Path(__file__).resolve().parent / "jev_phase0_out" / "noauth_probe.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Guardado en: {dest}")

    print("=" * 72)
    print("LECTURA")
    print("=" * 72)
    ctrl = out.get("deepseek/deepseek-v4.1-flash-1017", {})
    if ctrl.get("http") == 401:
        print("  Control da 401 -> la ruta /chat/completions responde y el test es valido.")
    else:
        print(f"  AVISO: el control dio HTTP {ctrl.get('http')} (no 401).")
        print("  El test pierde valor: no podemos comparar.")
    for model in TARGETS[:2]:
        info = out.get(model, {})
        h = info.get("http")
        if h == 404:
            print(f"  {model}: 404 -> NO ENRUTABLE (sin endpoint que lo sirva).")
        elif h == 401:
            print(f"  {model}: 401 -> EXISTE, solo requiere API key.")
        else:
            print(f"  {model}: HTTP {h} -> revisar mensaje.")


if __name__ == "__main__":
    main()
