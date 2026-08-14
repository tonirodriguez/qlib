# Futuros, Opciones y Derivados — Guía de Referencia

> Vault de Inversión Cuantitativa | Julio 2026
> Fuente principal: Deribit, CME, Polymarket

---

## 1. Futuros — Lo Básico

Un **futuro** es un contrato que obliga a comprar/vender un activo a un precio fijado hoy, pero con liquidación en una fecha futura.

### Contango vs Backwardation

| Estado | Curva | Significado |
| :--- | :--- | :--- |
| **Contango** | Futuro > Spot | El mercado espera precio más alto en el futuro. Es lo normal (coste de financiación + storage) |
| **Backwardation** | Futuro < Spot | El mercado espera precio más bajo. Ocurre en mercados con restricciones de oferta inmediata |

**Ejemplo real (BTC, 30 Jul 2026):**
```
Spot:    $64,722
31 Jul:  $64,707  ← prácticamente flat
28 Ago:  $64,885  ← +$178 contango
25 Sep:  $65,135  ← +$428 contango
25 Dic:  $65,792  ← +$1,070 contango
```

La pendiente de la curva = **coste de carry** (funding rate + riesgo de contraparte). Si es muy pronunciada, hay incentivo a hacer cash-and-carry arbitrage.

### La Curva de Futuros como Predictor

La curva NO es una predicción de precio futuro, sino que refleja:
1. **Coste de financiación** — mantener la posición cuesta (o paga) funding
2. **Expectativas de dividendos** (para equities) — no aplica a crypto
3. **Sentimiento** — contango pronunciado = mercado alcista; backwardation = mercado bajista
4. **Coste de oportunidad** — el dinero inmovilizado tiene un coste (~tasa libre de riesgo)

**Regla práctica:** Cuando el contango se estrecha o se invierte a backwardation, suele preceder a movimientos bruscos de precio.

---

## 2. Opciones — Lo Básico

Una **opción** da el derecho (no la obligación) de comprar (call) o vender (put) un activo a un precio fijado (strike) antes de una fecha (vencimiento).

| Tipo | Derecho | Apuestas a... |
| :--- | :--- | :--- |
| **Call** | Comprar | Subida del activo |
| **Put** | Vender | Bajada del activo |

### Moneyness

| Estado | Call | Put |
| :--- | :--- | :--- |
| **ITM** (In The Money) | Strike < Spot | Strike > Spot |
| **ATM** (At The Money) | Strike ≈ Spot | Strike ≈ Spot |
| **OTM** (Out The Money) | Strike > Spot | Strike < Spot |

**ATM** es la referencia porque es donde hay más liquidez y donde el precio es más "limpio" (sin distorsiones de skew).

### Griegas (Greeks)

| Griega | Símbolo | Qué mide |
| :--- | :--- | :--- |
| **Delta** | Δ | Cuánto se mueve la opción por cada $1 del subyacente (0 a 1) |
| **Gamma** | Γ | Cuánto cambia Delta por cada $1 (aceleración) |
| **Theta** | Θ | Pérdida de valor por día (decaimiento temporal) |
| **Vega** | ν | Cuánto se mueve la opción por cada 1% de cambio en IV |
| **Rho** | ρ | Cuánto se mueve por cambio en tasa de interés |

---

## 3. Volatilidad Implícita (IV)

### ¿Qué es?

La **volatilidad implícita** es la volatilidad que, al introducirla en el modelo Black-Scholes, produce el precio actual de mercado de la opción.

- **No es** la volatilidad histórica (lo que ya pasó)
- **Es** la expectativa del mercado sobre la volatilidad futura
- Se expresa en % anualizado

### ATM IV — La Referencia Estándar

**ATM IV** = volatilidad implícita de las opciones At The Money.

Es el número más importante del mercado de opciones porque:

1. **Máxima liquidez** — las opciones ATM son las más negociadas, su precio es el más fiable
2. **Sin distorsiones** — las OTM tienen sobreprecio por skew (cola de riesgo), las ITM tienen descuento. Las ATM están "limpias"
3. **Ancla de la superficie** — a partir de ATM IV se construye toda la estructura de volatilidad por strikes y vencimientos
4. **Refleja la incertidumbre** — IV alta = mercado espera movimiento; IV baja = mercado tranquilo

### Analogía del Seguro

| Tipo de opción | Tipo de seguro |
| :--- | :--- |
| Call OTM | Seguro de incendios con franquicia alta |
| Put OTM | Seguro de robo con franquicia alta |
| **Opción ATM** | **Seguro todo riesgo sin franquicia** |

