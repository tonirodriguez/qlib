# Conceptos Investment

## Turnover

En el contexto del trading y la gestión de carteras, el **turnover** (o rotación) es una medida que indica con qué frecuencia se compran y venden los activos de una cartera en un periodo determinado (generalmente un año).

Es, básicamente, la velocidad a la que un gestor o un algoritmo "refresca" sus posiciones.

---

### 1. ¿Cómo se calcula?

Aunque existen variaciones, la fórmula más estándar es:

$Turnover = \frac{\min(\text{Compras}, \text{Ventas})}{\text{Valor Total de la Cartera}}$

Si tienes una cartera de **100.000€** y durante el año vendiste acciones por valor de **50.000€** para comprar otras nuevas, tu turnover es del **50%**. Un turnover del **100%** significaría que, en promedio, has renovado todas tus posiciones una vez en el año.

---

### 2. ¿Por qué es importante?

El turnover es una métrica crítica por tres razones principales:

- **Costes de Transacción:** Cada vez que operas, pagas comisiones y sufres el *spread* (diferencia entre precio de compra y venta). Un turnover alto puede "comerse" tus beneficios.
- **Impacto Fiscal:** En muchas jurisdicciones, vender una posición con ganancias genera el pago de impuestos. Un turnover bajo suele ser más eficiente fiscalmente (estrategias *Buy & Hold*).
- **Estilo de Inversión:** * **Bajo Turnover (<20%):** Inversión a largo plazo, estilo Value.
    - **Alto Turnover (>100%):** Estrategias cuantitativas, trading de alta frecuencia (HFT) o gestión muy activa.

---

### 3. El Turnover en el Rebalanceo

Como estás trabajando con un sistema de **rebalanceo de cartera**, el turnover es el valor que te dice cuánto peso has tenido que mover para ajustar tu cartera actual a tu **cartera objetivo**.

Si tu script de rebalanceo genera muchas órdenes de compra/venta cada día, tu turnover será altísimo. En sistemas automáticos, a menudo se añaden "penalizaciones por turnover" en el código para evitar que el algoritmo opere demasiado por cambios insignificantes en los precios.

---

### 4. Ejemplo Práctico

- **Día 1:** Tienes 100% en Apple.
- **Día 2:** Tu modelo dice que ahora Apple debe ser el 90% y Microsoft el 10%.
- **Acción:** Vendes un 10% de Apple y compras 10% de Microsoft.
- **Turnover de la operación:** 10%.