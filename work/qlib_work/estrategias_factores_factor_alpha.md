# 📈 Estrategias y Factores con Alpha Empírico para Megacaps Tech USA — Guía de Implementación en Qlib

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — inversión cuantitativa sistemática
> **Universo:** tech_giants (16 tickers: AAPL, MSFT, GOOGL, META, AMZN, NVDA, TSLA, NFLX, AMD, ADBE, AVGO, INTC, QCOM, CSCO, TXN, ORCL)
> **Diagnóstico de partida:** LightGBM + Alpha158 (158 factores técnicos) dio **IC OOS = 0.0078** ≈ ruido (sin alpha real; el +24% era beta del sector).
> **Objetivo:** fuentes de alpha con **respaldo empírico documentado** y que pasen walk-forward con **IC OOS > 0.02**.

---

## 1. Resumen Ejecutivo (veredicto)

**Veredicto honesto:** en un universo de 16 megacaps tecnológicas de *el mismo sector*, no existe un "factor mágico" con IC 0.05 listo para copiar. El IC 0.0078 de Alpha158+LightGBM no es un fallo del modelo, es una señal de que **el problema estructural es el universo y la fuente de señal**, no el hiperparámetro. La buena noticia: sí hay familias de factores con respaldo empírico sólido (décadas de papers) que **mejoran materialmente el IC**, pero hay que **aceptar su magnitud real** (IC 0.02–0.04 = buen alpha explotable, no 0.10).

**Las 5 recomendaciones clave, en orden de prioridad:**

1. **🚀 Momentum de 12–1 meses y nearness al 52-week high (George & Hwang 2004) como columna vertebral.** Es el factor con más evidencia transversal (EE.UU., 8 mercados y clases de activo: Asness, Moskowitz & Pedersen 2013) y el que mejor se adapta a un universo de megacaps de crecimiento. En este universo, momentum actúa más como **momentum de series temporales / tendencia** (Moskowitz, Ooi & Pedersen 2012) que como factor transversal puro. **Esta debe ser tu señal Nº1 y tu línea base de comparación.** Expectativa realista: IC 0.03–0.05 OOS sobre ranking de 16 nombres.

2. **🧮 Pasar de "158 factores correlacionados" a "pocos factores ortogonales con base teórica" (5–12).** El fracaso de Alpha158+LightGBM (158 variables de OHCVL casi todas con la misma información de tendencia/volatilidad → multicolinealidad masiva → LightGBM sobreajusta ruido y pierde la señal) es el problema. Microsoft RD-Agent logró **mejor rendimiento con un 70% MENOS de factores** por esta misma razón. Menos, pero con fundamento, gana.

3. **⚡ PEAD / Earnings Momentum (Bernard & Thomas 1989; Chan, Jegadeesh & Lakonishok 1996) es la fuente de alpha más "real" para nombres que reportan trimestralmente, PERO requiere añadir datos fundamentales (EPS/SUE) a Qlib.** Es ortogonal a momentum puro de precios. En megacaps muy cubiertas el drift es más débil, pero el **revisiones de analistas (earnings revision)** sigue siendo una señal potente.

4. **🛡️ Combinar momentum (señal de entrada) + quality/profitability y low-vol (selección y gestión de riesgo).** La evidencia es robusta de que **value y momentum tienen correlación NEGATIVA** (Asness, Moskowitz & Pedersen 2013): combinarlos da mejor Sharpe que cada uno solo. En tu universo all-growth, el equivalente a "value" es **profitability/quality** (Novy-Marx 2013) y **low-vol como posicionamiento defensivo en crisis** (Frazzini & Pedersen 2014; Daniel & Moskowitz 2016 sobre crash de momentum).

5. **⚠️ Gestiona el riesgo de momentum-crash explícitamente (Daniel & Moskowitz 2016) y sé honesto sobre el límite de "breadth".** Con solo 16 nombres altamente correlacionados, tu IR está acotado por la ley fundamental (IR ≈ IC×√BR). No esperes IR>1 sostenido; un IR 0.5–0.7 con costes IB (~0.1% round-trip) ya es un resultado realista y bueno.

