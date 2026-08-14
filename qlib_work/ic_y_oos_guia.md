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

## 9. ¿Qué es el IR (Information Ratio)?

**IR = Information Ratio (Ratio de Información)**

Es la métrica que mide **cuánto retorno extra (exceso) obtienes por cada unidad de riesgo extra que asumes**. Es, en esencia, un **Sharpe ratio, pero en relación al benchmark en lugar de al efectivo**.

### Fórmula

```
IR = (Retorno de la cartera − Retorno del benchmark) / Desviación del exceso
```

Es decir:
- **Numerador:** el *exceso de retorno* (cuánto ganas por encima del índice de referencia)
- **Denominador:** la *volatilidad de ese exceso* (cuánto fluctúa esa ventaja, su riesgo)

Un IR de **0.5** significa que por cada 1% de riesgo (volatilidad del exceso) que asumes, obtienes 0.5% de retorno por encima del benchmark.

### Diferencia con el Sharpe

| | Sharpe Ratio | Information Ratio |
|---|---|---|
| Referencia | Efectivo / riesgo-free | **Benchmark** (ej. ^NDX) |
| Mide | Retorno absoluto por unidad de riesgo | **Exceso sobre el índice** por unidad de riesgo |
| Para qué | ¿Es buena la estrategia en sí? | ¿Supera al mercado de forma consistente? |

---

## 10. Tabla de interpretación del IR

| Valor de IR | Qué significa |
|---|---|
| **IR > 1.0** | Excelente — edge muy consistente (nivel de fondos de élite) |
| **IR 0.5–1.0** | Bueno — supera al benchmark de forma clara |
| **IR 0.3–0.5** | Aceptable / modesto — hay algo de ventaja |
| **IR 0–0.3** | Débil — el alpha es marginal |
| **IR < 0** | La estrategia **pierde** frente al benchmark |

*Referencia: en gestión activa, un IR sostenido >0.5 se considera bueno; la mayoría de fondos profesionales no superan 0.5-1.0.*

---

## 11. Relación entre IR, IC y frecuencia de operar (la ley fundamental)

El IR se puede descomponer según la **ley fundamental de la gestión activa**:

```
IR ≈ IC × √(BR)
```

Donde:
- **IC** = tu ventaja predictiva por operación (correlación predicción→resultado)
- **BR** (breadth) = el número de **apuestas independientes** al año

**Interpretación clave:**
- El IR **no depende solo de cuánto aciertas (IC)**, sino también de **cuántas veces al año** puedes aplicar esa ventaja de forma independiente.
- Puedes tener un IC bajo (0.02-0.03) pero si operas muchísimo con señales independientes → IR alto.
- O un IC alto pero operando pocas veces → IR bajito.

**Para el inversor:** esto explica por qué una estrategia con IC modesto pero muy activa puede superar a una con mejor IC pero que opera poco.

---

## 12. Cómo usarlo como inversor (lo práctico)

1. **Criterio de selección:**
   Busca estrategias con **IR OOS > 0.5** (idealmente `>1`). Un IR <0.3 indica que el exceso sobre el índice es marginal y probablemente no compense el esfuerzo y el riesgo.

2. **Diferenciar de la rentabilidad absoluta:**
   Un +24% absoluto puede ser puro beta (el mercado subió). El IR te dice *cuánto de eso es exceso real sobre el índice*. En nuestro walk-forward, el LightGBM tenía exceso modesto y que se degradaba OOS — señal de IR débil.

3. **Es sensible a los costes:**
   El IR se calcula **con** o **sin** costes de transacción. Siempre compara la versión **con costes reales** (IB), porque los costes reducen el exceso y por tanto el IR. Un IR que pasa de 0.5 a 0.1 con costes reales es una bandera roja.

4. **Monitorizar en el tiempo:**
   Como el IC, el IR **decae**. Si cae de forma sostenida, la ventaja sobre el benchmark se erosiona.

5. **Usarlo junto al IC:**
   - El **IC** te dice si *predices bien* (calidad de la señal).
   - El **IR** te dice si *eso se traduce en superar al mercado* (rentabilidad ajustada al riesgo del exceso).
   - Ambos deben ser **positivos y sostenidos out-of-sample** para confiar en la estrategia.

---

## 13. Limitaciones del IR

- Es **relativo al benchmark** — elegir un benchmark fácil infla el IR, uno difícil lo castiga. Hay que comparar contra el índice correcto del universo.
- **No distingue la dirección del exceso** — un IR alto pero negativo (pierde consistentemente) diría consistencia, no bondad.
- Depende de la **frecuencia de evaluación** (diario vs semanal cambia ligeramente el valor).
- Necesita **suficiente histórico** para ser fiable (con pocos datos, el IR puede ser ruido).

---

## 14. Resumen de cómo leer las tres métricas juntas

| Métrica | Responde a | Valor deseable OOS |
|---|---|---|
| **IC** | ¿Predices bien (la señal ordena)? | `> 0.02` |
| **IR** | ¿Superas al benchmark con consistencia? | `> 0.5` |
| Sharpe | ¿Buen retorno absoluto por unidad de riesgo? | `> 1.0` |

**Las tres deben mirarse sobre datos out-of-sample.** Un backtest que muestra retornos bonitos pero IC≈0 e IR<0.3 está, casi seguro, engañándote con beta y/o overfitting.

---

*Documento de referencia del proyecto Qlib Work. Base: estadística de correlación (Pearson), teoría de gestión activa (ley fundamental del manejo activo) y gestión de riesgo estándar.*
