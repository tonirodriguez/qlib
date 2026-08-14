# Cómo generar y servir la LLM Wiki de qlib

> **Propósito:** Documentar los pasos para regenerar la LLM Wiki desde los datos de `mlruns/` y servirla para acceso local o remoto.

## Estructura

```
obsidian/       → Fuente de autoría (Markdown, vault de Obsidian)
    └── sincronización manual
wiki/           → Lo que sirve MkDocs (se regenera entero)
    ├── research/dashboard.md      ← generado desde mlruns/
    ├── experiments/baselines.md   ← generado desde mlruns/
    ├── experiments/signal-vs-portfolio.md ← generado desde mlruns/
    ├── research/runs-index.md     ← generado desde mlruns/
    ├── research/project-state.md  ← generado desde mlruns/
    └── llm-context.md             ← volcado plano de toda la wiki
mkdocs-llm-wiki.yml → Configuración de MkDocs
```

## Flujo completo

```bash
# 1. Sincronizar contenido de Obsidian a wiki/
bash scripts/sync_obsidian_to_wiki.sh

# 2. Regenerar páginas automáticas desde mlruns/
bash scripts/update_llm_wiki.sh    # hace sync + generate

# 3. Servir la wiki en local
bash scripts/serve_llm_wiki.sh     # http://localhost:8016
```

## En el contenedor Docker (OpenClaw)

La wiki necesita arrancarse manualmente tras un reinicio del contenedor:

```bash
cd qlib
nohup bash scripts/serve_llm_wiki.sh > /tmp/mkdocs-wiki.log 2>&1 &
```

Hay un **keepalive** configurado (cada 5 min) que la arranca si se cae.

### Puerto mapeado en docker-compose

El puerto `8016` se expone al host en `openclaw-stack/docker-compose.yml`:

```yaml
ports:
  - "${QLIB_WIKI_PORT:-8016}:8016"
```

Acceso desde el host: `http://localhost:8016/`

## En otra máquina (solo el repo, sin entorno Qlib)

Prerrequisitos: solo Python + pip.

```bash
pip install mkdocs mkdocs-material

git clone git@github.com:tonirodriguez/agent_qlib.git
cd agent_qlib

# Sincronizar y servir
bash scripts/sync_obsidian_to_wiki.sh
bash scripts/serve_llm_wiki.sh
```

O con el script todo-en-uno:

```bash
bash scripts/qlib-wiki-standalone.sh /ruta/a/agent_qlib
```

Esto:
1. Instala mkdocs si no está
2. Sincroniza `obsidian/ → wiki/`
3. Sirve en `http://0.0.0.0:8016/`

## Dependencias

| Componente | Necesario para |
|---|---|
| `mkdocs` + `mkdocs-material` | Servir la wiki |
| Python + `.venv/` de qlib | Regenerar páginas desde `mlruns/` |
| `obsidian/` (en git) | Contenido fuente |
| `scripts/sync_obsidian_to_wiki.sh` | Mapping de carpetas Obsidian → wiki |
| `scripts/serve_llm_wiki.sh` | Arrancar MkDocs |

## Notas importantes

- **No editar directamente en `wiki/`**: se sobreescribe con cada sync.
- **Editar siempre en `obsidian/`**.
- **Regenerar después de cada experimento**: `./scripts/update_llm_wiki.sh`
- **`llm-context.md`** contiene toda la wiki en un solo archivo plano (links stripped) para inyectar como contexto a un LLM.

## Snapshot automático

Al regenerar, se crea un tag de git automático:

```bash
git tag wiki-snapshot-YYYYMMDDTHHMMSS
```

Esto permite trazabilidad histórica del estado de la wiki.

## Validación

Tras cada regeneración, se ejecuta:

```bash
mkdocs build --strict -f mkdocs-llm-wiki.yml
```

Si hay links rotos, el build falla.
