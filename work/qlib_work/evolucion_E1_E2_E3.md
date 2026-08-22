# 🔄 La evolución E1 → E2 → E3: secuencia y motivos

> **Fecha:** 2026-08-23
> **Proyecto:** Qlib Work
> **Autor:** Toni (con la investigación de Quinn y el análisis riguroso del laboratorio)
> **Propósito:** Documentar el razonamiento completo que llevó de la estrategia 1 a la 3, para que quede clara la lógica del cambio de arquitectura.

---

## 🏁 Resumen ejecutivo

Pasamos de **una estrategia (momentum puro)** a **tres en paralelo**, porque la investigación rigurosa (purged CV) reveló que **el momentum NO es un pilar robusto**, mientras que el **PEAD sí lo es**. La E3 es la arquitectura correcta: **PEAD como núcleo + momentum táctico con vol-gating**.

Este documento explica el **porqué** de cada paso.

---

## E1 — Momentum 120 puro (el punto de partida)

### Qué era
La estrategia **momentum 120d**: comprar las **30 acciones** del S&P500 (sp500_liquid) con mejor retorno acumulado en 120 días, rebalanceo semanal, con costes IB tiered y €20,000 ficticios en paper-trading.

### Por qué se creó
- El **momentum es el factor con más respaldo empírico** de la literatura (Jegadeesh & Titman, 1993).
- **Validado en backtest**: IC OOS +0.066, retorno +18-21% anual, Sharpe ~1.0.
- Era la **primera estrategia rentable** tras probar muchas (universo tech_giants falló, etc.).
- Se montó el **paper-trading** (14-ago-2026) para validarla en vivo.

### Motivo de su estado hoy (monitor)
La E1 se mantiene como **control / monitor**: es "qué pasa si no cambio nada". Su evolución en paper (−2.45% al inicio) coincide con lo que luego descubrimos: el momentum no es robusto.

---

## E2 — Momentum + filtro PEAD (la primera mejora)

### Qué añadió
La E2 = momentum puro + **filtro PEAD negativo**: si un ticker del topk tiene una **sorpresa de earnings catastrófica** (SUE < −2σ, fresca), se sustituye por el siguiente del ranking. Se reconstruyó retroactiva al 14-ago.

### Por qué se creó (el razonamiento)
1. **Descubrimos el PEAD**: la sorpresa de earnings predice el retorno post-anuncio (IC Spearman 0.19-0.22; y con purged CV +0.085 a +0.130).
2. **Intentamos combinarlos de 2 formas** y aprendimos:
   - **Suma de señales** (z-momentum + z-PEAD): Sharpe 0.57 vs 1.0 → **FALLÓ** (señal de evento se diluye como serie continua).
   - Conclusión: el PEAD **no se suma al momentum, se usa como filtro/refuerzo**.
3. Así nació la E2: el PEAD evita comprar momentum "tocado" por malos earnings.

### Motivo de su estado hoy (monitor)
La E2 fue un paso intermedio valioso (su lección: el PEAD aporta vía filtro o núcleo, no suma). Pero **seguía teniendo al momentum como pilar** — el error de fondo que el purged CV destapó.

---

## 🔍 El hallazgo que cambió todo: el Purged CV

### Qué hicimos
Aplicamos **Purged Cross-Validation** (método riguroso de López de Prado) al momentum y al PEAD por separado, para eliminar el solapamiento de etiquetas (data leakage).

### Los resultados (SEMANA 3)
| Factor | IC en calma | IC en estrés | Veredicto |
|---|---|---|---|
| **Momentum 120d** | +0.024 | **−0.184** | ⚠️ Régimen-dependiente (CI NO se solapan) |
| **PEAD** | +0.085 a +0.130 | idem | ✅ Robustos (CI estrechos, positivos) |

**Hallazgos clave:**
1. **El momentum NO es robusto**: funciona en calma (+0.024) pero **FALLA en estrés** (−0.184). Su Sharpe ~1.0 era una media que disfrazaba periodos de reversión (2020-22).
2. **El PEAD SÍ es robusto**: IC positivo y estable en todos los estados.
3. **La regresión confirmó**: el `vol_alta` es significativo (t=−3.06) y el tiempo NO (t=+1.32) → es **régimen, no decaimiento secular**.

