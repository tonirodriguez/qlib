# Planificación Crypto

## Objetivo

Construir una línea de investigación cuantitativa sobre criptomonedas que sea
causal, reproducible y verificable, desde la descarga de datos hasta un posible
paper trading. Ningún resultado de este proyecto constituye una recomendación
de inversión ni autoriza operaciones reales.

El avance debe respetar este orden:

```text
Contención
→ corrección metodológica
→ datos robustos y atómicos
→ backtest realista
→ consolidación y experimento formal
→ paper trading
```

## Universo de investigación

El universo inicial contenía cinco activos:

- BTC
- ETH
- SOL
- XLM
- ADA

El universo ampliado validado técnicamente contiene nueve:

- BTC
- ETH
- SOL
- XLM
- ADA
- XRP
- DOGE
- LINK
- LTC

Los cuatro activos nuevos aportan exposiciones adicionales a pagos y consenso
(XRP), meme/retail y proof of work (DOGE), infraestructura y oráculos (LINK), y
pagos proof of work de larga trayectoria (LTC).

La incorporación técnica no demuestra que el universo ampliado mejore el
modelo. El experimento formal deberá comparar el universo original de cinco,
el ampliado de nueve y, si procede, una selección reducida mediante clustering.

## Estado general

| Fase | Estado | Resultado principal |
|---|---|---|
| 0. Contención | Completada | Resultados antiguos invalidados y marcados como investigación |
| 1. Corrección metodológica | Completada en su alcance actual | Leakage corregido y nested walk-forward validado |
| 2. Datos robustos | Completada en su alcance actual | Provider atómico, incremental, validado y trazable |
| 3. Backtest realista | Completada para las estrategias simples | Costes por turnover y escenarios optimista/base/adverso; el modelo SFM se descartó antes de cerrar esta fase |
| 4. Consolidación y experimento formal (SFM) | **Cancelada** | La auditoría de v8 confirmó tres fugas de futuro; sus métricas no son evidencia |
| 5. Paper trading | **En curso desde 2026-10-25** | TSMOM20 (momentum 20d + vol-target) y carry de funding, diarios |

## Reorientación 2026-10: SFM cerrado, trend following y carry

La línea SFM se cerró el 26-oct-2026 tras la auditoría de `AUDITORIA_V8.md`:
tres fugas de futuro confirmadas y cuantificadas invalidan sus resultados
(Sharpe 2.74, equity 20x). El cron diario de v8 se eliminó. Los ficheros se
conservan como base de código y comparación histórica, no como evidencia.

En su lugar se probaron dos estrategias simples y auditables, sin modelo ML:

- **TSMOM20** — momentum 20 días con vol-targeting (40% y 60%) y filtro de
  amplitud. Backtest 2016-2026 sobre 9 criptos con 10 pb por operación:
  vol40-breadth +4.625% total (42%/año, Sharpe 1.27, DD −41,3%) frente a BTC
  buy&hold +18.519% (Sharpe 1.06, DD −83,3%). El retorno está concentrado en
  2017, 2020 y 2021; pierde en 2016, 2018, 2022 y 2026. t-stat ≈ 1,4.
- **Carry de funding** — long spot + short perpetuo. Variante "siempre"
  +116,4% total (12,0%/año, Sharpe 4.60, DD −6,5%). El Sharpe está inflado por
  la baja volatilidad diaria del funding; el rendimiento real ha caído a
  ~4-5%/año en los últimos cinco años. Riesgo de contraparte no modelado.

Correlación diaria entre ambas ≈ 0,00 (rolling 63d media −0,15): se
complementan. La combinación 50/50 mejora el Sharpe a 1.85 y reduce el DD a
−21,4% en el backtest, aunque el TSMOM no bate claramente a holdear BTC.

**Estado real del paper trading:** capital ficticio 10.000 € por variante.
TSMOM20 corre a diario a las 09:00 (hoy 100% efectivo: 0 señales, amplitud 0%);
carry a las 09:05 (carry-9 +16,82 pb, carry-majors +3,81 pb al 26-oct). Ninguna
de las dos está aprobada para capital real: deben acumular semanas de datos en
vivo y superar una revisión explícita. Los gates de las fases 0-2 siguen siendo
el marco de referencia; las fases 3-4 se reinterpretan para estrategias sin ML.

## Fase 0. Contención

### Objetivo

Evitar que resultados afectados por fuga temporal o validaciones insuficientes
se interpreten como evidencia financiera o se utilicen en operativa.

### Acciones