**Falsable:** este informe será un éxito si, tras implementar la Hoja de Ruta §6, algún combo de momentum/PEAD/quality **pasa walk-forward con IC agregado OOS > 0.02** en tu universo. Si tras 2–3 iteraciones serias sigues en IC<0.02, la conclusión honesta es que el universo de 16 megacaps no ofrece alpha transversal explotable y la respuesta correcta es **cartera de índice/calidad + gestión de riesgo** (opción que tu propio diagnóstico ya contempla).

---

## 2. Factores con Respaldo Empírico

> **Nota de implementación general (Qlib):** Alpha158/Alpha360 usan solo OHLCV. Cualquier factor fundamental (value, quality, PEAD) requiere **añadir columnas (PE, EPS, book value, ROE, SUE) a tus datos CSV/parquet y re-dump a formato Qlib**, o usar un `DataHandlerLP` con expresiones `factor` propias. La documentación oficial de Qlib lo dice explícitamente: "si quieres usar tu propio alpha-factor que no se calcula con OHLCV (como PE, EPS), añádelo a los CSV junto con OHLCV y luego dump a formato Qlib". Alternativa rápida para testear: usa expresiones de retorno de precio (`Ref`, `Mean`, `Std`) para las variantes de precio (momentum, 52-week high, low-vol).

### 2.1 Momentum 12–1 y 52-week high — **LA señal principal**

| Aspecto | Detalle |
|---|---|
| **Definición** | Comprar ganadores pasados 12 meses (omitiendo el último mes por reversión de corto plazo), vender perdedores. |
| **Mecanismo** | *Underreaction*: los precios tardan en incorporar noticias; la información buena se difunde gradualmente. Más (discutido): autocorrelación de flujos de fondos y sesgos de disposición. |
| **Evidencia** | **Jegadeesh & Titman (1993, *Journal of Finance*)** — estrategia 6/6 sobre NYSE-AMEX 1965–1989: ~12% anual compuesto. **Jegadeesh & Titman (2001, JF)** — confirman que los beneficios PERSISTEN en los años 90 (no fue artefacto de la muestra). **Asness, Moskowitz & Pedersen (2013, JF)** — momentum consistente en 8 mercados/clases de activo. **George & Hwang (2004, JF)** — el *nearness al 52-week high* (precio/máximo de 52 semanas) explica gran parte de los beneficios de momentum y es más robusto. |
| **Magnitud esperada** | Momentum transversal: ~0.5–1.0% mensual long-short en universos amplios. En 16 megacaps, espera IC transversal 0.03–0.05. |
| **⚠️ Advertencia** | **Daniel & Moskowitz (2016, *JFE*)** — momentum tiene cola negativa: "momentum crashes" en rebotes de mercados bajistas. Gestión de riesgo obligatoria (ver §2.5). |
| **Implementación Qlib** | **12–1: `Ref($close,-21)/Ref($close,-252)-1`** (retorno últimos 12 meses omitiendo ~21 días). **52-week high: `$close / Max($high, 252)`** (proximidad al máximo anual, George-Hwang). Añade ambas como `factor` en tu handler y puntúa el ranking. |

### 2.2 Value — limitado en este universo, pero para combinación

| Aspecto | Detalle |
|---|---|
| **Definición** | Comprar barato: bajo book-to-market, bajo PE, bajo EV/EBITDA, alto dividend yield. |
| **Mecanismo** | Prima de riesgo por "barato con fundamentos deprimidos" + corrección de sobre-reacción a malas noticias. |
| **Evidencia** | **Fama & French (1993, JF)** — factor HML (book-to-market). **Asness, Moskowitz & Pedersen (2013, JF)** — value y momentum premios consistentes y con correlación NEGATIVA. |
| **⚠️ Realidad en tu universo** | Las 16 megacaps tech son **todas growth y de múltiplos altos**; el spread transversal de value entre ellas es mínimo y poco fiable. **Usar value transversal aquí es casi ruido.** En cambio, el *timing* value del ÍNDICE sectorial puede servir (cuando el sector está barato vs historia), pero es secundario. |
| **Implementación Qlib** | Requiere datos fundamentales (B/M, E/P). Añade PE, book value a tus datos. Para test rápido puedes usar el inverso de la capitalización relativa, pero en este universo prioriza quality sobre value. |

