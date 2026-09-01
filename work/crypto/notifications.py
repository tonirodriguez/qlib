"""
notifications.py — Notificaciones por Telegram para el paper trading SFM v8 (Paso 7).

Usa `hermes send` (mecanismo oficial de Hermes) para enviar mensajes a la
plataforma de mensajeria configurada (Telegram), REUTILIZANDO las credenciales
del gateway. No requiere crear bot ni guardar tokens de exchange.

Envio por defecto a tu canal de Telegram ("Home", chat_id 899024572), o al que
se indique via env TELEGRAM_TARGET / NOTIFY_TARGET.

Uso:
  python work/crypto/notifications.py "mensaje"                          # notify
  python work/crypto/notifications.py --subject "[v8]" "mensaje"         # con asunto
  python work/crypto/notifications.py --metrics 10450 10000              # resumen de metricas
  echo "..." | python work/crypto/notifications.py                        # desde stdin

Exit code: 0 ok, !=0 error de entrega.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
HERMES_BIN = os.getenv("HERMES_BIN", "/opt/hermes/.venv/bin/hermes")
# Canal por defecto: el DM de Toni en Telegram. Override via env.
DEFAULT_TARGET = "telegram:899024572"


def get_target() -> str:
    return os.getenv("NOTIFY_TARGET", os.getenv("TELEGRAM_TARGET", DEFAULT_TARGET))


def send_message(text: str, subject: str | None = None, target: str | None = None) -> bool:
    """Envia un mensaje por Telegram via hermes send. Devuelve True si OK."""
    tgt = target or get_target()
    cmd = [HERMES_BIN, "send", "-t", tgt]
    if subject:
        cmd += ["-s", subject]
    cmd += [text]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if proc.returncode == 0:
            return True
        sys.stderr.write(f"hermes send fallo (rc={proc.returncode}): {proc.stderr}\n")
        return False
    except Exception as exc:  # noqa
        sys.stderr.write(f"Error enviando notificacion: {exc}\n")
        return False


def format_metrics_report(current_value: float, start_capital: float) -> str:
    """Componer un resumen legible de metricas/P&L del paper."""
    pnl_pct = (current_value - start_capital) / start_capital * 100
    return (
        f"💰 PAPER TRADING v8\n"
        f"   Valor: ${current_value:,.2f} (inicio ${start_capital:,.0f})\n"
        f"   P&L: {pnl_pct:+.2f}%"
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("message", nargs="?", help="Texto a notificar (o stdin si se omite)")
    ap.add_argument("-s", "--subject", default=None, help="Asunto/linea de cabecera")
    ap.add_argument("--metrics", nargs=2, type=float, metavar=("CURRENT", "START"),
                    help="Enviar resumen de metricas (valor actual, capital inicio)")
    ap.add_argument("--target", default=None, help="Override de target (ej. telegram:123)")
    args = ap.parse_args()

    if args.metrics:
        text = format_metrics_report(args.metrics[0], args.metrics[1])
    elif args.message:
        text = args.message
    else:
        # leer de stdin
        text = sys.stdin.read().strip()
        if not text:
            ap.error("no message provided")

    ok = send_message(text, subject=args.subject, target=args.target)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()