- Marcar los experimentos SFM v2, v3 y v4 originales como `research-only`.
- Invalidar sus métricas, gráficas, JSON y checkpoints como evidencia fuera de
  muestra.
- Identificar v5 como experimento sobre S&P 500, no sobre criptomonedas.
- Separar las nuevas salidas causales de los artefactos antiguos.
- Bloquear la generación diaria de señales mientras no exista un artefacto
  completo y validado.
- Prohibir la conexión del prototipo con ejecución de órdenes.

### Criterios de aceptación

- Los artefactos históricos muestran claramente su estado inválido.
- Ningún script incompleto puede generar señales operativas silenciosamente.
- Las ejecuciones nuevas escriben en directorios distintos.

### Estado

Completada.

## Fase 1. Corrección metodológica

### Objetivo

Eliminar fugas de información futura y garantizar que entrenamiento,
selección y evaluación respetan estrictamente el tiempo.

### Acciones realizadas

- Desactivar el denoising wavelet aplicado sobre la serie completa.
- Ajustar clipping exclusivamente con observaciones de entrenamiento.
- Ajustar el scaler exclusivamente con entrenamiento y reutilizarlo sin
  `fit` sobre validación o test.
- Mantener labels de retorno futuro alineadas como objetivo `t+1`.
- Añadir tests anti-leakage y de costes por cambios de posición.
- Desactivar el walk-forward antiguo porque reutilizaba hiperparámetros
  seleccionados globalmente.

### Acciones pendientes

- Ejecutar el protocolo nested formal con el presupuesto completo de trials,
  epochs y seeds después de cerrar el modelo de costes.
- Congelar la configuración ganadora antes de abrir el holdout final.

### Criterios de aceptación

- Cambiar cualquier observación posterior a `t` no altera ninguna feature o
  predicción anterior o igual a `t`.
- Cada fold conserva sus propios parámetros de preprocessing.
- El holdout final nunca aparece en operaciones de `fit` o selección.
- Todos los tests temporales pasan offline.

### Estado actualizado

- Cada fold nested crea un estudio Optuna independiente.
- Clipping y scaler se ajustan por separado con el train de cada fold.
- Las ventanas externas de test son contiguas, disjuntas y terminan antes del
  holdout final.
- El smoke de dos folds produjo Sharpe 2,04 y -2,16, con media -0,06 y
  desviación 2,10. La fuerte dispersión confirma que una sola ventana no es
  evidencia suficiente.
- El holdout final conserva 165 fechas y permanece marcado como no evaluado.

## Fase 2. Datos robustos, reproducibles y atómicos

### Objetivo

Disponer de un dataset Qlib fiable, trazable y seguro ante interrupciones o
actualizaciones parciales.

### Acciones realizadas

- Descargar OHLCV público mediante CCXT y Binance.
- Normalizar timestamps en UTC.
- Incorporar reintentos, backoff, límites de paginación y controles de
  monotonía.
- Restringir los patrones de nombres para impedir escrituras fuera del
  directorio configurado.
- Escribir CSV mediante archivo temporal y reemplazo.
- Generar un manifest de descarga con hashes SHA-256, rango y número de filas.
- Construir y validar un provider Qlib de nueve activos.
- Verificar 1.100 velas diarias por activo para el periodo común comprendido
  entre 2023-08-11 y 2026-08-14.

### Acciones pendientes

- Añadir alertas operativas de datos obsoletos y tolerancias de continuidad
  cuando se programe la actualización automática.
- Conservar versiones históricas de manifests cuando se implante retención de
  datasets.

### Criterios de aceptación

- Dos ejecuciones con las mismas entradas producen el mismo manifest y hashes.
- Una ejecución fallida no altera el provider activo.
- Qlib carga exactamente los instrumentos y fechas declarados.
- No se publican datasets con errores de esquema o continuidad.

### Estado actualizado

- El provider se construye completamente en staging.
- Antes de publicar se validan calendario, universo y todos los binarios.
- La sustitución conserva el provider anterior como backup recuperable hasta
  que la nueva versión queda publicada.
- Un fallo previo a la publicación no modifica el provider activo.
- La descarga es incremental con siete días de solapamiento configurable.
- Las velas diarias abiertas se excluyen.
- El dataset activo contiene 1.099 velas cerradas por activo, desde 2023-08-11
  hasta 2026-08-13.
- El manifest Qlib registra nueve instrumentos y hashes de 93 ficheros.

## Validación del universo ampliado

Esta actividad conecta las fases 2, 3 y 4.

### Acciones

