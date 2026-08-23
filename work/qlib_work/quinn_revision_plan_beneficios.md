# 🎯 Quinn — Revisión del Plan de la Siguiente Fase: enfocado a BENEFICIOS REALES

**Autor:** Quinn · Investment Research Senior (14+ años buy-side)
**Sujeto:** Toni · proyecto Qlib work (lab + paper E1/E2/E3 sin capital real) **+ cartera real NVO/AAPL/GOOGL/MSFT/META**
**Fecha:** 2026-08-23
**Mandato:** adecuar `plan_siguiente_fase_senales_ortogonales.md` a lo que **da beneficio real AHORA**, no a más investigación académica. Inverno de stroza: priorizar beneficio y plazo.

---

## 1. VEREDICTO DIRECTO — qué da beneficio real AHORA

**La señal ortogonal (Amihud/reversal) NO es la prioridad. Es sobre-investigación en este momento.**

Razón brutal y honesta: esa señal es una *diversificación académica del PAPER de E3*, que corre con **capital ficticio**. Le va a costar **24–50 semanas** demostrar algo, y aunque lo demuestre no toca un euro real hasta que Toni decida meter capital. Ningún plan de 6 a 12 meses desde hoy produce un céntimo en la cartera real. **No es la palanca de beneficios.**

La palanca de beneficios está en la **cartera real de Toni** ($14,228 USD, +9.2%), que tiene **dinero real en juego y riesgos concretos y corregibles YA**. Ahí está el trabajo que devuelve valor inmediato:

- **MSFT = 44% del valor de la cartera** (una sola posición pesa el 44%). Un solo batacazo de MSFT es el riesgo dominante de TODO el dinero real de Toni — y la E3 en papel ni siquiera lo contempla.
- **META = -17.2%** y la posición más lastrada (-6.8% esta semana). Es la única decisión de "hold vs cortar" real del libro.
- Los ganadores (MSFT +17.3%, NVO +17.5%, AAPL +12.5%) **no tienen regla de recogida de beneficios ni de rebalanceo**. El +9.2% es una cartera sin gobierno de riesgo, no un sistema.

**Conclusión directa: el mayor beneficio real NO es nuevo research; es disciplinar con reglas el dinero que YA está invertido.** Eso no requiere esperar semanas ni validar nada; solo un poco de gestión aplicada. Es lo que haría cualquier buy-side con la cartera de un cliente en este estado.

---

## 2. PRIORIZACIÓN DE FRENTES (re-ordenados a beneficio)

| Rango | Frente | Veredicto |
|---|---|---|
| 🥇 **1º** | **Cartera real** (5 posiciones, dinero real) | **LA prioridad.** Gobernar concentración (MSFT 44%), decidir META, reglas de recogida de beneficios. Beneficio inmediato, riesgo cero de sobreajuste (es gestión, no modelado). |
| 🥈 **2º** | **Paper E3** (en marcha, medición) | **No tocar.** Seguir midiendo pasivamente hacia S8 (~2 meses). Mantener `decision_s8_alarmas.py`. Es la única fuente futura legítima de "capital en paper→real". |
| 🥉 **3º** | **Señal ortogonal** (Amihud/reversal) | **Congelar/parkear.** Solo se reactiva DESPUÉS de S8 y SOLO si hay decisión de capital real cercana. Un mini-paso de robustez (20d) si sobra 1 tarde, sin construir E4. |
| 🔴 **4º** | **Cripto** (`work/crypto/`) | **Descartar para beneficios.** README: leak temporal invalida toda evidencia, gates no pasan, es research-only. Sin dinero real → no es frente de beneficio. Frente separado, no lo hagas. |

**Cambio clave vs plan anterior:** el plan viejo ponía la señal ortogonal como protagonista del siguiente ciclo ("4ª piedra, 10%"). **Eso queda rebajado a tercer frente congelado.** El protagonista pasa a ser la cartera real.

---

## 3. PLAN FINAL REVISADO — operativo y a beneficio

### Panorama (3-4 semanas, todo accionable hoy)

#### 🥇 Frente 1 — Gobernar la CARTERA REAL (beneficio inmediato)

**Objetivo:** convertir una cartera improvisada (+9.2%) en una cartera con reglas de riesgo; recortar el riesgo dominante (MSFT 44%) y decidir META explícitamente.

**Acciones/scripts concretos (`work/estrategias/`):**

1. **Regla de concentración por posición (cap ~25-30%).** MSFT al 44% viola cualquier mandato razonable. Acción concreta y de bajo riesgo: **recoger beneficios de MSFT para bajar a ~30%** (liberar ~$2,000 -> canjear a cash o diversificar). Es la decisión de mayor impacto riesgo/beneficio de todo el libro, y es inmediata. No es market timing: es recorte de riesgo de una posición única desproporcionada.
2. **Decisión explícita sobre META (-17.2%):** escribir una línea de tesis (¿sigue intacta la razón de compra?) y fijarla en escrito. Tres salidas honestas:
   - Tesis intacta → mantener pero fijar un **stop duro** (p.ej. -25% o salir si rompe un soporte clave).
   - Tesis dañada → **cortar ahora**, liberar capital, reasignar.
   - No decides → esa indecisión ES una decisión: prohíbe no tener stop. **No dejar META "a la deriva" es lo más caro.**
