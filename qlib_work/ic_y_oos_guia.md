# 📐 IC (Information Coefficient) y OOS — Guía para el inversor

> **Fecha:** 2026-08-14
> **Ámbito:** Métricas de evaluación de estrategias cuantitativas en Qlib
> **Proyecto:** Qlib Work

---

## 1. ¿Qué es el IC?

**IC = Information Coefficient (Coeficiente de información)**

Es, simplemente, la **correlación entre dos cosas**:
1. Lo que tu modelo **predice** (la señal: score de momentum, de LightGBM, etc.)
2. Lo que **realmente pasó** (el retorno futuro real)

Se mide con la correlación de Pearson, un número entre **−1 y +1**:

```
IC = correlación( predicción , retorno futuro real )
```

---

## 2. De dónde sale (ejemplo concreto)

Imagina que en 10 fechas tu modelo ordena las empresas así, y al final resulta:

| Empresa | Score modelo | Retorno real +10d |
|---|---|---|
| A | 0.9 (alto) | +5% ✅ |
| B | 0.7 | +3% ✅ |
| C | 0.5 | 0% |
| D | 0.3 | −2% |
| E | 0.1 (bajo) | −4% ✅ |

Cuando el modelo puntúa **alto**, el retorno real tiende a ser **alto** → hay correlación positiva → **IC alto (+)**. El score ordena bien a las ganadoras.

- Si el modelo puntuara alto a las perdedoras → **IC negativo** (señal invertida)
- Si no hay relación → **IC ≈ 0** (el modelo no predice nada, puro ruido)

En Qlib se calcula correlacionando la columna `pred` (predicción) con la columna `label` (retorno futuro) sobre el conjunto evaluado (normalmente test / out-of-sample).

---

## 3. Tabla de interpretación

| Valor de IC | Qué significa | Implicación |
|---|---|---|
| **IC > 0.05** | Excelente | Señal muy informativa; pocos modelos llegan aquí |
| **IC 0.02–0.05** | Bueno | Alpha real y explotable |
| **IC 0.005–0.02** | Débil | Hay algo, pero marginal |
| **IC ≈ 0** | Ruido | El modelo no predice mejor que el azar |
| **IC < 0** | Invertido | Predice al revés (a veces se corrige invirtiendo la señal) |

---

## 4. ¿Qué nos aporta como métrica?

| Lo que hace | Por qué es valioso |
|---|---|
| **Aisla el alpha del beta** | Un backtest puede dar +24% solo porque el mercado subió (beta), aunque el modelo no prediga nada. El IC mira específicamente si la **predicción** se relaciona con el **resultado**, separando "¿predigo bien?" de "¿el mercado subió?". |
| **Es out-of-sample por naturaleza** | Si se calcula sobre datos no vistos, es muy difícil de falsear con overfitting. |
| **Es comparable** | Un IC de 0.03 en momentum vs 0.008 en LightGBM te dice cuál es mejor *antes* de montar el backtest completo. |
| **Guía el dimensionamiento** | El IC te dice cuánto "edge" tienes por operación → decide el tamaño de posición. |

### El caso real de nuestro proyecto
El walk-forward del LightGBM dio **IC ~0.008** mientras el backtest mostraba +24% absoluto. Ese contraste es exactamente el valor del IC: **el modelo no predecía nada (IC≈0); la ganancia era puro beta del sector tech**. Sin mirar el IC, habríamos creído que teníamos una estrategia ganadora cuando no era así.

---

## 5. El IC y la ley fundamental de la gestión activa

Relación entre el IC y tu ventaja:

```
IR ≈ IC × √(número de apuestas independientes al año)
```

Donde IR = Information Ratio (retorno por unidad de riesgo).

**Interpretación:**
- Cuanto **mayor el IC** y **más veces al año** operes con señales independientes, mayor será tu IR.
- Un IC pequeño (0.02–0.03) puede dar buen IR si operas a menudo.
- Un IC de ~0.008 difícilmente compensa los costes de transacción.

---

## 6. Cómo usarlo como inversor (lo práctico)

1. **Criterio de selección (el más importante):**
   No confíes en ninguna estrategia cuyo **IC out-of-sample no sea > 0.02**. Si el IC es ~0, da igual lo bonito que sea el backtest: matemáticamente no estás prediciendo.

2. **Dimensionar la confianza:**
   Mayor IC → más ventaja y más margen para posiciones mayores. Menor IC → posiciones pequeñas (la señal es débil).

3. **Decidir el tamaño de posición:**
   El IC te dice cuánto edge tienes por operación; eso dicta cuánto apostar (Kelly ajustado).

4. **Monitorizar en el tiempo:**
   El IC **no es fijo — decae**. Calcúlalo de forma rodante (por trimestre/año). Si cae sostenidamente hacia 0, tu ventaja se erosiona → reducir exposición o cambiar la fuente de alpha.

5. **Regla práctica para TI:**
   IC OOS > 0.02 → avanzas con el modelo. IC ~0 → descarta, sin excepciones.

---

## 7. Limitaciones del IC

- **Es lineal** — capta si la predicción *ordena* bien, pero no no-linealidades (a veces el modelo acierta solo en colas).
- **No dice el tamaño del retorno**, solo si hay relación (puede haber buen IC pero bajo retorno).
- **Decae** — hay que monitorizarlo, no es permanente.
- **Necesita volumen de datos** — con pocas muestras un IC alto puede ser casualidad.

---

## 8. ¿Qué es OOS (Out-of-Sample)?

**OOS = Out-of-Sample = "fuera de muestra"**

### Definición
Un resultado es **out-of-sample** cuando se obtiene sobre **datos que el modelo NO utilizó durante su entrenamiento**. Es la única forma honesta de saber si una estrategia predice de verdad o solo memorizó los datos vistos.

### Los dos mundos

| | **In-sample (en muestra)** | **Out-of-sample (fuera de muestra)** |
|---|---|---|
| Datos | Los que el modelo usó para aprender | Los que el modelo NO vio |
| Resultado | Siempre bueno (el modelo los memoriza) | Honesto: mide la generalización real |
| Peligro | Overfitting: parece perfecto pero no predice nada nuevo | Es la prueba definitiva |

### Cómo se logra OOS
- **División temporal:** entrenar con 2008-2021, validar 2022-2023, **testear 2024-2026** (el test nunca se usa para entrenar)
- **Walk-forward:** ventanas móviles, cada una entrenada solo con pasado y probada en el siguiente periodo. Es la forma más robusta de OOS porque barre muchos periodos y prohibe ver el futuro.

### Por qué es crítico
- Un modelo "in-sample" siempre parece ganador, pero sobre los mismos datos memoriza.
- Solo el **rendimiento out-of-sample** te dice si hay **alpha real explotable** (IC OOS > 0.02) o era **overfitting / beta**.
- En nuestro proyecto: el walk-forward (OOS) reveló que el LightGBM tenía IC ~0.008 → **sin alpha OOS**, pese al backtest bonito.

### Regla de oro
**Solo cuentan las métricas out-of-sample.** Un IC, retorno o Sharpe calculado in-sample no tiene valor para decidir si inviertes; el que importa es el calculado sobre datos no vistos (test / walk-forward).

---

*Documento de referencia del proyecto Qlib Work. Base: estadística de correlación (Pearson) y teoría de gestión activa (ley fundamental del manejo activo).*
