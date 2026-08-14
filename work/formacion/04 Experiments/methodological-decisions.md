# Decisiones metodológicas

## Decisiones ya tomadas

### Usar Microsoft Qlib como base oficial

**Decisión:** usar Qlib desde el repo clonado en `vendor/microsoft-qlib`.

**Por qué:** era un requisito del proyecto y evita depender del paquete publicado en PyPI.

### Nombrar el paquete propio `qlib_project`

**Decisión:** no usar `qlib` como nombre del paquete interno.

**Por qué:** evita colisiones de import con la librería oficial.

### Usar un baseline reproducible estable antes de ampliar el espacio experimental

**Decisión:** fijar primero `Alpha158 + csi300` como referencia.

**Por qué:** permite comparar variantes con sentido y no perder trazabilidad.

### No declarar ganador un modelo solo por `IC`

**Decisión:** evaluar siempre también:

- retorno con costes
- information ratio
- drawdown
- comportamiento de portfolio

**Por qué:** ya hay evidencia directa de desacople entre señal y monetización.

## Decisiones provisionales

### Priorizar robustez frente a retorno aislado

**Decisión provisional:** seguir usando el baseline como referencia principal, aunque `tuned + top20` tenga mayor retorno anualizado.

**Por qué:** el drawdown y el `IR` de esa variante todavía son peores.

### Explorar primero portfolio antes de cambiar muchas cosas del modelo

**Decisión provisional:** agotar algo más la capa de portfolio sobre la tuned antes de abrir demasiadas variantes de features/modelo.

**Por qué:** ya vimos que ahí hay sensibilidad real.
