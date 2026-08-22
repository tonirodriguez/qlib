# ¿Certificar régimen + detector? — La lectura de Quinn

**Autor:** Quinn · Investment Research Senior (14+ años buy-side)
**Sujeto:** Toni · cartera sistemática Qlib (momentum 120d, paper-time €20k, 2 estrategias en paper)
**Fecha:** 2026-08-22

---

## 1. VEREDICTO DIRECTO

**"Certificar que el momentum solo funciona en ciertos regímenes + construir un detector avanzado" es PREMATURO como certificación y SOBREINGENIERÍA como detector.** Pero el *núcleo del hallazgo* — que el alpha del momentum es dependiente del régimen — es **correcto, bien apoyado y debe guiar tu diseño**. La respuesta no es "construir un régimen-detectador", es "parar de depender del momentum como pilar único".

Desglosémoslo:

- **Certificar regímenes: PREMATURO.** Tienes ~2 ciclos (COVID+2022 vs 2023-26). Eso son 2 observaciones de régimen. No se "certifica" con 2 puntos de datos; se *hipotetiza* fuertemente.
- **Detector avanzado (HMM/Markov/vol regime): SOBREINGENIERÍA** a esta escala y con esta historia. No tienes suficientes transiciones de régimen etiquetadas ni robustez de parámetros para calibrar un HMM de forma honesta. El 90% del beneficio lo obtienes con una regla de volatilidad simple que ya posees.
- **Lo accionable es real, no teórico:** el purged CV ya te dijo lo único que necesitas — el momentum **no es una fuente de retorno estable**. Eso no lo arregla un detector; se arregla *dejando de apostar tanto al momentum*.

---

## 2. RESPUESTAS CON RIGOR

### P1. ¿Es defendible "certificar" que el momentum solo funciona en ciertos regímenes? ¿Cómo demostrarlo con rigor?

**Es defendible como hipótesis bien fundamentada; NO como certificación.** La literatura lo apoya con fuerza: *Momentum Crashes* (Daniel & Moskowitz 2016) demuestra exactamente esto — los momentum crashes ocurren tras mercados bajistas y en periodos de alta volatilidad agregada, cuando el momentum se revierte por el "rebote" de los perdedores. Tu hallazgo es coherente con la evidencia publicada, lo cual aumenta la confianza a priori.

**Cómo demostrarlo con rigor** (para pasar de hipótesis a afirmación defensable):

1. **Más ciclos / más transiciones, no más datos del mismo régimen.** Necesitas observar *múltiples* transiciones alcista→bajista. Tu muestra tiene ~1 transición limpia (2021→2022). Extiende el backtest todo lo posible hacia atrás y añade ex-regímenes (2000-02, 2008-09, 2015, 2018, 2020) aunque sea con datos más sucios.
2. **Condicionaliza la métrica por estado, no solo por fecha.** Calcula IC *oscilando condicionado al régimen*, no IC crudo por ventana. El IC por ventana de 3 años mezcla régimen con ruido.
3. **Test de interacción formal.** Regresión: `IC_momentum ~ factor_mercado + I(vol alta) + momentum_crash_indicator`. Si el coeficiente del momento de volatilidad/crisis es significativo y estable, tienes evidencia estructural, no anecdótica.
4. **Reporta intervalos de confianza, no puntos.** IC -0.13 vs +0.065: ¿se solapan los CI? Si con 2 ciclos se solapan, no puedes afirmar "técnicamente distinto" — solo "direccionalmente consistente con la teoría".
5. **Criterio falsable explícito:** "El momentum es regime-dependent" se falsifica si, pese a más transiciones, el IC condicionado a crisis NO difiere sistemáticamente del IC en calma. Escríbelo antes de mirar los datos.

**El riesgo de sobreinterpretar:** con 2-3 ciclos, una lectura alternativa igualmente válida es que el momentum simplemente **degradó** en eficiencia (más competencia, saturación del factor) y no que "dependa de régimen". Tus dos hipótesis compiten; no las confundas. Un detector de régimen no separa estas dos — un decaimiento secular no es un régimen.

### P2. ¿Detector de régimen a esta escala, o sobreingeniería?

**Sobreingeniería. Prioridad: (b) vol-gating simple > (c) pivotar a PEAD > (d) combinar > (a) HMM/Markov.**