- Calcular correlaciones Pearson y Spearman de retornos.
- Comparar correlaciones en ventanas móviles y distintos regímenes.
- Aplicar clustering sobre retornos, volatilidad, volumen y drawdowns.
- Comparar XRP frente a XLM para medir duplicación del factor pagos.
- Comparar LTC frente a BTC para medir la aportación marginal del factor PoW.
- Comprobar que DOGE y LINK aportan comportamientos distintos y no solo mayor
  volatilidad.
- Definir un máximo de activos por cluster.
- Medir cobertura, gaps, liquidez y estabilidad por activo.
- Crear dos aproximaciones:
  - panel balanceado de nueve activos desde 2023-08-11;
  - universo point-in-time con fechas reales de elegibilidad.
- Registrar listings, delistings, rebrandings y activos fallidos para reducir
  el sesgo de supervivencia.

### Decisión esperada

Determinar si se conserva el universo de nueve o si se elimina algún activo
redundante antes del experimento formal. Esta decisión se tomará exclusivamente
con train y validación, nunca observando el holdout final.

### Resultado del primer análisis

El análisis utilizó 934 fechas entre 2023-08-11 y 2026-03-01. Las 165 fechas
entre 2026-03-02 y 2026-08-13 permanecieron reservadas como holdout y no
participaron en correlaciones ni clustering.

- XRP y XLM forman el mismo cluster. Su correlación Pearson fue 0,754, la
  Spearman 0,846 y la mediana móvil de 90 días 0,843. Existe redundancia clara
  que deberá contrastarse mediante ablación.
- LTC quedó en un cluster propio. Su correlación Pearson con BTC fue 0,604 y la
  mediana móvil de 90 días 0,674, por lo que aporta más diversidad que la
  anticipada por una comparación puramente narrativa.
- BTC, ETH, SOL, ADA, DOGE y LINK formaron un cluster amplio bajo el umbral de
  distancia configurado. Esto no implica eliminar activos automáticamente:
  sus volatilidades, liquidez y contribución predictiva siguen siendo distintas.

El experimento formal deberá comparar al menos el universo completo de nueve
contra variantes sin XLM y sin XRP. La elección definitiva no utilizará el
holdout reservado.

## Fase 3. Backtest realista

### Objetivo

Estimar el comportamiento neto de la estrategia bajo condiciones operativas
plausibles, sin presentar un backtest simplificado como resultado ejecutable.

### Acciones realizadas

- Utilizar 365 periodos anuales para datos diarios de criptomonedas.
- Cobrar costes solo cuando cambia la posición.
- Contabilizar dos operaciones al cambiar directamente de un activo a otro.
- Calcular turnover y drawdown máximo.
- Ejecutar la señal sobre el retorno futuro, evitando ejecución retrospectiva
  en la misma vela de información.

### Acciones pendientes

- Sustituir las comisiones genéricas por tiers maker/taker documentados para el
  venue y tamaño de cuenta definidos.
- Hacer que spread y slippage dependan de liquidez y tamaño de orden.
- Definir latencia y ejecución en la siguiente vela disponible.
- Incorporar funding y coste de préstamo si se permiten cortos o derivados.
- Aplicar límites de volumen negociado, exposición y concentración.
- Modelar posiciones cash explícitamente.
- Añadir hit rate y exposición por activo.
- Calcular intervalos de confianza mediante bootstrap temporal por bloques.
- Corregir multiple testing mediante PSR/DSR u otra metodología documentada.
- Comparar con baselines simples: cash, equal weight, buy-and-hold, momentum y
  predicción ingenua.

### Criterios de aceptación

- Todos los resultados se muestran netos de costes.
- La estrategia conserva un comportamiento aceptable bajo el escenario
  adverso definido previamente.
- Las métricas incluyen incertidumbre y no solo estimaciones puntuales.
- Ninguna decisión se toma usando el holdout final.

### Estado actualizado

- Se calculan escenarios optimista, base y adverso con comisión, half-spread y
  slippage diferenciados.
- Los costes se cargan por cada lado ejecutado; cambiar directamente de activo
  cuenta como salida y nueva entrada.
- Las métricas incluyen Sharpe, Sortino, Calmar, drawdown máximo, VaR 95%,
  CVaR 95%, retorno anualizado y turnover.
- Los tests verifican que la equity se deteriora de forma monótona al pasar del
  escenario optimista al base y al adverso.

## Fase 4. Consolidación y experimento formal

### Objetivo

Convertir los prototipos en un flujo mantenible y ejecutar una comparación
formal, reproducible y estadísticamente defendible.

### Acciones de consolidación

