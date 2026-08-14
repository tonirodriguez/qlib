# Análisis: Dylan Patel (SemiAnalysis) y Pierre Ferragu (New Street Research)

> **Propósito:** Recopilación extendida de las tesis de inversión y marcos analíticos de dos de los analistas más influyentes en el sector de infraestructura de IA. Ambos proporcionan lentes complementarias sobre los cuellos de botella, dinámicas de pricing power y flujos de capital en la cadena vertical de IA.
>
> **Actualización:** Junio 2026

---

## Índice

1. [Dylan Patel — SemiAnalysis: Tokconomics y Cuellos de Botella Físicos](#1-dylan-patel--semianalysis-tokconomics-y-cuellos-de-botella-físicos)
   - [1.1 Contexto y Metodología](#11-contexto-y-metodología)
   - [1.2 Thesis #1: Márgenes de Inferencia en Frontier Labs](#12-thesis-1-márgenes-de-inferencia-en-frontier-labs)
   - [1.3 Thesis #2: Compresión de Ciclos de Producto](#13-thesis-2-compresión-de-ciclos-de-producto)
   - [1.4 Thesis #3: Memoria (HBM/DRAM) como Cuello de Botella Central](#14-thesis-3-memoria-hbmdram-como-cuello-de-botella-central)
   - [1.5 Thesis #4: TSMC Super-Cycle y WFE Whiplash](#15-thesis-4-tsmc-super-cycle-y-wfe-whiplash)
   - [1.6 Thesis #5: El Cuello de Botella Paralelo en CPUs (RL + Agentic)](#16-thesis-5-el-cuello-de-botella-paralelo-en-cpus-rl--agentic)
   - [1.7 Thesis #6: Fragmentación de Model Tiers](#17-thesis-6-fragmentación-de-model-tiers)
   - [1.8 Thesis #7: El S-Curve del Gasto en Tokens](#18-thesis-7-el-s-curve-del-gasto-en-tokens)
   - [1.9 Síntesis Patel: Mapa de Inversión](#19-síntesis-patel-mapa-de-inversión)
2. [Pierre Ferragu — New Street Research: Visibilidad Extendida y Pricing Power](#2-pierre-ferragu--new-street-research-visibilidad-extendida-y-pricing-power)
   - [2.1 Contexto y Cobertura](#21-contexto-y-cobertura)
   - [2.2 Thesis #1: NVDA Run Rate de $1T — Best Ideas List 2026](#22-thesis-1-nvda-run-rate-de-1t--best-ideas-list-2026)
   - [2.3 Thesis #2: Hyperscalers Emitiendo Equity No es Señal de Debilidad](#23-thesis-2-hyperscalers-emitiendo-equity-no-es-señal-de-debilidad)
   - [2.4 Thesis #3: Broadcom y la Validación de ASICs Custom hasta 2028](#24-thesis-3-broadcom-y-la-validación-de-asics-custom-hasta-2028)
   - [2.5 Thesis #4: Momento Agentic y CPU Demand](#25-thesis-4-momento-agentic-y-cpu-demand)
   - [2.6 Thesis #5: Cuellos de Botella Generalizados en la Cadena](#26-thesis-5-cuellos-de-botella-generalizados-en-la-cadena)
   - [2.7 Cobertura completa de Ferragu: Ratings y Tickers](#27-cobertura-completa-de-ferragu-ratings-y-tickers)
   - [2.8 Síntesis Ferragu: Mapa de Inversión](#28-síntesis-ferragu-mapa-de-inversión)
3. [Síntesis Cruzada: Dónde Coinciden, Dónde Difieren](#3-síntesis-cruzada-dónde-coinciden-dónde-difieren)
4. [Bibliografía y Fuentes](#4-bibliografía-y-fuentes)

---

## 1. Dylan Patel — SemiAnalysis: Tokconomics y Cuellos de Botella Físicos

### 1.1 Contexto y Metodología

Dylan Patel es fundador de **SemiAnalysis**, una firma de investigación que se ha convertido en referencia obligada para entender la economía de los semiconductores y la infraestructura de IA. Su enfoque combina:

- **Ingeniería inversa de costes de fabricación:** Modelan el coste real por wafer, por chip y por bit en cada nodo y cada tipo de memoria.
- **Seguimiento granular de la cadena de suministro:** Desde obleas de silicio hasta empaquetado CoWoS, rastrean cuellos de botella físicos.
- **"Tokconomics":** Reencuadran la economía de la IA en torno a la oferta y demanda de *tokens* — la unidad de output de los modelos. La pregunta clave no es "cuántas GPUs se venden" sino "cuántos tokens se pueden generar y a qué precio".

**Entrevista de referencia:** Abril 2026 con Patrick O'Shaughnessy en *Invest Like The Best*. Título: *"The Supply and Demand of AI Tokens"*.

> **Fuente principal:** [The Supply and Demand of AI Tokens | Dylan Patel Interview - YouTube](https://www.youtube.com/watch?v=LF3aUIM57uw)
>
> **Resumen detallado:** [AlphaAbstract — Dylan Patel AI Token Supply & Demand Investment Thesis](https://alphabstract.com/summaries/dylan-patel/dylan_patel_ai_token_supply_demand_investment_thesis)

---

### 1.2 Thesis #1: Márgenes de Inferencia en Frontier Labs

**Argumento central:** Los frontier labs (OpenAI, Anthropic) tienen márgenes brutos de inferencia mucho más altos de lo que el mercado descuenta. El gasto en tokens de las empresas está creciendo exponencialmente, pero el coste del cómputo de inferencia no escala al mismo ritmo debido al racionamiento de capacidad y a los contratos enterprise.

**Evidencia empírica:**

1. **SemiAnalysis como caso de estudio:**
   - Su propia cuenta enterprise de Claude escaló a un **run-rate de ~$7M/año** en tokens.
   - Esto representa ~25% de su gasto total en salarios (~$25M).
   - Patel lo usa como proxy de lo que las empresas enterprise van a enfrentar — el gasto en tokens como porcentaje de nómina se dispara.

2. **Márgenes de Anthropic (reconstrucción de Patel):**

   > **📘 ¿Qué es ARR?**
   >
   > **ARR = Annual Recurring Revenue** (Ingreso Recurrente Anual). Es el **run-rate de ingresos normalizado a 12 meses** basado en el momento actual. No son los ingresos reales del último año, sino una proyección.
   >
   > - Si Anthropic factura ~$3B este mes → **~$36B ARR** (3 × 12).
   > - Si el mes pasado facturaba $2.5B → ~$30B ARR.
   > - La métrica captura **momentum** y permite comparar empresas en distintas fases de crecimiento.
   > - Se usa universalmente en SaaS y suscripciones. Una empresa con $10B ARR creciendo al 300% anual vale más que una con $50B ARR creciendo al 10%.
   > - Cuando Patel dice que Anthropic añade ~$10B ARR en incrementos mensuales, significa que cada mes su run-rate sube ~$10B — un crecimiento vertiginoso.

   - Ingresos escalando de ~$9B → $35-45B ARR (según su tracking).
   - Mes a mes, Patel afirma que Anthropic añade aproximadamente ~$10B ARR en incrementos mensuales.
   - El cómputo no escala proporcionalmente porque el throughput de inferencia está racionado (capacity constraints).
   - **Estimación de márgenes brutos: ≥72% hoy**, frente a ~30-40% reportado en documentos filtrados de principios de año.
   - Fórmula mental: incluso si todo el cómputo incremental se destinase a inferencia (y nada a I+D), los márgenes estarían en ~72%. Si parte fue a I+D (lo habitual), los márgenes reales son aún mayores.

3. **La dinámica del racionamiento:**
   - Los labs racionan throughput (rate limits, tiering de SKUs).
   - Las empresas enterprise pagan precios premium por acceso garantizado.
   - Esto funciona como **pricing power en una escasez de commodity física** — los labs capturan el valor del token muy por encima de su coste marginal.

**Implicación de inversión:**
- Larga en los frontier labs privados (Anthropic es la más mencionada).
- Larga en los "silicon lessors" que se benefician del rent-seeking: Oracle (ORCL), CoreWeave (CRWV), Microsoft Azure, Amazon AWS con Trainium.
- El revenue de los labs puede superar las expectativas de los "GPU bears" que solo miran el sticker price de los chips.

---

### 1.3 Thesis #2: Compresión de Ciclos de Producto

**Argumento central:** "Las ideas son baratas, la ejecución es fácil (aunque cara)". El coste de implementación de nuevas ideas ha colapsado, lo que comprime los ciclos de desarrollo de producto y acelera el ritmo de innovación.

**Mecánica:**
- **Antes:** Ciclo de producto de ~6 meses: idea → implementación → test → release.
- **Ahora:** Ciclo de ~2 meses. El código generado por IA acelera la implementación. Los equipos se reducen. Las iteraciones son más rápidas.
- Patel afirma que su propio equipo usa agentes de código para ingeniería inversa de chips, mapping de grids eléctricos nacionales — cosas que antes requerían equipos de 100 personas en productos legacy de hace una década.

**La trampa de los "AI wrapper":**
- Las startups genéricas de "AI wrapper" se quedan sin acceso a tokens frontier (son demasiado caros para ellas).
- Los ganadores son los que tienen **capital + distribución + customer lock-in**.
- **Paradoja:** La IA hace la ejecución más fácil, pero la barrera de entrada sube porque el coste de los tokens frontier escala con la demanda enterprise.

**Implicación de inversión:**
- Larga en Microsoft (MSFT) — ecosistema Copilot/GitHub como el distribuidor más potente.
- Larga en Amazon (AMZN) — Bedrock + reach enterprise.
- Proveedores de datos/API de alta calidad que alimentan workflows de agentes.

---

### 1.4 Thesis #3: Memoria (HBM/DRAM) como Cuello de Botella Central

**Argumento central:** La memoria (HBM + DRAM) es el cuello de botella *más largo y profundo* de toda la cadena de suministro de IA. Patel cree que los ASP de DRAM pueden **duplicarse o triplicarse desde los niveles actuales**.

**¿Por qué?**
1. **Las fabs de memoria crecen low-mid single digits anual.** No hay capacidad de expansión rápida.
2. **Añadir capacidad significativa requiere hasta 2027-28** incluso con respuestas urgentes de los fabricantes.
3. **Para conseguir más capacidad de HBM, los fabricantes tienen que robar capacidad de DRAM de consumo** — eso requiere destrucción de demanda vía precio, no racionamiento.
4. **El HBM es el input más crítico para una GPU de IA.** Sin HBM, la GPU no funciona. NVIDIA, AMD y los ASICs compiten por el mismo suministro limitado.

**Cita textual de Patel:**
> "DRAM will double or triple from here still because that's how much capacity is required and they have to steal capacity from somewhere else."

**El error del consenso:**
- El consenso dice "ya estamos largos de memoria" porque los precios han subido mucho.
- Pero Patel argumenta que el mercado subestima los **años necesarios para convertir fabs greenfield** — la tightness se extiende a través de todo el ramp actual.

**Implicación de inversión:**
- Larga en Micron (MU).
- Larga en SK Hynix (HXSCF, OTC).
- Samsung (temática más diluida por su conglomerado, pero exposición significativa).
- Cualquier fund de semis que sobrepondere memoria sobre lógica.

---

### 1.5 Thesis #4: TSMC Super-Cycle y WFE Whiplash

**Argumento central:** TSMC está en camino de gastar ~$100B anuales en CapEx alrededor de 2028. Esto crea un super-ciclo para los fabricantes de WFE (Wafer Fabrication Equipment).

**Los números:**
- TSMC guió ~$56B de CapEx para el año fiscal actual (2025/26).
- SemiAnalysis rastrea ~$57.4B en gasto real desde enero.
- La trayectoria apunta a ~$100B/año en ~2028.
- Esto implica una aceleración significativa en el gasto en herramientas (ASML, AMAT, LRCX) y componentes downstream.

**El "whiplash":**
- La elasticidad de la oferta de WFE es baja — lleva años cualificar nuevas herramientas.
- Los cuellos de botella se mueven de la litografía (ASML EUV) al empaquetado (CoWoS) a los subcomponentes (láseres, vidrio, laminados de cobre).
- Patel menciona específicamente a **MKS Instruments (MKSI)** como ejemplo de vendor de componentes que se beneficia de forma no obvia.

**Implicación de inversión:**
- Larga en TSMC (TSM) — el monolito.
- Larga en ASML — monopolio de litografía EUV.
- Larga en Applied Materials (AMAT) y Lam Research (LRCX) — WFE general.
- Larga en MKSI y otros vendors de subcomponentes.

---

### 1.6 Thesis #5: El Cuello de Botella Paralelo en CPUs (RL + Agentic)

**Argumento central:** El entrenamiento con Reinforcement Learning (RL) y el despliegue de agentes autónomos crean una demanda masiva de **CPUs** que el mercado está ignorando — todo el mundo mira las GPUs.

**¿Por qué?**
1. **Las environments de RL corren en CPU:** Simulaciones de física, edición de archivos, CAD hooks, entornos de juego — todo eso se ejecuta en CPUs mientras la GPU solo hace el forward/backward pass del modelo.
2. **Las cadenas de agentes:** Cada paso de un agente implica orquestación, llamadas a herramientas, parsing de respuestas — todo en CPU.
3. **FPGAs por rack:** Patel menciona ~120 FPGAs por rack de IA de próxima generación para tareas de control y aceleración auxiliar.

**Cita textual de Patel:**
> "CPUs are completely sold out and demand is skyrocketing."

**Implicación de inversión:**
- Intel (INTC) — exposición masiva a CPU de servidor en un mercado apretado. Pero con sus propios problemas estructurales (foundry, productos de IA).
- Proveedores de FPGA temáticos — AMD/Xilinx, Lattice (LSCC), aunque la exposición limpia en USA es limitada.
- La sorpresa alcista para Intel si el mercado CPU se tensa más de lo esperado.

---

### 1.7 Thesis #6: Fragmentación de Model Tiers

**Argumento central:** El mercado de modelos se va a fragmentar en tiers claros:
- **Frontier labs:** Capturan el premium máximo (enterprise, defensa, alta fiabilidad).
- **Modelos abiertos (Llama, Mistral, Qwen):** Se convierten en infraestructura básica — commodity con márgenes ajustados.
- **Modelos especializados:** Pequeños, fine-tuned para tareas específicas (SLMs como Phi, Gemma).

**Dinámica:**
- Los frontier labs compiten por ser el mejor modelo general; los labs que no lleguen al top 3 se quedan sin pricing power.
- Meta y open-source presionan hacia la commoditización desde abajo.
- El valor se desplaza de "tener el mejor modelo" a "tener los mejores datos + distribución".

**Implicación de inversión:**
- No invertir en modelos a secas sin datos propietarios.
- El mejor modelo abierto + tus datos > el mejor modelo cerrado sin contexto.
- Meta (META) como jugador infravalorado por su estrategia open-source + escala de datos.

---

### 1.8 Thesis #7: El S-Curve del Gasto en Tokens

**Argumento central:** El gasto enterprise en tokens sigue una curva en S, no lineal. SemiAnalysis lo vive internamente — pasaron de $0 a $7M/año en tokens en ~18 meses, y esperan que siga acelerando.

**Implicaciones:**
- Las proyecciones lineales de demanda de cómputo infraestiman la realidad.
- Cada "killer app" de IA (code generation primero, luego customer service, luego agentic workflows) añade un nuevo tramo de la S-curve.
- El gasto en inferencia eventualmente **duplica o triplica** el gasto en training, porque los modelos se usan continuamente después de entrenados.

---

### 1.9 Síntesis Patel: Mapa de Inversión

| Thesis | Ticker/Activo | Tipo | Riesgo principal |
|--------|--------------|------|------------------|
| Márgenes frontier labs | Anthropic (privado), ORCL, CRWV | Crecimiento | Labs no logran escalar revenue |
| Compresión de ciclos | MSFT, AMZN | Quality | Regulación antitrust |
| Memoria (HBM/DRAM) | MU, SK Hynix, Samsung | Cíclico con sesgo alcista | Peak DRAM pricing |
| TSMC super-cycle | TSM, ASML, AMAT, LRCX, MKSI | Crecimiento/Equipment | Geopolítica Taiwan |
| Cuello de botella CPU | INTC, AMD (FPGA) | Value/Contrarian | INTC no ejecuta |
| Fragmentación de tiers | META | Crecimiento | Regulación, ciclo publicitario |
| S-Curve de tokens | Todo el sector (temática) | Macro | Burbuja de infra sin retorno |

---

## 2. Pierre Ferragu — New Street Research: Visibilidad Extendida y Pricing Power

### 2.1 Contexto y Cobertura

Pierre Ferragu es **Global Head of Technology Infrastructure** en New Street Research. Antes de New Street, pasó más de 10 años en Bernstein cubriendo Telecom Equipment, Data Networking, Cybersecurity y Semiconductores. Ha sido reconocido múltiples años como el analista #1 en encuestas de Institutional Investor, Extel y Thomson Reuters.

**Formación:** Telecom y Computer Sciences por Centrale-Supélec; Sociología por Sciences-Po (París).

**Cobertura principal (2026):**
- **Compra (Buy):** AMD, Arista Networks, Broadcom, Grab, Infineon, Mobileye, Nokia, NVIDIA, Palo Alto Networks, Soitec, Tesla, TSMC, Uber, BE Semiconductor, Microsoft, Rocket Lab.
- **Neutral:** Apple, Applied Materials, ASML, Cisco, Ericsson, Intel, Micron, SoftBank, Arm, KLA, Tokyo Electron, Lam Research.
- **Venta (Sell):** Planet Labs.

> **Fuente principal:** [New Street Research — Pierre Ferragu](https://www.newstreetresearch.com/team/pierre-ferragu/)

---

### 2.2 Thesis #1: NVDA Run Rate de $1T — Best Ideas List 2026

**Fecha:** 19 marzo 2026, tras GTC.

**El detonante:** Jensen Huang dijo en GTC 2026: *"Veo, a través de 2027, al menos $1 trillion"* en órdenes acumuladas.

**El contraste de Ferragu:**
- En GTC Washington (octubre 2025), Huang dijo que tenía "visibilidad de $0.5T" en demanda acumulada de Blackwell y Rubin temprano a través de 2026.
- Huang *no* dijo que la visibilidad se duplicara en marzo 2026 porque las órdenes acumuladas se consumieran. **NVDA añadió $500B en visibilidad de órdenes en solo 5 meses.**

**La implicación:**
- El run rate de órdenes hoy es **más de $1T por año**, no acumulado a 2027.
- Si este run rate se mantiene, NVDA podría estar operando a un **run rate de revenue de ~$1T anual para finales de 2027**.
- A esos niveles de revenue, NVDA podría generar **> $20 EPS**.
- La acción cotiza a **<10x ese EPS potencial**.

**La decisión:** New Street añade NVDA a su **Best Ideas List para 2026**, junto a AMD y TSMC.

**El contexto de precio:** NVDA cotiza a ~$180 (marzo 2026), YTD -3.3%. Ferragu mantiene precio objetivo **$340**.

**Refuerzo externo:** Dan Ives (Wedbush) respalda independientemente — ve camino a $6T de market cap para 2027, citando ratio demanda/oferta de 12:1 para los chips de NVIDIA.

> **Fuente:** [BigGo — Nvidia's $1 Trillion Order Run Rate Prompts New Street to Add Stock to 2026 Best Ideas List](https://finance.biggo.com/news/yT1wBp0BNZYCTTDvYioV)
>
> **Fuente original:** New Street Research, 19 marzo 2026.

---

### 2.3 Thesis #2: Hyperscalers Emitiendo Equity No es Señal de Debilidad

**Fecha:** 12 junio 2026.

**Título del research:** *"How to interpret hyperscalers raising equity? Here is our perspective (or is Wall Street in denial?)"*

**El problema de percepción:**
- Los hyperscalers (MSFT, GOOG, AMZN, META) están emitiendo deuda y equity para financiar CapEx récord.
- El mercado lo interpreta como: "están quemando caja, la IA no genera retorno, es una burbuja".
- Ferragu argumenta lo contrario.

**La tesis de Ferragu:**
- **El CapEx de IA tiene ROI demostrable.** Las emisiones de deuda/equity no son para sobrevivir, sino para **acelerar** una inversión que ya ha probado su retorno.
- El revenue de aplicaciones de IA (Copilot, Gemini, AWS Bedrock, META AI) ya está fluyendo — y con márgenes altos.
- La emisión de equity es una señal de **confianza en el forward ROI**, no de desesperación.
- Los hyperscalers están integrados verticalmente: cloud + modelos + apps. Cualquier sobreinversión en infra se amortiza con el revenue de aplicaciones.

**Implicación para el framework del ciclo:**
- Ferragu valida empíricamente el modelo de "espiral ascendente": el revenue de apps retroalimenta el CapEx de infra.
- No es una burbuja si el ROI está demostrado — es una **inversión racional en un cuello de botella**.
- La emisión de equity es la prueba de que los hyperscalers **se toman en serio la oportunidad** y no quieren dejar capacidad sin cubrir.

> **Fuente:** New Street Research, 12 junio 2026 (report behind paywall, título y tesis inferidas de metadatos públicos).

---

### 2.4 Thesis #3: Broadcom y la Validación de ASICs Custom hasta 2028

**Fecha:** 4 junio 2026.

**Título del research:** *"Broadcom 2FQ26: Visibility on AI demand extending into 2028. Buy, $600 TP."*

**La tesis:**
- Broadcom es el fabricante de ASICs custom más relevante fuera de NVIDIA — sus chips alimentan TPUs de Google, Trainium de Amazon, y otros proyectos de hyperscalers.
- Ferragu ve **visibilidad de demanda AI extendiéndose hasta 2028**, lo que valida que el ciclo de CapEx no es un "one-time spend" sino estructural.
- Precio objetivo: **$600**. Rating: **Buy**.

**Implicación para el sector:**
- La validación de ASICs custom hasta 2028 implica que los hyperscalers **no se fían solo de NVIDIA** a largo plazo — están construyendo su propio stack de silicio.
- Esto es bueno para Broadcom, bueno para la diversificación del ecosistema, pero introduce presión competitiva para NVIDIA en 2027+.

**Cobertura relacionada:**
- Socionext (6526 JP): Arming META — 22 junio 2026. Broadcom no es el único fabricante de ASICs; Socionext está armando a META con chips custom.
- Compeq (2313 TT): See Ya Mobile, Hello LEO & DC — 23 junio 2026. Los fabricantes de PCBs se están moviendo de móvil a datacenter y LEO satellites.

> **Fuente:** New Street Research, 4 junio 2026.

---

### 2.5 Thesis #4: Momento Agentic y CPU Demand

**Fecha:** 9-18 junio 2026.

**Título del research:** *"Bible 1Q26 - Hyperscale & Cloud: visibility improving; agentic AI drives CPU demand; supply constraints across the board."* (9 junio, con Antoine Chkaiban).

*"The Tech Infrastructure Quarterly Bible 1Q26"* (18 junio 2026).

**La tesis:**
- La visibilidad de demanda AI está mejorando significativamente (coincidiendo con Patel: S-curve, no lineal).
- La **IA agentic** (agentes autónomos, cadenas de agentes) está disparando la demanda de **CPUs de servidor** aparte de GPUs.
- Hay **cuellos de botella en toda la cadena de suministro** — no solo en GPUs y memoria, sino también en networking, packaging, y energía.

**Por qué agentic IA consume CPU (refuerza a Patel):**
- Los agentes orquestan múltiples llamadas a modelos, ejecutan herramientas, mantienen estado, gestionan memoria de contexto.
- Esto requiere CPU servers dedicados para la capa de orquestación.
- El ratio CPUs servidor / GPUs acel cluster sube con cada wave de agentic deployment.

> **Fuente:** New Street Research, 9 y 18 junio 2026.

---

### 2.6 Thesis #5: Cuellos de Botella Generalizados en la Cadena

**Argumento transversal en toda la cobertura de Ferragu (2025-2026):**

Ferragu ve un **entorno de cuellos de botella generalizados** que da pricing power a los proveedores en toda la cadena — desde el silicio hasta el datacenter.

**Cuellos de botella identificados:**

| Capa | Cuello de botella | Quién tiene pricing power |
|------|-------------------|--------------------------|
| Chips | Fabricación (CoWoS, EUV) | TSMC, ASML |
| Chips | HBM/DRAM | SK Hynix, Samsung, Micron |
| Chips | ASICs custom | Broadcom |
| Chips | CPU servidor | Intel (por tightness, no por mérito) |
| Infra | Networking 800G/1.6T | Arista (ANET), Broadcom |
| Infra | Refrigeración líquida | Vertiv (VRT) |
| Infra | Construcción de datacenters | DLR, EQIX |
| Energy | Nuclear + gas | CEG, VST |
| Supply chain | Componentes sub-fab | MKSI, entrantes |

Ferragu mantiene **Buy** en la mayoría de estos nombres, lo que refleja su convicción de que la demanda no es transitoria.

---

### 2.7 Cobertura Completa de Ferragu: Ratings y Tickers

**Buy (Compra):**
| Ticker | Compañía | Nota |
|--------|----------|------|
| AMD | Advanced Micro Devices | Competencia en GPUs, MI400 en camino |
| ANET | Arista Networks | Networking 800G para clústeres masivos |
| AVGO | Broadcom | ASICs custom hasta 2028, TP $600 |
| GRAB | Grab Holdings | No-IA, movilidad/SEA |
| IFNNY | Infineon | Semis de potencia |
| MBLY | Mobileye | Conducción autónoma |
| NOK | Nokia | No-IA, infraestructura telco |
| NVDA | NVIDIA | Best Ideas List 2026, TP $340 |
| PANW | Palo Alto Networks | Ciberseguridad |
| SOIEF | Soitec | Sustratos SOI para semis |
| TSLA | Tesla | Vehículos + Optimus |
| TSM | TSMC | Foundry monolito, super-cycle |
| UBER | Uber | No-IA, movilidad |
| BESIY | BE Semiconductor | Equipment de packaging |
| MSFT | Microsoft | Ecosistema Copilot + Azure |
| RKLB | Rocket Lab | LEO satellites (cobertura dual con Space) |

**Neutral:**
| Ticker | Compañía |
|--------|----------|
| AAPL | Apple |
| AMAT | Applied Materials |
| ASML | ASML Holding |
| CSCO | Cisco |
| ERIC | Ericsson |
| INTC | Intel |
| MU | Micron |
| SFTBY | SoftBank |
| ARM | Arm Holdings |
| KLAC | KLA Corp |
| TOELY | Tokyo Electron |
| LRCX | Lam Research |

**Sell (Venta):**
| Ticker | Compañía |
|--------|----------|
| PL | Planet Labs |

---

### 2.8 Síntesis Ferragu: Mapa de Inversión

Ferragu construye un **portafolio de infraestructura de IA** con tres clusters:

**Cluster 1 — Habilitadores directos (Best Ideas):**
- NVDA, TSM, AVGO (ASICs), AMD — los que fabrican el cómputo.
- ANET (networking), MSFT (integrador cloud + apps).

**Cluster 2 — Cadena extendida:**
- BESIY, SOIEF (packaging + sustratos).
- INFN, NOK (no-IA, estables).
- PANW (seguridad para IA enterprise).

**Cluster 3 — Apuestas complementarias:**
- TSLA (Optimus como eventual consumidor de cómputo).
- RKLB (LEO satellites como mercado alternativo de chips).
- UBER, GRAB (movilidad, no-IA).

**Venta o neutral en:**
- PL (no hay demanda de satélites de imágenes que compita con IA).
- AAPL (neutral — no tiene exposición directa a IA infra).
- INTC, MU, LRCX, AMAT, ASML (neutral — buenos pero ya priced in o con riesgos geopolíticos).

---

## 3. Síntesis Cruzada: Dónde Coinciden, Dónde Difieren

### Coincidencias

| Tema | Patel | Ferragu |
|------|-------|---------|
| **Cuellos de botella generalizados** | Los físicos (fab, memoria, energía) son el driver principal | Supply constraints across the board |
| **Agentic IA → CPU demand** | RL environments corren en CPU, FPGAs por rack | "Agentic AI drives CPU demand" (Bible 1Q26) |
| **NVDA pricing power** | Larga en NVDA, los "silicon lessors" | NVDA en Best Ideas List, TP $340 |
| **TSMC super-cycle** | $100B CapEx ~2028 | Buy en TSM |
| **El gasto de hyperscalers es racional** | El revenue de apps retroalimenta el CapEx | Equity raising es señal de confianza, no desesperación |
| **HBM/DRAM es cuello de botella** | "DRAM ASP se duplica o triplica" | Neutral en MU y Samsung (más cauto que Patel) |

### Diferencias

| Tema | Patel | Ferragu |
|------|-------|---------|
| **MU / HBM** | Largo agresivo — "multiple doubles ahead" | Neutral — riesgo de peak pricing o sobrecompra |
| **INTC** | Largo temático (CPU tightness) | Neutral — problemas estructurales de foundry y productos IA |
| **Tono general** | Más agresivo, más "frontier" | Más institucional, cartera diversificada, ratings conservadores |
| **Horizonte de visibilidad** | 2027-2028 | 2028+ (Broadcom like), pero más escalonado |
| **Riesgo geopolítico Taiwan** | Mencionado pero no central en las tesis | Neutral en ASML, AMAT, LRCX → sugiere preocupación implícita |

### El marco unificado

Ferragu proporciona la **validación institucional** del framework del ciclo de inversión de IA. Patel proporciona la **visión granula** de la oferta (semis, memoria, packaging). Juntos:

```
Patel: "¿Cuántos tokens se pueden producir y a qué coste?"
Ferragu: "¿Quién captura el valor y durante cuánto tiempo?"

Respuesta conjunta: Los cuellos de botella físicos dan pricing power 
a los habilitadores (NVDA, TSM, AVGO, MU), pero los integradores 
verticales (MSFT, AMZN) capturan el valor recurrente.
```

Este análisis detallado de Patel y Ferragu se integra dentro del framework más amplio de [[Ciclo de Inversión en IA — Modelo de las 5 Capas]], que describe las 3 olas del ciclo (Supply-Push, Demand-Pull, Madurez) y cómo el flujo de capital y valor viaja por la cadena vertical Energy → Chips → Infra → Models → Applications.

**Contrapunto obligatorio:** La visión opuesta a Patel y Ferragu la representa [[Análisis Jim Covello — Goldman Sachs Tesis Bear IA|Jim Covello (Goldman Sachs)]], que argumenta que el ROI enterprise nunca llegará y que el CapEx actual es una burbuja impulsada por FOMO. Ver el análisis completo de su tesis bear para el balance.

---

## 4. Bibliografía y Fuentes

### Dylan Patel — SemiAnalysis

1. **[The Supply and Demand of AI Tokens | Dylan Patel Interview - YouTube](https://www.youtube.com/watch?v=LF3aUIM57uw)**
   - Patrick O'Shaughnessy, *Invest Like The Best*, abril 2026.
   - Entrevista principal de la que se extraen la mayoría de las tesis.

2. **[AlphaAbstract — Dylan Patel AI Token Supply & Demand Investment Thesis](https://alphabstract.com/summaries/dylan-patel/dylan_patel_ai_token_supply_demand_investment_thesis)**
   - Resumen detallado y estructurado de la entrevista anterior.

3. **[SemiAnalysis Newsletter (Substack)](https://newsletter.semianalysis.com/)**
   - Publicación recurrente con análisis detallados de semis, IA y energía. Acceso parcial gratuito, análisis profundos bajo suscripción.

4. **[Dealroom — $7M/year in tokens and anti-AI protests](https://app.dealroom.co/news/note/7m-year-in-tokens-and-anti-ai-protests-on-the-horizon-dylan-patel-on-the-ai-supply-crunch)**
   - Resumen adicional de la entrevista con Patel, abril 2026.

### Pierre Ferragu — New Street Research

1. **[New Street Research — Pierre Ferragu (Perfil)](https://www.newstreetresearch.com/team/pierre-ferragu/)**
   - Perfil profesional, cobertura completa y lista de research reports.

2. **[BigGo — Nvidia's $1 Trillion Order Run Rate Prompts New Street to Add Stock to 2026 Best Ideas List](https://finance.biggo.com/news/yT1wBp0BNZYCTTDvYioV)**
   - Resumen del research de Ferragu del 19 marzo 2026 tras GTC.
   - Fuente original: New Street Research research note (paywall).

3. **New Street Research Reports (referenciados, paywall):**
   - *"How to interpret hyperscalers raising equity? Here is our perspective"* — 12 junio 2026.
   - *"Bible 1Q26 - Hyperscale & Cloud: visibility improving; agentic AI drives CPU demand"* — 9 junio 2026 (con Antoine Chkaiban).
   - *"Broadcom 2FQ26: Visibility on AI demand extending into 2028. Buy, $600 TP."* — 4 junio 2026.
   - *"The Tech Infrastructure Quarterly Bible 1Q26"* — 18 junio 2026.
   - *"Nvidia into PC? A $550m TAM for ARM"* — 2 junio 2026.
   - *"Socionext (6526 JP): Arming META"* — 22 junio 2026 (con Peter Vogel).
   - *"Besi capital markets day: Strong outlook"* — 19 junio 2026.
   - *"Arm model update. Downgrade to Neutral."* — 18 junio 2026.

4. **Bloomberg — AI Spending Spree Rattles Wall Street** (30 octubre 2025)
   - [Link al video](https://www.bloomberg.com/news/videos/2025-10-30/ai-spending-spree-rattles-wall-street-video) (paywall).
   - Ferragu entrevistado sobre el gasto en IA de big tech.

### Caso Práctico Relacionado

6. **[[Análisis DXYZ — Destiny Tech100 CEF Private Tech]]**
   - Análisis detallado de un vehículo de inversión que aplica la tesis de Patel sobre márgenes de frontier labs: su mayor posición es Anthropic (18.1%), seguida de SpaceX (14.4%) y OpenAI (5.7%). Ejemplo de cómo apostar por la capa Models del ciclo desde mercado público.

### Marco Conceptual Relacionado

5. **[[Ciclo de Inversión en IA — Modelo de las 5 Capas]]**
   - Framework conceptual donde se integran las tesis de Patel y Ferragu. Incluye notas técnicas sobre wafer, die, CoWoS y HBM. Es el mapa general; este documento es el análisis detallado de los analistas.

---

> **Última actualización:** 24 junio 2026
> **Tags:** #semianalysis #newstreetresearch #dylanpatel #pierreferragu #nvda #ia #inversión #hbm #tsmc #broadcom #hyperscalers #tokconomics #semiconductores
>
> **Ficha complementaria:** [[Análisis NVDA — NVIDIA Corporation]] — valoración actual, targets de analistas, escenarios de sensibilidad y opiniones detalladas.
