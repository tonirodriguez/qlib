# 🧪 Experimento Qlib — Resultados v1 vs v2, Diagnóstico y Test de Dirección

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — inversión cuantitativa US (NASDAQ/S&P 500)
> **Mercado:** Datos US (12,737 tickers) · Benchmark: ^NDX

---

## 1. Resultados obtenidos

### 1.1 Versión v1 (`tech_experiment.yml` — original)
- **Config:** topk=1, label retorno 1 día, LightGBM 210 hojas, backtest 2024→2026-03
- **Resultados (exceso vs benchmark):**

| Métrica | Benchmark ^NDX | Exceso sin costes | Exceso con costes |
|---|---|---|---|
| Retorno anualizado | +18.0% | **−14.6%** | **−37.1%** |
| Information Ratio | 0.90 | −0.64 | −1.62 |
| Max drawdown | −25.3% | −42.5% | **−89.0%** |

- **Indicadores:** FFR=1.0, PA=0, POS=0 (sin señal útil)

### 1.2 Versión v2 (`tech_experiment_v2.yml` — refinada)
- **Config:** topk=10, label retorno 10 días, LightGBM regularizado (64 hojas, LR 0.03, λ1=1, λ2=5, 500 árboles), backtest 2022→2026-08, only_tradable
- **Resultados (exceso vs benchmark):**

| Métrica | Benchmark ^NDX | Exceso sin costes | Exceso con costes |
|---|---|---|---|
| Retorno anualizado | +14.8% | **−9.0%** | **−11.9%** |
| Information Ratio | 0.65 | −0.43 | −0.56 |
| Max drawdown | −39.2% | −107.0% | −119.3% |

- **Indicadores:** FFR=1.0, PA=0, POS=0

---

## 2. Comparativa y por qué los cambios

| Aspecto | v1 | v2 | Motivo del cambio |
|---|---|---|---|
| **topk** | 1 | 10 | v1 compraba 1 sola acción → rotación extrema, costes destruían todo (−89%). Con topk 10 se diversifica y baja la rotación |
| **Label** | retorno 1d | retorno 10d | Label de 1 día es puro ruido; 10 días capta mejor tendencia |
| **LightGBM** | 210 hojas, LR 0.04 | 64 hojas, LR 0.03, λ1=1, λ2=5, 500 árboles | 210 hojas casi seguro = overfitting (memorizar train); modelo más contenido y regularizado |
| **Backtest** | 2024→03-26 | 2022→08-26 | Rango más amplio y completo |
| **only_tradable** | no | sí | Evita comprar activos no negociables |

**Resultado neto:** los cambios sí mejoraron la *ejecución* (costes: −37% → −12%), lo que confirma que **el overfitting y la rotación eran problemas reales**. Pero la estrategia **sigue perdiendo** frente al benchmark.

---

## 3. Diagnóstico

**El problema ya no es la ejecución, es la señal (alpha).** Los indicadores FFR=1.0 / PA=0 / POS=0 indican que las posiciones long/short no generan retorno por encima del azar. Hipótesis principales, en orden de prioridad:

1. **Señal invertida** — que el modelo aprenda a predecir *bien* pero el ranking salga al revés (el modelo elige malas y evita buenas). Es el diagnóstico más barato de comprobar.
2. **Label a 10 días demasiado incierto** — en acciones USA de alta volatilidad, predecir retorno a 10 días con Alpha158 puede ser ruido.
3. **Universo demasiado amplio** — entrenar sobre todo el mercado diluye; quizá `tech_giants_universe` (concentrado en tecnológicas) rinde mejor.
4. **Falta filtro de liquidez/volumen** — puede estar seleccionando microcaps ilíquidas cuyas señales no son ejecutables.

---

## 4. Test de Dirección

**Objetivo:** comprobar si las señales del modelo están invertidas. Si tomamos las señales del v2 pero comprando las *peores* puntuadas (señal invertida) y eso produce **exceso de retorno positivo**, entonces el modelo predice bien pero el ranking está invertido.

**Método:** ejecutar el backtest del v2 con la señal multiplicada por −1 (o seleccionando el bottom-10 en vez del top-10).

---

## 5. Resultado del Test de Dirección (2026-08-14)

**Datos:** 64,462 muestras (instrumento × fecha) en el segmento de test (2024→2026)

| Métrica | Valor | Lectura |
|---|---|---|
| **IC global** (corr. pred→label) | **−0.010** | Muy cercano a cero → señal esencialmente ruido |
| Retorno label TOP 10% predicho | +0.66% (10d) | |
| Retorno label BOTTOM 10% | +0.85% (10d) | |
| **Long-Short spread** (top−bottom) | **−0.18%** (10d) | Ligeramente negativo |

### Interpretación crítica (matizada)

⚠️ **NO hay una señal "invertida" fuerte — hay prácticamente AUSENCIA de señal.**

- El IC de **−0.010** con 64K muestras es estadísticamente indistinguible de cero (ruido puro).
- El spread de **−0.18%** es marginal. Es negativo, pero de magnitud tan pequeña que no justifica decir "la señal está invertida" — más bien el modelo **no discrimina** entre buenas y malas predicciones.
- Invertir la señal (−1) no convertiría esto en alpha: convertiría un spread de −0.18% en +0.18%, que sigue siendo insignificante frente a los costes (~0.1%+ por operación).

### Conclusión del test de dirección

**❌ La causa del bajo rendimiento NO es la dirección de la señal.** Es que **el modelo LightGBM + Alpha158 con label a 10 días no produce señal predictiva útil** en este universo. El test de dirección descarta la hipótesis #1 (señal invertida) como causa principal.

---

## 6. Sugerencias (actualizadas tras el test de dirección)

1. ~~Test de dirección~~ ✅ **Hecho** — descartado como causa principal (señal ≈ ruido, IC −0.01)
2. **Probar universo `tech_giants_universe`** (concentrado en tecnológicas) en vez de todo el Nasdaq100
3. **Añadir filtro de liquidez** (volumen mínimo) al handler para evitar microcaps ilíquidas
4. **Probar label más corto (3-5 días) o más largo (20-60 días)** — el de 10 días puede ser demasiado ruidoso
5. **Comparar con un modelo simple** (momentum puro, `qlib_us_simple_signal.py`) como línea base
6. **Probar otro modelo** (si se acepta que Alpha158+LightGBM no capta la estructura)
7. **Reducir el universo de entrenamiento** — entrenar solo sobre un subconjunto líquido y coherente

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