La **ATM IV** es la **prima de ese seguro todo riesgo**.

### Traducción a Movimiento Esperado

Fórmula aproximada para el rango esperado a 1 desviación estándar (~68% de probabilidad):

```
Movimiento esperado = Precio × IV × √(días / 365)
```

**Ejemplo BTC (IV 27%, 1 día):**
```
$64,707 × 0.27 × √(1/365) = ~$915
Rango 68%: $63,792 — $65,622
```

**Ejemplo ETH (IV 37%, 1 día):**
```
$1,921 × 0.37 × √(1/365) = ~$37
Rango 68%: $1,884 — $1,958
```

### IV Histórica vs Actual (BTC)

| Periodo | IV Media | IV Actual (30 Jul 26) |
| :--- | :---: | :---: |
| Media histórica BTC | ~55-65% | **27%** |
| Media histórica ETH | ~50-60% | **37%** |

La IV actual está **muy por debajo de la media histórica**, lo que indica que el mercado de opciones está infravalorando el riesgo o, alternativamente, que comprar opciones ahora es barato.

---

## 4. Skew y Sonrisa de Volatilidad

La IV no es constante entre strikes. La gráfica IV vs strike se llama **volatility smile** o **skew**.

```
  IV
  ↑
  │                      ___
  │                 ____/   \____
  │            ____/            \____
  │       ____/                     \____
  │   ___/                              \___
  └─────────────────────────────────────────→ Strike
    ITM ←                → OTM
      Puts                Calls
```

- Las puts OTM suelen tener IV más alta (la gente paga más por protección ante caídas)
- Las calls OTM tienen IV más baja (menos miedo a subidas extremas)
- El skew es más pronunciado en periodos de incertidumbre

---

## 5. Datos en Vivo — Dónde Consultarlos

### Deribit (API pública, sin autenticación)

```bash
# Futuros BTC
curl -s "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=future"

# Opciones BTC
curl -s "https://www.deribit.com/api/v2/public/get_book_summary_by_currency?currency=BTC&kind=option"

# Índice BTC
curl -s "https://www.deribit.com/api/v2/public/get_index_price?index_name=btc_usd"
```

### Polymarket (API gamma pública)

```bash
# Eventos activos tag crypto
curl -s "https://gamma-api.polymarket.com/events?closed=false&tag=crypto&limit=50"
```

### CME

Los futuros de CME se pueden consultar en su web, pero requieren scraping o suscripción para datos en vivo vía API.

---

## 6. Estrategias Básicas con Opciones

| Estrategia | Composición | Direccional? | Riesgo |
| :--- | :--- | :---: | :--- |
| **Long Call** | Comprar Call | ✅ Alcista | Limitado (prima) |
| **Long Put** | Comprar Put | ✅ Bajista | Limitado (prima) |
| **Covered Call** | Tener activo + vender Call | Neutral-Alcista | Asignación del activo |
| **Protective Put** | Tener activo + comprar Put | Neutral | Limitado a prima |
| **Straddle** | Comprar Call + Put ATM | ❌ (dirección) | Limitado (prima x2) |
| **Strangle** | Comprar Call OTM + Put OTM | ❌ (dirección) | Limitado (menor prima) |
| **Iron Condor** | Vender Call OTM + Put OTM + comprar más lejos | Neutral | Limitado |

**Straddle** es la apuesta directa a volatilidad: ganas si el activo se mueve mucho en cualquier dirección. Es la forma más pura de jugar IV.

---

## 7. Glosario Rápido

| Término | Significado |
| :--- | :--- |
| **Spot** | Precio actual del activo |
| **Strike** | Precio al que se ejecuta la opción |
| **Expiry / Vencimiento** | Fecha en que la opción expira |
| **Prima** | Precio de la opción |
| **IV** | Implied Volatility (volatilidad implícita) |
| **ATM** | At The Money |
| **ITM** | In The Money |
| **OTM** | Out of The Money |
| **Contango** | Futuros > Spot |
| **Backwardation** | Futuros < Spot |
| **Skew** | Diferencia de IV entre strikes |
| **Surface** | Matriz IV × Strike × Vencimiento |
| **Open Interest** | Número de contratos abiertos |
| **Funding Rate** | Coste de mantener posición en futuros perpetuos |

---

## 8. Referencias

- Deribit API docs: https://docs.deribit.com/
- Polymarket API: https://docs.polymarket.com/
- CME Bitcoin Futures: https://www.cmegroup.com/markets/cryptocurrencies/bitcoin/bitcoin.html
- Black-Scholes: https://en.wikipedia.org/wiki/Black–Scholes_model
