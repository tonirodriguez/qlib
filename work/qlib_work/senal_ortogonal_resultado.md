# 🧬 Señales Ortogonales — Resultado purged CV (2026-08-23)

**Script:** `reversal_illiquidity_purgedcv.py` · **Prioridad 2 (Quinn)** · **Protocolo:** purged CV + co-seno (idéntico al PEAD/momentum). Hipótesis falsable pre-registrada: IC purged > 0.02 Y co-seno bajo (<0.3) con momentum y PEAD.

## Resultado (retorno fut. 60d)

| Señal | IC global | IC purged | CI 95% | cos momentum | cos PEAD | Veredicto |
|---|---|---|---|---|---|---|
| **reversal 5d** | +0.036 | **+0.044** | [+0.034, +0.039] | −0.196 | −0.025 | ✅ Ortogonal y útil |
| **Amihud illiquidity** | +0.073 | **+0.070** | [+0.070, +0.076] | **−0.007** | −0.073 | ✅ **Muy ortogonal** |

## Veredicto

**Las 2 señales ortogonales son prometedoras** con el protocolo riguroso purged-CV:

1. **reversal 5d** (media-reversión corto plazo): IC +0.044, co-seno bajo con momentum (−0.20) — captura el horizonte OPUESTO al momentum (como Quinn predijo).

2. **Amihud illiquidity** (prima de liquidez): IC +0.070, **co-seno con momentum −0.007 (casi cero = totalmente ortogonal)**, co-seno con PEAD −0.07. Es la señal más independiente → **ideal para diversificar**.

## Implicación

Sin pagar por datos fundamentales y sin infra frágil, hemos encontrado **2 señales con alpha propio y casi independientes** de momentum y PEAD. Esto sustenta el objetivo de la Prioridad 2: **no depender de un factor único** — una tercera pierna viable para post-S8.

## Límite aplicado (según Quinn)
- Estas señales **NO entran en el paper de E3** hasta la decisión S8.
- Se documentan como candidatas de laboratorio para diversificar en el siguiente ciclo.

## Próximo paso
- Confirmar robustez en otro horizonte (20d) y quizá probar 1 año extra atrás si el universo lo permite.
- El **value/quality real con fundamentales** queda pospuesto (requeriría datos de pago; solo si una señal ortogonal sobrevive a S8 y hay capital real).

---

*Documento de referencia del proyecto Qlib Work. Complementa `quinn_prioridad2.md`.*
