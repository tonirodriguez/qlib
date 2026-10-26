# Fase 1 — Sizing de exposición por régimen con Jev (OpenRouter)

> ### ❌ RESULTADO FINAL: DESCARTADO
> Fase 2 ejecutada el 2026-10-26. **Ninguna de 7 fórmulas supera al `vol_gate`.**
> Causa raíz: las probabilidades de Jev no tienen rango dinámico — nunca superó
> `P(crisis) > 0.5` en 9 años. Ver **§6** (resultado) y `JEV_GUIA.md` §10 (guía).
>
> Este documento se conserva como registro del diseño y de la metodología.
> `vol_gate.py` sigue siendo la solución en uso.

**Estado:** Fase 1 implementada y verificada en vivo (`jev_regime.py`).
Fase 2 ejecutada y cerrada con resultado negativo.
**Fecha:** 2026-10-26
**Alcance:** capa de decisión AISLADA. No toca el paper-trading vivo ni los
simuladores E1/E2/E3.

---

## 1. Qué hemos construido y por qué así

`extract_estados.py` ya produce los *indicadores* de régimen
(`vol_pct`, `drawdown120`, `mom_crash`). Lo que faltaba era la **capa de
decisión**: convertir esos indicadores en una exposición concreta.

La Fase 0 demostró que el endpoint nativo de decisiones de Jev
(`POST https://openrouter.ai/api/alpha/decisions`, modelo
`~typesafe/jev-latest`) no devuelve sólo una etiqueta, sino
**probabilidades calibradas sobre las opciones**:

```json
{
  "model": "typesafe/jev-1.14-20261014",
  "answers": {
    "regimen": {
      "type": "choice",
      "choice": "crisis",
      "probabilities": {"risk_on": 0, "neutral": 0.03, "risk_off": 0.09, "crisis": 0.88},
      "confidence": 0.84
    }
  },
  "usage": {"input_tokens": 522, "output_tokens": 50, "cost": 2.1924e-05},
  "provider": "TypeSafe"
}
```

Ese vector es lo interesante: permite **sizing continuo** en lugar de un
interruptor on/off. Un clasificador de etiquetas habría dado lo mismo que un
`if vol_pct > 0.9`, sin justificar el uso de Jev. La probabilidad sí aporta:
distingue "crisis 88%" de "crisis 100%" y escala la posición en consecuencia.

### Fórmula acordada

```
exposicion = 1 - P(crisis) - 0.5 * P(risk_off)      acotada a [0, 1]
```

- `crisis` resta exposición completa (posición fuera).
- `risk_off` resta media exposición (recorte parcial).
- `neutral` y `risk_on` no restan.

Con el vector real de arriba: `1 - 0.88 - 0.5*0.09 = 0.075` → **7,5 % de
exposición** en un mercado de crisis. En `risk_on_calm` da **1.00** (exposición
plena). La fórmula es monótona: más probabilidad de crisis ⇒ menos exposición,
siempre.

---

## 2. Resultados de la demo en vivo

| Estado | Etiqueta | Exposición | Conf. | Probabilidades |
|---|---|---|---|---|
| crisis_2008_style | crisis | **0.080** | 0.83 | crisis .87 / risk_off .10 |
| risk_off_2022_style | risk_off | **0.500** | 1.00 | risk_off 1.00 |
| neutral_mixed | neutral | **0.900** | 0.72 | neutral .79 / risk_off .20 |
| risk_on_calm | risk_on | **1.000** | 0.99 | risk_on .99 |

- Coste: **~$0.000022 por decisión** ($0.000087 los 4 estados).
- Latencia: **~0.44 s** por decisión.
- Modelo servido: `typesafe/jev-1.14-20261014`, proveedor TypeSafe.

El coste es despreciable: clasificar 2.000 días de historia (~2.000 llamadas)
costaría **~$0.044**.

---

## 3. Contrato de la API

> Documentado en Fase 0; **no está en la documentación pública de OpenRouter**.
> Verificar en cada subida de versión.

- **Endpoint:** `POST https://openrouter.ai/api/alpha/decisions`
- **Cabeceras:** `Authorization: Bearer <OPENROUTER_API_KEY>`,
  `Content-Type: application/json`