### 2.3 Quality / Profitability — **el "value" que sí funciona en growth**

| Aspecto | Detalle |
|---|---|
| **Definición** | Empresas con alta rentabilidad y balance sólido: alta **profitabilidad bruta / activos** (Novy-Marx), alto ROE, baja deuda. |
| **Mecanismo** | La rentabilidad real es un predictor del retorno futuro tan potente como book-to-market; empresas de alta calidad generan retornos superiores ajustados por valoración. |
| **Evidencia** | **Novy-Marx (2013, *JFE*)** — "The Other Side of Value: The Gross Profitability Premium": gros profit/activos predice la sección transversal con tanta fuerza como B/M. **Fama & French (2015, JFE)** — añaden el factor profitability (RMW) a su modelo de 5 factores. **Asness, Frazzini & Pedersen (2019, *Review of Asset Pricing Studies*)** — factor **"Quality Minus Junk" (QMJ)**: calidad (rentabilidad, crecimiento, seguridad, payout) paga una prima transversal robusta. |
| **Implementación Qlib** | Necesita fundamentales: **ROE, gross margin, gross profit/assets**. En tu universo las 16 son de alta calidad (rentables) → poco spread, pero es el *filtro* correcto para no caer en la trampa "momentum de la peor empresa". Combínalo como *cap* o *screen*, no como ranking principal. |

### 2.4 Low-Volatility / Low-Beta — **gestión de riesgo que añade alpha ajustado**

| Aspecto | Detalle |
|---|---|
| **Definición** | Las acciones de baja volatilidad/beta tienden a superar en retorno ajustado al riesgo a las de alta beta (anomalía "low-vol"). |
| **Mecanismo** | Restricciones de apalancamiento y "lottery preferences" hacen que los inversores sobrevaloren activos volátiles (altas betas) e infravaloren los seguros → prima para quien aguanta baja vol. |
| **Evidencia** | **Haugen & Baker (1996)** — las carteras de baja vol superan. **Ang, Hodrick, Xing & Zhang (2006, *JF*)** — alta volatilidad idiosincrática = menores retornos. **Frazzini & Pedersen (2014, *JFE*)** — "Betting Against Beta" (BAB): cartera long low-beta / short high-beta produce alpha significativo en EE.UU. y 20 mercados. |
| **⚠️ Realidad en tu universo** | Dentro de 16 tech todo es alta vol; pero en el *timing* de mercado sectorial, **el posicionamiento en los nombres de menor beta relativa en drawdowns** reduce el riesgo de momentum-crash. Úsalo como **escala de riesgo / posición**, no como señal principal. |
| **Implementación Qlib** | **Beta 252d: `RegressionBeta($close, benchmark, 252)`** o vol 60d `Std($close/$ref($close,1)-1, 60)`. Úsalo para **vol-targeting** y para reducir peso en los nombres más volátiles cuando el momentum de mercado sea negativo. |

### 2.5 Size — no aplica, pero explícito

| Aspecto | Detalle |
|---|---|
| **Definición** | Prima de tamaño: las pequeñas superan a las grandes. |
| **Evidencia** | **Fama & French (1993, JF)** — factor SMB. **Israel & Moskowitz (2013)** — la prima de tamaño es débil y variable en el tiempo. |
| **⚠️ Realidad en tu universo** | **No aplica**: son las 16 empresas MÁS grandes del mundo. No hay spread de tamaño entre ellas. Ignóralo como factor; solo lo menciono para descartarlo explícitamente y evitar perder tiempo. |

---

## 3. Estrategias Completas para Megacaps Tech

### 3.1 High-Momentum concentrado (relativo + tendencia)
- **Señal:** ranking de 16 nombres por 12–1 momentum y nearness 52-week high. Top tercil = comprar; cuando un nombre rompe bajo su media/52-week high → salir.
- **Base empírica:** Jegadeesh & Titman (1993/2001); George & Hwang (2004).
- **Qlib:** señal = `Ref($close,-21)/Ref($close,-252)-1` y `$close/Max($high,252)`. Rebalanceo semanal, topk pequeño (3–5). **Añade vol-targeting.**
- **Riesgo:** crash de momentum (Daniel & Moskowitz 2016). Mitigar con regla de salida (stop en el 52-week high) y reducción de posición en mercados bajistas sectoriales.

