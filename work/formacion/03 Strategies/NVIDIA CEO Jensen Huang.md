# Five-Layer Cake de Jensen Huang (NVIDIA) — Guía Completa

**Fuente original:** [NVIDIA Blog — AI 5-Layer Cake](https://blogs.nvidia.com/blog/ai-5-layer-cake/)
**Origen en este vault:** Post de @BillBrooklyn10 en X ([enlace](https://x.com/BillBrooklyn10/status/2068697785424306319/video/1))
**Vinculado con:** [[03 Strategies/Bill Brooklyn]]
**Fecha:** 23 Jun 2026

---

## Introducción

El **Five-Layer Cake** es el framework de Jensen Huang (CEO de NVIDIA) para describir la cadena de valor completa de la Inteligencia Artificial. La tesis central es que la IA no es solo software — es un **sistema industrial completo** que va desde la generación de electricidad hasta las aplicaciones finales, y cada capa representa una oportunidad de inversión multimillonaria.

```
   🎯 Applications (Medicina, finanzas, defensa, conducción autónoma)
       ↑
   🧠 Models (LLMs, algoritmos, software de IA)
       ↑
   🏗️ Infrastructure (Datacenters, networking, fotónica, servidores)
       ↑
   💾 Chips (GPUs, CPUs, memoria, semiconductores)
       ↑
   ⚡ Energy (Electricidad, nuclear, cobre, refrigeración)
```

---

# ⚡ Capa 1: Energy (Energía)

## Qué es

La capa fundamental que alimenta las **AI Factories**. Jensen Huang describe los centros de datos de IA como "fábricas de inteligencia" que consumen tanta electricidad como ciudades enteras. Sin energía barata y abundante, la escala de IA está limitada.

## Por qué es crítica ahora

- Un datacenter de IA típico consume **50-100 MW** (equivalente a ~40,000 hogares)
- Los megadatacenters planificados para 2026-2028 requieren **1-5 GW** cada uno (equivalente a una central nuclear pequeña)
- Se estima que la IA consumirá **el 10% de la electricidad global** para 2030 (vs ~2-3% hoy)
- El cuello de botella ya no son los chips — es la **energía disponible** para alimentarlos

## Empresas clave de la watchlist en esta capa

### ☢️ Nuclear (OKLO)

**Oklo Inc** desarrolla **microreactores nucleares** (Advanced Fission) diseñados específicamente para alimentar datacenters de IA. Su propuesta de valor:

- Reactores de **15-50 MW** modulares, instalables junto al datacenter
- Diseño de **combustible reciclado** (usan residuos nucleares como combustible)
- **Sin reposición de combustible durante 20+ años**
- Acuerdos ya firmados con operadores de datacenters para suministro directo (behind-the-meter)

**Competidores fuera de la watchlist:** NuScale Power (SMR), Constellation Energy (nuclear tradicional), Talen Energy (planta nuclear + datacenter en Pennsylvania)

### 🥉 Cobre (FCX, SCCO, TECK)

El cobre es el **conductor eléctrico de todo el sistema**. Cada datacenter de IA necesita toneladas de cobre para:

- Cableado eléctrico de alta capacidad dentro del datacenter
- Sistemas de distribución de energía (PDUs, switchgear)
- Transformadores y subestaciones
- Refrigeración líquida (tuberías de cobre)
- Interconexiones de red (fibra óptica + cobre para alimentación)

**Freeport-McMoRan (FCX)** es el mayor productor público de cobre del mundo. Sus minas en EE. UU. (Arizona, Nuevo México) son estratégicas para el suministro nacional.

**Southern Copper (SCCO)** opera en Perú y México. Bajos costos de extracción, alta exposición a la demanda china y ahora también a IA.

**Teck Resources (TECK)** está pivotando hacia cobre (venta de su negocio de carbón). Su mina **QB2** en Chile es uno de los mayores proyectos de cobre nuevos del mundo.

### Otros actores en Energy (fuera de la watchlist)

- **Constellation Energy** (nuclear tradicional, acuerdos con AWS, Microsoft)
- **Vistra Corp** (energía para datacenters en Texas)
- **GE Vernova** (turbinas de gas para energía de respaldo)
- **Bloom Energy** (pilas de combustible para datacenters)

---

# 💾 Capa 2: Chips (Semiconductores)

## Qué es

El silicio que **computa la inteligencia**. Sin chips no hay IA. Es la capa donde NVIDIA domina, pero donde la competencia se está intensificando.

## Por qué es crítica ahora

- Los chips son el **cuello de botella físico** de la IA desde 2022
- Una GPU H100 de NVIDIA cuesta ~$25,000; una B200 ~$35,000
- Los hyperscalers (Microsoft, Google, Amazon, Meta) gastarán **>$200B** en 2026 solo en chips de IA
- La demanda está tan concentrada que NVIDIA tiene >80% del mercado de GPUs para IA

## Empresas clave de la watchlist

### 🟢 Memory (MU, SNDK, WDC, STX)

**Micron Technology (MU)** es el fabricante líder de **HBM (High Bandwidth Memory)** — la memoria ultrarrápida que va pegada a las GPUs de NVIDIA. Cada GPU H100 lleva 80 GB de HBM3; cada GPU B200 llevará 144 GB de HBM3E. Micron es el único proveedor de HBM3E además de Samsung y SK Hynix.

- **Qué compite:** HBM3E es el producto estrella — sin memoria de alta velocidad, las GPUs no pueden alimentarse de datos lo suficientemente rápido
- **Ventaja:** Micron tiene la tecnología más avanzada en HBM3E con 1β (1-beta) DRAM
- **Riesgo:** Dependencia extrema de NVIDIA y del ciclo de actualización de datacenters

**SanDisk (SNDK)** — recientemente escindida de Western Digital — se centra en **almacenamiento NAND flash** para datacenters de IA. El almacenamiento rápido es esencial para los pipelines de entrenamiento (datasets masivos) y para inferencia (modelos grandes que no caben en RAM).

**Western Digital (WDC)** y **Seagate (STX)** compiten en **HDD (discos duros) de alta capacidad** para almacenamiento masivo en frío de datos de entrenamiento, y también en SSDs empresariales. Seagate domina con su tecnología **HAMR** (Heat-Assisted Magnetic Recording) que permite discos de 30+ TB.

**Dinámica competitiva entre ellos:**
| Compañía | Producto clave | Cliente principal | Tendencia |
|----------|---------------|-------------------|-----------|
| MU | HBM3E DRAM | NVIDIA (directo) | 📈 Alta demanda, cuellos de botella |
| SNDK | NAND flash enterprise | Hyperscalers (MSFT, GOOG, AMZN) | 📈 IA impulsa almacenamiento rápido |
| WDC | HDD 30TB + SSD | Datacenters | 📉 IA favorece SSD/Flash sobre HDD |
| STX | HDD 30TB+ (HAMR) | Datacenters | 📉 Poco room para crecer; IA no es HDD-intensiva |

### 🔬 Semis generales (NVDA, AMD, ARM, INTC)

**NVIDIA (NVDA)** — el jugador dominante en **GPUs para IA**. Arquitecturas Hopper (H100), Blackwell (B200), Rubin (2026). Produce las CUDA cores que ejecutan el 95% del entrenamiento de modelos grandes. También fabrica chips de networking (NVLink, InfiniBand) y sistemas completos (DGX, HGX).

- **Cuota de mercado:** ~80-90% en GPUs para datacenter AI
- **Moat:** CUDA ecosystem + NVLink interconexión + años de optimización software-hardware
- **Amenaza:** Los hyperscalers están diseñando sus propios chips (Google TPU, Amazon Trainium, Microsoft Maia, Meta MTIA)

**AMD (AMD)** — el competidor más directo de NVIDIA. Sus GPUs **Instinct MI300X/MI400** compiten con las H100/B200. También fabrica CPUs **EPYC** (muy usadas en servidores de IA para tareas de pre/post-procesamiento).

- **Riesgo:** Ha perdido cuota consistentemente; sus GPUs tienen peor software stack (ROCm vs CUDA)
- **Oportunidad:** Si los hyperscalers quieren un segundo proveedor de GPUs, AMD es la opción natural

**Arm Holdings (ARM)** — diseña la **arquitectura de CPU** que usan prácticamente todos los smartphones del mundo, y cada vez más servidores. Los chips personalizados de los hyperscalers (Google TPU, Amazon Graviton, Microsoft Cobalt) usan arquitectura ARM.

- **Tesis de inversión:** Cada chip personalizado que un hyperscaler diseña para IA paga royalties a ARM
- **Crecimiento:** De ~0% a ~15% del mercado de servidores en 3 años gracias a chips de IA personalizados

**Intel (INTC)** — el fabricante tradicional de CPUs (Xeon) está perdiendo terreno rápidamente en IA:
- Sus GPUs **Gaudi** (adquiridas de Habana Labs) no han despegado
- Su negocio de **foundry** (fabricación para terceros) está en pérdidas
- Está perdiendo cuota de CPUs en datacenter frente a AMD y ARM
- **Tesis bajista:** La IA necesita GPUs, no CPUs, e Intel no tiene GPU competitiva. Su servicio de foundry necesita años para ser rentable.

**Dinámica competitiva:**
| Jugador | Producto IA | Posición | Amenaza principal |
|---------|------------|----------|-------------------|
| NVDA | GPUs H100/B200/Rubin | Dominante (80%+) | Chips personalizados de hyperscalers |
| AMD | Instinct MI300X | Segundo (5-10%) | Adopción lenta de ROCm |
| ARM | Arquitectura Neoverse | Base de chips custom | Que hyperscalers diseñen RISC-V propio |
| INTC | Gaudi + Xeon | Residual | Foundry caro + sin GPU competitiva |

---

# 🏗️ Capa 3: Infrastructure

## Qué es

El **entorno físico y de red** que une miles de chips en un superordenador funcional. Jensen Huang la llama "la nueva TI" — todo lo que está entre los chips y el software.

## Por qué es crítica ahora

- Un clúster de 100,000 GPUs necesita **redes de alta velocidad, refrigeración, energía, y espacio físico**
- La infraestructura es el **segundo gasto más grande** después de los chips (~40-60% del coste total de un datacenter de IA)
- La **latencia de red** entre GPUs es a menudo el cuello de botella real del entrenamiento (no los propios chips)
- La fotónica (fibra óptica) está reemplazando al cobre en interconexiones de datacenters

## Subcapas y empresas

### 🌐 Networking (AVGO, MRVL, CRDO)

**Broadcom (AVGO)** es el líder en **chips de networking para datacenters**. Fabrica los **switches de red** (Tomahawk, Jericho, Trident) que conectan miles de GPUs en un clúster. También diseña chips personalizados (ASICs) para hyperscalers (Google TPU, Meta MTIA).

- **Qué compite:** Todo el tráfico de red dentro y entre datacenters de IA — switches Ethernet de alta velocidad (800G, 1.6T)
- **Ventaja:** Virtualmente no tiene competencia en switches de datacenter de alta capacidad (desplazó a Cisco en este nicho)
- **Riesgo:** Concentración excesiva en dos clientes (Google, Meta) para sus chips personalizados

**Marvell Technology (MRVL)** se centra en:
- **DPUs (Data Processing Units):** chips que descargan procesos de red de las CPUs en datacenters
- **Connectivity:** chips para interconexión de datacenters (DCI)
- **Almacenamiento:** controladores SSD empresariales

**Credo Technology Group (CRDO)** es un jugador puro de **conectividad de alta velocidad** (800G, 1.6T Ethernet). Fabrica:
- **Retimers / line cards** para switches de red
- **Active Electrical Cables (AEC)** para conectar GPUs dentro del rack
- **Chips PHY** (Physical Layer) para transmisión de datos a alta velocidad

**Dinámica competitiva en Networking:**
| Ticker | Nicho | Por qué IA lo impulsa | Competidores |
|--------|-------|----------------------|-------------|
| AVGO | Switches ASIC de datacenter | Cada clúster de GPUs necesita switches | Cisco, Huawei (China) |
| MRVL | DPUs + conectividad | Descarga de red en clústeres masivos | Intel (Mount Evans), NVIDIA (BlueField) |
| CRDO | AECs + retimers 800G/1.6T | Interconexión entre GPUs a alta velocidad | Spectra7, Macom |

### 💡 Photonics (AAOI, LITE, COHR, NVTS, GLW)

La fotónica es la capa que permite que la luz, no la electricidad, transporte datos dentro del datacenter. La interconexión óptica es crítica cuando tienes decenas de miles de GPUs que necesitan comunicarse sin latencia.

**Applied Optoelectronics (AAOI)** fabrica:
- **Láseres** para transmisión óptica de datos (Ethernet 400G/800G)
- **Componentes fotónicos** para interconexión de datacenters

**Lumentum Holdings (LITE)** es el mayor fabricante de **láseres de alta potencia** para comunicaciones ópticas y fotónica de silicio.

**Coherent Corp (COHR)** produce **componentes fotónicos** (moduladores, amplificadores, detectores). También fabrica equipos de soldadura láser para la fabricación de chips.

**Navitas Semiconductor (NVTS)** no es fotónica pura — fabrica chips de **GaN (nitruro de galio)** para **gestión de energía** en datacenters. Los GaN son más eficientes que los transistores de silicio tradicionales, reduciendo el consumo energético y el calor generado.

**Corning (GLW)** es el fabricante global de **fibra óptica** (imagina: cada datacenter de IA necesita kilómetros de fibra para conectar GPUs, racks, y edificios).

### 🏗️ Infrastructure de servidores (DELL, SMCI)

**Dell Technologies (DELL)** y **Super Micro Computer (SMCI)** fabrican los **servidores** que alojan las GPUs de NVIDIA.

**Dell:** Líder en servidores empresariales (PowerEdge). Su negocio tradicional es el mercado enterprise. En IA, ensambla y vende servidores NVIDIA-certificados (Dell PowerEdge XE9680). Crecimiento lento pero estable.

**Super Micro:** Se ha convertido en el **campeón de los servidores de IA**. Su modelo "build-to-order" y su capacidad para integrar directamente las GPUs de NVIDIA le han dado una ventaja enorme. SMCI crece al ~100% anual en ingresos.

**Diferencia clave:**
| Aspecto | Dell | Super Micro |
|---------|------|-------------|
| Velocidad de entrega | 4-8 semanas (pedido estándar) | 2-3 semanas (optimizado para NVIDIA) |
| Personalización | Media | Alta (configuración directa de GPU + red + refrigeración) |
| Clientes | Enterprise tradicional | Hyperscalers + startups de IA |
| Margen | 25-30% | 10-15% (volumen por precio) |
| Crecimiento | +5-10% anual | +50-100% anual |

### 🏢 Data Centers (IREN, CIFR, APLD, NBIS)

**Iris Energy (IREN)** empezó minando Bitcoin y ha pivotado hacia **HPC/AI Cloud**. Tiene capacidad eléctrica contratada (más de 500 MW) con acceso directo a energía. Su ventaja es que ya tiene la infraestructura eléctrica y de refrigeración — están reconvirtiendo miners de Bitcoin en GPUs de NVIDIA.

**Cipher Mining (CIFR)** — mismo perfil: minero de Bitcoin con infraestructura eléctrica lista, pivotando hacia IA/HPC. Más pequeño que IREN.

**Applied Digital (APLD)** — opera datacenters de IA llave en mano (no son reconvertidos de mining). Construyen instalaciones específicas para HPC/AI con refrigeración líquida directa. Tienen acuerdos para suministrar 100+ MW a clientes de IA.

**Nebius Group (NBIS)** — es el resultado de la reestructuración de Yandex (Rusia). Ahora es un operador cloud europeo centrado en IA. Opera datacenters en Finlandia y tiene planes de expansión para alquilar capacidad GPU en Europa.

---

# 🧠 Capa 4: Models (Modelos y Software)

## Qué es

Los "cerebros" de la IA. Incluye los modelos fundacionales (LLMs, modelos de visión, difusión) y el software que los ejecuta, entrena y despliega.

## Por qué es crítica ahora

- Es la capa donde ocurre la **innovación más rápida** (nuevos modelos cada semana)
- Determina qué chips se necesitan (modelos más grandes = más GPUs)
- Es la capa más **competitiva y volátil** — los líderes cambian cada 6 meses
- Aquí es donde se está librando la guerra entre **open source y propietario**

## Empresas clave

### 💻 Software (MSFT, NOW, SNOW)

**Microsoft (MSFT)** es probablemente la compañía **mejor posicionada en todas las capas** del Five-Layer Cake:
- **Chips:** Diseña sus propios chips (Azure Maia AI, Azure Cobalt ARM)
- **Infra:** Azure — el segundo cloud más grande del mundo
- **Models:** Copilot (basado en OpenAI), Azure OpenAI Service
- **Applications:** Microsoft 365 Copilot, GitHub Copilot, Dynamics 365 Copilot
- **Además:** Inversión de $13B en OpenAI (lo que le da acceso privilegiado a GPT)

**ServiceNow (NOW)** es una plataforma de **workflow empresarial** que está integrando IA generativa para automatizar procesos IT y de negocio. Su asistente **NowAssist** está impulsando renovaciones de contrato.

**Snowflake (SNOW)** es la plataforma de datos en la nube. Empresas que entrenan modelos de IA necesitan **gestionar, limpiar y servir sus datos** — Snowflake lo hace. Su producto Snowpark permite ejecutar Python directamente sobre los datos.

### ⚛️ Quantum (IONQ, QBTS, RGTI)

La computación cuántica no compite directamente con la IA actual (los LLMs se entrenan en GPUs clásicas), pero es la **próxima frontera** para ciertos tipos de cómputo que podrían beneficiar a la IA.

**IonQ (IONQ)** lidera en **trampas de iones** con la mayor fidelidad del sector (~99.9% en puertas de 2 qubits). Su enfoque es modular, conectando trampas para escalar.

**D-Wave (QBTS)** se centra en **recocido cuántico** (no computación cuántica universal). Útil para problemas de optimización (logística, scheduling). No es un competidor directo de GPUs — es complementario.

**Rigetti (RGTI)** fabrica chips cuánticos superconductores. Más pequeño, más riesgo, pero con tecnología diferenciada.

### 🤖 Robótica (OUST, SYM, TSLA)

**Ouster (OUST)** fabrica **sensores LiDAR** (detección por láser) para robots, vehículos autónomos y automatización industrial. La IA necesita "ver" el mundo físico — los LiDAR son sus ojos.

**Symbotic (SYM)** automatiza almacenes con robots móviles. Sus sistemas usan IA para optimizar la disposición de inventario, picking y embalaje. Cliente principal: Walmart.

**Tesla (TSLA)** bajo Jensen Huang no está en la capa de Chips (aunque Tesla diseña su propio chip Dojo) — está en **Robótica/Aplicaciones** con Optimus (robot humanoide) y Full Self-Driving. Ambos dependen de GPUs de NVIDIA y de modelos de IA entrenados en hardware NVIDIA.

---

# 🎯 Capa 5: Applications (Aplicaciones)

## Qué es

La capa donde la IA genera **valor económico real**. Jensen Huang insiste en que esta capa es la que justifica toda la inversión de las capas inferiores. Sin aplicaciones que paguen por la IA, no hay sostenibilidad.

## Por qué es crítica ahora

- Es la capa que está **monetizando** la inversión de $1T+ en infraestructura de IA
- Las aplicaciones de IA están reemplazando workflows existentes (optimización de costes, no solo ingresos nuevos)
- Es donde se formarán los **monopolios del futuro** (la Compañía que domine una aplicación vertical de IA tendrá poder de pricing real)

## Empresas clave

### 🛡️ Defense (PLTR, KTOS, AVAV)

**Palantir (PLTR)** es la compañía más pura de **AI para defensa y gobierno**. Su plataforma **Gotham** (inteligencia militar) y **Foundry** (datos empresariales) se están renovando con IA generativa. Su **AIP (Artificial Intelligence Platform)** permite desplegar modelos LLM seguros en entornos clasificados.

**Kratos (KTOS)** fabrica **drones militares** y sistemas de defensa. Sus drones no tripulados (BQM-177, XQ-58 Valkyrie) utilizan IA para navegación autónoma y reconocimiento.

**AeroVironment (AVAV)** produce **drones tácticos pequeños** (Switchblade, Puma, Raven) para el ejército de EE.UU. IA está transformando estos drones hacia operación autónoma.

### 🚁 Drones (ONDS, DPRO, UMAC)

**Ondas Holdings (ONDS)** desarrolla sistemas de drones autónomos para seguridad perimetral y defensa. Su plataforma **Autonomous Scout** usa IA para detectar intrusos sin intervención humana.

**Draganfly (DPRO)** es fabricante de UAVs para agricultura, defensa y emergencias. IA para análisis de imágenes.

**Unusual Machines (UMAC)** fabrica componentes para drones civiles (menos exposición directa a IA, más a la cadena de suministro de drones).

### 💳 Fintech (HOOD, SOFI, AFRM)

**Robinhood (HOOD)** usa IA para:
- Recomendación de inversiones personalizadas
- Risk management en opciones
- Procesamiento de transacciones en tiempo récord

**SoFi (SOFI)** usa IA para scoring crediticio, detección de fraude, y su asistente de finanzas personales **Lantern**.

**Affirm (AFRM)** usa IA para decisiones de crédito en milisegundos (BNPL). Redes neuronales para evaluar solvencia sin historial crediticio tradicional.

### ✈️ Autonomous (JOBY, ACHR)

**Joby Aviation (JOBY)** y **Archer Aviation (ACHR)** están desarrollando **taxis aéreos eléctricos (eVTOL)**. La IA es crítica para:
- Navegación autónoma y evitación de obstáculos
- Gestión de flota y routing
- Predicción de mantenimiento

### 🚀 Space (ASTS, RKLB, RDW, LUNR)

**AST SpaceMobile (ASTS)** construye una red celular satelital (direct-to-phone). IA para optimizar el beamforming y la asignación de ancho de banda.

**Rocket Lab (RKLB)** fabrica cohetes y satélites. IA en guiado de lanzamiento, análisis de telemetría y diseño de componentes.

**Redwire (RDW)** construye infraestructura espacial (paneles solares, brazos robóticos). IA para operaciones autónomas en el espacio.

**Intuitive Machines (LUNR)** aterrizó la primera nave privada en la Luna. IA para navegación autónoma de aterrizaje.

---

# 🌍 Mapa Completo: Five-Layer Cake + Watchlist Bill Brooklyn

| Capa | Subcapa | Tickers | Tesis de inversión en la capa |
|------|---------|---------|-------------------------------|
| ⚡ **Energy** | Nuclear | OKLO | Microreactores para datacenters — energía directa detrás del contador |
| ⚡ **Energy** | Cobre | FCX, SCCO, TECK | Conductor físico de toda la electrificación de IA |
| 💾 **Chips** | Memoria | MU, SNDK, WDC, STX | HBM3E (cuello de botella) + almacenamiento para datasets masivos |
| 💾 **Chips** | Semis | NVDA, AMD, ARM, INTC | GPUs (dominante NVIDIA) + CPUs (ARM/AMD) + arquitectura (ARM royalties) |
| 🏗️ **Infra** | Networking | AVGO, MRVL, CRDO | Interconexión de GPUs a alta velocidad — Ethernet 800G/1.6T |
| 🏗️ **Infra** | Photonics | AAOI, LITE, COHR, NVTS, GLW | Fibra óptica + fotónica para comunicaciones dentro del datacenter |
| 🏗️ **Infra** | Servidores | DELL, SMCI | Ensamblaje de servidores de IA listos para NVIDIA |
| 🏗️ **Infra** | Data Centers | IREN, CIFR, APLD, NBIS | Operadores de infraestructura física de HPC/AI |
| 🧠 **Models** | Software | MSFT, NOW, SNOW | Plataformas cloud, datos y workflow — fuel para modelos de IA |
| 🧠 **Models** | Cuántica | IONQ, QBTS, RGTI | Computación cuántica — próxima frontera (no compite hoy, complementa mañana) |
| 🧠 **Models** | Robótica | OUST, SYM, TSLA | IA que interactúa con el mundo físico — sensores + automatización |
| 🎯 **Apps** | Defensa | PLTR, KTOS, AVAV | IA para inteligencia militar, drones autónomos, seguridad nacional |
| 🎯 **Apps** | Drones | ONDS, DPRO, UMAC | Drones civiles y de defensa con IA embarcada |
| 🎯 **Apps** | Fintech | HOOD, SOFI, AFRM | Scoring crediticio, trading y finanzas personales con IA |
| 🎯 **Apps** | Autónomos | JOBY, ACHR | Taxis aéreos eVTOL — IA para navegación y operación autónoma |
| 🎯 **Apps** | Espacio | ASTS, RKLB, RDW, LUNR | Satélites, cohetes e infraestructura lunar con IA embarcada |

---

# 💰 Flujo de Capital y Rotación entre Capas

## Tesis principal

El capital tiende a rotar **de abajo arriba** en el Five-Layer Cake:

1. **Fase 1 — Enable:** Capital fluye a Energy + Chips (los facilitadores)
2. **Fase 2 — Build:** Capital fluye a Infrastructure (los constructores)
3. **Fase 3 — Run:** Capital fluye a Models (los cerebros)
4. **Fase 4 — Harvest:** Capital fluye a Applications (la monetización)

## Señales de rotación entre capas

| Movimiento | Qué observarlo | Señal de compra/venta |
|------------|---------------|----------------------|
| Energy → Chips | OKLO + FCX suben → NVDA + MU suben en 2-4 semanas | Comprar Chips cuando Energy se activa |
| Chips → Infrastructure | NVDA/MU se toman un respiro → AVGO/DELL/SMCI se activan | Vender Chips parcialmente, comprar Infrastructure |
| Infrastructure → Models | AVGO/AAOI lateralizan → MSFT/NOW aceleran | Vender Infrastructure, comprar Software |
| Models → Apps | MSFT/NOW se ralentizan → PLTR/JOBY se activan | Vender Models, comprar Applications |

## Fase actual del ciclo (Junio 2026)

Según el discurso de Jensen Huang en GTC 2026 y el gasto declarado por los hyperscalers:

- **Energy:** ⚠️ Comenzando a ser un cuello de botella real — se están firmando PPAs nucleares (OKLO, Constellation) a un ritmo acelerado
- **Chips:** 🟢 Plena expansión — gasto de $200B+ en NVIDIA; AMD ganando algo de tracción; memoria en máximos
- **Infrastructure:** 🟢 Construyendo — las AI Factories se están construyendo ahora; SMCI y DELL ampliando capacidad al máximo
- **Models:** 🟡 Auge competitivo — guerra de modelos abiertos/cerrados; gasto creciente pero con riesgo de commoditization
- **Applications:** 🟢 Búsqueda de unicornios de aplicación — incremento de startups en defensa, fintech y robótica

---

# 🔄 Ciclo de Retroalimentación

La genialidad del Five-Layer Cake es que **no es lineal** — es un **bucle de retroalimentación**:

```
Innovación en Chips (más rápidos) → 
  Permite mejores Models (más grandes) → 
    Exige mejor Infrastructure (más red, más energía) → 
      Permite mejores Applications (más capaces) → 
        Genera más demanda → 
          Más ingresos → 
            Más inversión en Chips
```

Cada mejora en una capa se propaga hacia arriba, y la demanda de la capa superior tira de la capa inferior. Esto es lo que está sosteniendo el **superciclo de inversión** en IA desde 2023.

**Cuando el bucle se rompe:** Si las Applications no generan suficiente retorno, la inversión en las capas inferiores se desacelera. Esto sería un **AI Winter** selectivo — no un colapso, sino una pausa hasta que la capa Applications demuestre que puede monetizar la inversión.

---

# 🔗 Conexiones con otros documentos

- [[03 Strategies/Bill Brooklyn]] — Watchlist completa que mapea los 52 tickers a las 5 capas, con metodología de rotación sectorial
- [[03 Strategies/Bill Brooklyn]] → sección "Leading vs Lagging Sectors" para entender el timing de rotación entre capas

---

*Basado en el Five-Layer Cake descrito por Jensen Huang (NVIDIA) en GTC 2025-2026 y en el blog oficial de NVIDIA ([enlace](https://blogs.nvidia.com/blog/ai-5-layer-cake/)). Actualizado: 23 Jun 2026.*
