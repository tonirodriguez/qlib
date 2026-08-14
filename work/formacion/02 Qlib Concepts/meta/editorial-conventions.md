# Convenciones editoriales

## Objetivo de la wiki

Esta wiki está pensada como capa de orientación rápida para humanos y LLMs.

Debe ser:

- compacta
- enlazada
- actualizable
- útil para reanudar trabajo sin releer todo el repositorio

## Reglas de estilo

- una página = una idea clara
- enlazar a la fuente canónica cuando exista
- no duplicar tablas enormes si ya viven mejor en `docs/`
- priorizar resúmenes, contexto y decisiones
- dejar explícito qué es estable y qué es provisional

## Qué sí poner aquí

- mapas del proyecto
- resúmenes de runs
- decisiones y aprendizajes
- rutas importantes
- workflows operativos

## Qué no poner aquí

- dumps largos de logs
- blobs generados automáticamente
- notebooks exportados enteros
- documentación redundante con `vendor/microsoft-qlib/`

## Patrón recomendado

Cada página útil debería responder al menos a una de estas preguntas:

- ¿qué es esto?
- ¿por qué importa?
- ¿dónde está la fuente canónica?
- ¿qué decisión o aprendizaje deja?

## Plantillas

Para documentar contenido relevante, usar preferentemente:

- `meta/templates/experiment-page-template.md`
- `meta/templates/hypothesis-template.md`
- `meta/templates/methodological-decision-template.md`
