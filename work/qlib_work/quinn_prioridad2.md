# 🧭 QUINN — Prioridad 2: 3ª señal ortogonal sin datos fundamentales (bloqueo resuelto)

**Autor:** Quinn · Investment Research Senior (14+ años buy-side)
**Sujeto:** Toni · proyecto Qlib work
**Fecha:** 2026-08-23
**Problema:** Qlib US solo tiene OHLCV ($open,$high,$low,$close,$volume). Value (B/M, E/P) y quality (ROE/ROIC, dividend yield) exigen fundamentales que NO hay en el dataset. ¿Qué hacer?

**Hechos base verificados:** PEAD-núcleo validado (~1 año yahooquery, purged CV IC +0.085…+0.130, NO se paga FMP — `decision_historico_earnings.md`). Momentum 120d = régimen, no factor robusto. Low-vol YA probado como selección y NO aporta (`lowvol_diagnostico.md`: IC +0.126, el crecimiento gana en alcista → se usa solo como riesgo, no como señal). Earnings descargados tienen: `ticker, quarter, actual, estimate, surprise_pct, reported_ts` (~2 años, 1138 filas).

---

## 1. Diagnóstico del bloqueo (honesto)

La Prioridad 2 como estaba planteada (value/quality con B/M, ROE, div yield) **NO es ejecutable con datos limpios** ahora: ninguna fuente gratuita da fundamentales point-in-time (book value as-of histórico, ROE restateado). PERO eso **no bloquea el objetivo real**, que es: *una 3ª señal ortogonal a momentum y a PEAD, simple y validada con purged-CV antes de la S8, sin meterla en paper*. La palabra clave es **ortogonal**, no "value" o "quality". Hay señales de precio/volumen estructuralmente ortogonales que sí podemos construir con lo que Qlib ya tiene.

**Regla de oro aplicada:** no pagar antes de validar, no infra frágil sin valor, no sobreingeniería. El objetivo es un factor modesto y probado, no una base de datos.

---

## 2. Priorización de las opciones (a–e)

| Rango | Opción | Veredicto |
|---|---|---|
| 🥇 **1º** | **(a) Señales ortogonales con datos que YA tenemos (OHLCV + volume + earnings ya bajados)** | **HACER.** Es la salida limpia del bloqueo. Sin coste, sin infra nueva, con la metodología purged-CV ya validada. |
| 🥈 2º | **(d) Posponer el VALUE/QUALITY propiamente dicho (con fundamentales)** | **PARCIALMENTE SÍ** — el value/quality literal queda pospuesto a post-S8 / solo si se paga. Pero NO significa "no hacer la 3ª señal": la 3ª señal se hace ahora vía (a). |
| ⚪ 3º | **(b) Scraping de stockanalysis (book value, ROE, PE histórico)** | **NO para la señal.** Fragilidad + **no point-in-time** (figuras restated/current ≠ as-of histórico) lo invalidan para un purged CV honesto. Es exactamente el "infra frágil sin valor". |
| 🔴 | **(c) FMP $29/mes ANTES de la S8** | **NO.** Rompe lo decidido en la Prioridad 1 y — lo más importante — **estás pagando para descubrir una señal que aún no has demostrado que exista en este universo.** Primero validas barato; si una señal ortogonal promete Y la S8 confirma el PEAD, entonces se valora pagar por lo limpio. |
| 🔴 | **(e) Otra (HMM/fundamentales sintéticos/etc.)** | NO. Detector sofisticado / proxies cosidos = sobreingeniería. |

---

## 3. QUÉ HACER: opción (a) — señales ortogonales precio/volumen, un factor a la vez

**Candidatos concretos, simples, 100% con datos Qlib** (no necesitan ni un tick de fundamental nuevo):

1. **Reversal de corto plazo (retorno 1–5 días, sentido negativo).** Media-reversión semanal. Por construcción captura el horizonte OPUESTO al momentum 120d → correlación estructural baja con momentum. Clara y sin fundamentales. **Primer candidato.**
2. **Amihud illiquidity (|ret| / (precio×volumen)).** Prima de liquidez/iliquidez, clásica, puramente precio-volumen (no necesita market cap: precio×volumen compartido ya está en OHLCV). Razonablemente ortogonal a momentum y a sorpresa de earnings. **Segundo candidato.**
3. **Secondary (solo si hay ganas): "earnings consistency/quality"** a partir de los datos de earnings ya descargados (p.ej. estabilidad del surprise entre trimestres). **Cuidado:** es el MISMO evento que el PEAD → riesgo alto de correlación. Trátalo como tercero y mide su ortogonalidad antes de creértelo.

**Descartados por evidencia previa:** low-vol (ya probado, no aporta como selección — `lowvol_diagnostico.md`); size proxy (necesita shares/float que Qlib no da de forma limpia; proxy por precio es ruido).

### Protocolo (replica EXACTA lo ya validado — `pead_purgedcv.py` / `momentum_purgedcv.py`)
- Script nuevo en `work/estrategias/` (p.ej. `reversal_illiquidity_purgedcv.py`), **sin tocar las sims E1/E2/E3**.
- **Pre-registrar por escrito** la hipótesis falsable antes de correr.
- Métrica: IC Spearman, purged CV, CI bootstrap a 20d/60d (idéntico al PEAD).
- **CRÍTICO — medir la ortogonalidad de verdad:** reportar la **correlación/co-seno entre el IC de la señal nueva, el IC del momentum 120d y el IC del PEAD**. No basta IC>0; tiene que ser **bajo co-seno** con los dos existentes. Si co-seno alto → descartarla aunque tenga IC.
- Entregable: `señal_ortogonal_resultado.md` — IC por señal, CI, co-seno con momentum/PEAD, y veredicto "ortogonal y útil / correlacionado / ruido".
- **Límite duro:** NO entra en el paper de E3 hasta la decisión S8.
- **Horizonte:** ~1–2 semanas de laboratorio. Si el primer candidato da co-seno alto o IC~0, no forces el segundo con grid; documéntalo y cierra.

---

## 4. Cuándo SÍ volver al value/quality con fundamentales (path futuro)

Desbloquear el value/quality limpio solo cuando se cumpla **dos de tres**:
1. La S8 confirma el PEAD en vivo.
2. Alguna señal ortogonal (p.ej. reversal/illiquidity) sobrevive a su purged CV y va a paper.
3. Estás considerando capital real.

En ese momento, FMP ($29/mes) deja de ser "pagar por curiosidad" y pasa a ser "comprar datos limpios para una señal que ya demostró valer". Hasta entonces, queda pospuesto — y **eso está bien**: el lab hace su trabajo y te ahorra el gasto en señales que no has validado.

---

## 5. Veredicto en una frase

**No pagues ni rasques: reconstruye la "3ª señal" como señal ortogonal de precio/volumen (reversal 1–5d primero, Amihud illiquidity después), valídala con el mismo purged-CV que el PEAD, y exige bajo co-seno con momentum y PEAD; el value/quality real con fundamentales queda pospuesto a post-S8 / solo si la señal vale y hay capital real.**

---

*Documento de decisión del proyecto Qlib Work — Prioridad 2. Complementa `decision_historico_earnings.md` (Prioridad 1) y `quinn_ahora.md` §2(c).*