- Crear un entorno Conda exclusivo para el proyecto crypto.
- Evitar el conflicto actual entre PyTorch 2.2/NumPy 1.x y las dependencias de
  `finance` que requieren NumPy 2.x.
- Fijar versiones y generar un lockfile reproducible.
- Unificar la lógica v2-v4 en un paquete configurable.
- Separar físicamente los experimentos S&P 500 del directorio crypto.
- Eliminar paths absolutos y configurar rutas, fechas y universo mediante
  variables o ficheros versionados.
- Configurar CI con tests unitarios e integración offline.
- Convertir el notebook en consumidor de módulos probados y ejecutarlo desde
  cero sin outputs locales ni paths del autor.

### Diseño del experimento formal

- Comparar tres universos:
  - cinco activos originales;
  - nueve activos ampliados;
  - universo reducido mediante clustering, si procede.
- Utilizar exactamente las mismas fechas, folds, costes y presupuesto de
  Optuna para las tres variantes.
- Ejecutar múltiples seeds.
- Usar nested walk-forward y un holdout final intocable.
- Registrar duración, consumo, configuración y resultados de cada ejecución.
- Analizar rendimiento agregado y contribución marginal por activo.
- Exigir que cualquier mejora sea estable entre seeds, folds y escenarios de
  costes.

### Artefacto reproducible

Cada modelo deberá incluir o referenciar:

- pesos del modelo;
- arquitectura e hiperparámetros;
- scaler y límites de clipping;
- orden exacto de activos y features;
- esquema de entrada y salida;
- commit del repositorio;
- hash y manifest del dataset;
- versiones de Python y dependencias;
- seed y configuración del experimento;
- rango temporal de train, validación y test;
- métricas y escenarios de costes.

### Criterios de aceptación

- Un entorno limpio reproduce un experimento pequeño y todos sus tests.
- El artefacto falla de forma segura si el esquema o el universo no coinciden.
- La comparación 5 vs. 9 usa el mismo protocolo y no favorece una variante.
- Los resultados formales incluyen incertidumbre, baselines y sensibilidad a
  costes.

## Fase 5. Paper trading

### Objetivo

Validar durante un periodo prolongado el flujo de datos, inferencia, costes y
controles sin enviar órdenes reales.

### Condiciones de entrada

- Todas las fases anteriores están aprobadas.
- Nested walk-forward y holdout final completados.
- Artefacto reproducible generado y verificado.
- Backtest realista supera los umbrales definidos previamente.
- Revisión explícita de datos, modelo, backtest y riesgo operativo.

### Acciones

- Cargar un artefacto versionado, nunca pesos aislados.
- Validar esquema, orden de activos y freshness antes de cada inferencia.
- Confirmar que la vela utilizada está cerrada.
- Registrar inputs, predicciones, posiciones simuladas, costes y resultados.
- Reconciliar señales contra datos posteriores y precios ejecutables.
- Aplicar límites de exposición, concentración, turnover y drawdown.
- Implementar alertas y un kill switch probado.
- Detener el sistema ante datos stale, gaps, cambios de esquema o divergencias.
- Mantener paper trading durante un mínimo de 30 días antes de cualquier
  nueva decisión.

### Criterios de aceptación

- No existen desalineaciones entre features, activos, predicciones y retornos.
- Las señales y costes se reconcilian diariamente.
- Los controles y el kill switch han sido probados.
- No se superan los límites de riesgo definidos.
- La revisión final documenta explícitamente aprobar, prolongar o rechazar el
  paso siguiente.

## Uso real

El paper trading no implica aprobación automática para trading real. Una posible
operativa requeriría un proyecto y una autorización independientes que cubran,
como mínimo, custodia, credenciales de mínimo privilegio, límites financieros,
cumplimiento, monitorización, respuesta a incidentes y aprobación humana.

## Próximas acciones prioritarias (revisadas 2026-10-27)

1. Acumular y revisar el paper trading diario de TSMOM20 y carry (09:00 y 09:05).
2. Corregir el arranque del libro TSMOM: el capital no compone el primer día y
   el ledger parece congelado en 10.000 €. Revisar la condición `fecha > start`.
3. Documentar el desfase de un día en los datos de funding del carry.
4. Medir en vivo la correlación TSMOM/carry y validar la combinación 50/50.
5. Decidir con datos de al menos 30 días si alguna merece capital real; por
   defecto, no.
6. Si se retoma un modelo ML, exigir nested walk-forward, holdout intocable y
   auditoría anti-leakage antes de cualquier backtest creíble.
7. Congelar el pipeline SFM v8 como referencia histórica; no reprogramarlo.
