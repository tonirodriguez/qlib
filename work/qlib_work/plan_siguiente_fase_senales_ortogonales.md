# 🏁 Plan de la Siguiente Fase (post-S8) — Nuevas señales ortogonales

> **Fecha:** 2026-08-23
> **Proyecto:** Qlib Work
> **Base:** señales ortogonales ya validadas en laboratorio (`senal_ortogonal_resultado.md`), pendientes de implementar a partir de la S8.
> **Regla (Quinn):** estas señales NO entran en el paper de E3 hasta la decisión S8. Son la diversificación del "no dependas de un factor único".

---

## 🎯 Contexto: por qué esta fase

Tras el ciclo E1→E2→E3 (momentum-pilar → PEAD-núcleo + momentum-táctico + vol-gate), la siguiente pregunta estratégica es:

> **¿Cómo diversifico para no depender solo de PEAD + momentum?**

La respuesta del laboratorio (Prioridad 2, `quinn_prioridad2.md`): construir **señales ortogonales** con datos que ya tenemos (OHLCV + volume), sin pagar ni infra frágil. El resultado validó **2 señales** que son las candidatas para esta fase.

---

## 🧬 Las 2 señales a atacar a partir de la S8

(Validadas con purged CV a 60d — `reversal_illiquidity_purgedcv.py`)

| Señal | Qué es | IC purged | Co-seno momentum | Co-seno PEAD | Estado |
|---|---|---|---|---|---|
| **A. Reversal 5d** | Media-reversión de corto plazo (retorno 1-5d, sentido negativo) | **+0.044** | −0.20 | −0.03 | ✅ Candidata |
| **B. Amihud illiquidity** | Prima de liquidez `\|ret\|/(precio×vol)` | **+0.070** | **−0.007** | −0.07 | ✅ Candidata (muy ortogonal) |

**Amihud es la más prometedora** (IC +0.07, co-seno con momentum casi CERO = totalmente independiente).

---

## ⏭️ Plan de acción para la siguiente fase (tras la S8)

### Paso 0 — Gate de entrada (se cruza tras la S8)
Solo se ataca esta fase si **al menos una de estas** se cumple en la S8:
- El PEAD-núcleo de E3 se confirma en vivo (E3 estable/bate a E1/E2), **o**
- El paper de E3 muestra que el reponderamiento fue correcto.

**Si el PEAD también se degrada → NO se ataca esto; se pausa el espacio de señales** (alarma §5.2).

### Paso 1 — Robustez adicional (laboratorio, ~1 semana)
Antes de integrar en paper, reforzar la validación de las 2 señales:
- **Revalidar a 20 días** (no solo 60d) con el mismo purged CV.
- Probar **1 año extra hacia atrás** si el universo lo permite (más transiciones).
- Confirmar que el **co-seno con momentum y PEAD sigue bajo** en ambos horizontes.
- **Entregable:** `senal_ortogonal_resultado_v2.md`.

### Paso 2 — Seleccionar la(s) señal(es) que pasen (criterio Quinn)
Una señal pasa a paper si en TODOS los horizontes probados:
1. **IC purged > 0.02** (y CI que no cruce 0)
2. **Co-seno < 0.3** con momentum Y con PEAD
3. Resultado **estable**, no dependiente de un parámetro único (p.ej. la ventana exacta)

Si ambas pasan, priorizar **Amihud** (más ortogonal). Si solo pasa una, usar esa.

### Paso 3 — Integración como 4ª piedra (o refuerzo) sin romper E3
**No tocar E3.** Crear **E4** (`simulate_pead_core.py` no se modifica; un nuevo simulador si hace falta) o un **libro nuevo** en el mismo motor replicando el patrón de libros:
- **Libro 1 — PEAD** (núcleo, 60%)
- **Libro 2 — Momentum táctico** (30%)
- **Libro 3 — Señal ortogonal nueva** (10%, Amihud o reversal)

**Peso inicial pequeño (10%)** para no contaminar la cartera mientras se valida en paper. Endpoint igual que los cronjobs (sábado 15:00/16:00/17:00 + nueva hora).

**Ojo de costes:** la señal ortogonal (especialmente reversal, alta rotación) tiene **turnover alto** → vigilar costes IB netos. Amihud es de menor rotación.

### Paso 4 — Medición en paralelo (semanas siguientes)
- Mantener E1/E2/E3 como monitores.
- Medir E4 (o el libro nuevo) contra las demás con el **mismo comparativo** (`decision_s8_alarmas.py`).
- Esperar **≥24-50 rebalances** antes de juzgar (criterio Quinn).

---

## 📅 Cronograma orientativo

| Periodo | Acción |
|---|---|
| **Tras S8** | Gate de entrada (¿PEAD vivo OK?) |
| **1ª-2ª semana** | Robustez adicional lab (20d + 1 año atrás) → `senal_ortogonal_resultado_v2.md` |
| **3ª semana** | Seleccionar señal(es) que pasen; montar E4/libro nuevo (peso instrumento 10%) |
| **4+ semana** | Paper paralelo de E4, medición con comparativo, vigilancia de costes |
| **~8 semanas** | Decisión: promover la señal ortogonal o descartarla |

---

## 🔍 Riesgos y controles

- **Turnover/costes** del reversal → vigilar costes IB netos, no solo retorno bruto.
- **No sobreapostar** la señal ortogonal: peso inicial pequeño (10%), crece solo si mejora riesgo-ajustado neto.
- **No romper E3** en el proceso: E3 es la apuesta principal que ya viene validándose; la señal nueva es incremental.

---

## 📎 Documentos relacionados
- `senal_ortogonal_resultado.md` — validación de las 2 señales (este ciclo)
- `quinn_prioridad2.md` — la recomendación de Quinn de usar señales ortogonales
- `plan_E3_quinn_futuro.md` — el plan del ciclo actual (E3), del que esta fase es la continuación
- `decision_s8_alarmas.py` — infraestructura de medición para decidir en S8

---

*Plan de la siguiente fase del proyecto Qlib Work. Se activa tras la decisión S8.*
