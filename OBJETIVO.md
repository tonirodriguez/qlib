# OBJETIVOS DEL PROYECTO

> **Última revisión:** 2026-10-27

---

## El objetivo

**Aprender investigación cuantitativa rigurosa, con la ambición explícita de
batir al mercado.**

Las dos cosas no son alternativas ni hay que elegir. El aprendizaje es **el
método**; batir al mercado es **la meta**. Se aprende construyendo la capacidad
de medir, y se mide para intentar ganar.

---

## La tensión que hay que entender

Querer batir al mercado es **exactamente lo que produce resultados falsos**.

Cuando deseas que algo funcione:

- sigues buscando después del primer resultado negativo
- ajustas la ventana de datos hasta que mejora
- pruebas otra variante "por si acaso"
- y al final encuentras algo, porque con suficientes intentos siempre se
  encuentra algo

Eso no es falta de rigor. Es el sesgo natural de tener una hipótesis que
quieres confirmar. Por eso el proyecto anterior produjo diez números falsos sin
que nadie mintiera.

**La disciplina no está en tensión con la ambición: es la única forma de que la
ambición pueda satisfacerse honestamente.** Sin ella, uno no bate al mercado —
se convence de que lo ha batido.

---

## Qué significa "batir el mercado" — definición operativa

Una ambición sin definición medible no es una meta: es un deseo. Así queda
definida:

| Elemento | Definición |
|---|---|
| **Benchmark** | `^GSPC`, misma base de precios (precio vs precio, o total return vs total return — nunca mezclados) |
| **Métrica primaria** | Exceso de retorno **ajustado por riesgo**, medido fuera de muestra |
| **Umbral de evidencia** | **t > 3,0** tras corregir por número de intentos (Harvey-Liu-Zhu 2016; Deflated Sharpe) |
| **Periodo de evaluación** | Datos **no usados** durante el desarrollo, pre-registrados |
| **Mínimo de observaciones** | Suficiente para detectar el efecto declarado *antes* de medir |

**No cuenta como batir al mercado:**

- Ganar en una ventana elegida después de ver los resultados
- Ganar con más riesgo y peor drawdown (eso es beta, no habilidad)
- Ganar sin significancia estadística corregida
- Ganar en el papel sin costes realistas

---

## Las dos fases

### Fase 1 — Construir la capacidad de medir

**Niveles 0 a 6** del `PLAN_APRENDIZAJE_DESDE_CERO.md`.

**Éxito:** poder ejecutar un test honesto de una hipótesis, con hipótesis nula,
corrección por intentos y holdout respetado.

**Aquí todavía no se busca alfa.** Se construye la herramienta que permitirá
buscarlo sin engañarse.

### Fase 2 — Buscar edge con esa capacidad

Después del nivel 6. Cada idea entra por el protocolo de pre-registro.

**Éxito:** un resultado que sobreviva al protocolo completo. Si aparece, es un
candidato serio, no una promesa.

---

## Criterios de éxito

**De la Fase 1:**

1. Saber, dado un dataset, si permite concluir algo **antes** de medir.
2. Encontrar el look-ahead de un backtest ajeno en menos de 10 minutos.
3. Construir la hipótesis nula de cualquier estrategia.
4. Entregar un resultado negativo con la misma calidad que uno positivo.

**Del proyecto completo:**

> Encontrar al menos una estrategia con alfa positivo, estadísticamente
> significativo después de corregir por múltiples comparaciones, que sobreviva
> en datos no usados durante su diseño.

Si eso no ocurre, el resultado honesto es: *"con estos datos, este universo y
estos métodos, no he encontrado ventaja."* Eso es un **resultado**, no un
fracaso. Y es infinitamente más valioso que un Sharpe de 1,07 que no existe.

---

## Las tres reglas

1. **Ningún resultado se interpreta sin su hipótesis nula.**
2. **Un resultado negativo es un entregable**, con el mismo rigor que uno positivo.
3. **Nada de capital real** hasta que un resultado haya sobrevivido al
   protocolo completo de la Fase 2.

---

## Lo que este proyecto NO es

- **No es una promesa.** La mayoría de los intentos serios de batir al mercado
  fracasan. El plan no cambia esa probabilidad; cambia la capacidad de saber en
  qué lado estás.
- **No tiene plazo de rentabilidad.** Tiene plazos de aprendizaje (10 semanas),
  no de resultado.
- **No compite con indexarse.** Si al final el resultado honesto es "el índice
  es mejor", la decisión correcta será indexarse — y se sabrá con datos, no por
  resignación.

---

## Estado actual

| | |
|---|---|
| **Fase** | Fase 1, no iniciada |
| **Último hito** | Plan de aprendizaje creado (6 niveles, 582 líneas) |
| **Línea abierta** | Ninguna: las once auditorías cerraron sin edge demostrado |
| **Siguiente paso** | Nivel 0 — auditoría de datos |

---

*Este documento manda sobre los demás. Si un análisis contradice estos
objetivos, se revisa el análisis — no el objetivo.*
