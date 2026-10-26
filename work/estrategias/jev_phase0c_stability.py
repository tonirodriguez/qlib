#!/usr/bin/env python
"""
FASE 0c - El router ELIGE modelo distinto entre llamadas: implica no-determinismo.

HALLAZGO de la Fase 0: en 5 llamadas identicas, `model_returned` fue
z-ai/glm-5.3-flash las 4 primeras, pero en la 5a el provider cambio
(Together -> Cohere) y aparecieron 48 reasoning_tokens de mas.

Es decir: la ETIQUETA fue estable ('crisis' x5), pero el MODELO EJECUTOR
NO lo fue. Eso importa para un backtest, porque:
  1. El comportamiento puede cambiar cuando el router cambie de modelo.
  2. La reproducibilidad de un backtest historico no esta garantizada si
     dentro de 3 meses el router elige otro modelo distinto.
  3. El coste por llamada es variable (2.57e-05 vs 4.97e-05 ~ 2x).

Este script mide: con N llamadas identicas, ¿cuantos modelos distintos usa?
Prueba varias temperaturas y varios prompts para forzar al router a moverse.
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

from jev_phase0_probe import CHAT_URL, ca_bundle, get_key, headers, load_env_file, OUT_DIR

MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-router")

# Prompts de dificultad creciente: un router deberia escalar a modelos mejores
# (y mas caros) cuando la tarea es dificil. Eso es lo que queremos observar.
PROMPTS = {
    "trivial": "Clasifica: el mercado sube. Responde solo: risk_on",
    "regimen_facil": (
        "Clasifica el regimen en: risk_on, neutral, risk_off, crisis.\n"
        "Vol 20d: 41% (p97). Drawdown: -28%. Breadth: 12%. Correlacion: 0.78.\n"
        "Responde SOLO con la etiqueta."
    ),
    "regimen_dificil": (
        "Clasifica el regimen en: risk_on, neutral, risk_off, crisis.\n"
        "Vol 20d: 18% (p55). Drawdown: -4%. Breadth: 48%. Correlacion: 0.31.\n"
        "Curva 10y-2y: +0.12. Credit spreads: estrechos. Earnings: mixtos.\n"
        "El momentum de 3 meses es positivo pero decreciente.\n"
        "Responde SOLO con la etiqueta."
    ),
}


def call(prompt: str, temperature: float) -> dict:
    import requests
    body = {
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 512,
        "temperature": temperature,
    }
    t0 = time.time()
    r = requests.post(CHAT_URL, headers=headers(get_key()), json=body,
                      timeout=120, verify=ca_bundle())
    dt = time.time() - t0
    try:
        j = r.json()
    except Exception:  # noqa: BLE001
        j = {}
    choices = j.get("choices") or [{}]
    content = (choices[0].get("message") or {}).get("content")
    usage = j.get("usage") or {}
    return {
        "http": r.status_code,
        "latency_s": round(dt, 2),
        "label": (content or "").strip()[:60] or None,
        "model_returned": j.get("model"),
        "provider": j.get("provider"),
        "cost": usage.get("cost"),
        "reasoning_tokens": (usage.get("completion_tokens_details") or {}).get("reasoning_tokens"),
    }


def main() -> None:
    load_env_file()
    if not get_key():
        print("Falta OPENROUTER_API_KEY")
        sys.exit(2)

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    print("=" * 74)
    print(f"FASE 0c - ESTABILIDAD DEL ROUTER  (modelo={MODEL}, N={n})")
    print("=" * 74)

    report: dict = {"model": MODEL, "n": n, "blocks": {}}

    for pname, prompt in PROMPTS.items():
        for temp in (0.0, 0.7):
            key = f"{pname}|T={temp}"
            print(f"\n--- {key} ---")
            runs = []
            for i in range(n):
                try:
                    r = call(prompt, temp)
                except Exception as exc:  # noqa: BLE001
                    r = {"error": str(exc)}
                runs.append(r)
                if r.get("error"):
                    print(f"  {i+1}: [ERROR] {r['error']}")
                else:
                    print(f"  {i+1}: {r['latency_s']:>5}s  modelo={r['model_returned']:<24} "
                          f"prov={str(r['provider']):<9} cost={r['cost']} "
                          f"reason={r['reasoning_tokens']}  label={r['label']!r}")

            models = Counter(x["model_returned"] for x in runs if x.get("model_returned"))
            provs = Counter(x["provider"] for x in runs if x.get("provider"))
            labels = Counter(x["label"] for x in runs if x.get("label"))
            costs = [x["cost"] for x in runs if x.get("cost")]

            block = {
                "models_used": dict(models),
                "n_distinct_models": len(models),
                "providers_used": dict(provs),
                "label_distribution": dict(labels),
                "cost_min": min(costs) if costs else None,
                "cost_max": max(costs) if costs else None,
                "cost_total": round(sum(costs), 8) if costs else None,
                "runs": runs,
            }
            report["blocks"][key] = block
            print(f"  => modelos distintos: {len(models)} {dict(models)}")
            print(f"  => etiquetas: {dict(labels)}")
            if costs:
                print(f"  => coste: {min(costs):.2e}..{max(costs):.2e} "
                      f"(ratio {max(costs)/min(costs):.1f}x)")

    dest = OUT_DIR / "phase0c_router_stability.json"
    dest.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nGuardado en: {dest}")

    # Veredicto agregado
    print("\n" + "=" * 74)
    print("VEREDICTO - ESTABILIDAD DEL ROUTER")
    print("=" * 74)
    all_models = Counter()
    all_labels_stable = True
    for k, b in report["blocks"].items():
        all_models.update(b["models_used"])
        if len(b["label_distribution"]) > 1:
            all_labels_stable = False
    print(f"  Modelos ejecutores distintos en todo el barrido: {len(all_models)}")
    for m, c in all_models.most_common():
        print(f"     {m:<28} {c} llamadas")
    print(f"  Etiquetas estables en todos los bloques: {all_labels_stable}")
    if len(all_models) > 1:
        print("\n  >> El router NO es fijo: elige modelos distintos segun la llamada.")
        print("  >> Consecuencia: un backtest no es reproducible si depende del modelo")
        print("     elegido, aunque la etiqueta coincida hoy.")
    else:
        print("\n  >> El router uso un unico modelo en este barrido.")


if __name__ == "__main__":
    main()