- **Cuerpo:**
  ```json
  {
    "model": "~typesafe/jev-latest",
    "state": { "...": "..." },
    "questions": {
      "regimen": {
        "type": "choice",
        "instructions": "Clasifica el REGIMEN DE MERCADO actual ...",
        "criteria": {"risk_on": "...", "neutral": "...", "risk_off": "...", "crisis": "..."}
      }
    }
  }
  ```
- **Respuesta:** `answers.<question_id>.{type, choice, probabilities, confidence}`
  más `usage.cost`, `model`, `provider`, `id`.
- **Modelo:** acepta el alias con tilde (`~typesafe/jev-latest`) y resuelve a la
  versión concreta, que se devuelve en `model` para dejar trazabilidad.
- **TLS:** el proxy de esta máquina usa la CA de Kaspersky; se combina con
  `certifi` en `jev_phase0_out/ca_bundle.pem`.

### Robustez implementada

- Reintentos con backoff en 429 y errores de red; los 4xx no se reintentan.
- **Fail-open:** si Jev falla, la exposición queda en `1.0` (no se recorta
  por una caída del clasificador). Decisión deliberada: un fallo de API no debe
  desinvertir la cartera por accidente. Revisar si se prefiere fail-safe.
- Normalización de probabilidades que no suman 1 y de claves sobrantes
  (`options`) que Jev a veces incluye.
- Cada decisión guarda estado usado, modelo, coste, latencia y error: auditable.

---

## 4. Uso

```bash
# Demostración con 4 estados sintéticos
python work/estrategias/jev_regime.py --demo

# Sobre datos reales de estados de mercado
python work/estrategias/jev_regime.py --csv estados_mercado.csv --limit 10 --out jev_sizing.csv
```

Como librería:

```python
from jev_regime import JevRegimeClassifier
clf = JevRegimeClassifier()
d = clf.classify({"vol_pct": 0.97, "drawdown120": 1.0, "mom_crash": 1})
print(d.label, d.probabilities, d.exposure)
```

Requiere `OPENROUTER_API_KEY` (se lee del `.env` del repo).

---

## 5. Advertencia metodológica — verificada empíricamente

> **CORRECCIÓN (2026-10-26):** una versión previa de este documento afirmaba que
> `vol_pct` filtraba futuro. **Era falso** y se ha verificado con
> `demo_leak_vol_pct.py`. Lo que sigue es la conclusión corregida.

### 5.1. Los tres indicadores SON causales — verificado

| Indicador | Fuente en `extract_estados.py` | Veredicto |
|---|---|---|
| `vol_pct` | `vol.rolling(252, min_periods=120).apply(lambda x: (x.iloc[-1] > x).mean())` | ✅ causal |
| `drawdown120` | `bench / bench.shift(120) - 1 < 0` | ✅ causal |
| `mom_crash` | ranking cross-section por fecha (decil perdedor > ganador) | ✅ causal |

**Por qué `vol_pct` es causal:** `rolling` en pandas evalúa siempre la ventana
`[i-251, i]`, que termina en la fecha evaluada. El `min_periods=120` no permite
mirar adelante: sólo permite emitir el valor antes de acumular 252
observaciones *pasadas*. Y `(x.iloc[-1] > x).mean()` compara el último valor de
la ventana (= hoy) contra esa misma ventana. Todo lo comparado es ≤ hoy.

**Evidencia:** al recalcular con una implementación explícitamente causal
(bucle que sólo mira hacia atrás) sobre una serie sin NaN iniciales:

```
SIN NaNs iniciales -> max |diff|: 0.0
filas comparadas: 1362
```

Diferencia **exacta cero**. La discrepancia de 132 filas que apareció en la
primera prueba era un artefacto del propio test: los 19 NaN iniciales de la
serie (los primeros días no tienen vol 20d por falta de retornos previos)
se trataban de forma distinta en cada implementación. Confinada a
2018-07-12 → 2019-01-11, el arranque de la muestra. **No era fuga de futuro.**

### 5.2. El riesgo real: percentiles GLOBALES

Lo que sí filtraría futuro es normalizar contra el rango completo:

```python
vol_global = vol.rank(pct=True)   # ⚠️ ESTO sí filtra futuro
```

`rank` ordena cada día contra **toda la serie**, incluidos años posteriores. El
máximo futuro contamina el percentil del pasado. Medido con umbral p90:

| Versión | Días marcados "crisis" |
|---|---|
| causal (`rolling`) | 226 |
| global (`rank`) | **149** |

La versión global **pierde el 34% de las señales de estrés**, porque los picos
futuros diluyen los percentiles pasados. Acuerdo entre ambas: sólo 87,4%.

**Regla:** nunca usar `rank(pct=True)` ni `minmax` sobre la serie completa para
construir features. El `rolling` actual es la forma correcta.

### 5.3. El riesgo que sigue vivo (no es `vol_pct`)

`vol_pct` está limpio, pero un backtest puede filtrar futuro **en otro sitio**:

1. **Normalización del panel de resultados.** Escalar o estandarizar los
   retornos/IC sobre la serie completa antes de partir train/test contamina.
   Normaliza con estadísticos de la ventana de entrenamiento, nunca con los de
   todo el histórico.
2. **Selección de umbrales.** Elegir el umbral de exposición mirando el
   resultado del backtest completo es sobreajuste. Fija el umbral a priori
   (p90, como en el `vol_gate` actual) o valídalo out-of-sample.
3. **Etiquetas de régimen de Jev.** Las probabilidades se piden *por fecha*
   con estado causal; está bien. Pero no reutilices una clasificación de 2026
   para fechas de 2019.
4. **Purga/embargo.** Con `mom_crash` mirando 120 días atrás, las observaciones
   vecinas se solapan. Usa purga entre train/test (ya está en `momentum_purgedcv.py`).

Ninguno de estos problemas está en `extract_estados.py`. Están en el código de
simulación que se construya encima.

---

## 6. Fase 2 — CERRADA (resultado negativo)

> **Fecha de cierre:** 2026-10-26 · **Periodo:** 2018-01-02 → 2026-10-23
> **Resultado:** ❌ **Jev se descarta.** Guía completa: `JEV_GUIA.md` §10.

**Desbloqueado:** los indicadores de `extract_estados.py` son causales
(sección 5.1), así que `estados_mercado.csv` puede pasarse a Jev sin filtrar
futuro. El bloqueante #1 que figuraba antes aquí no existía.

### 6.1. Qué se ejecutó

1. ✅ **Backtest A/B.** Exposición fija vs. `vol_gate` vs. Jev, sobre 2018–2026
   con costes de 5 bps y el mismo motor de momentum (top-20, lookback 120d,
   rebalanceo semanal).
2. ✅ **7 fórmulas de sizing.** Ante el mal resultado inicial, se probaron
   variantes que *sí* pueden cerrar la posición, reutilizando los vectores de
   probabilidad ya pagados.
3. ⬜ **Calibración (Brier score).** No ejecutada: resultó innecesaria, porque el
   problema no es que las probabilidades estén mal calibradas, sino que **no
   tienen rango dinámico suficiente** (sección 6.2).
4. ⬜ **Varias preguntas / caché por hash.** No ejecutadas: sin sentido una vez
   descartado el uso principal.

### 6.2. Resultado y causa raíz

Ninguna de las 7 fórmulas supera al `vol_gate` (Sharpe 0.9687 vs. 0.9148 de la
mejor variante Jev).

**Causa raíz — las probabilidades no tienen resolución:**

La fórmula `binaria_.5` (*fuera si `P(crisis) > 0.5`*) dio un resultado
**idéntico a la exposición fija hasta el cuarto decimal** (Sharpe 0.9148,
exposición media 1.000, 0 días fuera). Es decir: **Jev nunca devolvió
`P(crisis) > 0.5` en 9 años.** El umbral jamás se activó.

No es un fallo de la fórmula. Jev reparte probabilidad entre `risk_off` y
`crisis` en vez de concentrarla, y **nunca emite la certeza que un sizing
binario necesita**. En el caso más extremo medido (Fase 0, escenario tipo 2008)
el peor valor fue `P(crisis)=0.88`; en las crisis reales del periodo las
probabilidades fueron mucho más suaves.

