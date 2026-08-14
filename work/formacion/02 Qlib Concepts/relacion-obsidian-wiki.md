# Relación Obsidian ↔ LLM Wiki

> **Fecha:** 2026-05-31
> **Contexto:** Aclaración sobre cómo se relacionan el vault de Obsidian (notas) con la LLM Wiki (conocimiento curado).

---

## Mapa conceptual

```
┌─────────────────────────────────────┐
│          OBSIDIAN (vault)           │
│  Notas rápidas · Ideas · Borradores │
│  Mapas mentales · Lectura en curso  │
│  Conexiones tentativas · Día a día  │
│                                     │
│  🛠️  Es el **taller**               │
└────────────┬────────────────────────┘
             │  Cuando una nota madura
             │  (es importante, está clara,
             │   merece conservarse)
             ▼
┌─────────────────────────────────────┐
│      SCRIPT DE TRANSFORMACIÓN       │
│  Extrae · Limpia · Reestructura     │
│  Aplica plantillas del wiki         │
│  Coloca en la sección correcta      │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│          LLM WIKI (wiki/)           │
│  Conocimiento curado y estable      │
│  Decisiones con razonamiento        │
│  Conexiones explícitas y verificadas│
│  Navegable por humanos y LLMs       │
│                                     │
│  📚 Es la **estantería organizada**  │
└────────────┬────────────────────────┘
             ▼
┌─────────────────────────────────────┐
│          MkDocs (site)              │
│  Preview local navegable            │
└─────────────────────────────────────┘
```

---

## Principios clave

1. **No todo lo de Obsidian pasa al wiki.** Solo lo que merece la pena conservar de forma estable. Si es una nota fugaz, una idea a medias, un apunte rápido — se queda en Obsidian.

2. **El wiki no es un volcado.** Transformas, no copias. La nota de Obsidian es el borrador; la página del wiki es la versión destilada, estructurada y revisada.

3. **Dos ritmos diferentes:**
   - Obsidian → escritura rápida, exploratoria, diaria
   - Wiki → actualización cuando algo madura, decisiones firmes, conocimiento verificado

4. **Para qlib:** El flujo principal no es Obsidian→Wiki, sino `mlruns/` → Wiki (generación automática desde experimentos). Obsidian se usa para planificación y notas de estrategia.

5. **Para PhD:** El flujo Obsidian→Wiki tiene más sentido porque la investigación empieza como notas sueltas que luego merecen ser curadas.

---

## En una frase

> **Obsidian es el taller donde trabajas. La LLM Wiki es la estantería donde guardas lo que has aprendido.**

---

**Related:**
- [[transformacion-llm-wiki]]
- [[Welcome]]
- `phd/obsidian/00 Inbox/relacion-obsidian-wiki.md`

**Next step:** Mantener esta distinción clara al implementar los scripts de transformación.
