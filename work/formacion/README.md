# Qlib Obsidian Vault

Vault for the Qlib quantitative investment project.

## Estructura

| Carpeta | Contenido |
|---|---|
| `01 Literature/` | Papers, cursos, referencias externas |
| `02 Qlib Concepts/` | Mapa del proyecto, arquitectura, meta |
| `03 Strategies/` | Ideas de alpha y diseños |
| `04 Experiments/` | Dashboard, baselines, hipótesis, backlog |
| `05 Backtests/` | Resultados y análisis de backtests |
| `06 Data/` | Datasets, features, calidad |
| `07 Operations/` | Runbook, docker, logs |
| `99 Archive/` | Material inactivo |

## Publicar cambios en la LLM Wiki

```bash
./scripts/update_llm_wiki.sh   # sync obsidian → wiki + regenerar
./scripts/serve_llm_wiki.sh    # preview en localhost:8016
```
