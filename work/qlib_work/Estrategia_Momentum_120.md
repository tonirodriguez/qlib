# 📈 Estrategia Momentum 120 días — Guía completa

> **Fecha:** 2026-08-19
> **Proyecto:** Qlib Work — inversión cuantitativa sistemática
> **Universo:** sp500_liquid (292 tickers del S&P 500)
> **Estado:** en paper-trading con €20,000 ficticios

---

## 🎯 ¿Qué es la estrategia momentum 120?

Es una estrategia basada en el principio del **momentum**: *los activos que han subido en el pasado tienden a seguir subiendo en el corto/medio plazo* (y los que han caído, siguen cayendo). El "120" se refiere a la **ventana de 120 días** (~6 meses) para medir el momentum.

**La idea central:** comprar las **30 acciones del S&P 500 con mayor retorno acumulado en los últimos 120 días**.

---

## ⚙️ Cómo funciona (paso a paso)

### 1. Calcular el momentum de cada acción
Para cada acción del universo (292 de sp500_liquid):
```
momentum = (precio_hoy / precio_hace_120_días) − 1
```
Es el **% que ha subido (o bajado) la acción en los últimos 6 meses**.

### 2. Ordenar y seleccionar (top 30)
Se ordenan de mayor a menor momentum y se eligen las **30 con mejor momentum** (`topk = 30`).

### 3. Rebalancear semanalmente
Cada semana (~sábado):
- Se recalculan los momentum (con cierres del viernes)
- Se re-seleccionan las 30 mejores
- Se ajusta la cartera: se venden las que salieron del top 30, se compran las que entraron
- Se pagan los **costes de Interactive Brokers** (reales, no tarifa plana)

---

## 📊 Rendimiento validado

| Métrica | Valor |
|---|---|
| **IC out-of-sample** | **+0.066** (alpha real confirmado) |
| Retorno anualizado (backtest) | ~+18–21% |
| Sharpe | ~0.9–1.1 |
| Max drawdown | ~−19% |
| Horizonte | medio plazo (120 días) |

---

## 🔍 Por qué funciona (base teórica)

El momentum tiene respaldo empírico sólido (Jegadeesh & Titman, 1993 — de los papers más citados de finanzas):

- **Reacción insuficiente (underreaction):** los inversores tardan en incorporar las buenas noticias; el precio sigue subiendo mientras la información se difunde.
- **Sesgos de comportamiento:** los inversores venden ganadores demasiado pronto (asegurar ganancias) y aguantan perdedores demasiado tiempo (aversión a pérdidas) → el precio no refleja toda la información al instante.

---

## ⚙️ Parámetros de implementación

| Parámetro | Valor | Razón |
|---|---|---|
| Universo | sp500_liquid (292) | Amplio y diversificado |
| Ventana momentum | 120 días | Punto óptimo (el label-250 no funcionó) |
| topk | 30 acciones | Diversifica el alpha |
| Rebalanceo | semanal | Balance entre costes y frescura |
| Costes | IB tiered reales | No tarifa plana |

---

## ⚠️ Riesgos

1. **Momentum crash:** en transiciones bruscas (2020, 2022), el momentum puede invertirse — lo que más subió cae más fuerte. Se mitiga con vol-targeting.
2. **Decae con el tiempo:** el alpha se erosiona a medida que más gente lo usa.
3. **Correcto en medio plazo:** no esperes resultados en semanas — necesita meses para mostrar su edge.

---

# 1️⃣ Cómo se calcula el IC (Information Coefficient)

El **IC** mide si las predicciones se relacionan con los resultados reales. Es la métrica clave que valida que la estrategia tiene alpha.

### Paso a paso

**Paso 1 — Tener la predicción y el resultado:**
- **Predicción** = momentum 120d (lo que ordena la selección)
- **Resultado real** = retorno futuro (lo que la acción hizo después)

**Paso 2 — La correlación:**
```
IC = correlación( momentum_pasado , retorno_futuro )
```
(correlación de Pearson entre ambas series)