### 3.2 Time-Series Momentum (TS-MOM) — **la más robusta en este universo**
- **Señal:** por cada activo, si su retorno pasado (12m) es **positivo** → long; si negativo → short/flat. Escalar posición por la inversa de la volatilidad.
- **Base empírica:** **Moskowitz, Ooi & Pedersen (2012, *JFE*)** — "Time Series Momentum": consistentemente rentable en 58 instrumentos y 5 clases de activo, con alpha frente a factores estándar; se comporta mejor en mercados extremos. Complementa (no sustituye) al momentum transversal.
- **Por qué aquí:** en un universo de 16 nombres del mismo sector, "cuál es mejor" (transversal) tiene poco spread; "el sector y cada nombre sube/baja en tendencia" (time-series) es una señal mucho más accionable. **Esta es probablemente tu fuente de alpha más fiable.**
- **Qlib:** label/predicción basada en el signo del retorno 12m; posición ∝ `sign(ret12m)/σ`. Es implementable con una señal simple (no ML) y rebalanceo mensual/semanal. Espera IC sobre la tendencia del índice sectorial.

### 3.3 PEAD / Earnings Momentum (y revisiones de analistas)
- **Señal:** tras anunciar resultados, las empresas con sorpresa de beneficios positiva (SUE, standardized unexpected earnings) siguen subiendo semanas/meses (drift); negativas siguen bajando.
- **Base empírica:** **Bernard & Thomas (1989, *JAR*)** — PEAD original: ~18% anual long-short en decil extremo. **Chan, Jegadeesh & Lakonishok (1996, *JF*)** — momentum de beneficios (earnings revisions) y su combinación con momentum de precios. **Jegadeesh & Livnat (2006)** — revenue surprises también predicen.
- **Realidad en megacaps:** el drift es más pequeño en empresas muy seguidas, pero las **revisiones de EPS a futuro** siguen siendo información valiosa y ortogonal al momentum de precios.
- **Qlib:** necesitas datos fundamentales (EPS real, EPS esperado/consenso, fecha de anuncio) para calcular SUE = (EPS_real − EPS_consenso)/σ_histórico, y revisiones. Añade columnas a Qlib y usa el retorno post-anuncio (ventana 60–90 días) como label.
- **⚠️ Requiere:** suscripción/importación de datos fundamentales de analistas (no los tienes con OHLCV). Es el paso de mayor fricción de datos, pero también el que más alpha "fuera de mercado" aporta.

