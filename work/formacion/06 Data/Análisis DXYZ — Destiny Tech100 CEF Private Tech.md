# Análisis: Destiny Tech100 (DXYZ) — Closed-End Fund de Private Tech

> **Propósito:** Análisis detallado de DXYZ como vehículo de inversión para acceder a private tech (SpaceX, Anthropic, OpenAI, Stripe, etc.) desde bolsa. Incluye mecánica de CEFs, NAV, prima/descuento, cartera, riesgos estructurales y contexto en el ciclo de inversión en IA.
>
> **Fecha:** 24 junio 2026
> **Precio referencia:** $26.49 (NYSE, cierre 23 jun 2026)

---

## Índice

1. [¿Qué es DXYZ?](#1-qué-es-dxyz)
2. [¿Qué es un Closed-End Fund (CEF) y cómo funciona?](#2-qué-es-un-closed-end-fund-cef-y-cómo-funciona)
3. [¿Qué es el NAV y por qué importa tanto?](#3-qué-es-el-nav-y-por-qué-importa-tanto)
4. [Ficha Técnica](#4-ficha-técnica)
5. [Cartera Completa](#5-cartera-completa)
6. [Estructura: El Problema de los SPVs y Forward Contracts](#6-estructura-el-problema-de-los-spvs-y-forward-contracts)
7. [Análisis Detallado](#7-análisis-detallado)
   - [7.1 Lo que gusta](#71-lo-que-gusta)
   - [7.2 Lo que preocupa](#72-lo-que-preocupa)
8. [DXYZ en el Contexto del Ciclo de Inversión en IA](#8-dxyz-en-el-contexto-del-ciclo-de-inversión-en-ia)
9. [Escenarios y Sensibilidad](#9-escenarios-y-sensibilidad)
10. [Veredicto](#10-veredicto)
11. [Notas y Fuentes](#11-notas-y-fuentes)

---

## 1. ¿Qué es DXYZ?

**Destiny Tech100 Inc.** es un **closed-end management investment company** (CEF) registrado bajo el **Investment Company Act de 1940**, que cotiza en la **New York Stock Exchange (NYSE)** bajo el ticker **DXYZ**.

**Propósito declarado:**
> "Proporcionar a inversores cotidianos acceso a las 100 principales compañías tecnológicas privadas de alto crecimiento respaldadas por venture capital, por primera vez."

**Estado actual:**
- **Target de cartera:** 100 compañías privadas late-stage.
- **Cartera actual:** 36 compañías (a 31 marzo 2026).
- **Efectivo:** 31.4% del portfolio — aún en fase de despliegue.
- **Comisión de gestión:** 2.5% anual.
- **Market Cap:** ~$807M.

Es un producto diseñado para resolver un problema real: los inversores minoristas no pueden comprar acciones de SpaceX, OpenAI, Anthropic, Stripe, Databricks, etc. en bolsa porque son empresas privadas. DXYZ compra esas participaciones a través de SPVs y forwards, y tú compras acciones de DXYZ en NYSE.

---

## 2. ¿Qué es un Closed-End Fund (CEF) y cómo funciona?

Un **Closed-End Fund** es un vehículo de inversión que:
1. **Recauda capital en una OPV** (oferta pública inicial) emitiendo un número fijo de acciones.
2. **Invierte ese capital** en una cartera de activos (en este caso, participaciones de startups privadas).
3. **Sus acciones cotizan en bolsa** como cualquier acción normal.

**Diferencia clave con un ETF o un fondo mutuo:**
- En un ETF, el precio sigue muy de cerca el valor de los activos subyacentes (NAV) porque el market maker crea/redime acciones para mantener el equilibrio.
- En un **CEF**, el número de acciones es fijo. El precio de mercado lo determina **oferta y demanda** en bolsa, **no** el valor de los activos subyacentes. Por eso los CEFs pueden cotizar con **prima** (precio > NAV) o **descuento** (precio < NAV).

**En el caso de DXYZ:**
- La demanda minorista por los nombres sexy (SpaceX, OpenAI) puede hacer que la acción cotice muy por encima del NAV.
- Cuando la euforia se enfría, la prima se comprime — y puedes perder dinero aunque las empresas subyacentes sigan valiendo lo mismo.
- A diferencia de un ETF, **no hay mecanismo de arbitraje** que fuerce el precio hacia el NAV. Puede desviarse durante meses o años.

---

## 3. ¿Qué es el NAV (Net Asset Value) y por qué importa tanto?

> **📘 NAV = Net Asset Value (Valor Neto de los Activos)**

Es el **valor contable por acción** de todos los activos del fondo menos sus pasivos, dividido entre el número de acciones en circulación.

**La fórmula:**
```
NAV = (Valor de mercado de todos los activos del fondo - Pasivos) / Acciones en circulación
```

**Ejemplo simplificado con DXYZ:**
- Activos del fondo: $500M (SpaceX $72M + Anthropic $90M + OpenAI $28M + efectivo $157M + resto $153M)
- Pasivos: $5M (gastos de gestión, operativos)
- Acciones en circulación: ~30M
- **NAV por acción: ($500M - $5M) / 30M = ~$16.50**

Si la acción cotiza a $26.49, estás pagando una **prima del ~60% sobre el NAV**.

**Por qué el NAV no es perfecto aquí:**

1. **Valoraciones de privadas son estimaciones.** SpaceX no cotiza en bolsa. Su valoración la determina la última ronda de financiación o un modelo interno del fondo. Puede estar desactualizada o ser poco precisa.
2. **No hay precio de mercado diario** para las posiciones subyacentes. El NAV de un CEF de privadas es menos fiable que el de uno de acciones líquidas.
3. **La prima/descuento es lo que realmente importa para tu retorno.**
   - Si compras a $26.49 con NAV de $16.50 y la prima se comprime a 0% (precio = NAV), pierdes ~38% aunque las privadas no se muevan.
   - Si la prima se mantiene y las privadas suben, ganas el upside del NAV + la prima constante.

**Los movimientos históricos de la prima en DXYZ ilustran este riesgo:**
- En su pico (~$72.87 en 2024), la prima era **astronómica** — probablemente 300-400% sobre NAV.
- Hoy (~$26.49), la prima está más comprimida pero sigue siendo significativa (~60-84% estimado según última declaración).
- Si el mercado decide que DXYZ no merece prima y cotiza a NAV, el precio caería a ~$14-16 aunque Anthropic y SpaceX sigan subiendo.

> **Regla de oro de los CEFs:** La prima puede ir a cero o a negativo (descuento) independientemente del rendimiento de los activos subyacentes. **No confundas el rendimiento del fondo con el rendimiento de su cartera.**

---

## 4. Ficha Técnica

| Métrica | Valor |
|---------|-------|
| **Ticker** | DXYZ (NYSE) |
| **Precio** (cierre 23 jun 2026) | **$26.49** |
| **Overnight** (Blue Ocean ATS) | $26.54 (+0.19%) |
| **Market Cap** | **$807M** |
| **52-Week Rango** | $19.71 – $72.87 |
| **YTD Return** | **+13.52%** (S&P 500: +7.60%) |
| **1-Year Return** | **+32.82%** |
| **3-Year Return** | **+221.09%** |
| **P/E (TTM)** | 7.48 |
| **EPS (TTM)** | $3.54 |
| **Price/Book (mrq)** | 1.84 |
| **Price/Sales (ttm)** | 12.12 |
| **Volumen diario medio** | ~4.8M acciones |
| **Volumen último cierre** | 2.6M acciones |
| **Comisión de gestión** | **2.5% anual** |
| **Nº posiciones actual** | 36 (target: 100) |
| **Efectivo en cartera** | 31.4% |
| **Tipo de vehículo** | Closed-End Fund (1940 Act) |

---

## 5. Cartera Completa

### Top Holdings (a 31 marzo 2026)

| Posición | % Cartera | Sector | Tipo de exposición |
|----------|-----------|--------|-------------------|
| **Anthropic PBC** | **18.1%** | IA / Frontier Labs | SPV con forward contracts |
| **SpaceX** (varios SPVs) | **~14.4%** | Espacio / Defensa | Múltiples SPVs en capas |
| **OpenAI** (Goanna + DXYZ OAI) | **~5.7%** | IA / Frontier Labs | Profit Participation Units |
| **OpenEvidence** | **4.6%** | IA / Healthcare | SPV forward |
| **Shield AI** | **4.2%** | Defensa / IA autónoma | SPV |
| **CHAOS Industries** | **2.1%** | Defensa / Tecnología | SPV |
| **Boom Technology** | **2.0%** | Aero / Supersónicos | Directa |
| **Hermeus** | **2.0%** | Aero / Hipersónicos | Directa |
| **Beast Industries** | **2.0%** | Consumo / Medios | Directa |
| **Tenstorrent** | **1.7%** | Chips / IA | SPV con forward |
| **Revolut** | **1.6%** | Fintech | Directa |
| **Hexagon/Ferox Games** | **1.5%** | Gaming | SPV |
| **Databricks** (varios SPVs) | **~2.5%** | Datos / IA | SPVs |
| **Skild AI** | **1.4%** | IA / Robótica | Directa |
| **Vast** | **0.7%** | Espacio | Directa |
| **Redwood Materials** | **0.7%** | Reciclaje baterías | Directa |
| **Astranis Space** | **~1.0%** | Espacio | Directa + SPV |
| **Payward (Kraken)** | **0.6%** | Crypto / Exchange | Directa |
| **Stripe** | **0.4%** | Fintech / Pagos | SPV con forward |
| **Axiom Space** | **0.6%** | Espacio | Directa |
| **Discord** | **~0%** | Social | Directa (muy diluida) |
| **Klarna** | **0.1%** | Fintech / BNPL | Directa |
| **Chime** | **0.2%** | Fintech / Banca | Directa |
| **Supabase** | **0.2%** | Infra / DB | Directa |
| **Vercel** | **0.3%** | Infra / Frontend | Directa |
| **Otros** (Automation Anywhere, Flexport, ClassDojo, Impossible Foods, etc.) | **~3%** | Varios | Directas o SPVs |
| **Efectivo y equivalentes** (Treasury Money Market) | **31.4%** | — | Letras del Tesoro |

### Concentración sectorial (estimada sobre cartera no-efectivo)

| Sector | % estimado |
|--------|-----------|
| **IA / Frontier Models** | ~30% (Anthropic, OpenAI, Skild AI, Databricks, OpenEvidence) |
| **Espacio / Defensa** | ~25% (SpaceX, Shield AI, CHAOS, Astranis, Axiom, Boom, Hermeus, Vast) |
| **Fintech** | ~5% (Revolut, Stripe, Klarna, Chime, Kraken) |
| **Chips / Infra** | ~3% (Tenstorrent, Discord, Supabase, Vercel) |
| **Consumo / Otros** | ~5% (Beast, Impossible Foods, Redwood, etc.) |
| **Efectivo** | **31.4%** |

---

## 6. Estructura: El Problema de los SPVs y Forward Contracts

DXYZ no compra acciones de las startups directamente en la mayoría de los casos. Utiliza una estructura compleja de **SPVs (Special Purpose Vehicles)** y **forward contracts** que es importante entender.

### ¿Qué es un SPV?

Un SPV es una sociedad instrumental creada específicamente para mantener una participación en una empresa. En lugar de que DXYZ posea directamente acciones de Anthropic, el fondo posee **unidades de un SPV**, y ese SPV posee acciones de Anthropic.

### ¿Qué es un forward contract?

El SPV a menudo no posee las acciones hoy, sino que tiene un **contrato a futuro** para recibirlas cuando se levanten las restricciones de transferencia (cuando la empresa salga a bolsa, sea adquirida, o permita transferencias secundarias).

### Las capas reales (del informe del fondo):

> *"The SPV has invested through five underlying SPVs, resulting in the related economic exposure to the Fund. Five of the underlying SPVs have one additional layer of SPVs, while one has two layers."*

**Traducción:** Para algunas posiciones, entre tú (accionista de DXYZ) y la empresa real hay **3-4 capas de SPVs**:
1. Tú → Acciones de DXYZ
2. DXYZ → Unidades de SPV Master
3. SPV Master → Unidades de SPV Intermedio
4. SPV Intermedio → Unidades de SPV Subyacente
5. SPV Subyacente → Forward contract → Acciones reales de la empresa

**Riesgos de esta estructura:**

| Riesgo | Explicación |
|--------|------------|
| **Costes** | Cada capa tiene costes legales, de auditoría, de administración |
| **Riesgo de contrapartida** | Si un SPV incumple, pierdes la exposición |
| **Riesgo de liquidación** | Los forwards pueden no liquidarse si la empresa privada no coopera |
| **Opacidad** | Sabes que tienes exposición económica, pero los derechos de voto, liquidez y protecciones son diferentes |
| **Retraso en distribución** | Si SpaceX paga un dividendo, tiene que atravesar todas las capas de SPVs antes de llegar a DXYZ y luego a ti |
| **Riesgo fiscal** | La estructura multi-SPV puede generar ineficiencias fiscales |

### Ejemplo de la exposición a OpenAI:

DXYZ tiene dos vehículos para OpenAI:
- **Goanna Capital 26E LLC:** Un SPV que invirtió en OpenAI Series C Preferred Stock. Representa el **4.7%** del portfolio.
- **DXYZ OAI I LLC:** Un SPV con Profit Participation Units (PPUs) de OpenAI. Representa el **1.0%**.

Ni siquiera ambos son acciones directas: uno es preferred stock via SPV, el otro son PPUs (un derivado que paga un % de los beneficios de OpenAI, sin tener derechos de propiedad reales).

### Ejemplo de la exposición a SpaceX:

SpaceX aparece a través de **tres vehículos distintos**:
1. **DXYZ SpaceX I LLC** (9.6% del portfolio) — 99% Class A Common + 1% Series J Preferred
2. **MWAM VC SpaceX-II LLC** (2.8%) — 55% Class A + 45% Class C Common
3. **Snowpoint Growth 2.6 LLC** (2.0%) — Class B Common

Y DXYZ SpaceX I LLC a su vez "has invested through five underlying SPVs, resulting in the related economic exposure". O sea, hay hasta **5 SPVs debajo de DXYZ SpaceX I LLC**, y debajo de esos SPVs pueden haber más.

---

## 7. Análisis Detallado

### 7.1 🟢 Lo que gusta

#### 1. Exposición a nombres imposibles de conseguir para retail

No hay ningún otro producto en NYSE que te dé exposición a **SpaceX, Anthropic, OpenAI, Databricks, Stripe, Revolut, Tenstorrent, Shield AI** simultáneamente. Ese es el valor único del vehículo.

| Compañía | ¿Accesible de otro modo para retail? |
|----------|-------------------------------------|
| SpaceX | No. Solo secundarios privados con acreditación + $100k mínimo |
| Anthropic | No. Inversores acreditados o institucionales |
| OpenAI | No. Rondas cerradas a institucionales |
| Stripe | No. Mercado secundario ilíquido |
| Databricks | No. Última ronda privada (valoración ~$60B+) |
| Tenstorrent | No. Startup de chips, solo venture |
| Shield AI | No. Defensa/IA, no cotiza |

Si tu tesis es que **las empresas privadas de IA van a revalorizarse más que las públicas** (porque capturan el crecimiento temprano sin el discount del mercado público), DXYZ es la única opción cotizada.

#### 2. La prima se ha comprimido — mejor punto de entrada que en 2024

DXYZ llegó a cotizar a $72.87. Hoy está en $26.49. La prima sobre NAV se ha comprimido significativamente.

Si la prima se mantiene en estos niveles (~60-84% sobre NAV), el retorno depende del rendimiento de las subyacentes. Si las privadas suben, DXYZ sube proporcionalmente.

Si el mercado decide que DXYZ merece una prima más baja por la calidad de su cartera (está acumulando buenos nombres), el riesgo de compresión adicional es menor que cuando cotizaba a $72.

#### 3. YTD +13.5%, superando al S&P 500

El portfolio de privadas está rindiendo. Anthropic y OpenAI han subido en rondas privadas. SpaceX mantiene su valoración. Revolut sigue creciendo. El YTD de DXYZ duplica al del S&P 500 (+13.5% vs +7.6%).

Esto sugiere que, al menos en el corto plazo, la tesis de fondo se cumple: las privadas de IA de alto crecimiento están generando retornos.

#### 4. El efectivo es un arma de doble filo — pero puede ser oportunidad

31.4% en efectivo significa que el gestor tiene **~$250M para desplegar**. Si despliega bien (comprando participaciones en las próximas rondas de SpaceX, OpenAI, Stripe, etc.), el NAV puede subir significativamente sin que el accionista tenga que poner más capital.

El gestor ha dicho que el target es 100 compañías. Hoy tienen 36. Queda ~2/3 del portfolio por construir.

---

### 7.2 🔴 Lo que preocupa

#### 1. La prima sobre NAV es el riesgo #1

DXYZ cotiza a **1.84x Book Value**. Si el NAV por acción es ~$14.40, estás pagando una prima del ~84%.

**Escenarios de la prima:**

| Escenario | Precio DXYZ | NAV estimado | Prima | Tu retorno |
|-----------|------------|-------------|-------|-----------|
| **Hoy** | $26.49 | ~$14.40 | ~84% | — |
| **Prima se duplica** (euforia) | $43.20 | $14.40 | 200% | +63% |
| **Prima se mantiene** | $31.68 | $17.28 (+20%) | 84% | +20% |
| **Prima se comprime a 30%** | $18.72 | $14.40 | 30% | **-29%** |
| **Prima desaparece** (precio = NAV) | $14.40 | $14.40 | 0% | **-46%** |
| **Descuento** (típico CEF) | $11.52 | $14.40 | -20% | **-57%** |

**El riesgo real:** Aunque las empresas subyacentes suban un 20% (NAV → $17.28), si la prima se comprime a 30%, pierdes dinero. Has acertado la tesis de fondo y has perdido dinero por la estructura.

**Y esto ya pasó:** DXYZ cotizó a $72.87. ¿Cayeron SpaceX, Anthropic y OpenAI un 60% en el año siguiente? Probablemente no. Lo que cayó fue la **prima**. La gente pagó $72 por algo que valía ~$20 de NAV, y cuando la euforia pasó, el precio se ajustó.

#### 2. Comisión de gestión del 2.5% anual

Es **muy alta** para un CEF:

| Vehículo | Comisión | Sobre $800M |
|----------|----------|-------------|
| **DXYZ** | **2.50%** | **$20M/año** |
| ETF de tecnología típico (QQQ, VGT) | 0.03-0.20% | $0.2-1.6M/año |
| CEF de bonos típico | 0.50-1.00% | $4-8M/año |
| Hedge fund de VC típico | 2.0% + 20% performance | $16M + performance |

La comisión del 2.5% se aplica sobre el total de activos **incluyendo el efectivo**. Estás pagando $20M al año para que gestionen ~$550M en privadas + ~$250M en letras del Tesoro que no necesitan gestión activa.

#### 3. 31.4% en efectivo = drag en el retorno

De tu dinero, casi un tercio está en **First American Treasury Obligations, Class X, 3.59%** (un money market fund). No está trabajando.

- Rendimiento del efectivo: ~3.6% anual
- Comisión que pagas sobre ese efectivo: 2.5% anual
- **Neto del efectivo: ~1.1% anual**
- Si la inflación está en ~2-3%, estás perdiendo poder adquisitivo en el 31.4% del portfolio.

**El coste de oportunidad:** Ese 31.4% podría estar en SpaceX, Anthropic o Stripe generando retornos de venture.

#### 4. Estructura opaca de SPVs

Ya detallado en la [sección 6](#6-estructura-el-problema-de-los-spvs-y-forward-contracts). Las capas de SPVs añaden:

- **Costes invisibles:** Honorarios legales, de auditoría, de administración de cada SPV. No aparecen en la comisión del 2.5%.
- **Riesgo de ejecución:** Si una empresa privada se niega a honrar un forward o hay disputas legales, el accionista de DXYZ no tiene recurso directo.
- **Dificultad de valoración:** Con 3-4 capas de SPVs, ¿cuánto vale realmente tu exposición? Las valoraciones son estimaciones de estimaciones.
- **Riesgo de concentración en SPVs con problemas:** Algunos SPVs del portfolio tienen valor 0 ("During the year ended December 31, 2024 the SPV disposed of the underlying asset. As of March 31, 2026 the SPV does not hold any underlying assets."). Hay SPVs muertos que todavía aparecen en el portfolio con exposición 0%.

#### 5. Riesgo de liquidez de las subyacentes

DXYZ cotiza con ~4.8M acciones/día de volumen — es líquido. Pero las subyacentes (SpaceX, Anthropic) **no lo son**.

**El problema:**
- Las valoraciones de privadas se marcan "a la última ronda". Si no hay ronda en 12 meses, la valoración puede estar desactualizada.
- Si el mercado público cae y arrastra las valoraciones de privadas, el NAV puede caer **con retraso** — el precio de DXYZ caería primero, la prima se abriría, y luego el NAV se ajustaría cuando llegue la próxima ronda privada.
- **No hay transparencia en tiempo real** sobre el valor de los activos.

#### 6. Concentración peligrosa

Anthropic (18.1%) + SpaceX (14.4%) + OpenAI (5.7%) = **~38% del portfolio** en 3 compañías.

Sobre el portfolio no-efectivo (~68.6% del total), esas tres representan **~55%**.

Si OpenAI tiene un problema regulatorio, o si Anthropic no alcanza los ingresos que Patel estima, o si SpaceX tiene un retraso en Starship — el fondo se resiente de forma desproporcionada.

#### 7. Riesgo de mercado: la prima de los CEFs tiende a cero con el tiempo

Los CEFs que cotizan con prima elevada suelen converger hacia NAV o descuento con el tiempo. Es un fenómeno estadístico bien documentado. Las razones:

- Los early adopters compran en la OPV/IPO con prima; los late adopters llegan cuando la prima ya está alta y hay menos "mayor tonto" (greater fool) a quien venderle.
- El mercado se da cuenta de que el CEF no es más que un wrapper para activos que podrían comprarse más baratos en privado (si tuvieras acceso).
- La dilución por comisiones erosiona el valor lentamente pero de forma constante.

DXYZ ha existido desde 2024. La prima ha caído de ~300-400% a ~84%. La tendencia es hacia abajo. ¿Dónde para? Podría parar en 0% o podría ir a descuento del 10-20%, como la mayoría de CEFs de private equity/venture que existen (ej: BXMX, CET, etc.).

#### 8. ¿Quién es el gestor?

Destiny Management LLC es una gestora relativamente nueva. No tiene el track récord de firmas como Blackstone, KKR o Apollo en la gestión de CEFs de activos alternativos. No hay información pública extensa sobre su equipo de inversión ni su historial en private tech investing.

**Esto importa porque:**
- La calidad del despliegue del 31.4% de efectivo determina el retorno futuro.
- La capacidad de conseguir acceso a rondas calientes (SpaceX, Anthropic) en buenos términos es lo que justifica la comisión del 2.5%.
- Si el gestor no tiene relaciones sólidas, pagará precios más altos o tendrá que comprar en secundarios con peores términos.

---

## 8. DXYZ en el Contexto del Ciclo de Inversión en IA

En el marco de las 5 capas ([[Ciclo de Inversión en IA — Modelo de las 5 Capas]]) y el análisis de [[Análisis Dylan Patel y Pierre Ferragu — AI Infrastructure & Tokconomics]], DXYZ se posiciona de la siguiente forma:

### Exposición por capa

| Capa | ¿Exposición vía DXYZ? | Comentario |
|------|----------------------|-----------|
| **Energy** | ❌ 0% | Sin exposición a la capa que Patel y Ferragu identifican como cuello de botella definitivo |
| **Chips** | 🟡 ~1.7% (Tenstorrent) | Muy pequeña. Sin exposición a NVDA, TSM, AVGO, MU |
| **Infra / Cloud** | ❌ 0% | Sin exposición a los hyperscalers ni datacenters |
| **Models** | 🟢 ~30% (Anthropic, OpenAI, Databricks) | Aquí está la tesis: Patel dice que los frontier labs tienen márgenes ≥72% |
| **Applications** | 🟢 ~15% (OpenEvidence, Shield, Stripe, Revolut) | Variado, pero no son aplicaciones de IA puras en su mayoría |
| **Defense / Space** | 🟡 ~25% (SpaceX, Shield, CHAOS, etc.) | Tesis separada, no relacionada con el ciclo de IA |

### Dónde encaja con las tesis de Patel y Ferragu

**A favor:**
- La mayor posición es Anthropic (18.1%), que es exactamente la empresa que Patel usa para argumentar márgenes ≥72% de inferencia y escalada de ARR $9B→$35-45B.
- Si la tesis de Patel se cumple (márgenes altos + escasez de inferencia), Anthropic se revaloriza y DXYZ sube.
- OpenEvidence (4.6%) es IA aplicada a healthcare — uno de los verticales que Patel identifica como creciente.

**En contra:**
- No hay exposición a NVDA ni TSMC, que son donde Patel y Ferragu ven pricing power más claro y visible.
- No hay exposición a la energía, que Ferragu identifica como cuello de botella emergente.
- El 31.4% en efectivo es capital que no trabaja en un momento donde el acceso a rondas de IA es el recurso más escaso.
- Si la tesis de la "commoditización de modelos" se cumple (modelos abiertos suficientes → márgenes de frontier labs se comprimen), Anthropic y OpenAI pierden valor — y DXYZ pierde su posición más grande.

---

## 9. Escenarios y Sensibilidad

### Escenario base (probable): Prima estable, NAV crece ~15-25% anual

- Las privadas suben en rondas (SpaceX +20%, Anthropic +30%, OpenAI +20%).
- El gestor despliega el efectivo restante en buenos términos.
- El NAV sube de ~$14.40 a ~$17-18 en 12 meses.
- La prima se mantiene en ~60-80%.
- Precio objetivo: **$28-32** en 12 meses → **+6-21%**.

### Escenario alcista: Prima se re-expande + las privadas suben fuerte

- Una OPV de SpaceX o Stripe genera FOMO en el mercado.
- La prima vuelve a niveles de 100-150%.
- Las privadas se revalorizan fuerte (Anthropic duplica).
- NAV sube a ~$22.
- Precio objetivo: **$44-55** en 12 meses → **+66-108%**.

### Escenario bajista: Prima se comprime a descuento CEF típico

- El mercado se da cuenta de la estructura SPV y la prima desaparece.
- Las privadas no se revalorizan (ciclo de IA se enfría, rendimientos decrecientes).
- El gestor despliega mal el efectivo.
- NAV se estanca o cae ligeramente (~$13).
- Prima se comprime a 0% o descuento del 10%.
- Precio objetivo: **$12-14** en 12 meses → **-47 a -55%**.

### Sensibilidad de la prima

```
Si NAV = $14.40:

Prima →  0%   20%   50%   84%   100%   200%
Precio → $14   $17   $22   $26    $29    $43
```

---

## 10. Veredicto

| Dimensión | Valoración |
|-----------|-----------|
| **🧠 Idea conceptual** | Excelente. Dar acceso retail a unicornios privados es un problema real y DXYZ lo resuelve. |
| **⚙️ Ejecución / Estructura** | **Débil.** SPVs en múltiples capas, opacidad, efectivo improductivo, comisión alta. |
| **📊 Cartera** | **Buena.** Anthropic + SpaceX + OpenAI son nombres de primera calidad. Concentración extrema pero controlada. |
| **💸 Valoración actual** | **Cara.** Prima del ~84% sobre NAV. No es barato aunque ha caído desde $72. |
| **📈 Momento en el ciclo** | Mejor que en 2024 (prima más baja), pero peor que si esperas a que la prima se comprima más. |
| **⚠️ Riesgo principal** | La prima sobre NAV se comprime o desaparece. No controlas ese riesgo. |
| **🎯 Para quién es** | Alguien que: (a) quiere exposición a SpaceX/Anthropic/OpenAI, (b) acepta pagar 2.5%/año + prima sobre NAV, (c) tiene horizonte 3-5 años, (d) entiende que la estructura no es limpia. |
| **🚫 Para quién no es** | Alguien que: (a) quiere exposición limpia a IA (mejor NVDA, MSFT, GOOG, AMZN + ETFs a 0.03%), (b) tiene horizonte <2 años, (c) le preocupa la prima sobre NAV, (d) quiere sleep-well factor. |

### Alternativas directas

| Lo que quieres | Alternativa mejor |
|---------------|------------------|
| Exposición a IA (general) | Compra NVDA, MSFT, GOOG, AMZN, META. Más líquido, más barato, más diversificado. |
| Exposición a private tech | Acepta que eres minorista y no tienes acceso. No pagues 2.5% por un proxy imperfecto. |
| Exposición a SpaceX | No hay alternativa pública. DXYZ es la única. Pregúntate si vale la prima. |
| Exposición a Anthropic | DXYZ es la única opción pública. Mismo dilema. |
| Jugar la prima/descuento de un CEF | Hay CEFs más baratos y con más historia (BXMX, BST, CET, etc.) |

**Resumen:** DXYZ no es un mal producto para lo que hace, pero es un producto de **propósito específico** con costes y riesgos estructurales que hay que entender. La prima sobre NAV es el driver de corto plazo; la evolución de SpaceX y Anthropic es el driver de largo plazo. No es un core holding — es una **apuesta táctica** con un vehículo imperfecto para acceder a activos que de otro modo serían inaccesibles.

Si entras, hazlo sabiendo que el 31.4% de tu dinero está parado y que el 84% de prima puede desaparecer sin relación con el rendimiento de las subyacentes. El tamaño de la posición debería reflejar ese riesgo estructural.

---

## 11. Notas y Fuentes

1. **Yahoo Finance — DXYZ** ([quote](https://finance.yahoo.com/quote/DXYZ/)): Precio, métricas, returns a 23 junio 2026.
2. **Destiny.xyz — Tech100 Portfolio** ([portfolio](https://destiny.xyz/tech100)): Cartera completa a 31 marzo 2026, estructura de SPVs, notas.
3. **Destiny.xyz — Eligibility Criteria** ([criteria](https://destiny.xyz/tech100)): Criterios de inclusión y metodología de inversión.
4. **SEC Filings — Destiny Tech100 (DXYZ):** Investment Company Act reports, NAV disclosures.
5. **[[Ciclo de Inversión en IA — Modelo de las 5 Capas]]** — Framework conceptual del ciclo de inversión donde se enmarca este análisis.
6. **[[Análisis Dylan Patel y Pierre Ferragu — AI Infrastructure & Tokconomics]]** — Tesis de analistas sobre los cuellos de botella y pricing power en el sector.

---

> **Disclaimer:** Esto no es una recomendación de compra o venta. Es un análisis estructural del producto para que puedas tomar una decisión informada. Los CEFs con prima sobre NAV tienen riesgos específicos que no aparecen en los análisis tradicionales de acciones.
>
> **Última actualización:** 24 junio 2026
> **Tags:** #dxyz #destinytech100 #cef #privateequity #venturecapital #spacex #anthropic #openai #ia #inversión #nav #prima-descuento
