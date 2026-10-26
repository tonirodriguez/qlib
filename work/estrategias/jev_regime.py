"""jev_regime.py — Capa de decision de REGIMEN via Jev (TypeSafe) + sizing.

FASE 1 del plan Jev/OpenRouter. Ver `jev_fase1_diseno.md` para el diseno.

QUE HACE
    Convierte un vector de indicadores de mercado (el mismo que ya produces en
    extract_estados.py) en un multiplicador de exposicion, usando el endpoint
    NATIVO de decisiones de Jev, que devuelve PROBABILIDADES calibradas.

POR QUE PROBABILIDADES Y NO UNA ETIQUETA
    La Fase 0 demostro que Jev no devuelve solo `choice`, sino:
        probabilities: {risk_on: 0, neutral: 0, risk_off: 0.03, crisis: 0.97}
        confidence: 0.96
    Usar el vector completo da un sizing CONTINUO en vez de un interruptor.
    Formula (acordada):
        exposicion = 1 - P(crisis) - 0.5 * P(risk_off)
    acotada a [0, 1]. Ver `exposure_from_probabilities`.

CONTRATO DE LA API (deducido en Fase 0, no documentado publicamente)
    POST https://openrouter.ai/api/alpha/decisions
    {
      "model": "~typesafe/jev-latest",
      "state": <string|record|array>,
      "questions": {
        "<id>": {
          "type": "choice"|"noul"|"score"|"box",
          "instructions": <string|record|array>,
          "criteria": <record>
        }
      }
    }

IMPORTANTE — NO toca el paper-trading vivo. Es una capa nueva y aislada.

Uso como libreria:
    from jev_regime import JevRegimeClassifier, exposure_from_probabilities
    clf = JevRegimeClassifier()
    d = clf.classify({"vol_pct": 0.97, "drawdown120": 1.0, ...})
    print(d.exposure)

Uso como CLI (con datos de ejemplo o un CSV):
    python jev_regime.py --demo
    python jev_regime.py --csv estados_mercado.csv --limit 10 --out jev_sizing.csv
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Configuracion
# ---------------------------------------------------------------------------

DECISIONS_URL = "https://openrouter.ai/api/alpha/decisions"
NATIVE_MODEL = os.environ.get("JEV_NATIVE_MODEL", "~typesafe/jev-latest")

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent

# Etiquetas del regimen. El orden importa para la formula de exposicion.
LABELS = ["risk_on", "neutral", "risk_off", "crisis"]

# Pesos de castigo por etiqueta en el sizing. crisis resta 1.0 completo,
# risk_off la mitad. Acordado con el usuario.
RISK_WEIGHTS = {"crisis": 1.0, "risk_off": 0.5, "neutral": 0.0, "risk_on": 0.0}

DEFAULT_KASPERSKY_CA = r"C:\Users\trodriguez\certs\kaspersky-root.cer"
_BUNDLE_CACHE: Path | None = None


def load_env_file() -> None:
    """Carga variables desde el .env del repo si no estan ya en el entorno."""
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


def ca_bundle() -> str | bool:
    """Bundle de CAs (certifi + CA local de Kaspersky). Ver Fase 0."""
    global _BUNDLE_CACHE
    try:
        import certifi
        base = Path(certifi.where())
    except Exception:  # noqa: BLE001
        return True

    kaspersky = Path(os.environ.get("KASPERSKY_CA_PATH", DEFAULT_KASPERSKY_CA))
    if not kaspersky.exists():
        _BUNDLE_CACHE = base
        return str(base)

    out_dir = HERE / "jev_phase0_out"
    out_dir.mkdir(parents=True, exist_ok=True)
    bundle = out_dir / "ca_bundle.pem"
    if _BUNDLE_CACHE is not None and bundle.exists():
        return str(bundle)
    try:
        bundle.write_bytes(base.read_bytes() + b"\n" + kaspersky.read_bytes())
        _BUNDLE_CACHE = bundle
        return str(bundle)
    except Exception:  # noqa: BLE001
        _BUNDLE_CACHE = base
        return str(base)


def get_key() -> str | None:
    return os.environ.get("OPENROUTER_API_KEY") or None


# ---------------------------------------------------------------------------
# Sizing
# ---------------------------------------------------------------------------

def exposure_from_probabilities(probs: dict[str, float],
                                weights: dict[str, float] | None = None) -> float:
    """Multiplicador de exposicion en [0,1] a partir del vector de probabilidad.

        exposicion = 1 - sum_i( w_i * P(i) )

    con w = {crisis: 1.0, risk_off: 0.5, neutral: 0.0, risk_on: 0.0}.

    Normaliza las probabilidades si no suman 1 (Jev a veces devuelve solo
    las etiquetas con peso no nulo, p.ej. {options:0, risk_on:0, crisis:1}).
    """
    w = weights or RISK_WEIGHTS
    total = sum(v for k, v in probs.items() if k in w and isinstance(v, (int, float)))
    if total <= 0:
        return 1.0  # sin senal de riesgo -> exposicion plena
    norm = {k: v / total for k, v in probs.items()
            if k in w and isinstance(v, (int, float))}
    penalty = sum(w.get(k, 0.0) * v for k, v in norm.items())
    return float(min(1.0, max(0.0, 1.0 - penalty)))


# ---------------------------------------------------------------------------
# Cliente
# ---------------------------------------------------------------------------

@dataclass
class RegimeDecision:
    """Resultado de una clasificacion, con todo lo necesario para auditar."""
    label: str | None
    probabilities: dict[str, float]
    confidence: float | None
    exposure: float
    state_used: dict | str | list | None = None
    model_returned: str | None = None
    cost: float | None = None
    latency_s: float | None = None
    error: str | None = None
    raw: dict = field(default_factory=dict)

    def to_row(self) -> dict:
        d = asdict(self)
        d.pop("raw", None)
        d.pop("state_used", None)
        d["probabilities"] = json.dumps(d["probabilities"], ensure_ascii=False)
        return d


class JevRegimeClassifier:
    """Clasificador de regimen via el endpoint nativo de decisiones de Jev."""

    def __init__(self, model: str = NATIVE_MODEL, timeout: int = 90,
                 retries: int = 2, verbose: bool = False):
        load_env_file()
        self.model = model
        self.timeout = timeout
        self.retries = retries
        self.verbose = verbose
        self.key = get_key()
        if not self.key:
            raise RuntimeError(
                "Falta OPENROUTER_API_KEY. Anade la clave al .env del repo."
            )

    # -- construccion del payload -------------------------------------------

    @staticmethod
    def build_state(features: dict) -> dict:
        """Convierte indicadores crudos en el `state` que espera Jev.

        Se pasa un record (no un string) para que Jev reciba los numeros
        estructurados y no tenga que parsear prosa.
        """
        return {k: (float(v) if isinstance(v, (int, float)) else v)
                for k, v in features.items()}

    def build_payload(self, features: dict) -> dict:
        return {
            "model": self.model,
            "state": self.build_state(features),
            "questions": {
                "regimen": {
                    "type": "choice",
                    "instructions": (
                        "Clasifica el REGIMEN DE MERCADO actual a partir de los "
                        "indicadores del estado. Usa criterios cuantitativos."
                    ),
                    "criteria": {
                        "risk_on": "Volatilidad baja (percentil <40), sin drawdown, breadth amplio (>60%).",
                        "neutral": "Senales mixtas: volatilidad media (p40-p70) o breadth intermedio.",
                        "risk_off": "Volatilidad elevada (p70-p90) o drawdown moderado (0 a -20%), breadth deteriorado.",
                        "crisis": "Volatilidad extrema (p>90) Y drawdown severo (<-20%) con correlaciones altas (>0.6).",
                    },
                }
            },
        }

    # -- llamada -------------------------------------------------------------

    def classify(self, features: dict) -> RegimeDecision:
        """Clasifica un estado. Nunca lanza por error de API: lo devuelve."""
        payload = self.build_payload(features)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
            "HTTP-Referer": "https://github.com/tonirodriguez/qlib",
            "X-Title": "qlib-jev-regime",
        }

        last_err = None
        for attempt in range(self.retries + 1):
            t0 = time.time()
            try:
                r = requests.post(DECISIONS_URL, headers=headers, json=payload,
                                  timeout=self.timeout, verify=ca_bundle())
                dt = time.time() - t0
                body = r.json() if r.content else {}

                if r.status_code != 200:
                    msg = (body.get("error") or {}).get("message", r.text[:300])
                    last_err = f"HTTP {r.status_code}: {msg}"
                    # 4xx no se reintenta salvo 429
                    if r.status_code != 429:
                        break
                    time.sleep(1.5 * (attempt + 1))
                    continue

                ans = (body.get("answers") or {}).get("regimen") or {}
                probs = ans.get("probabilities") or {}
                label = ans.get("choice")
                conf = ans.get("confidence")
                usage = body.get("usage") or {}

                if not label and not probs:
                    last_err = "respuesta sin 'choice' ni 'probabilities'"
                    continue

                return RegimeDecision(
                    label=label,
                    probabilities={k: float(v) for k, v in probs.items()
                                   if isinstance(v, (int, float))},
                    confidence=conf,
                    exposure=exposure_from_probabilities(probs),
                    state_used=payload["state"],
                    model_returned=body.get("model"),
                    cost=usage.get("cost"),
                    latency_s=round(dt, 2),
                    raw=body,
                )
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
                time.sleep(1.0 * (attempt + 1))

        return RegimeDecision(
            label=None, probabilities={}, confidence=None,
            exposure=1.0,  # fail-open: sin senal, no se recorta exposicion
            state_used=payload["state"], error=last_err,
        )

    def classify_batch(self, rows: list[dict], sleep_s: float = 0.0) -> list[RegimeDecision]:
        out = []
        for i, feats in enumerate(rows):
            d = self.classify(feats)
            if self.verbose:
                print(f"  [{i+1}/{len(rows)}] {d.label or 'ERR'} "
                      f"exp={d.exposure:.3f} {d.cost or ''} {d.error or ''}")
            out.append(d)
            if sleep_s:
                time.sleep(sleep_s)
        return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

DEMO_STATES = {
    "crisis_2008_style": {
        "vol_pct": 0.97, "drawdown_52w": -0.28, "breadth": 0.12,
        "correlacion_media": 0.78, "curva_10y2y": -0.45,
    },
    "risk_off_2022_style": {
        "vol_pct": 0.85, "drawdown_52w": -0.15, "breadth": 0.28,
        "correlacion_media": 0.55, "curva_10y2y": -0.20,
    },
    "neutral_mixed": {
        "vol_pct": 0.55, "drawdown_52w": -0.04, "breadth": 0.48,
        "correlacion_media": 0.31, "curva_10y2y": 0.12,
    },
    "risk_on_calm": {
        "vol_pct": 0.18, "drawdown_52w": 0.0, "breadth": 0.72,
        "correlacion_media": 0.19, "curva_10y2y": 0.45,
    },
}


def _print_decision(name: str, d: RegimeDecision) -> None:
    if d.error:
        print(f"  {name:<24} ERROR: {d.error}")
        return
    probs = ", ".join(f"{k}={v:.2f}" for k, v in sorted(d.probabilities.items()))
    print(f"  {name:<24} {str(d.label):<9} exp={d.exposure:.3f} "
          f"conf={d.confidence} [{probs}]")


def main() -> int:
    ap = argparse.ArgumentParser(description="Clasificador de regimen via Jev.")
    ap.add_argument("--demo", action="store_true", help="Ejecuta los 4 estados de ejemplo")
    ap.add_argument("--csv", type=str, help="CSV con columnas de indicadores (p.ej. estados_mercado.csv)")
    ap.add_argument("--limit", type=int, default=20, help="Filas maximas del CSV (default 20)")
    ap.add_argument("--out", type=str, help="CSV de salida con label/exposure por fecha")
    ap.add_argument("--model", type=str, default=NATIVE_MODEL)
    args = ap.parse_args()

    if not args.demo and not args.csv:
        ap.print_help()
        return 1

    clf = JevRegimeClassifier(model=args.model, verbose=True)

    if args.demo:
        print("=" * 74)
        print("DEMO - clasificacion de regimen con sizing por probabilidad")
        print("=" * 74)
        print(f"  modelo: {clf.model}")
        print(f"  formula: exposicion = 1 - P(crisis) - 0.5*P(risk_off)\n")
        total = 0.0
        for name, feats in DEMO_STATES.items():
            d = clf.classify(feats)
            _print_decision(name, d)
            total += d.cost or 0.0
        print(f"\n  coste total demo: ${total:.6f}")
        return 0

    # --- modo CSV ---
    import pandas as pd
    df = pd.read_csv(args.csv)
    if "datetime" in df.columns:
        df = df.set_index("datetime")
    df = df.head(args.limit)
    print(f"CSV: {args.csv} | {len(df)} filas | columnas: {list(df.columns)}")

    rows = df.to_dict(orient="index")
    decisions = clf.classify_batch(list(rows.values()))

    out_df = pd.DataFrame([{**{"date": k}, **d.to_row()}
                           for k, d in zip(rows.keys(), decisions)])
    print("\n" + out_df.to_string(index=False))

    if args.out:
        out_df.to_csv(args.out, index=False)
        print(f"\nGuardado en: {args.out}")
        print(f"Coste total: ${sum(d.cost or 0 for d in decisions):.6f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