- **(a) HMM / Markov switching / vol regime: NO AHORA.** Un HMM necesita suficientes transiciones etiquetadas para estimar la matriz con honestidad. Con tu historia, el modelo detectará "régimen" que en realidad es 1-2 eventos. Además, el *lag* de detección (el régimen ya cambió cuando lo confirmas) destruye gran parte del beneficio. Es atractivo porque es "avanzado", pero el retorno marginal sobre una regla de vol es bajo y el riesgo de overfit altísimo. **Apártalo: reservarlo como experimento de laboratorio, jamás como capa de producción aun.**
- **(b) Vol-gating / vol-targeting: es tu mejor "detector".** La volatilidad realizada es un *proxy* decente del régimen de estrés y, crucialmente, se mide sin lag de *estado* (es contemporánea). Tú ya tienes vol-targeting. La mejora barata: **un switch de facto**: cuando la vol realizada del SP500 supere un umbral (p.ej. percentil 75-80 o VIX implícito en zona alta), reducir el peso del momentum (p.ej. a 1/3) o pausarlo. No "predices" el crash; solo no apuestas fuerte cuando el entorno lo favorece. Esto captura la mayor parte del beneficio de Daniel-Moskowitz (que muestra que el crash del momentum *sigue* a la alta vol).
- **(c) Pivotar a PEAD cuando momentum falle: útil, pero requerirá señal de "fallo".** El PEAD es transversalmente más limpio (IC +0.085 a +0.130 estable). Pero "switch cuando momentum falle" introduce su propio lag y sobreajuste al decidir *cuándo* falló. Más simple y robusto: darle al PEAD un peso base *permanente*.
- **(d) Combinar: sí, pero con pesos fijos o ligeramente condicionados, no con un oráculo de régimen.** La combinación diversifica la imperfección de cada señal.

**Clave: "detector avanzado" es la respuesta a la pregunta equivocada.** La pregunta correcta no es "¿en qué régimen estoy?" sino "¿qué hago cuando mi estrategia principal no es robusta?" La respuesta de menor varianza es *no depender de ella*, no *saber en qué régimen estás*.

### P3. Uso CORRECTO del momentum y del PEAD. ¿Debe el momentum ser el pilar?

**No. El momentum no debe ser tu estrategia principal.** El purged CV (bien hecho) es evidencia de que NO es una fuente robusta en tu muestra. Eso es exactamente el tipo de señal que un investigador honesto NO debe ignorar. Continuar apalancando el momentum como pilar único es sobreconfianza en un factor que tu propia validación señala como dependiente del entorno.

**Uso correcto:**

- **Momentum = estrategia de oportunidad / táctico, condicionada a entorno, con tamaño reducido.** Trátalo como el componente que gana en tendencias y pierde en reversiones — taméalo con vol-gating y dale un peso moderado. Es un *enhancer* de entornos alcistas, no el seguro de la cartera.
- **PEAD = ancla de robustez / estrategia base.** Su IC estable transversalmente lo hace más apto como componente estructural. Puede ser el corazón, con el momentum de sabor táctico.
- **Combinación recomendada:** una cartera donde el PEAD aporta la base robusta y el momentum un overlay táctico con tope de peso y regla de reducción por vol. Esto es lo que tu estrategia "momentum + filtro PEAD" ya insinúa — el hallazgo te dice que **invierte los pesos implícitos**: PEAD como núcleo, momentum como satélite, no al revés.

**La trampa a evitar:** no uses el hallazgo para *justificar* mantener el momentum a tamaño pleno ("solo hay que esperar al régimen correcto, el detector me dirá cuándo"). Eso es racionalización. La honestidad del dato es: *el momentum no es confiable de forma autónoma; el PEAD sí lo es a esta escala*. Ajusta la arquitectura a eso.

### P4. Recomendación priorizada con criterios de decisión

**Prioridad 1 — Reducir exposición al momentum YA (semanas, no meses).**
- Pasa la estrategia principal a convivencia PEAD-núcleo + momentum-táctico, o al menos baja momentum a ≤50-60% del peso y activa vol-gating severo.
- *Criterio de decisión:* si el momentum sigue en paper-time negativo y el PEAD sigue plano/positivo, este reponderamiento estás validándolo en vivo — no esperes a "detectar régimen".

**Prioridad 2 — Demostrar rigormente la dependencia de régimen (laboratorio).**
- Extiende el backtest hacia atrás, condiciona IC por estado, corre la regresión de interacción y reporta CI. Esto convierte "sospecha" en "afirmación cuantificada" o la desecha.
- *Criterio falsable:* interacción significativa y estable en múltiples transiciones → confirmado. Sin ella → el problema es decaimiento secular, y la respuesta es otra (reducir size, no añadir régimen).

