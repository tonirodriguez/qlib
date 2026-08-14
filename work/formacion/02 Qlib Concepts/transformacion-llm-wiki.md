# Transformación LLM Wiki — qlib

> **Fecha:** 2026-05-31
> **Contexto:** Diagnóstico completo del estado actual de la LLM Wiki del proyecto qlib y plan de implantación del paradigma completo (conocimiento curado + automatización + orientación LLM).

---

## 📐 El paradigma LLM Wiki en general

Tres capas diferenciadas:

```
[datos/experimentos/código] ──genera──→ [wiki/ (Markdown curado)] ──sirve──→ [MkDocs site]
                                               ↑
                                   [scripts de automatización]
                                               ↑
                                   [editorial conventions + templates]
```

El wiki está **entre** los datos y la presentación: no es raw data ni docs estáticos, es **conocimiento destilado y navegable**.

---

## 🧪 Proyecto qlib — estado actual

### Lo que ya funciona bien

- Scripts de generación automática desde `mlruns/` (dashboard, baselines, comparativas)
- Plantillas para experimentos, hipótesis, decisiones
- Runbook operativo claro
- Sección de formación muy poblada
- MkDocs configurado y sirviendo en local

### Lo que falta o se puede mejorar

| Área | Problema | Solución |
|---|---|---|
| **Auto-sync** | `update_llm_wiki.sh` solo se ejecuta manual. No hay detección de cambios en `mlruns/` ni en workflows | Añadir un cron o hook post-ejecución que regenerue páginas relevantes |
| **Página "Estado del proyecto"** | El index.md tiene un resumen manual, no generado | Crear `research/project-state.md` generado que lea: último run, últimas decisiones, próximos pasos |
| **Cache de experimentos** | No hay un registro plano y legible de todos los runs que un LLM pueda leer de un tirón | Generar `research/runs-index.md` como tabla plana (cada línea = un run) |
| **Conexión hipótesis → experimento** | El link entre hipótesis en `hypotheses.md` y los resultados en `baselines.md` es difuso | Añadir cross-refs explícitas: cada hipótesis apunta a experimentos que la validan/invalidan, y cada experimento a la hipótesis |
| **Open questions + decisiones** | Existen pero sin fecha de última actualización | Timestamp automático al regenerar para saber qué está vivo y qué está stale |
| **Script de generación unificado** | Varios scripts separados que se ejecutan en orden con `update_llm_wiki.sh` | Consolidar en un solo `generate_llm_wiki.py` o mantener pero con mejor orquestación |
| **QA de la wiki** | No hay validación de que los enlaces internos no estén rotos | Añadir paso de validación (MkDocs build con `--strict`) |

---

## 📋 Plan de implementación qlib

### Fase 1 — Inmediata (~2h)

1. **Unificar scripts** en `generate_llm_wiki.py` (Python, dentro del venv)
2. **Añadir página `research/runs-index.md`** generada desde `mlruns/`
3. **Añadir timestamps** y cross-refs hipótesis↔experimento
4. **Hook post-run**: que `run_baseline_workflow.py` llame a regenerate automáticamente

### Fase 2 — Estructural (~1 sesión)

5. **Separar formación del wiki operativo** → mover formación a un wiki secundario o dejarlo como está pero con menos prioridad en nav (la wiki operativa debería priorizar project-state, experiments, research)
6. **Snapshot inmutable**: cada regeneración crear un tag/commit con el estado del wiki para trazabilidad histórica
7. **Validación automática** de enlaces internos (build con `--strict`)

### Fase 3 — LLM-first

8. **`llm-context.md` generado**: un único archivo que sea un volcado plano de TODO el wiki para inyectar como contexto a un LLM
9. **Metadata YAML** en cada página generada (`last_run_id`, `hypothesis_id`, etc.) para que un LLM pueda parsear y hacer queries estructuradas

---

## 🔄 Patrón transversal qlib + PhD

Ambos proyectos se beneficiarían de un patrón compartido:

```
┌───────────────────────────────────┐
│           LLM Context             │
│  (llm-context.md — volcado plano) │
└──────────┬────────────────────────┘
           │ se inyecta en prompt
┌──────────▼────────────────────────┐
│        MkDocs LLM Wiki            │
│  (navegable, curado, timestamped) │
└──────────┬────────────────────────┘
           │ se regenera desde
┌──────────▼────────────────────────┐
│   Generación automática           │
│   (scripts Python/bash)           │
└──────────┬────────────────────────┘
           │ lee de
┌──────────▼────────────────────────┐
│   Datos fuente                    │
│   mlruns / Obsidian / .bib / ...  │
└───────────────────────────────────┘
```

---

## ✅ Checklist de salud para la wiki

- [ ] `index.md` tiene un resumen del estado actual
- [ ] La página madre del proyecto (`project-map.md`) está actualizada
- [ ] Las open questions tienen timestamp de última revisión
- [ ] Las decisiones metodológicas están registradas (no solo implícitas en el código)
- [ ] Hay al menos un script de regeneración
- [ ] El LLM puede cargar todo el wiki en un solo contexto (`llm-context.md`)
- [ ] Los enlaces internos no están rotos (build con `--strict`)
- [ ] Hay trazabilidad (commits/snapshots)

---

## 🚀 Prioridades para arrancar

1. `generate_llm_wiki.py` unificado
2. `research/runs-index.md` generado
3. Hook automatizado post-run
4. `research/project-state.md` generado
5. Validación de enlaces

---

**Related:**
- [[Welcome]]
- `mkdocs-llm-wiki.yml`
- `scripts/update_llm_wiki.sh`
- `scripts/serve_llm_wiki.sh`
- `docs/llm-wiki-manual.md`
- `phd/obsidian/00 Inbox/transformacion-llm-wiki.md`

**Next step:** Arrancar Fase 1.1 — escribir el script unificado de generación.