### 3.4 QARP (Quality at a Reasonable Price) — para el caso "todo growth"
- **Definición:** filtrar por calidad (profitability, ROE, balance) y comprar los "menos caros" dentro de la calidad; con momentum como confirmación.
- **Base empírica:** síntesis de Novy-Marx (2013) + Fama-French (2015) + Asness, Frazzini & Pedersen (2019, QMJ). Concepto QARP ampliamente usado en gestión institucional (AQR, O'Shaughnessy).
- **Qlib:** score = combinación ponderada de profitability/ROE (calidad) + "reasonability" (P/E o E/P relativo al grupo) + momentum de confirmación. Top tercil → comprar.

### 3.5 GARP (Growth at a Reasonable Price) — enfoque PEG
- **Definición:** seleccionar crecimiento a precio razonable vía PEG = P/E ÷ crecimiento de EPS esperado.
- **Base empírica:** popularizado por Peter Lynch; academicmente el PEG predice retornos en algunos estudios (correlación positiva PEG-ajustado con retornos), aunque es menos riguroso que los factores Fama-French. **Advertencia:** en megacaps de alto múltiplo, PEG es poco discriminativo y sensible a estimaciones; úsalo como *complemento* de quality/momentum, no como señal única.
- **Qlib:** requiere EPS forward (analistas) → PEG. Fricción de datos similar a PEAD.

### 3.6 Combinación de factores ortogonales (el objetivo final)
- **Base empírica:** Asness, Moskowitz & Pedersen (2013) — **combinar value y momentum** (correlación negativa) mejora Sharpe y reduce drawdown. La lección general: **combinar señales de Baja correlación eleva el IR sin inventar nueva predicción**.
- **Qlib:** score final = z-score(momentum 12–1 + 52w-high) + λ₁·z(PEAD/earnings revision) + λ₂·z(profitability/quality). Pesos fijos o estimados en walk-forward. Mantén 3–5 señales, no 158.

---

## 4. Combinaciones de Factores Ortogonales

### Qué combinar y por qué
| Factor A | Factor B | Correlación | Por qué combinar |
|---|---|---|---|
| **Momentum de precio (12–1)** | **Value/Quality (profitability)** | **NEGATIVA** (Asness et al. 2013) | La mejor combinación documentada: cada uno cubre el hueco del otro. Value "salva" a momentum en crashes; momentum "salva" a value en los años de growth. |
| **Momentum de precio** | **PEAD / revisiones de EPS** | Baja (Chan, Jegadeesh & Lakonishok 1996: info distinta) | Momentum capta tendencia de precio; PEAD capta la información fundamental en difusión. Ortogonalidad real → buen aumento de IC. |
| **Momentum** | **Low-vol / beta** | Baja a media | Low-vol funciona como *riesgo*: reduce el momentum-crash (Daniel & Moskowitz 2016) sin anular la señal de tendencia. |
| **Momentum / Quality** | **Size** | N/A | Size no aplica (16 megacaps) → descarta. |

### Reglas de oro
1. **Mantén 3–5 factores, no 158.** Correlación media entre los Alpha158 es altísima → multicolinealidad → sobreajuste. RD-Agent demostró que **menos factores (y mejores) rinden más**. Combinar 3 señales ortogonales de base teórica casi siempre supera OOS a un modelo de 158 variables.
2. **Normaliza (z-score) y pondera con pesos fijos** estimados en train; **valida pesos en walk-forward**, no los "ajustes finos" en test (eso es overfitting).
3. **Mide la correlación de las señales** en tu universo antes de combinar: si dos señales tienen corr >0.7, una es redundante.

---

## 5. Diagnóstico: Por qué Alpha158 + LightGBM dio IC≈0, y qué cambiar

### 5.1 Por qué fracasó
1. **158 factores técnicos casi todos miden la MISMA cosa** (tendencia + volatilidad de OHLCV en ventanas solapadas). LightGBM con tantas variables correlacionadas **sobreajusta ruido** y la señal se pierde en la multicolinealidad.
2. **Label a 10 días sobre 16 nombres** = muy poco ratio señal/ruido; en acciones de alta vol, predecir el retorno a 10d con variables técnicas es esencialmente ruido.
3. **Universo de 16 nombres, todos del mismo sector:** el "cross-sectional alpha" transversal dentro de un grupo tan homogéneo y pequeño es **estructuralmente limitado**. Alpha158 está diseñado para universos amplios (CSI300/500, miles de acciones) donde hay spread transversal.
4. **Sin datos fundamentales:** solo OHLCV limita a factores de precio; se pierde la señal fundamental (PEAD, quality, value) que es donde está parte del alpha real.
5. **El +24% era beta:** el IC OOS 0.0078 lo demuestra — sin predicción, el retorno era el mercado.

### 5.2 Qué cambiar concretamente
| Cambio | Acción |
|---|---|
| **Nº de factores** | De 158 → **5–12 factores con base teórica** (momentum 12–1, 52-week high, low-vol, profitability, PEAD/revisiones). Menos, mejor. |
| **Modelo** | Empieza con **señal simple (no-ML)** para momentum/TS-momentum (reproducible, sin overfitting). Solo usa ML (LightGBM) DESPUÉS, sobre un conjunto pequeño de factores ortogonales, y valida con walk-forward purged (López de Prado). |
| **Label** | Prueba **labels más largos (20–60 días)** para captar tendencia, o *returns sobre horizonte de momentum* en lugar de 10d ruidosos. |
| **Factor mining** | Si quieres ML: usa **RD-Agent / R&D-Agent-Quant** (microsoft) que hacen factor mining con LLM+evolución **y seleccionan pocos factores de alta calidad** (resultado publicado: 2x rendimiento con 70% menos factores). Evita el "más factores = mejor". |
| **Señales simples ortogonales** | Combina 3–4 señales de base teórica con pesos fijos (z-score) en vez de un bosque sobre 158 variables. |
| **Datos** | Añade **fundamentales** (EPS, ROE, gross margin, book value) para desbloquear PEAD, quality y value. Es el ingrediente que falta. |

---

## 6. Hoja de Ruta Priorizada (implementar en Qlib)

> Criterio de aceptación en cada paso: **walk-forward con IC agregado OOS > 0.02**, no solo el backtest bonito.

| # | Qué probar | Cómo en Qlib | Expectativa realista de IC OOS |
|---|---|---|---|
| **1** | **TS-Momentum puro (señal simple)** | Posición ∝ sign(retorno 12m)/σ, rebalanceo mensual/semanal, vol-targeting. La señal Nº1 a probar primero. | **0.03–0.05** (es tu mejor apuesta de alpha real) |
| **2** | **Momentum 12–1 transversal + 52-week high** | Ranking de 16 por `Ref($close,-21)/Ref($close,-252)-1` y `$close/Max($high,252)`, topk 3–5, con stop de 52-week high. | 0.02–0.04 |
| **3** | **Añadir low-vol/beta como escala de riesgo** | β/σ 60d; reducir peso en los más volátiles cuando momentum de mercado negativo. Reduce momentum-crash. | no sube IC, pero mejora Sharpe/drawdown |
| **4** | **PEAD / earnings revision** (requiere fundamentales) | Añadir EPS/SUE a datos; señal de drift post-anuncio (60–90d) y revisiones de analistas. La fuente de alpha más ortogonal. | 0.02–0.04 (en megacaps, algo menor que en universos amplios) |
| **5** | **Quality (profitability) como filtro/cap** | ROE, gross margin como screen; no caer en momentum de la peor empresa. | no sube IC bruto, sube la calidad del alpha |
| **6** | **Combinación 3–4 señales ortogonales** | z(momentum) + λ·z(PEAD) + λ·z(quality); pesos fijos estimados en train, validados en walk-forward. | 0.03–0.05 con mejor Sharpe que cada uno solo |
| **7** | **Si IC sigue <0.02 tras 2–3 iteraciones serias** | **Conclusión honesta:** aceptar **cartera de índice/calidad + gestión de riesgo** (vol-targeting, diversificación) en lugar de forzar un modelo que no predice. Es la respuesta racional en un universo tan concentrado. | n/a — objetivo cambia de alpha a riesgo/calidad |

**Timeline realista:** pasos 1–3 en 1–2 semanas (solo OHLCV, señal simple). Paso 4 en 2–4 semanas (importar fundamentales). Pasos 5–7 en 1–2 meses consolidando.

**Nota sobre expectativas:** un **IC 0.02–0.05 es bueno y explotable**; no persigas 0.10 (señal de overfitting). Con IR ≈ IC×√BR y tu breadth limitado (16 nombres, ~rebalanceo semanal), espera **IR 0.5–0.7** con costes IB como resultado sólido. El exceso de complejidad (158 factores, modelos gigantes) es el enemigo declarado: **casi siempre sobreajusta**.

---

## 7. Fuentes y Limitaciones

### Fuentes primarias (papers reales, verificados por búsqueda web)
- Jegadeesh, N. & Titman, S. (1993). *Returns to Buying Winners and Selling Losers: Implications for Stock Market Efficiency.* **Journal of Finance**.
- Jegadeesh, N. & Titman, S. (2001). *Profitability of Momentum Strategies: An Evaluation of Alternative Explanations.* **Journal of Finance**.
- George, T. & Hwang, C.-Y. (2004). *The 52-Week High and Momentum Investing.* **Journal of Finance** 59, 2145–2176.
- Moskowitz, T., Ooi, Y. & Pedersen, L.H. (2012). *Time Series Momentum.* **Journal of Financial Economics** 104, 228–250.
- Asness, C., Moskowitz, T. & Pedersen, L.H. (2013). *Value and Momentum Everywhere.* **Journal of Finance** 68, 929–985.
- Bernard, V. & Thomas, J. (1989). *Post-Earnings-Announcement Drift: Delayed Price Response or Risk Premium?* **Journal of Accounting Research** 27, 1–36.
- Chan, L., Jegadeesh, N. & Lakonishok, J. (1996). *Momentum Strategies.* **Journal of Finance** 51, 1681–1713.
- Jegadeesh, N. & Livnat, J. (2006). *Revenue Surprises and Stock Returns.* **Journal of Accounting and Economics**.
- Fama, E. & French, K. (1993). *Common Risk Factors in the Returns on Stocks and Bonds.* **Journal of Financial Economics** 33, 3–56.
- Fama, E. & French, K. (2015). *A Five-Factor Asset Pricing Model.* **Journal of Financial Economics** 116, 1–22.
- Novy-Marx, R. (2013). *The Other Side of Value: The Gross Profitability Premium.* **Journal of Financial Economics** 108, 1–28.
- Asness, C., Frazzini, A. & Pedersen, L.H. (2019). *Quality Minus Junk.* **Review of Asset Pricing Studies**.
- Ang, A., Hodrick, R., Xing, Y. & Zhang, X. (2006). *The Cross-Section of Volatility and Expected Returns.* **Journal of Finance** 61, 259–299.
- Frazzini, A. & Pedersen, L.H. (2014). *Betting Against Beta.* **Journal of Financial Economics** 111, 1–25.
- Daniel, K. & Moskowitz, T. (2016). *Momentum Crashes.* **Journal of Financial Economics** 122, 221–247.
- Haugen, R. & Baker, N. (1996). *Commonality in the Determinants of Expected Stock Returns.* **Journal of Financial Economics**.
- Israel, R. & Moskowitz, T. (2013). *The Role of Shorting, Size and Time in Market Neutral Strategies.* **Review of Financial Studies**.
- Grinold, R. (1989). *The Fundamental Law of Active Management.* **Journal of Portfolio Management** (base del IC→IR).
- López de Prado, M. (2018). *Advances in Financial Machine Learning.* Wiley (sobre purged CV, overfitting, data snooping).

### Fuentes de implementación Qlib
- Documentación oficial Qlib: cómo añadir factores fundamentales no-OHLCV (PE, EPS) al dump de datos.
- Microsoft **RD-Agent / R&D-Agent-Quant** (factor mining con LLM; resultado publicado: mejor rendimiento con ~70% menos factores) — arxiv 2505.15155.
- Alpha158/Alpha360 (Microsoft Qlib).

### Limitaciones y advertencias honestas
1. **No he ejecutado backtests en este informe**: las magnitudes de IC son expectativas basadas en la literatura, NO resultados medidos en tu universo. Deben validarse con walk-forward en Qlib (criterio §6).
2. **Los papers citan universos amplios y mercados múltiples**; la transposición a 16 megacaps tech reduce el alpha transversal y cambia momentum a TS-momentum. No transfiero la magnitud exacta de los papers a tu universo.
3. **No he verificado las fuentes de datos fundamentales disponibles** para tu instalación Qlib US (EPS/ROE/consenso). Si no las tienes, PEAD/quality/value requieren una importación de datos nueva (fricción real).
4. **Decaimiento de factores (alpha decay) y crowding:** el momentum y PEAD se han erosionado parcialmente por el arbitraje institucional; en megacaps muy seguidas, el edge es menor que en los papers históricos.
5. **Los factores por sí solos no garantizan IC>0.02**: el resultado depende del universo, horizonte y costes. La única prueba válida es el walk-forward OOS.
6. **Sesgo de supervivencia en la selección de 16 tickers** (todas hoy "ganadoras"): esto infla la prima de momentum en muestra; el walk-forward con labels correctos lo mitiga, pero no lo elimina.

---

*Documento de referencia del proyecto Qlib Work — estrategias y factores con base empírica. Se actualiza con cada experimento de la hoja de ruta.*
