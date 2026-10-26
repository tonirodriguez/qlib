#!/usr/bin/env python
"""
FASE 0 - Verificacion de tiposafe/jev-router en OpenRouter.

Objetivo: determinar EMPIRICAMENTE, antes de disenar nada, si Jev:
  1. Es invocable por API (o solo un placeholder sin endpoints).
  2. Que formato de respuesta devuelve en una tarea de CLASIFICACION
     (su modalidad declarada es `decisions`, no `text`).
  3. Es DETERMINISTA (misma entrada N veces -> misma salida). Sin esto
     no vale para backtest.
  4. Cuanto cuesta y cuanto tarda.

NO toca el paper-trading vivo. Solo lee.

Uso:
    # 1) Sin key: inspecciona metadatos del catalogo (no gasta nada)
    python jev_phase0_probe.py --metadata-only

    # 2) Con key: prueba de invocacion real
    set OPENROUTER_API_KEY=sk-or-...
    python jev_phase0_probe.py

La key tambien se lee de un .env en la raiz del repo (OPENROUTER_API_KEY=...).
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

import requests

MODELS_URL = "https://openrouter.ai/api/v1/models"
CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"

# ---------------------------------------------------------------------------
# TLS: esta maquina tiene Kaspersky haciendo inspeccion TLS. Python no confia
# en su CA raiz, asi que las peticiones fallan con CERTIFICATE_VERIFY_FAILED.
# Solucion CORRECTA: construir un bundle = certifi + CA de Kaspersky. NO se
# desactiva la verificacion (verify=False seria un agujero de seguridad).
# ---------------------------------------------------------------------------

DEFAULT_KASPERSKY_CA = r"C:\Users\trodriguez\certs\kaspersky-root.cer"
_BUNDLE_CACHE: Path | None = None


def ca_bundle() -> str | bool:
    """Devuelve la ruta a un bundle de CAs que incluye la CA local si existe.

    El bundle se RECONSTRUYE si la CA local cambio de tamano o de mtime, para
    que sustituir el .cer no deje una cache obsoleta.
    """
    global _BUNDLE_CACHE

    try:
        import certifi
        base = Path(certifi.where())
    except Exception:  # noqa: BLE001
        return True  # deja que requests use su default

    kaspersky = Path(os.environ.get("KASPERSKY_CA_PATH", DEFAULT_KASPERSKY_CA))
    if not kaspersky.exists():
        _BUNDLE_CACHE = base
        return str(base)

    bundle = OUT_DIR / "ca_bundle.pem"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # Cache valida solo si el bundle es mas reciente que sus dos fuentes.
    if _BUNDLE_CACHE is not None and bundle.exists():
        try:
            bt = bundle.stat().st_mtime
            if bt >= base.stat().st_mtime and bt >= kaspersky.stat().st_mtime:
                return str(bundle)
        except OSError:
            pass

    try:
        bundle.write_bytes(base.read_bytes() + b"\n" + kaspersky.read_bytes())
        _BUNDLE_CACHE = bundle
        print(f"  [TLS] bundle CA construido: {bundle}")
        return str(bundle)
    except Exception as exc:  # noqa: BLE001
        print(f"  [TLS] no se pudo construir el bundle ({exc}); uso certifi")
        _BUNDLE_CACHE = base
        return str(base)

# Candidatos a probar, en orden de interes. Se pueden sobrescribir con la
# variable de entorno JEV_MODEL (definida en .env).
CANDIDATES = [
    "typesafe/jev-router",
    "~typesafe/jev-latest",
]


def candidates() -> list[str]:
    """Lista efectiva de modelos: JEV_MODEL primero, sin duplicados."""
    override = os.environ.get("JEV_MODEL", "").strip()
    out: list[str] = []
    if override:
        out.append(override)
    for m in CANDIDATES:
        if m not in out:
            out.append(m)
    return out

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(__file__).resolve().parent / "jev_phase0_out"

# ---------------------------------------------------------------------------
# Tarea de clasificacion: regimen de mercado. Es el Uso A de la propuesta.
# Le pedimos una etiqueta DISCRETA de un conjunto cerrado -> clasificacion pura.
# ---------------------------------------------------------------------------

REGIME_LABELS = ["risk_on", "neutral", "risk_off", "crisis"]

REGIME_PROMPT = """Eres un clasificador de regimen de mercado. Clasifica el estado
del mercado en UNA de estas etiquetas exactas: risk_on, neutral, risk_off, crisis.

Datos observados de hoy:
- Volatilidad realizada 20d del S&P500: 41%  (percentil historico: 97)
- Drawdown desde maximos de 52 semanas: -28%
- Breadth (% de valores por encima de su media de 200d): 12%
- Correlacion media entre acciones: 0.78
- Curva de tipos 10y-2y: -0.45 (invertida)