3. **Recogida de beneficios con regla:** fijar un criterio simple (p.ej. recortar ganadores que superen X% de peso o X% de ganancia) para **no dejar que el +9.2% se erosione**. NVO +17.5% / AAPL +12.5% / MSFT +17.3% son candidatos naturales.
4. **Script nuevo `portfolio_riesgo_real.py`** (read-only + memo, reusando `estado_portfolio_*.md` que ya existe):
   - Calcula peso por posición + alerta de **concentración >30%**.
   - Alerta de **posición >20% por debajo de stop** y flag de **META sin stop definido**.
   - Genera memo semanal `riesgo_real_<fecha>.md` con 1 línea por alarma. Añádelo al cron del sábado junto a `estado_portfolio_*`.
   - **NO** es un bot que opera solo: es un informe. Toni ejecuta con cabeza (o no ejecuta, pero informado).

**Por qué esto es "beneficio real":** recorta la cola izquierda del único capital real sin esperar validación, y obliga a decidir la única posición perdedora. Es lo que separa una cartera de una colección de acciones.

#### 🥈 Frente 2 — Paper E3: medir, NO tocar (rumbo a S8)

- **Continuar igual**: cronjobs sábado, regenerar `comparativo_estrategias_*.md` y `estado_portfolio_*.md`.
- **`decision_s8_alarmas.py`** (ya existe, read-only) — usarlo cada sábado para chequear las alarmas §5.2 (E3 plano/negativo sostenido, vol-gate sin aportar, DD fuera de rango).
- **Regla inmutable:** no reponderar, no cambiar topk/split, no patchear simuladores con datos nuevos antes de S8. La disciplina ES el activo.

#### 🥉 Frente 3 — Señal ortogonal: CONGELADA (no invertir semanas)

- **No construir E4.** No integrar Amihud/reversal en ningún libro ahora.
- **Único mini-paso opcional (1 tarde, no más):** correr la robustez 20d de `reversal_illiquidity_purgedcv.py` para dejar la base lista. Si no queda ancho de banda, **omitir sin culpa** — no avanza el P&L real.
- **Regla de reactivación:** solo tras S8 **Y** con la cartera real gobernada **Y** decisión de meter capital en paper cercana. Hasta entonces, cero horas.

#### 🔴 Frente 4 — Cripto: DESCARTADO para beneficios

- README explícito: leak temporal = evidencia inválida; gates no superados; research-only. No hay dinero real → no es frente de beneficio.
- No asignar tiempo hasta que el frente real y el papel E3 estén gobernados. Frente separado por diseño.

---

## 4. QUÉ DESCARTAR (anti-prioridades — evitar sobre-investigación)

- ❌ **NO invertir 1-2 semanas en robustez extra (20d/1 año atrás) de la señal ortogonal como plan principal.** Es sobre-investigación: valida una señal sin capital detrás. Congelar, no ampliar.
- ❌ **NO construir E4 / 4ª piedra / libro nuevo con Amihud ahora.** Esperar **24-50 semanas** para un resultado de papel es exactamente lo que NO hay que hacer para "beneficios".
- ❌ **NO desarrollar la 3ª señal (value/quality) este ciclo.** Misma lógica: otro estudio de papel con capital cero. Posponer tras S8 si hace falta.
- ❌ **NO avanzar el frente cripto** en este ciclo. Evidence inválida + sin dinero real = tiempo perdido.
- ❌ **NO tocar E1/E2/E3** (medición limpia). **NO HMM/detector sofisticado, NO "optimizar momentum", NO grid-search del split 65/35** (permanecen prohibidos).
- ❌ **NO confundir "diversificar el paper" con "beneficio real".** La diversificación del papel solo paga cuando hay capital real que proteger. Hoy el capital real es la cartera de Toni, y su mayor riesgo es **MSFT 44%**, no la falta de una 3ª pierna de paper.

---

## 5. SÍNTESIS / CONVICCIÓN

- **La pregunta no era "qué señal nueva investigar" sino "dónde está el dinero y su riesgo".** El dinero real está en 5 acciones; su riesgo no está en el alpha que falta sino en la **concentración (MSFT 44%)**, la **posición perdedora sin regla (META)** y la **falta de gobierno (recogida de beneficios/rebalanceo)**.
- Reordené la fase: **1º cartera real (gestión de riesgo + decisiones de posición), 2º seguir midiendo E3 hacia S8 sin tocarlo, 3º señal ortogonal congelada, 4º cripto descartado.**
- **Acción inmediata de mayor retorno:** recortar MSFT a ≤30% y **fijar por escrito la decisión + stop de META**. Eso es beneficio real hoy, sin esperar semanas ni validar nada.
- **Acción de menor retorno (descartar):** seguir añadiendo robustez a una señal ortogonal sin capital detrás.
- El paper E3 sigue siendo el camino legítimo hacia capital real futuro, pero **no toca nada**; se mide pasivamente y se decide en S8.

---

*Revisión del plan de la siguiente fase — Quinn. Sustituye el énfasis de `plan_siguiente_fase_senales_ortogonales.md` (señal ortogonal como objetivo) por gobernar la cartera real como objetivo de beneficio, manteniendo E3 en medición hacia S8.*
