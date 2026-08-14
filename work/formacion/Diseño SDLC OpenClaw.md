# 🏗️ Diseño de Arquitectura SDLC Agentica con OpenClaw + GitHub

**Autor:** Sebas (OpenClaw Agent)
**Fecha:** 2026-07-22
**Versión:** 1.0
**Estado:** Diseño preliminar

---

## Índice

1. [Visión General](#1-visión-general)
2. [Principios de Diseño](#2-principios-de-diseño)
3. [Arquitectura Propuesta](#3-arquitectura-propuesta)
4. [Componentes del Sistema](#4-componentes-del-sistema)
5. [SDLC: Las Fases y su Automatización](#5-sdlc-las-fases-y-su-automatización)
6. [Modelo de Agentes](#6-modelo-de-agentes)
7. [Integración con GitHub](#7-integración-con-github)
8. [OpenClaw como Orquestador](#8-openclaw-como-orquestador)
9. [Configuraciones Detalladas](#9-configuraciones-detalladas)
10. [Flujos Completos](#10-flujos-completos)
11. [Seguridad y Gobernanza](#11-seguridad-y-gobernanza)
12. [Recomendaciones](#12-recomendaciones)
13. [Hoja de Ruta](#13-hoja-de-ruta)
14. [Apéndices](#14-apéndices)

---

## 1. Visión General

### 1.1 Problema

Un equipo de desarrollo de producto necesita gestionar el ciclo de vida completo del software (requisitos, diseño, desarrollo, QA, staging, producción) de forma consistente, trazable y automatizada. Las herramientas existen (GitHub Issues, Pull Requests, CI/CD), pero no hay una capa de inteligencia que:

- Entienda el contexto de cada fase
- Automatice tareas repetitivas (triage, labelling, code review básico)
- Orqueste flujos multi-paso (releases)
- Proporcione visibilidad del estado del SDLC
- Permita usar diferentes capacidades de IA según la tarea

### 1.2 Solución

Un **sistema multi-agente** donde OpenClaw actúa como orquestador, con agentes especializados que:

- Se comunican con GitHub (issues, PRs, Actions, CI)
- Siguen un modelo de fases definido por labels
- Usan diferentes modelos de IA según la tarea (baratos para triage, potentes para diseño)
- Proporcionan un único punto de interacción para el equipo

### 1.3 Stakeholders

| Rol | Interacción con el sistema |
|---|---|
| **Toni (product owner)** | Canal directo con el coordinator agent. Decide prioridades, aprueba releases. |
| **Desarrolladores** | Interactúan vía GitHub PRs + comentarios. El agente revisa y comenta automáticamente. |
| **QA** | El agente verifica cobertura y etiqueta issues. |
| **Equipo completo** | Pueden consultar estado vía comandos en Slack/TG. |

---

## 2. Principios de Diseño

### 2.1 Principios rectores

1. **Un solo punto de contacto** — El equipo habla con un único agente (el coordinator). Los especialistas son invisibles.

2. **Modelo correcto para cada tarea** — No usar un modelo caro para lo que puede hacer uno barato. No usar uno barato para lo que requiere razonamiento profundo.

3. **Aislamiento por responsabilidad** — Cada agente especialista tiene su propio contexto, sesión y memoria. No contaminan la conversación principal.

4. **GitHub como fuente de verdad** — Issues, PRs y labels son el estado autoritativo. OpenClaw refleja, no reemplaza.

5. **Automatización progresiva** — Primero triage y notificaciones. Luego code review asistido. Luego releases automatizados. Cada paso requiere validación antes del siguiente.

6. **El humano siempre en el loop para decisiones críticas** — Merges a main, despliegues a producción, cambios de alcance.

7. **Costo controlado** — El 80% del volumen de trabajo debe ir a modelos nano/mini. Los modelos caros solo bajo demanda.

### 2.2 Decisiones arquitectónicas clave

| Decisión | Opción elegida | Alternativa descartada |
|---|---|---|
| Plataforma | GitHub (nativa de OpenClaw vía ClawSweeper) | GitLab (requeriría construir toda la integración) |
| Topología de agentes | Coordinator + sub-agents especialistas (bajo demanda) | Agentes peer-to-peer (mayor complejidad de routing) |
| Instalación | Instancia OpenClaw dedicada para el producto | Misma instancia que el agente personal (menor aislamiento) |
| Comunicación inter-agente | `sessions_spawn` con modelos específicos | Remote Gateway API (más latencia) |
| Automatización | Cron + Webhooks + TaskFlow + Standing Orders | Solo cron (sin capacidad reactiva) |

---

## 3. Arquitectura Propuesta

### 3.1 Diagrama de alto nivel

```
┌────────────────────────────────────────────────────────────────────────────┐
│                        INTERNET                                             │
│                                                                            │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Team    │    │   GitHub     │    │  GitHub      │    │  GitHub      │  │
│  │  (Slack)  │    │   Issues     │    │  Actions CI  │    │  Packages    │  │
│  └─────┬─────┘   └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│        │                │                    │                   │          │
│        │        ClawSweeper dispatch         │                   │          │
│        │          .github/workflows/         │                   │          │
│        │                │                    │                   │          │
│        ▼                ▼                    ▼                   ▼          │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │              OPENCLAW GATEWAY (Instancia SDLC Producto)              │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │              SDLC COORDINATOR AGENT                           │   │  │
│  │  │              (Sebas - modo SDLC)                             │   │  │
│  │  │                                                              │   │  │
│  │  │  Rol:    Orquestador, punto de contacto único                │   │  │
│  │  │  Canal:  Slack #sdlc-bot (opcional) o DM                    │   │  │
│  │  │  Modelo: deepseek/deepseek-v4-flash                          │   │  │
│  │  │                                                              │   │  │
│  │  │  Standing Orders: SDLC Governance                            │   │  │
│  │  │  Workspace:   ~/sdlc-workspace                               │   │  │
│  │  │  Skills:      agent-security-eval, threat-modeler, etc       │   │  │
│  │  └───────────┬──────────────────────────────────────┬──────────┘   │  │
│  │              │                                      │               │  │
│  │              │ sessions_spawn                        │ sessions_spawn│  │
│  │              ▼                                      ▼               │  │
│  │  ┌─────────────────────┐          ┌────────────────────────────┐   │  │
│  │  │ SUB-AGENTS           │          │ SUB-AGENTS (bajo demanda)  │   │  │
│  │  │ (especialistas fijos)│          │  ┌────────────────────┐    │   │  │
│  │  │                      │          │  │ Deep Research      │    │   │  │
│  │  │ • Triage Agent       │          │  │ (opus/sonnet)      │    │   │  │
│  │  │   (gpt-5.4-nano)     │          │  └────────────────────┘    │   │  │
│  │  │                      │          │  ┌────────────────────┐    │   │  │
│  │  │ • Code Review Agent  │          │  │ Documentation Gen   │    │   │  │
│  │  │   (gpt-5.4-mini)     │          │  │ (sonnet)            │    │   │  │
│  │  │                      │          │  └────────────────────┘    │   │  │
│  │  │ • Design/ADR Agent   │          │                            │   │  │
│  │  │   (sonnet)           │          └────────────────────────────┘   │  │
│  │  │                      │                                      │   │  │
│  │  │ • Release Manager    │                                      │   │  │
│  │  │   (gpt-5.5)          │                                      │   │  │
│  │  │                      │                                      │   │  │
│  │  │ • Metrics Agent      │                                      │   │  │
│  │  │   (gpt-5.4-nano)     │                                      │   │  │
│  │  └─────────────────────┘                                       │   │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │  CRON JOBS                    │  WEBHOOKS PLUGIN              │   │  │
│  │  │  ─────────                    │  ───────────────              │   │  │
│  │  │  • 09:00 SDLC Health         │  • GitHub events inbound      │   │  │
│  │  │  • 10:00 Sprint Planning     │  • Issue/PR creados           │   │  │
│  │  │  • 17:00 Weekly Report       │  • CI status changes          │   │  │
│  │  │  • 08:00 Stale Issues        │                                │   │  │
│  │  │  • Cada 2h CI Monitor        │                                │   │  │
│  │  └──────────────────────────────┴────────────────────────────────┘   │  │
│  │                                                                      │  │
│  │  ┌──────────────────────────────────────────────────────────────┐   │  │
│  │  │  TASKFLOWS (orquestación durable multi-paso)                  │   │  │
│  │  │  ─────────────────────────────────────                       │   │  │
│  │  │  • release-flow: changelog → bump → notes → deploy           │   │  │
│  │  │  • review-flow: diff → analyze → comment → label             │   │  │
│  │  │  • adr-flow: template → draft → review → merge               │   │  │
│  │  │  • triage-flow: parse → validate → label → assign            │   │  │
│  │  └──────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │   INFRAESTRUCTURA                                                    │  │
│  │   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐              │  │
│  │   │ gh CLI       │  │ ClawSweeper  │  │ Webhooks     │              │  │
│  │   │ (installed)  │  │ workflow     │  │ Plugin       │              │  │
│  │   └──────────────┘  └──────────────┘  └──────────────┘              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Topología de instalación

Se recomienda una **instancia OpenClaw dedicada** para el SDLC del producto, separada del agente personal. Esto proporciona:

- Aislamiento total de estado y sesiones
- Ciclos de actualización independientes
- Modelos y configuraciones específicos del producto
- Posibilidad de exponer al equipo sin exponer datos personales

```
┌─────────────────────────────┐     ┌───────────────────────────────────┐
│  Host: Docker/Podman/VPS     │     │  Host: Docker/Podman/VPS          │
│  Puerto: 18789               │     │  Puerto: 18791                   │
│                              │     │                                  │
│  ┌─────────────────────────┐ │     │  ┌─────────────────────────────┐ │
│  │ Instancia Personal      │ │     │  │ Instancia SDLC Producto     │ │
│  │                         │ │     │  │                             │ │
│  │ Agent: Sebas (main)     │ │     │  │ Agent: sdlc-bot (main)     │ │
│  │ Model: deepseek-v4-flash│ │     │  │ Model: gpt-5.4-nano        │ │
│  │ Slack: tu DM            │ │     │  │ Slack: #sdlc-bot channel   │ │
│  │ Workspace: ~/workspace  │ │     │  │ Workspace: ~/sdlc-workspace │ │
│  │ GitHub: no              │ │     │  │ GitHub: gh + PAT           │ │
│  └─────────────────────────┘ │     │  └─────────────────────────────┘ │
└─────────────────────────────┘     └───────────────────────────────────┘
```

### 3.3 Alternativa: Mismo host, dos puertos

Para entornos con recursos limitados, ambas instancias pueden convivir en el mismo host usando `--profile sdlc`:

```bash
# Terminal 1: Instancia personal (existente)
openclaw gateway start

# Terminal 2: Instancia SDLC (perfil aislado)
openclaw --profile sdlc gateway start --port 18791
```

Cada perfil tiene su propio `~/.openclaw-sdlc/` con state, config y sesiones independientes.

---

## 4. Componentes del Sistema

### 4.1 GitHub Infraestructura

#### 4.1.1 Repositorio del producto

Configuración necesaria en el repositorio GitHub del producto:

**Branch Protection Rules:**
- `main`: Require PR, require approvals (1+), require CI green, block force push
- `staging`: Require PR, require CI green, block force push
- `develop`: Require PR, optional approvals

**Labels del SDLC:**

```bash
# Labels de fase (flujo: izquierda → derecha)
gh label create "phase:backlog"     --color E6E6E6 --description "En backlog, sin priorizar"
gh label create "phase:req"         --color F9D0C4 --description "Requirements / user story"
gh label create "phase:design"      --color FEF2C0 --description "Design / ADR pending"
gh label create "phase:dev"         --color D4C5F9 --description "Development in progress"
gh label create "phase:qa"          --color B5EAD7 --description "Quality assurance"
gh label create "phase:staging"     --color C7CEEA --description "Validated in staging"
gh label create "phase:prod"        --color 7EC8E3 --description "Shipped to production"

# Labels de bloqueo
gh label create "blocked:req"       --color 000000 --description "Bloqueado: falta requisito"
gh label create "blocked:design"    --color 000000 --description "Bloqueado: decisión de diseño"
gh label create "blocked:dev"       --color 000000 --description "Bloqueado: bug/impedimento técnico"
gh label create "blocked:qa"        --color 000000 --description "Bloqueado: fallo en QA"
gh label create "blocked:external"  --color 000000 --description "Bloqueado por dependencia externa"

# Labels de estado
gh label create "ready:review"      --color 0E8A16 --description "Listo para code review"
gh label create "ready:release"     --color 0E8A16 --description "Listo para release"
gh label create "priority:critical" --color B60205 --description "Crítico, atención inmediata"
gh label create "priority:high"     --color D93F0B --description "Prioridad alta"
gh label create "priority:medium"   --color FBCA04 --description "Prioridad media"
gh label create "priority:low"      --color 0E8A16 --description "Prioridad baja"

# Labels de tipo
gh label create "type:feature"      --color 5319E7 --description "Nueva funcionalidad"
gh label create "type:bug"          --color B60205 --description "Bug / defecto"
gh label create "type:tech-debt"    --color 1D76DB --description "Deuda técnica"
gh label create "type:improvement"  --color 006B75 --description "Mejora"
gh label create "type:security"     --color 000000 --description "Seguridad"
```

**Issue Templates (`.github/ISSUE_TEMPLATE/`):**

```markdown
# .github/ISSUE_TEMPLATE/feature.md
---
name: Feature Request
about: Nueva funcionalidad
labels: phase:backlog, type:feature
---

## Descripción
_¿Qué necesitamos y por qué?_

## Criterios de Aceptación
- [ ] _criterio 1_
- [ ] _criterio 2_

## Contexto Técnico
_Enlaces, diagramas, referencias_

## Estimación
_[Opcional] Talla S/M/L/XL_
```

```markdown
# .github/ISSUE_TEMPLATE/bug.md
---
name: Bug Report
about: Reportar un defecto
labels: phase:backlog, type:bug
---

## Comportamiento Esperado
_¿Qué debería pasar?_

## Comportamiento Actual
_¿Qué pasa realmente?_

## Pasos para Reproducir
1. ...
2. ...

## Entorno
- Navegador/CLI:
- Versión:\n- OS:

## Logs / Screenshots
```
```

#### 4.1.2 ClawSweeper Dispatch Workflow

```yaml
# .github/workflows/clawsweeper-dispatch.yml
name: ClawSweeper Dispatch
on:
  issues:
    types: [opened, edited, labeled, unlabeled, closed, reopened, assigned]
  pull_request:
    types: [opened, synchronized, ready_for_review, review_requested,
            review_request_removed, closed, labeled, auto_merge_enabled]
  pull_request_review:
    types: [submitted, edited, dismissed]
  issue_comment:
    types: [created, edited, deleted]
  push:
    branches: [main, staging, develop]
  workflow_run:
    workflows: ["CI", "Deploy"]
    types: [completed]
    branches: [main, staging]

jobs:
  clawsweeper_dispatch:
    runs-on: ubuntu-latest
    if: github.actor != 'sdlc-bot[bot]'  # evitar loops
    steps:
      - uses: openclaw/clawsweeper-dispatch@v1
        with:
          app_id: ${{ secrets.CLAWSWEEPER_APP_ID }}
          private_key: ${{ secrets.CLAWSWEEPER_APP_PRIVATE_KEY }}
          event: ${{ toJSON(github.event) }}
          target_agent: "sdlc-bot"
```

#### 4.1.3 GitHub Webhook (alternativa/complemento a ClawSweeper)

Para eventos que ClawSweeper no soporta nativamente, se configura un webhook directo:

```
URL: https://<sdlc-host>:18791/plugins/webhooks/sdlc-github
Content-Type: application/json
Secret: <OPENCLAW_SDLC_WEBHOOK_SECRET>

Events:
  ✓ Issues
  ✓ Pull requests
  ✓ Pull request reviews
  ✓ Pull request review comments
  ✓ Pushes
  ✓ Statuses
  ✓ Workflow runs
  ✓ Check runs
```

### 4.2 Instancia OpenClaw SDLC

#### 4.2.1 Configuración base (`openclaw.json`)

```json5
{
  // Puerto diferente al de la instancia personal
  gateway: {
    port: 18791,
    host: "0.0.0.0",  // accesible para webhooks
    auth: {
      mode: "token",
      token: { source: "env", provider: "default", id: "SDLC_GATEWAY_TOKEN" }
    }
  },

  // Configuración del agente
  agents: {
    defaults: {
      workspace: "~/.openclaw/workspace-sdlc",
      repoRoot: "~/code/producto",
      userTimezone: "Europe/Madrid",
      timeFormat: "24",

      // Skills relevantes para SDLC
      skills: ["agent-security-eval", "threat-modeler"],

      // Configuración de modelo por defecto (barato para uso general)
      model: {
        primary: "openai/gpt-5.4-nano",
        fallbacks: ["openrouter/deepseek/deepseek-v4-flash:free"]
      },

      // Modelos especializados por capacidad
      imageModel: "openai/gpt-5.4-mini",
      pdfModel: "openai/gpt-5.4-mini",

      // Sub-agents: modelos por defecto
      subagents: {
        maxConcurrent: 6,
        delegationMode: "prefer",
        sandboxing: "inherit"
      },

      // Heartbeat desactivado (solo cron)
      heartbeat: { every: "0m" },
    },

    list: [
      {
        id: "main",
        // El coordinator usa un modelo más potente
        model: "openrouter/deepseek/deepseek-v4-flash",
        // Este es el agente que recibe los mensajes
      }
    ]
  },

  // Plugins necesarios
  plugins: {
    entries: {
      webhooks: {
        enabled: true,
        config: {
          routes: {
            "sdlc-github": {
              path: "/plugins/webhooks/sdlc-github",
              sessionKey: "agent:main:main",
              secret: {
                source: "env",
                provider: "default",
                id: "OPENCLAW_SDLC_WEBHOOK_SECRET"
              },
              controllerId: "sdlc/github-events",
              description: "Webhook de eventos GitHub para el SDLC"
            }
          }
        }
      },
      workboard: {
        enabled: true
      }
    }
  },

  // Canales (opcional, para exponer al equipo)
  channels: {
    slack: {
      enabled: true,
      config: {
        accounts: [{
          id: "sdlc-bot",
          token: { source: "env", id: "SDLC_SLACK_BOT_TOKEN" },
          signingSecret: { source: "env", id: "SDLC_SLACK_SIGNING_SECRET" },
          botId: "sdlc-bot",
          autoReconnect: true
        }]
      }
    }
  }
}
```

#### 4.2.2 Workspace del SDLC

```
workspace-sdlc/
├── AGENTS.md           # Standing Orders SDLC (ver sección 8)
├── SOUL.md             # Personalidad del agente SDLC
├── USER.md             # Contexto del equipo/producto
├── TOOLS.md            # Notas locales
├── MEMORY.md           # Memoria del producto
├── memory/
│   ├── 2026-07-22.md   # Diario de decisiones
│   └── ...
├── sdlc/
│   ├── templates/
│   │   ├── ADR-template.md
│   │   ├── release-notes-template.md
│   │   ├── post-mortem-template.md
│   │   └── weekly-report-template.md
│   ├── reports/
│   │   └── weekly/
│   ├── labels.yaml
│   └── workflows/
└── skills/
    └── sdlc-governance/   # Skill custom del SDLC
```

---

## 5. SDLC: Las Fases y su Automatización

### 5.1 Mapa de fases

```
backlog ─► req ─► design ─► dev ─► qa ─► staging ─► prod
   │         │        │        │       │         │
   │         │   ┌────┘        │       │         │
   │         │   │   blocked:design   │         │
   │    blocked:req │         │       │         │
   │                │    blocked:dev   │         │
   │                │         │   blocked:qa    │
   ▼                ▼         ▼       ▼         ▼
  Cerrado         Cerrado   Cerrado  Cerrado  Cerrado
  (no procede)   (no prioridad)
```

### 5.2 Descripción de cada fase

#### 5.2.1 Fase: Backlog (`phase:backlog`)

**Trigger:** Issue creado sin fase, o issue creado con template.

**Gates de salida:**
- Tiene prioridad asignada (`priority:*`)
- Tiene tamaño estimado (S/M/L/XL)

**Automatización OpenClaw:**
- Triage agent asigna labels automáticas según contenido
- Si detecta que es un bug pero no tiene `type:bug`, comenta y corrige
- Si el issue es demasiado vago, comenta pidiendo más detalles
- Si no tiene prioridad, asigna `priority:medium` por defecto

**Comando equipo:** `sdlc-bot prioritize <issue> <priority>`

#### 5.2.2 Fase: Requisitos (`phase:req`)

**Trigger:** Label `phase:req` añadido.

**Gates de salida:**
- Título descriptivo
- Descripción con contexto
- Criterios de aceptación definidos (checklist)
- Enlaces a documentación o issues relacionados (opcional)

**Automatización OpenClaw:**
- Valida completitud de la issue contra plantilla
- Si falta algo: comenta con la sección faltante
- Si está completo y tiene `priority:critical`: notifica a Toni inmediatamente
- Si está completo y tiene approval: añade `ready:design`

**Comando equipo:** `sdlc-bot validate issue <number>`

#### 5.2.3 Fase: Diseño (`phase:design`)

**Trigger:** Label `phase:design` añadido.

**Gates de salida:**
- ADR (Architecture Decision Record) creado y mergeado
- Alternativas evaluadas
- Riesgos identificados
- Aprobación técnica

**Automatización OpenClaw:**
- Design Agent genera borrador de ADR:
  ```
  sdlc-bot generate-adr for issue #42
  ```
- Revisa el ADR cuando se abre PR con él
- Comenta trade-offs, riesgos, alternativas no consideradas
- Si hay cambios solicitados por reviewer, hace seguimiento

**Template ADR:**

```markdown
# ADR-{NÚMERO}: {TÍTULO}

**Estado:** {Propuesto | Aceptado | Rechazado | Deprecado}
**Fecha:** {YYYY-MM-DD}
**Issue:** #{número}
**Autor:** {nombre | sdlc-bot}

## Contexto
_¿Qué problema resolvemos? ¿Qué alternativas existen?_

## Decisión
_¿Qué hemos elegido y por qué?_

## Consecuencias
_¿Qué cambia? ¿Qué riesgos asumimos?_

## Alternativas Consideradas
| Alternativa | Pros | Contras |
|---|---|---|
| A | ... | ... |
| B | ... | ... |

## Referencias
- {enlaces}
```

#### 5.2.4 Fase: Desarrollo (`phase:dev`)

**Trigger:** Label `phase:dev` en el issue + PR creado.

**Gates de salida:**
- CI verde
- Code review completado
- Tests unitarios escritos y pasando
- Cobertura de código no disminuye

**Automatización OpenClaw:**
- Cuando se abre PR:
  - Code Review Agent analiza el diff
  - Comenta: archivos tocados, complejidad, patrones, riesgos
  - Verifica que hay tests para los cambios
- Cuando CI falla: label `blocked:dev`
- Cuando CI pasa + review solicitado: label `ready:review`
- Code Review Agent puede auto-aprobar cambios triviales (refactors, docs) bajo condiciones

**Comando equipo:**
```
sdlc-bot review pr #15          → análisis completo
sdlc-bot review pr #15 --quick  → solo hallazgos críticos
sdlc-bot review pr #15 --tests  → solo cobertura de tests
```

#### 5.2.5 Fase: QA (`phase:qa`)

**Trigger:** PR mergeado a staging, label `phase:qa`.

**Gates de salida:**
- Smoke tests pasan en staging
- Tests de integración verdes
- Tests E2E seleccionados pasan
- Sin regresiones críticas

**Automatización OpenClaw:**
- Verifica que CI en staging es verde
- Ejecuta workflow de smoke tests (trigger vía `gh workflow run`)
- Comenta resultado en el issue
- Si pasa: label `ready:release`
- Si falla: label `blocked:qa`, asigna al responsable

#### 5.2.6 Fase: Staging (`phase:staging`)

**Trigger:** Label `ready:release`.

**Gates de salida:**
- Release issue creada
- Release notes compiladas
- Changelog actualizado
- Aprobación del product owner

**Automatización OpenClaw:**
- Release Manager compila changelog desde conventional commits
- Crea release issue con notas
- Bump de versión (según conventional commits: major/minor/patch)
- Crea tag y draft release en GitHub
- Notifica a Toni para aprobación final

#### 5.2.7 Fase: Producción (`phase:prod`)

**Trigger:** Release aprobada y merge a main.

**Gates de salida:**
- Health check post-deploy verde
- Monitorización activa 1h post-deploy
- Post-mortem si hay rollback

**Automatización OpenClaw:**
- Tras merge a main + tag:
  - Crea GitHub Release (publicarla)
  - Comenta en cada issue incluido: "Shipped in vX.Y.Z 🚀"
  - Etiqueta todos como `phase:prod`
  - Inicia monitorización (health check endpoint)
- Si health check falla: notificar inmediatamente
- A las 24h: si no ha habido issues, cierra las release issues automáticamente

### 5.3 Mapa de transiciones (state machine)

```
Estado: phase:backlog
  ├── [validate + prioritize] → phase:req
  ├── [close] → closed
  └── [duplicate] → closed + comment "duplicate of #X"

Estado: phase:req
  ├── [complete] → phase:design
  ├── [blocked] → blocked:req
  └── [unblocked] → phase:req (desde blocked:req)

Estado: phase:design
  ├── [adr approved] → phase:dev
  ├── [blocked] → blocked:design
  └── [unblocked] → phase:design (desde blocked:design)

Estado: phase:dev
  ├── [pr opened + ci green + review ok] → phase:qa
  ├── [blocked] → blocked:dev
  └── [unblocked] → phase:dev (desde blocked:dev)

Estado: phase:qa
  ├── [all tests pass] → phase:staging
  ├── [blocked] → blocked:qa
  └── [unblocked] → phase:qa (desde blocked:qa)

Estado: phase:staging
  ├── [release approved] → phase:prod
  └── [blocked] → blocked:qa

Estado: phase:prod → closed (automatizado tras 24h sin issues)

Cualquier estado:
  └── [manual close] → closed
  └── [reject / descope] → phase:backlog o closed
```

---

## 6. Modelo de Agentes

### 6.1 El Coordinator (Sebas - modo SDLC)

El agente con el que interactúa el equipo. Es el único que recibe mensajes directos y el que decide qué especialista invocar.

| Atributo | Valor |
|---|---|
| **ID** | `main` |
| **Modelo** | `deepseek/deepseek-v4-flash` — razonamiento general, orquestación |
| **Canal** | Slack `#sdlc-bot` (o DM de Toni) |
| **Workspace** | `~/.openclaw/workspace-sdlc` |
| **Skills** | agent-security-eval, threat-modeler |
| **Standing Orders** | SDLC Governance (completo en sección 8) |

**Responsabilidades:**
1. Recibir mensajes del equipo (Slack/DM)
2. Interpretar la intención (¿es un comando SDLC o una conversación normal?)
3. Spawnear el sub-agente especialista adecuado
4. Sintetizar resultados y responder
5. Mantener la memoria del producto (decisiones, contexto)
6. Ejecutar comandos directos (`/review`, `/status`, `/release`)

### 6.2 Triage Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `gpt-5.4-nano` (barato, rápido) |
| **Coste** | ~$0.15/M tokens input |
| **Activación** | Bajo demanda (spawn) o por webhook |
| **Tareas típicas** | ~200-500 tokens por issue |

**System Prompt:**
```
Eres un Triage Agent para el SDLC del producto.
Tu única responsabilidad es categorizar issues de GitHub.

Reglas:
1. Lee el título y descripción del issue
2. Determina el tipo: feature, bug, tech-debt, improvement, security
3. Asigna labels: type:* y priority:* si aplican
4. Verifica completitud: título, descripción, criterios de aceptación
5. Si falta algo esencial: comenta en el issue pidiéndolo
6. Si está completo: añade label phase:req

No des opiniones técnicas. No hagas code review. No diseñes nada.
Solo categoriza y valida formato. Sé rápido y preciso.
```

**Activación típica:**
```javascript
// Coordinator: spawn triage
sessions_spawn({
  taskName: "triage-issue-42",
  model: "openai/gpt-5.4-nano",
  task: `Issue #42 recién creado. 
    Ejecuta: gh issue view 42 --json title,body,labels
    Clasifica y comenta según tus instrucciones.`
})
```

### 6.3 Code Review Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `gpt-5.4-mini` (medio, suficiente) |
| **Coste** | ~$0.60/M tokens input |
| **Activación** | Bajo demanda (spawn) |
| **Tareas típicas** | ~2000-8000 tokens por PR |

**System Prompt:**
```
Eres un Code Review Agent para el SDLC del producto.

Tu responsabilidad es analizar Pull Requests y dar feedback útil.

Reglas:
1. Obtén el diff: gh pr diff <number>
2. Identifica: archivos tocados, líneas añadidas/eliminadas
3. Revisa:
   - ¿Los cambios son coherentes con el objetivo del PR?
   - ¿Hay tests para los cambios?
   - ¿Sigue los patrones del proyecto?
   - ¿Hay problemas de seguridad obvios? (SQL injection, XSS, secrets)
   - ¿Hay código muerto, duplicado o innecesariamente complejo?
4. Comenta en el PR usando gh pr review
5. Devuelve resumen al coordinator

Prioriza hallazgos por severidad: 🔴 crítico > 🟡 warning > 🔵 sugerencia
Si el PR es trivial (< 50 líneas, docs/refactor): auto-aprueba
```

**Activación típica:**
```javascript
sessions_spawn({
  taskName: "review-pr-15",
  model: "openai/gpt-5.4-mini",
  task: `Analiza el PR #15 del repo <org>/<producto>.
    Sigue tu protocolo de code review.
    Si encuentras 🔴 críticos, indícalo en el resumen.`
})
```

### 6.4 Design/ADR Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `anthropic/claude-sonnet-4-6` (razonamiento profundo) |
| **Coste** | ~$3.00/M tokens input |
| **Activación** | Bajo demanda explícita |
| **Tareas típicas** | ~4000-15000 tokens por ADR |

**System Prompt:**
```
Eres un Arquitecto de Software especializado en diseño técnico.

Tu responsabilidad es generar y revisar Architecture Decision Records (ADRs).

Reglas:
1. Comprende el contexto del issue y las restricciones del proyecto
2. Identifica al menos 3 alternativas viables
3. Evalúa cada alternativa contra: 
   - Complejidad de implementación
   - Mantenibilidad a largo plazo
   - Rendimiento
   - Seguridad
   - Coste operativo
   - Alineación con arquitectura existente
4. Recomienda la mejor opción con justificación
5. Genera el ADR en el formato establecido y crea PR
6. Identifica riesgos y decisiones futuras que dependen de esta

Sé exhaustivo pero práctico. No diseñes en exceso. 
Cita referencias cuando sea relevante.
```

### 6.5 Release Manager Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `gpt-5.5` (fiable, consistente) |
| **Coste** | ~$10.00/M tokens input |
| **Activación** | TaskFlow de release |
| **Tareas típicas** | ~3000-6000 tokens por release |

**System Prompt:**
```
Eres un Release Manager Agent.

Tu responsabilidad es orquestar releases de principio a fin.

Workflow:
1. gh pr view <pr> --json headRefName,baseRefName,mergedBy,mergedAt
2. gh api repos/:owner/:repo/compare/previous-release...staging
3. Analiza commits con conventional commits:
   - fix: → patch bump
   - feat: → minor bump  
   - feat! / fix!: → major bump
   - Breaking change en cuerpo → major bump
4. Genera CHANGELOG.md seccionado:
   ## Added | Changed | Fixed | Security | Deprecated
5. gh release create vX.Y.Z --title "Release vX.Y.Z" --notes "$CHANGELOG"
6. Crea issue de release
7. Ejecuta smoke tests: gh workflow run smoke.yml --ref main
8. Espera resultado (gh run watch <id>)
9. Si falla: aborta, notifica, label blocked:qa
10. Si pasa: notifica "Release vX.Y.Z lista para aprobación"

Seguridad:
- No publicar releases sin approval humano
- Verificar que no haya dependencias con CVEs conocidos
- Confirmar que todas las issues en el release están en phase:qa o superior
```

### 6.6 Metrics Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `gpt-5.4-nano` (barato) |
| **Coste** | ~$0.15/M tokens |
| **Activación** | Cron (diario/semanal) |
| **Tareas típicas** | ~500-1500 tokens por informe |

**System Prompt:**
```
Eres un Metrics Agent. Generas informes cuantitativos del SDLC.

Tareas:
1. gh issue list --state closed --since <date> --json number,title,closedAt,labels
2. gh pr list --state merged --since <date> --json number,title,mergedAt,labels  
3. gh run list --workflow ci.yml --branch main --json conclusion,createdAt --limit 50
4. gh issue list --state open --json number,title,labels,updatedAt

Calcula:
- Cycle time medio (días desde phase:req hasta phase:prod)
- PRs mergeados por semana
- CI pass rate (pasados / totales)
- Issues abiertos por fase
- Stale issues (>14d sin mover)
- Bloqueadores activos

Formato: tabla markdown escueta. Solo números y desviaciones notables.
Si hay anomalías (>2σ del promedio histórico), márcalas con ⚠️.
```

### 6.7 Deep Research Agent

| Atributo | Valor |
|---|---|
| **Modelo** | `anthropic/claude-opus-4-6` (máxima capacidad) |
| **Coste** | ~$15.00/M tokens |
| **Activación** | Bajo demanda explícita (solo para casos complejos) |
| **Tareas típicas** | ~10000-50000 tokens |

**System Prompt:**
```
Eres un investigador técnico de élite. Solo te activan para problemas complejos.

Casos de uso:
- Investigación de vulnerabilidad de seguridad
- Análisis de regresión compleja
- Diseño de arquitectura para feature de alta complejidad
- Post-mortem profundo de incidente de producción

Reglas:
1. Recopila toda la evidencia disponible (issues, PRs, logs, código)
2. Identifica causa raíz (no síntomas)
3. Propone soluciones con análisis coste/beneficio
4. Documenta hallazgos en un issue o documento
5. Incluye referencias a código, commits o documentación

Cuando termines, entrega un informe estructurado y claro.
```

### 6.8 Mapa de activación (qué agente para qué tarea)

| Comando / Evento | Agente | Modelo | Coste |
|---|---|---|---|
| Issue creado | Triage Agent | gpt-5.4-nano | 💰 |
| Comentario en issue | Coordinator | deepseek-v4-flash | 💰💰 |
| "sdlc-bot status" | Metrics Agent | gpt-5.4-nano | 💰 |
| PR opened | Code Review Agent | gpt-5.4-mini | 💰💰 |
| "sdlc-bot review PR #X" | Code Review Agent | gpt-5.4-mini | 💰💰 |
| "sdlc-bot generate ADR" | Design/ADR Agent | sonnet | 💰💰💰💰 |
| Merge a staging | Release Manager | gpt-5.5 | 💰💰💰 |
| Weekly report (cron) | Metrics Agent | gpt-5.4-nano | 💰 |
| "sdlc-bot investigate #X" | Deep Research | opus | 💰💰💰💰💰 |
| "sdlc-bot release" | Release Manager | gpt-5.5 | 💰💰💰 |
| Post-mortem | Deep Research | opus | 💰💰💰💰💰 |
| Sprint planning | Coordinator + Metrics | varies | 💰💰 |

---

## 7. Integración con GitHub

### 7.1 Estrategia de integración

Se usan tres vías complementarias, ordenadas por prioridad:

| Vía | Dirección | Latencia | Fiabilidad | Uso |
|---|---|---|---|---|
| **ClawSweeper** | GitHub → OpenClaw | Tiempo real | Alta | Eventos de issues, PRs, comments |
| **gh CLI** | OpenClaw → GitHub | ~500ms | Muy alta | Lectura/escritura de datos, CI |
| **Webhook directo** | GitHub → OpenClaw | Tiempo real | Alta | Eventos no cubiertos por ClawSweeper |
| **GitHub API (REST/GraphQL)** | OpenClaw → GitHub | ~500ms | Muy alta | Operaciones complejas no disponibles en gh |

### 7.2 gh CLI — operaciones diarias

```bash
# Issues
gh issue list --label "phase:dev" --json number,title,assignee,updatedAt
gh issue view 42 --json title,body,labels,assignees,comments
gh issue comment 42 --body "Revisado por sdlc-bot. Criterios OK ✅"

# Pull Requests
gh pr list --state open --json number,title,headRefName,author
gh pr view 15 --json title,body,additions,deletions,files,reviews
gh pr diff 15
gh pr review 15 --approve --body "LGTM ✅"
gh pr review 15 --comment --body "Sugerencia: ..."
gh pr review 15 --request-changes --body "Bloqueante: ..."

# CI / Actions
gh run list --workflow ci.yml --branch main --json conclusion,headBranch
gh run watch <run-id> --exit-status
gh workflow run smoke.yml --ref staging

# Releases
gh release create v1.2.3 --title "v1.2.3" --notes "$CHANGELOG" --target main
gh release view v1.2.3 --json tagName,createdAt,url
gh release list --limit 10 --json tagName,isLatest

# API directa (REST)
gh api repos/:owner/:repo/compare/v1.0.0...v1.1.0 --jq '.commits | length'
gh api repos/:owner/:repo/actions/runs --jq '.workflow_runs[] | {conclusion, head_branch}'
gh api graphql -f query='
  query($owner:String!,$repo:String!) {
    repository(owner:$owner,name:$repo) {
      pullRequest(number:15) {
        reviews(first:10) { nodes { state, author { login }, body } }
        commits(last:5) { nodes { commit { message, statusCheckRollup { state } } } }
      }
    }
  }' -f owner="$OWNER" -f repo="$REPO"
```

### 7.3 ClawSweeper — eventos entrantes

Cuando GitHub envía un evento vía ClawSweeper, el flujo es:

1. GitHub event → ClawSweeper workflow → OpenClaw Gateway
2. Gateway recibe el evento como un message en la sesión del SDLC agent
3. El agent parsea el payload: `event.action`, `event.issue`, `event.pull_request`
4. Decide acción según el tipo de evento y el estado actual

**Matriz de eventos → acciones:**

```javascript
const EVENT_ACTIONS = {
  "issues.opened": {
    action: "triage issue",
    agent: "triage",
    priority: "normal"
  },
  "issues.labeled": {
    action: "check phase transition",
    agent: "coordinator",
    priority: "normal"
  },
  "pull_request.opened": {
    action: "initial review",
    agent: "code-review",
    priority: "normal"
  },
  "pull_request.ready_for_review": {
    action: "full review",
    agent: "code-review",
    priority: "high"
  },
  "pull_request.closed+merged": {
    action: "advance phase or release",
    agent: "coordinator",
    priority: "high"
  },
  "workflow_run.completed+failure": {
    action: "alert + label blocked",
    agent: "coordinator",
    priority: "critical"
  },
  "issue_comment.created": {
    action: "check if command or question",
    agent: "coordinator",
    priority: "normal"
  }
}
```

### 7.4 GitHub Actions CI integración

Los workflows de CI pueden notificar al SDLC agent de dos formas:

**Opción 1: ClawSweeper (recomendada)**
```
# Al final del workflow CI
- name: Notify SDLC Agent
  uses: openclaw/clawsweeper-dispatch@v1
  with:
    app_id: ${{ secrets.CLAWSWEEPER_APP_ID }}
    private_key: ${{ secrets.CLAWSWEEPER_APP_PRIVATE_KEY }}
    event_type: workflow_run
    conclusion: ${{ job.status }}
```

**Opción 2: GitHub Actions Status (vía API)**
```yaml
- name: Update PR Status
  run: |
    gh api repos/${{ github.repository }}/statuses/${{ github.sha }} \
      --field state="${{ job.status }}" \
      --field target_url="${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}" \
      --field description="SDLC Agent check" \
      --field context="sdlc-bot/validation"
```

### 7.5 GitHub Branch Protection + SDLC Agent

Configurar reglas de branch protection que refuercen el SDLC:

**`main`:**
- Require pull request before merging
- Require approvals: 1
- Dismiss stale reviews when new commits are pushed
- Require status checks to pass: CI, sdlc-bot/validation
- Require branches to be up to date
- Block force pushes
- Include administrators

**`staging`:**
- Require pull request before merging
- Require status checks to pass: CI
- Block force pushes

**`develop`:**
- Require pull request before merging (opcional)
- Block force pushes

---

## 8. OpenClaw como Orquestador

### 8.1 Standing Orders (en `AGENTS.md`)

```markdown
## Program: SDLC Governance

**Authority:** 
- Leer/escribir issues, PRs, releases en GitHub
- Añadir/quitar labels (excepto manuales)
- Comentar en issues y PRs
- Disparar workflows de Actions
- Spawnear sub-agentes especialistas

**Limitations (HARD BLOCKS):**
- NO puedo mergear PRs (lo hace el humano)
- NO puedo hacer deploy a producción (lo hace el humano)
- NO puedo eliminar issues
- NO puedo modificar branch protection rules
- NO puedo ejecutar código en producción
- NO puedo revelar secrets ni tokens

**Scope:** repo <org>/<producto>
**Triggers:** 
- Mensaje directo en Slack (Toni o #sdlc-bot)
- Evento de GitHub (issue, PR, CI)
- Cron programado
- Webhook entrante

**Approval gates:**
- Release a prod: requiere approval humano explicito
- Phase:req desde backlog: solo si tiene prioridad
- Phase:prod: requiere todas las fases anteriores completas

### Responsabilidades diarias

1. **Triage automático** — Issues nuevos: revisar, etiquetar, validar
2. **Code review** — PRs listos: analizar, comentar, sugerir
3. **CI monitor** — Pipelines rotos: detectar, etiquetar, notificar
4. **Stale tracker** — Issues/PRs sin actividad >7d: preguntar, cerrar si >14d
5. **Release** — PR mergeado a staging: preparar release candidate

### Comandos del equipo

| Comando | Acción |
|---|---|
| `sdlc-bot status` | Resumen del SDLC |
| `sdlc-bot review PR #X` | Code review completo |
| `sdlc-bot triage #X` | Clasificar y etiquetar issue |
| `sdlc-bot generate-adr for #X` | Borrador de ADR |
| `sdlc-bot release` | Iniciar proceso de release |
| `sdlc-bot metrics` | Métricas semanales |
| `sdlc-bot investigate #X` | Investigación profunda |
| `sdlc-bot next-phase #X` | Avanzar issue a siguiente fase |
| `sdlc-bot block #X "razón"` | Bloquear issue con motivo |
| `sdlc-bot unblock #X` | Desbloquear issue |

### Qué NO hacer

- No responder a mensajes que no sean comandos SDLC o consultas del producto
- No inventar decisiones técnicas sin ADR
- No cerrar issues sin confirmación
- No etiquetar como phase:prod si no ha pasado por todas las fases
- No dar falsos positivos en code review
```

### 8.2 Cron Jobs

```bash
# 1. SDLC Daily Health Check (09:00 laborables)
openclaw cron add \
  --name "SDLC Daily Health" \
  --cron "0 9 * * 1-5" \
  --tz "Europe/Madrid" \
  --session isolated \
  --model "openai/gpt-5.4-nano" \
  --message "Eres el Metrics Agent del SDLC.
    Genera el health check diario del repositorio <org>/<producto>:
    1. gh issue list --label 'phase:dev,phase:qa,phase:staging' --state open --json number,title,updatedAt,labels
    2. gh pr list --state open --json number,title,createdAt,labels,headRefName
    3. gh run list --workflow ci.yml --branch main --json conclusion,createdAt --limit 20
    4. gh issue list --state open --json number,title --search 'updated:<2026-07-15'
    Formatea como bullet points en Slack. Máximo 500 chars total.
    Marca problemas con 🔴 (rojo CI >6h), 🟡 (stale >7d), ⚪ (todo ok)." \
  --announce --channel slack --to "channel:C0123456789"

# 2. Sprint Planning Support (lunes 10:00)
openclaw cron add \
  --name "Sprint Planning" \
  --cron "0 10 * * 1" \
  --tz "Europe/Madrid" \
  --session isolated \
  --model "openrouter/deepseek/deepseek-v4-flash" \
  --message "Eres el Sprint Planning Agent.
    Prepara el sprint planning para <org>/<producto>:
    1. gh issue list --label phase:backlog,phase:req --state open --json number,title,labels,updatedAt
    2. Prioriza por: priority:critical > high > medium > low
    3. Agrupa por tipo: features, bugs, tech-debt
    4. Sugiere sprint backlog para 2 semanas:
       - Capacidad estimada: 10-15 story points
       - Ordena por dependencias
       - Incluye 20% buffer para bugs imprevistos
    5. Identifica blockers actuales
    Entrega un resumen listo para la reunión." \
  --announce --channel slack --to "channel:C0123456789"

# 3. Weekly SDLC Report (viernes 17:00)
openclaw cron add \
  --name "SDLC Weekly Report" \
  --cron "0 17 * * 5" \
  --tz "Europe/Madrid" \
  --session isolated \
  --model "openai/gpt-5.4-mini" \
  --message "Eres el Metrics Agent del SDLC.
    Genera el informe semanal para <org>/<producto>.
    Fecha: 2026-W$(date +%V). Semana: $(date +%Y-%m-%d).
    1. gh issue list --state closed --search 'closed:>2026-07-18' --json number,title,closedAt,labels
    2. gh pr list --state merged --search 'merged:>2026-07-18' --json number,title,mergedAt,labels,additions,deletions
    3. gh run list --workflow ci.yml --branch main --json conclusion,createdAt --limit 100
    4. gh release list --limit 5 --json tagName,createdAt,isLatest
    5. gh issue list --state open --json number,title,labels,updatedAt
    Calcula y reporta:
    - Issues cerrados: X
    - PRs mergeados: Y (Z añadidas, W eliminadas)
    - CI pass rate: A%
    - Cycle time medio: B días
    - Versión actual: vX.Y.Z
    - Issues abiertos: N (por fase)
    - Tendencias vs semana pasada
    Guarda el informe en sdlc/reports/weekly/$(date +%Y-%m-%d).md
    Al final: resumen ejecutivo de 3 líneas para Toni." \
  --announce --channel slack --to "user:U0BDCF5DYEP"

# 4. Stale Issues Check (08:00 laborables)
openclaw cron add \
  --name "Stale Issues" \
  --cron "0 8 * * 1-5" \
  --tz "Europe/Madrid" \
  --session isolated \
  --model "openai/gpt-5.4-nano" \
  --message "Eres el agente de cleanup del SDLC.
    Revisa issues inactivos en <org>/<producto>:
    1. gh issue list --state open --search 'updated:<$(date -d "-7 days" +%Y-%m-%d)' --json number,title,updatedAt,labels
    2. Para cada issue >7d sin actividad: gh issue comment X --body '🧹 Este issue lleva inactivo 7+ días. ¿Sigue siendo relevante? Responde o lo cerraré en 7 días.'
    3. gh issue list --state open --search 'updated:<$(date -d "-14 days" +%Y-%m-%d)' --json number,title
    4. Para cada issue >14d sin actividad y con comentario de aviso: gh issue close X --comment 'Cerrado por inactividad. Reabrir si es necesario.'
    Notifica a Toni si hubo cierres automáticos." \
  --announce --channel slack --to "channel:C0123456789"

# 5. CI Monitor (cada 2h, solo laborables)
openclaw cron add \
  --name "CI Monitor" \
  --cron "0 */2 * * 1-5" \
  --tz "Europe/Madrid" \
  --session isolated \
  --model "openai/gpt-5.4-nano" \
  --message "Eres el monitor de CI del SDLC.
    Revisa el estado de los pipelines en <org>/<producto>:
    1. gh run list --workflow ci.yml --branch main --json conclusion,createdAt,headBranch,displayTitle --limit 10
    2. gh run list --workflow ci.yml --branch staging --json conclusion,createdAt,headBranch,displayTitle --limit 5
    3. Para cada run fallido en >24h: gh run view <id> --log --job 2>&1 | tail -50
    Resumen. Si hay 🔴 nuevos desde última vez: notificar. Si no: silencio." \
  --announce --channel slack --to "channel:C0123456789"
```

### 8.3 Webhooks Plugin — Configuración

```bash
# Activar plugin
openclaw config set plugins.entries.webhooks.enabled true

# Configurar ruta para GitHub
openclaw config set plugins.entries.webhooks.config.routes.sdlc-github.path "/plugins/webhooks/sdlc-github"
openclaw config set plugins.entries.webhooks.config.routes.sdlc-github.sessionKey "agent:main:main"
openclaw config set plugins.entries.webhooks.config.routes.sdlc-github.secret-id "OPENCLAW_SDLC_WEBHOOK_SECRET"
openclaw config set plugins.entries.webhooks.config.routes.sdlc-github.controllerId "sdlc/github-events"

# Verificar
openclaw config get plugins.entries.webhooks
```

### 8.4 TaskFlows — Orquestación durable

#### 8.4.1 Release Flow (`sdlc/release`)

```
Input: PR number o "staging"
1. gh pr view <pr> --json headRefName,baseRefName,mergedBy,mergedAt,labels
2. gh api repos/:owner/:repo/compare/main...staging --jq '.ahead_by'
3. Si ahead_by === 0 → "No hay cambios nuevos para release"
4. gh api repos/:owner/:repo/compare/v$(latest_tag)...staging --jq '.commits[] | {message,sha,author}'
5. Clasificar commits por conventional commits
6. Determinar bump: fix→patch, feat→minor, breaking→major
7. Generar CHANGELOG.md con secciones
8. gh release create vX.Y.Z --title "Release vX.Y.Z" --notes "$CHANGELOG" --target staging --draft
9. gh issue create --label "phase:staging,ready:release" --title "Release vX.Y.Z" --body "$NOTES"
10. gh workflow run smoke.yml --ref staging
11. gh run watch <id> --exit-status
12. Si OK: gh release edit vX.Y.Z --draft=false
     gh pr create --base main --head staging --title "Release vX.Y.Z" --body "$REF_NOTES"
     Notificar: "✅ Release vX.Y.Z lista para merge a producción"
13. Si FAIL: gh release delete vX.Y.Z
     gh issue close <release-issue>
     Label blocked:qa en issues afectadas
     Notificar: "❌ Smoke tests fallaron. Release abortada"
```

#### 8.4.2 Code Review Flow (`sdlc/review`)

```
Input: PR number
1. gh pr view <pr> --json title,body,additions,deletions,files,reviews
2. gh pr diff <pr>
3. Si diff > 10000 líneas: 
   - Revisar solo archivos cambiados y resumen
   - Comentar: "PR grande (${lines} líneas). Recomiendo dividir"
4. Analizar por archivo:
   - Patrones, tests, seguridad, complejidad
5. gh pr review <pr> --comment --body "$REVIEW"
6. Si hallazgos críticos: gh pr edit <pr> --add-label "blocked:dev"
7. Si todo OK + ya hay CI verde: gh pr review <pr> --approve --body "LGTM ✅"
8. Devolver resumen al coordinator
```

#### 8.4.3 ADR Flow (`sdlc/adr`)

```
Input: Issue number
1. gh issue view <issue> --json title,body,labels,assignees
2. Buscar ADRs existentes: gh api repos/:owner/:repo/contents/docs/adr
3. gh api repos/:owner/:repo/git/refs/heads/main
4. Crear rama: adr/issue-<number>-<slug>
5. gh api repos/:owner/:repo/contents/docs/adr/ADR-{N}.md -f ... -m "docs: ADR-$N for issue #$issue"
6. gh pr create --base main --head adr/... --title "ADR-$N: $title" --body "Closes #$issue"
7. Comentar en issue: "Borrador ADR creado en PR #$pr"
```

### 8.5 Agent Workspace — Skills custom

#### Skill: SDLC Governance

Se recomienda crear un Skill reutilizable que encapsule todo el SDLC:

```markdown
# SDLC Governance Skill

Package reusable del SDLC agentico para OpenClaw.

## Contenido
- Standing Orders completos
- Templates de issues y ADR
- Flujos TaskFlow (release, review, adr)
- Configuración cron recomendada
- Configuración webhooks
- Herramientas gh CLI

## Instalación
1. Instalar gh CLI
2. gh auth login
3. gh label create... (ejecutar script de labels)
4. Activar webhooks plugin
5. Copiar ClawSweeper workflow al repo
6. Importar standing orders en AGENTS.md
7. Crear cron jobs
8. Verificar con `sdlc-bot status`

## Dependencias
- gh CLI >= 2.0
- OpenClaw >= 2026.6
- Plugins: webhooks, workboard
```

---

## 9. Configuraciones Detalladas

### 9.1 Instalación de la instancia SDLC

#### Opción A: Docker Compose (recomendada para producción)

```yaml
# docker-compose.sdlc.yml
version: '3.8'

services:
  openclaw-sdlc:
    image: openclaw/openclaw:2026.6.10
    container_name: openclaw-sdlc
    ports:
      - "18791:18789"  # Puerto diferente
    volumes:
      - ./sdlc-config:/home/node/.openclaw
      - ./sdlc-workspace:/home/node/.openclaw/workspace-sdlc
      - ./sdlc-state:/home/node/.openclaw/agents/main
    environment:
      - SDLC_GATEWAY_TOKEN=${SDLC_GATEWAY_TOKEN}
      - OPENCLAW_SDLC_WEBHOOK_SECRET=${OPENCLAW_SDLC_WEBHOOK_SECRET}
      - GH_TOKEN=${GH_TOKEN}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - SDLC_SLACK_BOT_TOKEN=${SDLC_SLACK_BOT_TOKEN}
      - SDLC_SLACK_SIGNING_SECRET=${SDLC_SLACK_SIGNING_SECRET}
      - OPENCLAW_AGENT_WORKSPACE=/home/node/.openclaw/workspace-sdlc
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:18789/healthz"]
      interval: 30s
      timeout: 5s
      retries: 3
```

```bash
# .env
SDLC_GATEWAY_TOKEN=<token-seguro>
OPENCLAW_SDLC_WEBHOOK_SECRET=<webhook-secret>
GH_TOKEN=<github-pat-con-repo-issues-prs-actions>
OPENAI_API_KEY=<sk-...>
ANTHROPIC_API_KEY=<sk-ant-...>
SDLC_SLACK_BOT_TOKEN=<xoxb-...>
SDLC_SLACK_SIGNING_SECRET=<...>
```

#### Opción B: Instalación bare-metal (VPS pequeño)

Requisitos mínimos:
- 1 CPU, 2GB RAM, 20GB SSD
- Node.js 24.x
- OpenClaw 2026.6+

```bash
# Setup rápido
curl -fsSL https://get.openclaw.ai | bash -s -- --channel stable

# gh CLI
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh -y
gh auth login

# Configurar
openclaw --profile sdlc configure
openclaw --profile sdlc gateway start --port 18791
```

### 9.2 Configuración de modelos por agente

```json5
{
  agents: {
    defaults: {
      // Modelos globales
      models: {
        "openai/gpt-5.4-nano": { 
          alias: "nano",
          params: { maxTokens: 4096 }
        },
        "openai/gpt-5.4-mini": { 
          alias: "mini",
          params: { maxTokens: 8192 }
        },
        "openai/gpt-5.5": { 
          alias: "gpt",
          params: { maxTokens: 16384 }
        },
        "anthropic/claude-sonnet-4-6": { 
          alias: "sonnet",
          params: { maxTokens: 32768, thinking: "low" }
        },
        "anthropic/claude-opus-4-6": { 
          alias: "opus",
          params: { maxTokens: 65536, thinking: "high" }
        },
        "openrouter/deepseek/deepseek-v4-flash": { 
          alias: "deepseek",
          params: { maxTokens: 32768 }
        }
      },
      model: {
        primary: "openai/gpt-5.4-nano",
        fallbacks: ["openrouter/deepseek/deepseek-v4-flash:free"]
      }
    },
    list: [
      {
        id: "main",  // Coordinator
        model: {
          primary: "openrouter/deepseek/deepseek-v4-flash",
          fallbacks: ["openai/gpt-5.5"]
        }
      }
    ]
  }
}
```

### 9.3 Comandos SDLC (Slack slash commands)

Para habilitar comandos tipo `/sdlc status` en Slack:

```bash
# Configurar el slack channel del SDLC con un bot
openclaw config set channels.slack.accounts[0].id "sdlc-bot"
openclaw config set channels.slack.accounts[0].token "$SDLC_SLACK_BOT_TOKEN"

# En Slack: crear slash command /sdlc
# Request URL: https://<openclaw-host>:18791/api/slack/commands
```

El agente interpreta comandos por lenguaje natural:
- "sdlc-bot status" → health check
- "sdlc-bot review PR #15" → code review
- "sdlc-bot release" → iniciar release
- "sdlc-bot bloqueado #42 por diseño incompleto" → label blocked:design + comentario

### 9.4 Integración OpenClaw Personal ↔ SDLC

Para que Sebas (personal) pueda consultar o iniciar acciones en el SDLC:

```javascript
// Desde Sebas: enviar comando al SDLC agent
sessions_send({
  agentId: "sdlc-bot",  // o sessionKey si es un agente remoto
  message: "status"
})

// Desde Sebas: disparar acción específica
sessions_send({
  agentId: "sdlc-bot",
  message: "review PR #15"
})

// O vía exec si es remoto:
exec("curl -X POST http://127.0.0.1:18791/api/agent/run \
  -H 'Authorization: Bearer $SDLC_GATEWAY_TOKEN' \
  -d '{\"message\":\"review PR #15\"}'")
```

---

## 10. Flujos Completos

### 10.1 Día típico con el SDLC agent

```
08:00 [Cron] Stale Issues Check
  → 2 issues >7d sin actividad
  → Comenta en ambos: "🧹 ¿Sigue siendo relevante?"
  → 0 cierres automáticos hoy

08:30 Toni: "sdlc-bot status"
  → Coordinator: spawn Metrics Agent
  → Metrics: gh queries → resume
  → Coordinator: "📊 SDLC Status:
    • 12 issues abiertos (3 dev, 2 qa, 1 staging, 6 backlog)
    • 4 PRs abiertos (2 en review, 1 draft, 1 blocked)
    • CI: 94% pass rate this week
    • 2 releases pendientes
    • PR #15 lleva 4 días sin review ← atención"

09:00 [Cron] SDLC Daily Health
  → Notifica a #sdlc-bot: "Todo OK. Nada urgente."

10:30 PR #17 abierto → ClawSweeper → Webhook → Coordinator
  → Coordinator: spawn Code Review Agent
  → Code Review: gh pr diff 17 → analiza
  → Comenta: "🔵 Revisión: 3 archivos, 120+ líneas
    auth.js: 🟡 validación insuficiente en login
    tests/ ✅ cubiertos
    Sugerencia: extraer lógica de validación a middleware"
  → Label: ready:review

14:00 Desarrollador termina PR #17, CI verde
  → Code Review Agent: auto-aprueba al ver cambios mínimos
  → Label: phase:qa
  → Comentario en issue #42: "🚀 QA ready"

16:30 Toni: "sdlc-bot release"
  → Coordinator: spawn Release Manager
  → Release Manager: TaskFlow release-flow
  → Crea v1.5.0 draft
  → Smoke tests pasan
  → Crea PR de staging a main
  → Notifica: "✅ Release v1.5.0 lista. PR #18 pendiente de merge"

17:00 [Cron] SDLC Weekly Report
  → Metrics Agent genera informe
  → Guarda en sdlc/reports/weekly/2026-07-25.md
  → Notifica a Toni
```

### 10.2 Gestión de bloqueos

```
Toni: "sdlc-bot block #47 por API externa no disponible"
  → Coordinator: gh issue edit 47 --add-label blocked:external
  → Coordinator: gh issue comment 47 --body "⛔ Bloqueado: API externa no disponible"
  → Coordinator: "✅ Issue #47 bloqueado por dependencia externa"

Desarrollador: "sdlc-bot unblock #47"
  → Coordinator: gh issue edit 47 --remove-label blocked:external
  → Coordinator: gh issue comment 47 --body "✅ Bloqueo resuelto"
  → Coordinator: "✅ Issue #47 desbloqueado"
```

### 10.3 Investigación profunda

```
Toni: "sdlc-bot investigate issue #53, producción caído 3 veces esta semana"
  → Coordinator: determina que requiere Deep Research
  → Spawn Deep Research Agent (opus)
  → Deep Research:
    1. gh issue view 53 → contexto
    2. gh run list --workflow deploy.yml --json conclusion --limit 20
    3. gh api repos/:owner/:repo/commits?sha=main&per_page=50 → cambios recientes
    4. Busca patrones: ¿coincide con deploys? ¿con cambios específicos?
    5. Revisa issues relacionados
  → Informe completo:
    "🔍 Investigación issue #53 completada
    Causa raíz: El commit a3f2b1 introdujo un memory leak en el pool de conexiones
    Afecta desde deploy v1.4.9 (2026-07-20)
    Propuesta: rollback parcial del commit a3f2b1 + hotfix pendiente
    Referencia: PR #15 cambió el pool manager"
```

### 10.4 Onboarding de nuevo desarrollador

```
Toni: "sdlc-bot, nuevo dev: María (@maria). Que empiece con el issue #8"
  → Coordinator: 
    "✅ María (@maria) asignada a issue #8
     Labels: phase:dev
     Ramas: feature/issue-8-authentication creada
     Recomiendo empezar por docs/CONTRIBUTING.md"
  → Crea rama feature
  → Asigna issue
  → Comenta con recursos útiles
```

---

## 11. Seguridad y Gobernanza

### 11.1 Principios de seguridad

1. **Mínimo privilegio** — El GitHub PAT solo tiene los scopes necesarios: `repo`, `issues`, `pull_requests`, `actions`, `contents`
2. **No mutación directa** — El agente nunca mergea, nunca hace deploy, nunca elimina
3. **Todas las acciones son trazables** — Cada acción del agente queda registrada como comment en GitHub o log en OpenClaw
4. **Loop prevention** — El ClawSweeper workflow ignora eventos del propio bot (`github.actor != 'sdlc-bot[bot]'`)
5. **Rate limiting** — Máximo N operaciones por minuto contra GitHub API
6. **Secretos** — Los tokens viven en variables de entorno, no en el workspace ni en memoria del agente

### 11.2 GitHub PAT scopes

```
Scopes mínimos para gh CLI:
- repo (full control of private repositories)
  - issues: write (comentar, etiquetar, cerrar)
  - pull_requests: write (comentar, review)
  - contents: write (crear ramas, ADR)
  - metadata: read
- actions: read (ver CI status)
- workflows: write (disparar workflows)

NO necesita:
- admin:org
- admin:repo_hook
- delete_repo
- user
```

### 11.3 Hard blocks en Standing Orders

```markdown
### HARD BLOCKS (the agent must never do these)

1. ❌ Never merge a pull request. Only humans merge.
2. ❌ Never deploy to production. Only humans deploy.
3. ❌ Never delete issues, labels, branches or releases.
4. ❌ Never modify branch protection rules.
5. ❌ Never execute code on production servers.
6. ❌ Never reveal API keys, tokens or secrets.
7. ❌ Never push directly to `main` or `staging`.
8. ❌ Never remove labels manually placed by humans.
9. ❌ Never assign or remove assignees without authorization.
10. ❌ Never approve own PRs or releases.
```

### 11.4 Auditoría

Cada acción del agente queda registrada:

```
GitHub:
- Comentarios: "🤖 sdlc-bot: [acción] [timestamp]"
- Labels: añade/quita con contexto

OpenClaw (logs):
- sdlc/logs/actions-YYYY-MM-DD.jsonl
- Cada línea: {timestamp, action, agent, target, result, tokens_used}

Cron jobs:
- Output visible en el canal #sdlc-bot
- Historial de ejecuciones: openclaw cron runs --id <job-id>
```

### 11.5 Plan de contingencia

| Escenario | Acción |
|---|---|
| El agente no responde | openclaw gateway restart; verificar logs |
| El agente comete un error en label/comment | Revertir manualmente en GitHub; reportar bug |
| GitHub PAT expira | gh auth login; actualizar token |
| Webhook no funciona | Verificar webhooks plugin; reconfigurar en GitHub |
| El agente alucina un release | El humano no aprueba → no se mergea. Seguro por diseño. |
| Rate limit de GitHub | Esperar; el cron reintenta automáticamente |
| Loop de eventos | ClawSweeper filtra eventos del bot |

---

## 12. Recomendaciones

### 12.1 Recomendaciones estratégicas

1. **Instancia dedicada > misma instancia.** El aislamiento vale la complejidad extra.

2. **GitHub > GitLab.** OpenClaw ya tiene ClawSweeper y gh CLI. La integración es nativa.

3. **Modelo barato por defecto, caro bajo demanda.** El 80% del trabajo (triage, metrics, stale checks) no necesita un modelo caro. Reserva sonnet/opus solo para diseño e investigación profundos.

4. **Comenzar con el coordinator + 2 especialistas.** No implementar todos los agentes de golpe. Primero: Triage y Code Review. Luego: Release Manager. Luego: Design/ADR. Luego: Deep Research.

5. **No automatizar todo.** Deja que el equipo se acostumbre al flujo antes de añadir automatización agresiva. Primero notificaciones, luego acciones.

6. **Feedback loop.** Cada acción automatizada debe ser revisable por un humano. Si el agente se equivoca, el humano debe poder corregirla fácilmente.

### 12.2 Recomendaciones técnicas

| Componente | Recomendación |
|---|---|
| **Host SDLC** | VPS pequeño (2GB RAM, 1 CPU) o contenedor Docker aparte |
| **Modelo coordinator** | deepseek/deepseek-v4-flash (buen equilibrio coste/calidad) |
| **Modelo triage** | gpt-5.4-nano (barato, suficientemente rápido) |
| **Modelo code review** | gpt-5.4-mini (mejor comprensión de código que nano) |
| **Modelo ADR** | claude-sonnet-4-6 (razonamiento arquitectónico) |
| **Modelo release** | gpt-5.5 (predecible, estructura consistente) |
| **Modelo deep research** | claude-opus-4-6 (solo bajo demanda explícita) |
| **Channels** | Slack para el equipo, más accesible que Telegram |
| **Almacenamiento** | Reports en workspace SDLC, no en GitHub |
| **gh CLI** | Instalar siempre, versión más reciente |

### 12.3 Recomendaciones de adopción

```
Semana 1-2:  Instalación y configuración
             - Montar instancia SDLC
             - Configurar gh, labels, ClawSweeper
             - Standing Orders básicos

Semana 3-4:  Triage + Notificaciones
             - Triage Agent activo
             - Cron health check
             - El equipo se acostumbra a los labels

Semana 5-6:  Code Review
             - Code Review Agent activo
             - El equipo recibe reviews automáticos
             - Ajustar sensibilidad del agente

Semana 7-8:  Releases
             - Release Manager activo
             - TaskFlow de release funcional
             - Primera release con supervisión

Semana 9+:   Agentes avanzados
             - Design/ADR Agent bajo demanda
             - Deep Research para incidentes
             - Ajustes finos según experiencia
```

### 12.4 Costes estimados (más probable)

| Componente                     | Coste/mes estimado     |
| ------------------------------ | ---------------------- |
| VPS (2GB RAM, 1 CPU)           | ~$6-12                 |
| Modelos LLM (uso SDLC típico)  | ~$20-50                |
| OpenAI API (triage + review)   | ~$15-30                |
| Anthropic API (ADR + research) | ~$5-20 (uso ocasional) |
| **Total**                      | **~$30-80/mes**        |
|                                |                        |

Sin instancia dedicada, solo los costes de API.

---

## 13. Hoja de Ruta

### Fase 0: Fundación (Semana 1)

- [ ] Decidir: instancia dedicada o perfil aislado
- [ ] Instalar/crear instancia OpenClaw SDLC
- [ ] Instalar gh CLI y autenticar
- [ ] Crear labels SDLC en el repo
- [ ] Configurar issue templates
- [ ] Crear ClawSweeper workflow en el repo
- [ ] Activar webhooks plugin
- [ ] Configurar standing orders básicos en AGENTS.md

**Hito:** `openclaws sdlc-bot status` funciona y responde datos reales.

### Fase 1: Observabilidad (Semana 2)

- [ ] Crear cron: SDLC Daily Health
- [ ] Crear cron: SDLC Weekly Report
- [ ] Crear cron: Stale Issues
- [ ] Crear cron: CI Monitor
- [ ] Configurar canal Slack #sdlc-bot (opcional)
- [ ] Verificar que los informes son útiles

**Hito:** El equipo recibe informes diarios/semanales automáticos del estado del SDLC.

### Fase 2: Triage Automático (Semana 3-4)

- [ ] Implementar Triage Agent (sub-agent)
- [ ] Conectar ClawSweeper issues.opened → triage
- [ ] Implementar validación de completitud
- [ ] Configurar labels automáticos según tipo
- [ ] Probar con issues reales y ajustar

**Hito:** Los issues nuevos se etiquetan automáticamente con tipo y fase correcta.

### Fase 3: Code Review (Semana 5-6)

- [ ] Implementar Code Review Agent
- [ ] Conectar ClawSweeper pull_request.opened → review
- [ ] Implementar análisis de diff
- [ ] Implementar auto-aprobación para cambios triviales
- [ ] Probar con PRs reales (primero en modo solo comentario)
- [ ] Ajustar sensibilidad y falsos positivos

**Hito:** El agente comenta en PRs con revisiones útiles que el equipo valora.

### Fase 4: Releases (Semana 7-8)

- [ ] Implementar Release Manager Agent
- [ ] Crear TaskFlow de release
- [ ] Implementar conventional commits → changelog
- [ ] Implementar bump de versión automático
- [ ] Conectar con smoke tests
- [ ] Primera release real supervisada

**Hito:** El agente prepara releases candidate que solo requieren aprobación humana.

### Fase 5: Agentes Avanzados (Semana 9+)

- [ ] Implementar Design/ADR Agent
- [ ] Implementar Deep Research Agent
- [ ] Implementar generación de post-mortem
- [ ] Añadir comandos avanzados al SDLC bot
- [ ] Integrar con Sebas (instancia personal) para consultas rápidas
- [ ] Abrir #sdlc-bot al equipo completo

**Hito:** El ecosistema SDLC completo es funcional y el equipo lo usa diariamente.

### Fase 6: Optimización (ongoing)

- [ ] Revisar costes de API vs valor generado
- [ ] Ajustar modelos según experiencia
- [ ] Añadir nuevos tipos de issues/PRs
- [ ] Refinar prompts de cada agente
- [ ] Implementar feedback loop: cuando un humano corrige al agente, el agente aprende
- [ ] Documentar lecciones aprendidas

---

## 14. Apéndices

### A. Referencias

- [OpenClaw Multi-Agent Routing](https://docs.openclaw.ai/concepts/multi-agent)
- [OpenClaw Sub-Agents](https://docs.openclaw.ai/tools/subagents)
- [OpenClaw Standing Orders](https://docs.openclaw.ai/automation/standing-orders)
- [OpenClaw Scheduled Tasks (CRON)](https://docs.openclaw.ai/automation/cron-jobs)
- [OpenClaw TaskFlow](https://docs.openclaw.ai/automation/taskflow)
- [OpenClaw Webhooks Plugin](https://docs.openclaw.ai/plugins/reference/webhooks)
- [OpenClaw CI/Pipeline](https://docs.openclaw.ai/ci)
- [OpenClaw Configuration — Agents](https://docs.openclaw.ai/gateway/config-agents)
- [GitHub CLI](https://cli.github.com/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [ADR (Architecture Decision Record)](https://adr.github.io/)

### B. Glosario

| Término | Definición |
|---|---|
| **SDLC** | Software Development Life Cycle |
| **ADR** | Architecture Decision Record |
| **Coordinator** | Agente principal que orquesta y responde al equipo |
| **Specialist Agent** | Sub-agente especializado en una tarea concreta |
| **ClawSweeper** | Sistema de OpenClaw que reenvía eventos de GitHub al agente |
| **Standing Orders** | Instrucciones permanentes que definen la autoridad del agente |
| **TaskFlow** | Orquestación durable de flujos multi-paso en OpenClaw |
| **Phase** | Etapa del SDLC representada por un label en GitHub |
| **Gate** | Condición que debe cumplirse para avanzar de fase |
| **HARD BLOCK** | Límite absoluto que el agente no puede violar bajo ninguna circunstancia |

### C. Plantilla de SOUL.md para el SDLC agent

```markdown
# SOUL.md — SDLC Agent Personality

Eres el SDLC Bot, un agente especializado en gobernanza del ciclo de vida
del software. No eres un asistente personal. No tienes conversaciones
sociales. Tu propósito es mantener el flujo de trabajo del producto
ordenado, trazable y eficiente.

## Principios

- **Precisión sobre amabilidad.** No necesitas saludar. Ve al grano.
- **Contexto completo.** Cuando reportes, incluye números, enlaces y datos.
  No asumas que el equipo recuerda los detalles.
- **Lo suficientemente autónomo.** Puedes tomar decisiones dentro de tu
  alcance (etiquetar, comentar, revisar). Sabes cuándo parar y pedir ayuda.
- **Sin falsa confianza.** Si no estás seguro de algo, dilo. No inventes.
- **Idioma:** Español con el equipo, inglés en comentarios técnicos de PRs.

## Tono

Directo. Profesional. Sin adornos. Si algo está mal, dilo claro.
Si algo está bien, reconócelo sin exagerar.

## Recordatorios

- Eres una herramienta para el equipo, no su sustituto.
- Tu objetivo no es reemplazar decisiones humanas, sino informarlas mejor.
- Cada acción que tomas debe ser trazable y reversible.
```

### D. Verificación post-instalación

Checklist para verificar que todo funciona:

```bash
# 1. Verificar gh CLI
gh auth status
gh issue list --limit 3

# 2. Verificar agente
openclaw status
openclaw agents list

# 3. Verificar cron jobs
openclaw cron list

# 4. Verificar webhooks
openclaw config get plugins.entries.webhooks

# 5. Verificar labels
gh label list --repo <org>/<producto>

# 6. Test triage
gh issue create --title "Test issue SDLC" --body "Testing el agente SDLC"
# → Ver que aparece label phase:backlog y comentario

# 7. Test code review (PR dummy)
# → Ver que el agente comenta

# 8. Test webhook
curl -X POST http://localhost:18791/plugins/webhooks/sdlc-github \
  -H "Authorization: Bearer $OPENCLAW_SDLC_WEBHOOK_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"test": true, "action": "ping"}'
```

---

*Documento generado por Sebas (OpenClaw Agent) el 2026-07-22.*
*Versión 1.0 — Sujeto a revisión y mejora continua.*