Responde SOLO con la etiqueta."""


def load_env_file() -> None:
    """Carga OPENROUTER_API_KEY desde .env si no esta en el entorno."""
    for candidate in (REPO_ROOT / ".env", Path.cwd() / ".env"):
        if not candidate.exists():
            continue
        for raw in candidate.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v


def get_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY") or None


def headers(key: str | None) -> dict:
    h = {
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/tonirodriguez/qlib",
        "X-Title": "qlib-jev-phase0",
    }
    if key:
        h["Authorization"] = f"Bearer {key}"
    return h


# ---------------------------------------------------------------------------
# Paso 1: metadatos
# ---------------------------------------------------------------------------

def probe_metadata() -> dict:
    print("=" * 72)
    print("PASO 1 - METADATOS DEL CATALOGO")
    print("=" * 72)

    result: dict = {"catalog_hits": {}, "endpoint_probes": {}}

    try:
        r = requests.get(MODELS_URL, timeout=60, verify=ca_bundle())
        r.raise_for_status()
        catalog = r.json().get("data", [])
    except Exception as exc:  # noqa: BLE001
        print(f"  [ERROR] No se pudo leer el catalogo: {exc}")
        return result

    print(f"  Catalogo: {len(catalog)} modelos")

    for m in catalog:
        mid = m.get("id", "")
        if "jev" in mid.lower() or "typesafe" in mid.lower():
            result["catalog_hits"][mid] = {
                "name": m.get("name"),
                "modality": m.get("architecture", {}).get("modality"),
                "input_modalities": m.get("architecture", {}).get("input_modalities"),
                "output_modalities": m.get("architecture", {}).get("output_modalities"),
                "tokenizer": m.get("architecture", {}).get("tokenizer"),
                "context_length": m.get("context_length"),
                "pricing": m.get("pricing"),
                "supported_parameters": m.get("supported_parameters"),
            }

    if not result["catalog_hits"]:
        print("  [!!] NO aparece ningun modelo Jev/TypeSafe en el catalogo")
    for mid, info in result["catalog_hits"].items():
        print(f"\n  -> {mid}")
        for k, v in info.items():
            print(f"       {k}: {v}")

    # Endpoints: la ficha publica mostraba "endpoints": [] -> crucial confirmarlo
    print("\n  Sondeo de endpoints por modelo:")
    for mid in candidates():
        url = f"{MODELS_URL}/{mid}/endpoints"
        try:
            r = requests.get(url, timeout=60, verify=ca_bundle())
            payload = r.json() if r.content else {}
            eps = payload.get("data", {}).get("endpoints", None)
            n = len(eps) if isinstance(eps, list) else None
            result["endpoint_probes"][mid] = {
                "http": r.status_code,
                "n_endpoints": n,
                "raw_keys": list(payload.get("data", {}).keys()) if isinstance(payload, dict) else None,
            }
            print(f"    {mid:28s} HTTP {r.status_code}  endpoints={n}")
        except Exception as exc:  # noqa: BLE001
            result["endpoint_probes"][mid] = {"error": str(exc)}
            print(f"    {mid:28s} [ERROR] {exc}")

    return result


# ---------------------------------------------------------------------------
# Paso 2: invocacion real
# ---------------------------------------------------------------------------

def call_model(model: str, prompt: str, key: str, max_tokens: int = 256,
               temperature: float = 0.0) -> dict:
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    t0 = time.time()
    r = requests.post(CHAT_URL, headers=headers(key), json=body, timeout=120,
                      verify=ca_bundle())
    dt = time.time() - t0

    out = {"model": model, "http": r.status_code, "latency_s": round(dt, 2)}
    try:
        out["json"] = r.json()
    except Exception:  # noqa: BLE001
        out["text"] = r.text[:2000]
    return out


def extract_label(resp: dict) -> str | None:
    """Saca el texto de la respuesta sea cual sea la forma que devuelva."""
    j = resp.get("json")
    if not isinstance(j, dict):
        return None
    choices = j.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    msg = choices[0].get("message", {})
    content = msg.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):  # formato multimodal
        parts = [c.get("text", "") for c in content if isinstance(c, dict)]
        return " ".join(parts).strip()
    return None


def probe_invocation(key: str, repeats: int = 5) -> dict:
    print("\n" + "=" * 72)
    print("PASO 2 - INVOCACION REAL (tarea de clasificacion de regimen)")
    print("=" * 72)
    print(f"  Etiquetas esperadas: {REGIME_LABELS}")
    print(f"  Ground truth obvio: volatilidad p97 + drawdown -28% + breadth 12%")
    print(f"                      -> deberia ser 'risk_off' o 'crisis'\n")

    results: dict = {}

    for model in candidates():
        print(f"  --- {model} ---")
        attempts = []
        for i in range(repeats):
            try:
                resp = call_model(model, REGIME_PROMPT, key)
            except Exception as exc:  # noqa: BLE001
                attempts.append({"error": str(exc)})
                print(f"    intento {i+1}: [ERROR] {exc}")
                continue

            label = extract_label(resp)
            err = None
            j = resp.get("json")
            if isinstance(j, dict) and "error" in j:
                err = j["error"]
            attempts.append({
                "http": resp["http"],
                "latency_s": resp["latency_s"],
                "label": label,
                "error": err,
                "usage": (j or {}).get("usage") if isinstance(j, dict) else None,
                "provider": (j or {}).get("provider") if isinstance(j, dict) else None,
                "model_returned": (j or {}).get("model") if isinstance(j, dict) else None,
            })
            status = f"label={label!r}" if label else f"sin_label (error={err})"
            print(f"    intento {i+1}: HTTP {resp['http']}  {resp['latency_s']}s  {status}")

        valid = [a for a in attempts if a.get("label")]
        labels = [a["label"] for a in valid]
        lats = [a["latency_s"] for a in attempts if "latency_s" in a]

        summary = {
            "n_attempts": len(attempts),
            "n_valid_labels": len(valid),
            "distinct_labels": sorted(set(labels)),
            "deterministic": (len(set(labels)) == 1) if labels else None,
            "latency_median_s": round(statistics.median(lats), 2) if lats else None,
            "attempts": attempts,
        }
        results[model] = summary
        print(f"    => labels distintos: {summary['distinct_labels']}")
        print(f"    => determinista: {summary['deterministic']}")
        print(f"    => latencia mediana: {summary['latency_median_s']}s\n")

    return results


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--metadata-only", action="store_true",
                    help="Solo leer el catalogo (no requiere API key, no gasta)")
    ap.add_argument("--repeats", type=int, default=5,
                    help="Repeticiones para test de determinismo (default 5)")
    args = ap.parse_args()

    load_env_file()
    key = get_key()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    report: dict = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

    report["metadata"] = probe_metadata()

    if args.metadata_only:
        print("\n[--metadata-only] Se omite la invocacion real.")
        report["invocation"] = {"skipped": "metadata_only"}
    elif not key:
        print("\n" + "!" * 72)
        print("SIN API KEY: OPENROUTER_API_KEY no esta definida ni en el entorno ni en .env")
        print("Se omite el PASO 2 (invocacion real).")
        print("Para completar la Fase 0:")
        print("  1. Crea C:\\Users\\trodriguez\\src\\qlib\\.env con:")
        print("       OPENROUTER_API_KEY=sk-or-v1-...")
        print("  2. Vuelve a ejecutar: python jev_phase0_probe.py")
        print("!" * 72)
        report["invocation"] = {"skipped": "no_api_key"}
    else:
        print(f"\n  API key detectada (len={len(key)}, prefijo={key[:8]}...)")
        report["invocation"] = probe_invocation(key, repeats=args.repeats)

    out_file = OUT_DIR / "phase0_report.json"
    out_file.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nInforme guardado en: {out_file}")

    # Veredicto
    print("\n" + "=" * 72)
    print("VEREDICTO FASE 0")
    print("=" * 72)
    inv = report.get("invocation", {})

    # Resumen de lo aprendido en metadatos (independiente de la invocacion).
    hits = report.get("metadata", {}).get("catalog_hits", {})
    for mid, info in hits.items():
        pr = info.get("pricing") or {}
        free_marker = " (gratis)" if pr.get("prompt") == "0" else ""
        print(f"  [meta] {mid}: out={info.get('output_modalities')} "
              f"ctx={info.get('context_length')} pricing={pr.get('prompt')}{free_marker}")
    eps = report.get("metadata", {}).get("endpoint_probes", {})
    for mid, info in eps.items():
        print(f"  [meta] {mid}: endpoints={info.get('n_endpoints')}")

    if inv.get("skipped"):
        reason = inv["skipped"]
        if reason == "no_api_key":
            print("  INCOMPLETO - falta la API key para verificar invocacion.")
            print("  -> Rellena OPENROUTER_API_KEY en el .env del repo y repite.")
        elif reason == "metadata_only":
            print("  PARCIAL - solo metadatos leidos (--metadata-only).")
            print("  -> Ejecuta sin --metadata-only para probar la invocacion real.")
        else:
            print(f"  INCOMPLETO - invocacion omitida ({reason}).")
        return 2

    any_ok = False
    only_network_errors = True
    only_auth_errors = True
    for model, s in inv.items():
        if not isinstance(s, dict):
            continue
        if s.get("n_valid_labels"):
            any_ok = True
            print(f"  {model}: INVOCABLE, {s['n_valid_labels']}/{s['n_attempts']} "
                  f"respuestas validas, determinista={s['deterministic']}")
        for a in s.get("attempts", []):
            err = str(a.get("error", "")) + str(a.get("http", ""))
            if "SSLError" not in err and "Connection" not in err and "Max retries" not in err:
                only_network_errors = False
            if not (a.get("http") == 401 or "401" in err or "auth" in err.lower()):
                only_auth_errors = False

    if not any_ok:
        if only_auth_errors:
            print("  INCOMPLETO - OpenRouter rechaza la credencial (401).")
            print("  No es evidencia contra Jev: la key es invalida, caduca o sin saldo.")
            print("  -> Revisa OPENROUTER_API_KEY en el .env y repite.")
            return 4
        if only_network_errors:
            print("  INCONCLUSO - los fallos son de RED/TLS, no de Jev.")
            print("  Corrige la conectividad y repite; no es evidencia contra Jev.")
            return 3
        print("  Jev NO respondio con contenido utilizable (fallo de API, no de red).")
        print("  -> Plan B: usar un generador estandar de OpenRouter para el mismo problema.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
