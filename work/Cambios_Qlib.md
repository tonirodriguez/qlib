# 📋 Cambios_Qlib — Registro de archivos modificados / con rutas externas

> **Fecha:** 2026-08-14
> **Repo:** `/opt/data/qlib` (clon de `tonirodriguez/qlib`, fork de microsoft/qlib)
> **Contexto:** tras reestructurar el repo (los archivos de trabajo se movieron a `work/`), este documento registra qué archivos **fuera de `work/`** hemos creado/modificado nosotros y qué ficheros contienen **rutas a otra máquina** (no deben modificarse aquí).

---

## 1. Archivos NUESTROS creados fuera de `work/`

Estos no existen en el repo original de microsoft/qlib — los creamos nosotros durante las sesiones de esta máquina.

| Ruta | Qué es | Origen |
|---|---|---|
| `scripts/update_us_qlib_daily_here.sh` | **Wrapper de actualización ligera** de datos US (canal paralelo, adaptado a las rutas de esta máquina Hermes) | Creado hoy (commits `ce895b6d`, `1e84de27`) |

**Nota:** no hay más archivos propios fuera de `work/` — todo el resto de nuestro trabajo (scripts de momentum, experimentos, simulación, docs) vive en `work/estrategias/` y `work/qlib_work/`.

---

## 2. Archivos con rutas a OTRA máquina (NO modificar aquí)

Estos ficheros contienen rutas de la **otra máquina de Toni** (WSL/Windows: `/home/toni/...` y `/mnt/c/Users/toni/...`). **Pertenecen al data-collection del entorno original y NO deben modificarse en esta máquina** — la regla de oro del proyecto es no tocar la infraestructura de actualización de datos oficial.

| Ruta | Rutas a otra máquina |
|---|---|
| `scripts/task_load_data.sh` | `/home/toni/miniconda3/...`, `/mnt/c/Users/toni/src/qlib/...`, `/mnt/c/Users/toni/OneDrive...` |
| `scripts/update_us_qlib_daily.sh` | `/home/toni/miniconda3/envs/qlib/bin/python` |
| `scripts/update_us_qlib_rebuild.sh` | `/home/toni/.qlib/qlib_data/us_data/` |
| `scripts/update_sp500_qlib_daily.sh` | `/mnt/c/Users/toni/src/qlib` |
| `scripts/update_nasdaq_qlib_daily.sh` | `/mnt/c/Users/toni/src/qlib` |
| `scripts/check_us_qlib_update.py` | rutas `/home/toni` |
| `scripts/update_sp500.py` | rutas `/home/toni` |
| `scripts/update_nasdaq100.py` | rutas `/home/toni` |
| `scripts/test_normalización.ipynb` | `/home/toni/.qlib/qlib_data/us_data` (outputs) |
| `scripts/graph_stock.ipynb` | `/home/toni/.qlib/qlib_data/us_data` (outputs) |
| `examples/tutorial/detailed_workflow_US.ipynb` | `/home/toni/.qlib/qlib_data/us_data` (outputs) |
| `examples/workflow_autogluon.ipynb` | `/home/toni/.qlib/qlib_data/us_data`, `/home/toni` |

⚠️ **IMPORTANTE:** estos archivos son del flujo de data-collection original (WSL/Windows). Sus rutas apuntan a la otra máquina de Toni y se ejecutan ahí, **no en esta máquina Hermes**.

---

## 3. Archivos de la RAÍZ que no son de Microsoft

| Ruta | Qué es | Nota |
|---|---|---|
| `investment_data-2026-01-20.zip` | Zip de conectores de datos (36 KB) | Visto al inicio del proyecto; no es de microsoft/qlib core |
| `selector.log` | Log de selección (0 bytes) | Sin contenido relevante |
| `verify_env.py` | Script de verificación de entorno (931 bytes) | Herramienta auxiliar |
| `.codex` | Configuración de Codex | Config local del usuario |

---

## 4. Resumen

**Fuera de `work/`, lo que no es de microsoft/qlib:**
1. **`scripts/update_us_qlib_daily_here.sh`** — NUESTRO (creado hoy, único archivo propio fuera de work/)
2. **Ficheros de la otra máquina** (data-collection con rutas `/home/toni` y `/mnt/c`) — NO tocar, pertenecen al entorno WSL/Windows original
3. **Raíz:** `investment_data-2026-01-20.zip`, `selector.log`, `verify_env.py`, `.codex` — auxiliares

**Todo el resto de nuestro trabajo** (scripts de estrategias, experimentos momentum, simulación paper-trading, documentación) vive en:
- `work/estrategias/` (scripts y experimentos)
- `work/estrategias/simulation/` (paper-trading momentum 120d)
- `work/qlib_work/` (documentación y diagnósticos)

---

*Documento de referencia del proyecto. Se actualiza si cambia la estructura o se detectan más rutas externas.*
