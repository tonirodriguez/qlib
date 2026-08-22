# 🔄 El cambio de opinión sobre el PEAD: de "filtro" a "núcleo"

> **Fecha:** 2026-08-22
> **Proyecto:** Qlib Work
> **Propósito:** Documentar el porqué del aparente cambio de recomendación sobre el PEAD, para que quede claro en el historial.

---

## La pregunta

"Antes decías que el PEAD debía ser un **filtro** sobre el momentum; ahora dices que debe ser el **núcleo**. ¿Por qué el cambio de opinión?"

**Respuesta corta: no es un cambio de criterio, es un cambio de ESCENARIO.** Cambió un dato clave entre ambas recomendaciones: el resultado del **Purged Cross-Validation**.

---

## ⏱️ Antes (el filtro) — el supuesto era "el momentum es robusto"

Cuando se recomendó el **PEAD como filtro** (estrategia 2), el supuesto de fondo era:

> *"El momentum 120d es una estrategia robusta y validada (IC OOS 0.066, Sharpe ~1.0). El PEAD es una señal adicional para mejorar algo ya bueno."*

- **Momentum = pilar** (la base sólida)
- **PEAD = refinamiento** — un filtro para evitar comprar momentum "tocado" por malas sorpresas

En ese marco, añadir un filtro a una estrategia que funciona es lo lógico.

---

## 🧬 Después (invertir pesos) — el purged CV reveló la verdad

Luego se aplicó el **purged CV** al momentum 120d y apareció el dato decisivo:

> **El momentum 120d NO es robusto.** Su IC es fuertemente **dependiente del régimen**: positivo en 2023-26 (alcista), negativo en 2020-23 (crash COVID + corrección 2022). El Sharpe ~1.0 era una media que disfrazaba periodos malos.

En paralelo, el **PEAD sí resultó robusto** transversalmente: IC Spearman estable **+0.085 a +0.130** con purged CV.

**Con esta evidencia:**
- El momentum **ya no merece ser el pilar**
- El PEAD (lo robusto) **debe ser el núcleo**
- El momentum (lo frágil/regime-dependent) pasa a **satélite táctico** con tope de peso y vol-gating

---

## 🎯 La lógica en tabla

| | Antes (pre-purged CV) | Después (post-purged CV) |
|---|---|---|
| **Lo robusto** | Momentum (creído) | **PEAD (confirmado)** |
| **Momentum** | Pilar | Táctico, ≤50-60% |
| **PEAD** | Filtro sobre momentum | **Núcleo estructural** |

**Lo que NO cambió:** que PEAD y momentum son señales ortogonales y conviene usarlas juntas.
**Lo que SÍ cambió:** cuál es la base y cuál el refuerzo.

---

## 💡 La frase de Quinn que lo resume

> *"La combinación recomendada: una cartera donde el PEAD aporta la base robusta y el momentum un overlay táctico. Esto es lo que tu estrategia 'momentum + filtro PEAD' ya insinúa — el hallazgo te dice que **invierte los pesos implícitos**: PEAD como núcleo, momentum como satélite, no al revés."*

Es decir: **la arquitectura "PEAD + momentum" era correcta, pero con los papeles invertidos.**

---

## ⚠️ Honestidad intelectual

**Ni siquiera esto es "certificar" el PEAD.** El PEAD también tiene solo ~6 años de datos en la muestra. La lección del purged CV no es "el PEAD es la panacea", sino:

> **"Ninguna señal única es un pilar confiable por sí sola."**

El movimiento correcto es **diversificar señales** (PEAD base + momentum táctico) y **no depender de una sola** — y, sobre todo, **gestionar el tamaño** según la robustez medida, no según la creencia.

---

*Documento de referencia del proyecto Qlib Work. Complementa `quinn_regimenes.md`.*