**Paso 3 — Validación out-of-sample (walk-forward):**
Se mide el IC **por año** (2018, 2019, ...) y se promedia. Si el IC se sostiene ~0.06-0.07 **fuera de muestra**, es alpha real, no overfitting.

### Interpretación del IC
| IC | Significado |
|---|---|
| > 0.05 | Excelente (raro) |
| 0.02–0.05 | Bueno y explotable |
| ~ 0 | Ruido (sin alpha) |
| < 0 | Señal invertida |

**Nuestro caso:** momentum 120d → **IC OOS = +0.066** (alpha sólido y genuino).

---

# 2️⃣ Cómo funciona el vol-targeting

El **vol-targeting** gestiona **cuánto arriesgas** según la volatilidad del mercado: **si sube la volatilidad, reduce la exposición; si baja, la aumenta.** Mantiene una **volatilidad objetivo constante** ajustando el tamaño.

### Fórmula
```
risk_degree = vol_objetivo / vol_actual   (recortado entre 30% y 100%)
```
- **vol_objetivo** = volatilidad que quieres mantener (ej. 20% anual)
- **vol_actual** = volatilidad reciente del mercado (ej. ^NDX últimos 120 días)

### Ejemplo concreto
| Volatilidad actual | risk_degree | Exposición |
|---|---|---|
| 20% (normal) | 20/20 = 1.0 | 100% |
| 30% (tensa) | 20/30 = 0.67 | 67% |
| 40% (caos) | 20/40 = 0.50 | 50% |
| 15% (calmado) | 20/15 = 1.0 (máx) | 100% |

### Implementación
En `vol_target_strategy.py`, se ajusta el `risk_degree` antes de cada decisión: se calcula la vol del benchmark (^NDX), se ajusta `risk_degree = vol_target / vol_real`, recortado a un rango seguro (30–100%).

### Por qué funciona
En **momentum crashes** la volatilidad explota justo cuando el momentum va a fallar. Al **reducir exposición automáticamente**, evitas las peores caídas — por eso el **drawdown bajó de −48% a −19%** al añadirlo.

---

# 3️⃣ El detalle del rebalanceo semanal

El rebalanceo adapta la cartera al nuevo ranking de momentum cada semana.

### El proceso
1. **Valorar la cartera anterior** al precio de hoy
2. **Recalcular el momentum 120d** de todas las acciones (cierres del viernes)
3. **Re-seleccionar el top 30** nuevo
4. **Determinar los cambios**:
   - Vendes las que ya no están en el top 30
   - Compras las que entraron al top 30
   - Las que siguen, se ajustan al nuevo peso igualitario (~1/30)
5. **Aplicar costes IB reales** (comisión + SEC/TAF en ventas)
6. **Guardar el nuevo estado**

### Ejemplo de esta semana (15-ago)
- **Antes:** 30 posiciones valor $22,465
- **Rebalanceo:** vendes/ajustas, compras
- **Coste IB:** $11.28 (30 órdenes)
- **Después:** $22,454

### Clave de diseño
La señal es de **120 días** (estable), pero el **rebalanceo es semanal** (para no dejar un ganador que se cae, ni perder uno que entra). Equilibra **costes** (rebalancear mucho = comisiones) con **frescura** (no quedarse obsoleto).

**Validado:** semanal > diario (demasiados costes) y semanal > mensual (menos reactivo).

---

## 📊 Resumen de cómo encaja todo

```
CADA SEMANA (sábado):
  1. Datos nuevos → recalcular momentum 120d de 292 acciones
  2. Ordenar → elegir top 30
  3. Ajustar exposición (vol-targeting) según la volatilidad
  4. Rebalancear: vender/comprar con costes IB reales
  5. Guardar estado
```

- **IC (0.066)** = confirma que la *señal* predice (alpha)
- **Vol-targeting** = confirma que la *exposición* es segura (riesgo)
- **Rebalanceo** = confirma que la *ejecución* es eficiente (costes)

---

*Documento de referencia del proyecto Qlib Work. Estrategia en paper-trading.*
