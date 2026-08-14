# Roadmap de formación

Esta página convierte los materiales de `formacion/` en una secuencia útil para avanzar desde comprensión conceptual hasta trabajo experimental dentro del proyecto `qlib`.

## Objetivo

Usar los materiales no solo para leer, sino para alimentar tres salidas concretas:

1. mejores decisiones metodológicas en el proyecto
2. nuevos experimentos reproducibles en Qlib
3. criterios más claros para pasar de research a operativa diaria

## Orden recomendado de lectura

### Fase 1 — Marco conceptual mínimo

Objetivo: aclarar vocabulario, métricas y el tipo de preguntas que importan.

1. [Conceptos Investment](investing/Conceptos%20Investment.md)
2. [Doing Capitalism Video II](investing/Doing%20Capitalism%20Video%20II.md)
3. [Investments 2026](investing/Investments%202026.md)

Qué sacar de aquí:

- significado práctico de turnover
- diferencia entre idea de inversión y sistema operativo de trading
- lista de activos/temas que merecen análisis aparte

Salida esperada para el proyecto:

- documentar mejor el impacto de turnover y costes en los experimentos
- decidir qué parte del proyecto apunta a research cuantitativo y cuál a valoración fundamental

### Fase 2 — Base de series temporales

Objetivo: reforzar intuición estadística antes de añadir más complejidad al pipeline.

1. [Análisis Series Temporales](time-series/An%C3%A1lisis%20Series%20Temporales.md)
2. [Books Time Series](time-series/Books%20Time%20Series.md)

Qué sacar de aquí:

- sesgos habituales en series financieras
- diferencias entre señal, ruido y régimen de mercado
- ideas para labels y horizontes de predicción

Salida esperada para el proyecto:

- revisar si la label actual de Alpha158 es la adecuada para el objetivo
- plantear experimentos con horizontes alternativos: 1 día vs 5 días
- anotar hipótesis sobre estabilidad temporal de señales

### Fase 3 — Operativa Qlib básica

Objetivo: consolidar el flujo real que ya existe en el repo.

1. [Qlib Course](qlib/Qlib%20Course.md)
2. [Operaciones Downloads Qlib](qlib/Operaciones%20Downloads%20Qlib.md)
3. [Temas Pendientes Qlib](qlib/Temas%20Pendientes%20Qlib.md)

Qué sacar de aquí:

- actualización y verificación diaria de datos
- normalización y chequeos de salud del dataset
- puntos abiertos sobre MLflow, labels y selección de modelos

Salida esperada para el proyecto:

- contrastar estas notas con el flujo ya implementado en este repo
- convertir diferencias importantes en tareas concretas
- decidir qué partes antiguas de RD-Agent ya han quedado absorbidas por `qlib/`

### Fase 4 — Estrategias y variantes

Objetivo: usar los documentos estratégicos como backlog experimental, no como receta literal.

Lectura sugerida:

1. [Estrategia Qlib 1](qlib/Estrategia%20Qlib%201.md)
2. [Estrategia Qlib 2](qlib/Estrategia%20Qlib%202.md)
3. [Estrategia Qlib 3](qlib/Estrategia%20Qlib%203.md)
4. [Estrategia Qlib 4](qlib/Estrategia%20Qlib%204.md)
5. [Estrategia Qlib 5 Cryptos](qlib/Estrategia%20Qlib%205%20Cryptos.md)
6. [Estrategia Qlib 6 AutoGluon 1](qlib/Estrategia%20Qlib%206%20AutoGluon%201.md)
7. [Estrategia Qlib 6 AutoGluon 2](qlib/Estrategia%20Qlib%206%20AutoGluon%202.md)

Qué sacar de aquí:

- ideas de coste fijo vs proporcional
- updates incrementales diarios/mensuales
- labels alternativas
- GRU / deep learning / AutoGluon como líneas de exploración
- métricas de evaluación: IC, Rank IC, ICIR, turnover

Salida esperada para el proyecto:

- separar claramente ideas plausibles de sugerencias demasiado optimistas o no validadas
- convertir cada línea prometedora en experimento reproducible pequeño
- registrar qué hipótesis merecen pasar a la wiki de research

## Mapa de materiales a tareas del proyecto

### Tareas inmediatas

- **Costes y turnover**  
  Fuente: [Conceptos Investment](investing/Conceptos%20Investment.md), [Estrategia Qlib 2](qlib/Estrategia%20Qlib%202.md)  
  Acción: revisar si la documentación del proyecto deja suficientemente claro `min_cost`, el round-trip efectivo y el impacto de rotación.

- **Labels y horizonte**  
  Fuente: [Temas Pendientes Qlib](qlib/Temas%20Pendientes%20Qlib.md), materiales de estrategias Qlib  
  Acción: comparar label actual del baseline con variantes de 5 días o formulaciones más orientadas a ranking robusto.

- **Actualización diaria de datos**  
  Fuente: [Qlib Course](qlib/Qlib%20Course.md), [Estrategia Qlib 2](qlib/Estrategia%20Qlib%202.md)  
  Acción: contrastar las notas con el pipeline real del repo y decidir si merece añadirse una capa `us_data` separada para research/live en el futuro.

### Tareas de investigación aplicable

- **Comparar selección por IC vs monetización real**  
  Acción: reforzar la distinción entre calidad de señal y calidad de portfolio, ya visible en los runs actuales.

- **Explorar modelos alternativos ligeros**  
  Acción: evaluar si AutoGluon o una variante secuencial pequeña aporta más que LightGBM sin romper reproducibilidad/coste.

- **Formalizar criterios de promoción a trading real**  
  Acción: extraer de los materiales un checklist mínimo para separar research, paper trading y execution layer.

## Qué leer primero si hay poco tiempo

### Ruta corta de 30–60 minutos

1. [Conceptos Investment](investing/Conceptos%20Investment.md)
2. [Qlib Course](qlib/Qlib%20Course.md)
3. [Temas Pendientes Qlib](qlib/Temas%20Pendientes%20Qlib.md)
4. [Estrategia Qlib 2](qlib/Estrategia%20Qlib%202.md)

### Ruta práctica para mover el proyecto

1. [Qlib Course](qlib/Qlib%20Course.md)
2. [Temas Pendientes Qlib](qlib/Temas%20Pendientes%20Qlib.md)
3. [Estrategia Qlib 2](qlib/Estrategia%20Qlib%202.md)
4. [Estrategia Qlib 6 AutoGluon 1](qlib/Estrategia%20Qlib%206%20AutoGluon%201.md)
5. [Estrategia Qlib 6 AutoGluon 2](qlib/Estrategia%20Qlib%206%20AutoGluon%202.md)

## Criterio editorial recomendado

No tratar estos materiales como documentación canónica del proyecto. Mejor usarlos como:

- notas de trabajo
- backlog de hipótesis
- ideas para experimentos
- recordatorios de dudas abiertas

La versión canónica sigue estando en:

- `README.md`
- `docs/`
- `wiki/research/`
- `wiki/workflows/`

## Siguiente paso recomendado

Cuando aparezca una idea prometedora en `formacion/`, promoverla a uno de estos destinos:

- `wiki/research/hypotheses.md`
- `wiki/research/experimental-backlog.md`
- `wiki/research/methodological-decisions.md`
- una nueva config reproducible en `config/`
