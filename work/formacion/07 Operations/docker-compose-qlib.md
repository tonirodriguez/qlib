# docker-compose.yml — Montar workspace + datos Qlib desde el host

## 📁 Estructura esperada en el host

```
/opt/toni/openclaw/
├── .qlib/              ← datos Qlib (calendars, features, instruments)
│   └── qlib_data/
│       ├── cn_data/
│       └── us_data/
└── workspace/          ← repositorio agent_qlib
    ├── qlib/
    │   ├── docker-compose.yml
    │   └── ...
    └── ...
```

El `docker-compose.yml` monta:

| Host | Contenedor |
|------|-----------|
| `/opt/toni/openclaw/workspace` | `/home/node/.openclaw/workspace` |
| `/opt/toni/openclaw/.qlib` | `/home/node/.qlib` |

## ▶️ Arrancar

```bash
cd /opt/toni/openclaw/workspace/qlib
docker compose up -d
```

## 🔍 Verificar montaje

```bash
# Workspace (el repo)
docker exec openclaw-qlib ls /home/node/.openclaw/workspace/qlib/scripts

# Datos Qlib
docker exec openclaw-qlib ls /home/node/.qlib/qlib_data/us_data/instruments/
# → all.txt  nasdaq100.txt  sp500.txt
```

## 📌 Notas

- El contenedor corre como `node:node` (UID 1000) — asegúrate de que `/opt/toni/openclaw/` sea legible por UID 1000 en el host.
- La wiki de Qlib está en `http://<IP_DEL_HOST>:8016/`.
- El gateway de OpenClaw está en `http://<IP_DEL_HOST>:18789/`.