**Confirmación adicional:** forzar más cierres no ayuda. La fórmula `x2.5` cierra
344 días (más que el `vol_gate`, 260) y tiene el **peor Sharpe de todos** (0.684).
El valor del `vol_gate` está en cerrar *en los días correctos*, no en cerrar mucho.

### 6.3. Criterio de decisión (fijado antes de ver resultados)

Se estableció *a priori* en `JEV_GUIA.md` §7 que **C ≈ B o C < B** haría
descartar la capa. El resultado fue C < B con margen, así que la decisión no
requiere interpretación adicional.

Con 7 fórmulas probadas sobre los mismos datos existe riesgo de comparaciones
múltiples, pero **no afecta a esta conclusión**: el sesgo importa cuando algo
gana por poco, y aquí no ganó nada.

### 6.4. Entorno de ejecución (resuelto)

El backtest se ejecutó en **WSL (Ubuntu), con datos en
`~/.qlib/qlib_data/us_data`** (1.3 GB, 18.575 tickers con features, calendario
1999–2026).

Notas del entorno, por si se retoma:

- **No existe `sp500_liquid.txt`.** Los universos disponibles son `sp500.txt`
  (1.180 tickers, con composición histórica → evita sesgo de supervivencia),
  `nasdaq100.txt`, `all.txt` y `tech_giants_universe.txt`. El script prioriza
  `sp500.txt` y **no** usa `all.txt` (15.233 tickers con micro-caps).
- **`^gspc` está disponible**, así que el benchmark es el S&P 500 real.
- **WSL no es accesible desde la sesión de DSH** (sandbox: `Wsl/E_ACCESSDENIED`
  por token restringido en los named pipes). Se ejecuta desde una terminal
  normal de Windows. WSL en sí funciona correctamente.
- El repo se ejecuta desde `/mnt/c/...` (I/O lento entre sistemas, funcional).

`jev_regime.py` es autocontenido y funciona sin qlib, así que la capa de decisión
se puede probar en cualquier sitio; sólo el backtest con datos reales requiere el
entorno completo.

---

## 7. Nota sobre el modelo

`~typesafe/jev-latest` es un modelo de **decisiones**, no de chat: recibe
estado + preguntas y devuelve opciones con probabilidades. No sirve para
generar texto libre. Su valor aquí estaba en las probabilidades, que es lo que
se explotó — y lo que resultó insuficiente.

### 7.1. Veredicto sobre el modelo (tras Fase 2)

**Jev clasifica correctamente pero no cuantifica con suficiente resolución.**
La distinción importa:

| Aspecto | Resultado |
|---|---|
| Clasificación de estados obvios | ✅ 4/4 correctos (Fase 0) |
| Calibración aparente | ✅ plausible (`crisis 0.88`/`conf 0.83`) |
| **Rango dinámico de `P(crisis)`** | ❌ **nunca superó 0.5 en 9 años** |
| Utilidad para sizing binario | ❌ imposible: el umbral nunca se activa |
| Utilidad para sizing continuo | ❌ la fórmula lineal comprime a 0.37–0.98 |

Es decir: **identifica bien el estado, pero no se compromete con él.** Un
clasificador que dice "probablemente crisis" sin llegar nunca a "casi seguro
crisis" no sirve para decidir cuánto capital desplegar.

Esto **no invalida la Fase 0**: los hallazgos sobre el contrato de la API, el
endpoint `/api/alpha/decisions`, el endpoint nativo de decisiones y la
distinción con `typesafe/jev-router` siguen siendo válidos y reutilizables.

### 7.2. Lección reusable para futuros modelos de decisiones

Antes de construir una capa de sizing sobre cualquier modelo probabilístico,
**medir primero la distribución de sus probabilidades** a lo largo de la muestra:

```python
# Si esto no llega a valores altos, el modelo no sirve para sizing
probs["crisis"].max()      # ¿llega a >0.5? ¿a >0.8?
(probs["crisis"] > 0.5).sum()  # ¿cuántos días se activaría la señal?
```

Es una comprobación de minutos que evita un backtest completo. En este caso,
habría anticipado el resultado antes de gastar el primer dólar.