**Prioridad 3 — Prototype de vol-gating, NO HMM todavía.**
- Implementa el vol-gating como experimento de laboratorio y mide su efecto real sobre Sharpe/max-drawdown del momentum.
- *Criterio de decisión sobre el detector:* solo si el vol-gating simple ya mejora el backtest de forma material, y aun así, el siguiente paso es un modelo de vol/markov switching **como benchmark académico en laboratorio**, no como capa de producción. No lo pongas en paper-time hasta demostrar que supera al vol-gating por una holgura clara.

**Prioridad 4 — No escalar hasta que el diseño sea honesto.**
- Estás en paper-time; no hay capital real. Este es el momento barato para corregir la arquitectura. No metas dinero real hasta que la estrategia principal no dependa del momentum autónomo.

---

## 3. CONVICCIÓN Y SEÑALES DE ALARMA

**Convicción (declarada):**
- Alta (75-80%): el purged CV es la herramienta correcta y su señal (momentum no robusto, PEAD robusto) es la lectura más probable del dato tal como lo describes.
- Alta (70-75%): el momentum es dependiente de régimen en línea con Daniel-Moskowitz, NO solo con tu muestra. La teoría lo respalda.
- Media (50-60%): que un vol-gating simple capture la mayor parte del beneficio de un HMM en tu caso. No trivial, pero es la apuesta razonable.

**Señales de alarma (que te despierten):**
1. **El "detector de régimen" como escape.** Si buscas el detector para no tener que reducir el momentum, es racionalización. El dato ya te dio la respuesta más barata.
2. **Dos hipótesis competidoras sin separar.** "Régimen" vs "decaimiento del factor" producen acciones distintas. No las fusiones.
3. **IC por ventana de 3 años con CI que se solapan** presentados como "dos regímenes distintos". Qúzate: con n=2 ciclos, la separación puede ser ruido.
4. **El PEAD como "remedio mágico".** Aunque estable, un solo factor robusto en ~6 años de una muestra de SP500_liquid es señal prometedora, no certidumbre. No pases de sobreapostar momentum a sobreapostar PEAD.
5. **Lag de detección.** Si el régimen ya cambió cuando lo confirmas, tus decisiones llegan tarde. Cualquier diseño que dependa de "confirmar primero" es sospechoso.
6. **Sobrefit de los estados.** Si tu modelo encuentra "régimen" en 3 datos etiquetados, no encontró régimen: encontró tu sesgo.

---

## 4. RECOMENDACIÓN FINAL ACCIONABLE (orden)

**Esta semana:**
1. **Reestructura la cartera mariposa: PEAD como núcleo estructural, momentum como overlay táctico con tope de peso (≤50-60%) y vol-gating activo.** Invierte los pesos implícitos que hoy dan: el hallazgo manda.
2. **Deja el momentum puro activo en paper-time como monitor, no como apuesta principal.** Su performance sigue informándote, pero no es el pilar.

**Este mes (laboratorio):**
3. **Demuestra la dependencia de régimen con rigor:** backtest extendido hacia atrás, IC condicionado por estado, regresión de interacción con factor de vol/crisis, y CI reportados. Define la hipótesis falsable por escrito antes de ejecutar.
4. **Prototipa vol-gating** sobre el momentum y mide efecto real (Sharpe, max-DD, turnover).

**No hagas (todavía):**
5. **NO construyas el HMM/Markov detector para producción.** Reserve como benchmark académico de laboratorio, y solo promuévelo si supera al vol-gating con holgura clara y múltiples transiciones de régimen validadas.

**Criterio de decisión final:** si al reponderar hacia PEAD + momentum táctico el paper-time se estabiliza (drawdown acotado, PEAD aportando), has resuelto el problema de fondo — el detector era prescindible. Si, en cambio, el PEAD también empieza a degradarse, eso es la señal de alarma real, y ahí el problema ya no es de régimen sino del espacio completo de señales.

---

*Nota de Quinn: el hallazgo que hiciste es bueno y honesto. La tentación ahora es "hacerlo más sofisticado". Resístela: la lección del purged CV es que el momentum no debe ser tu pilar, y eso se arregla con arquitectura y tamaño de posición, no con un detector de régimen.*