### La conclusión (decisiva)
> **El momentum no debe ser el pilar de la estrategia.** El PEAD (robusto) debe ser el núcleo, y el momentum (frágil) un componente táctico con reducción de tamaño.

Este hallazgo **invierte los pesos** que teníamos implícitos en E2 (momentum pilar + PEAD filtro) → ahora el PEAD es el corazón y el momentum el satélite.

---

## E3 — PEAD-núcleo + momentum-táctico con vol-gate (la arquitectura correcta)

### Qué es
La E3 es la **respuesta directa al hallazgo**. Un solo simulador (`simulate_pead_core.py`) con **dos libros de capital separados**:

| Libro | % del capital | Lógica |
|---|---|---|
| **NÚCLEO (PEAD)** | 65% | Top 22 por **SUE positivo y fresco** (drift post-anuncio natural) |
| **TÁCTICO (momentum)** | 35% (techo 50%) | Top 12 por momentum 120d **+ vol-gate** |

### Por qué esta arquitectura
1. **PEAD como núcleo** → porque es la señal **robusta** (IC estable +0.085 a +0.130), la base estructural.
2. **Momentum como táctico** → porque es **dependiente del régimen**: gana en tendencias, pierde en estrés. Se limita a ≤50% y se apaga cuando la vol sube.
3. **Vol-gate** → el mecanismo que reduce/pausa el momentum en alta vol. **Validado (Semana 5)**: Sharpe 1.136 vs 0.96 puro, DD reduce de −19% a −15%.

### El vol-gate (componente clave)
- Cuando la vol del mercado está alta (percentil ≥75%), el momentum se reduce a la mitad o se pausa.
- Evita el **momentum-crash** exactamente cuando la evidencia (Semana 4) dice que va a fallar.
- El **PEAD NO se gatea** (es robusto en todos los estados).

### Estado hoy
- E3 arrancó en paper-trading (17:00 sábado, cronjob).
- **Valor: $22,023 = €19,489** · 34 posiciones (22 núcleo + 12 táctico) · rebalanceo semanal automático.

---

## 📊 Las 3 estrategias en paralelo (estado 23-ago-2026)

| Estrategia | Arquitectura | P&L | Rol |
|---|---|---|---|
| **E1** | Momentum 120 puro | −2.45% | Monitor (control) |
| **E2** | Momentum + filtro PEAD | −1.83% | Monitor |
| **E3** | PEAD-núcleo + momentum-táctico + vol-gate | −0.05% | **La apuesta** |

> *Al día de escritura, E3 acaba de nacer (solo costes de entrada). Comparaciones significativas requieren semanas (≥24-50 rebalanceos según Quinn).*

---

## 🧠 Síntesis de los motivos (una tabla)

| Paso | Decisión | Motivo |
|---|---|---|
| **E1** | Momentum puro | Factor con más respaldo, validado en backtest (Sharpe ~1.0) |
| **E2** | + filtro PEAD | Descubrimos el PEAD (IC 0.19); la suma falló, el filtro no |
| **Hallazgo** | Purged CV | Revela: momentum NO robusto (régimen), PEAD SÍ robusto |
| **E3** | PEAD-núcleo + momentum-táctico | Invierte los pesos: lo robusto (PEAD) al centro, lo frágil (momentum) al margen |
| **Vol-gate** | Validado (Sharpe 1.136) | Protege el momentum cuando la vol alta lo hace fallar |

---

## ⚠️ Advertencias honestas (para no repetir errores)

1. **No sobreapostar PEAD**: es robusto en ~6 años de muestra, no certidumbre absoluta.
2. **No racionalizar**: el momentum no debe volver a ser el pilar "esperando el régimen".
3. **Separar régimen vs decaimiento**: ya confirmamos es régimen (t no significativo); si el PEAD también se degradara, el problema sería todo el espacio de señales.
4. **No escalar a capital real** sin historial limpio de E3 (varias semanas).

---

*Documento de cierre de esta etapa. Complementa `plan_E3_quinn_futuro.md`, `quinn_regimenes.md`, `cambio_pead_filtro_a_nucleo.md` y `regimen_test_resultado.md`.*
