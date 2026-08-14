# qlib — Obsidian Vault

Este vault es la fuente de autoría para la LLM Wiki del proyecto qlib.

## Estructura del vault

| Carpeta | Contenido |
|---|---|
| `01 Literature/` | Papers, cursos, referencias externas |
| `02 Qlib Concepts/` | Mapa del proyecto, arquitectura, meta, documentación del framework |
| `03 Strategies/` | Ideas de alpha y diseños de estrategias |
| `04 Experiments/` | Dashboard, baselines, hipótesis, backlog, decisiones |
| `05 Backtests/` | Resultados y análisis de backtests |
| `06 Data/` | Notas sobre datasets, features, calidad |
| `07 Operations/` | Runbook, docker, logs, troubleshooting |
| `99 Archive/` | Material inactivo |

## Punto de partida

- [Welcome](Welcome.md)
- [Mapa del proyecto](02%20Qlib%20Concepts/project-map.md)
- [Relación Obsidian ↔ Wiki](02%20Qlib%20Concepts/relacion-obsidian-wiki.md)
- [Dashboard](04%20Experiments/dashboard.md)

## Sincronización a la wiki

Para publicar los cambios en la LLM Wiki:

```bash
./scripts/update_llm_wiki.sh
./scripts/serve_llm_wiki.sh
```
