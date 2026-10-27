# Cierre de la línea de investigación — resultado

> **Fecha:** 2026-10-27
> **Alcance:** 10 auditorías sobre los resultados del proyecto desde 2026-05
> **Conclusión:** 🔴 **Ninguna de las estrategias testeadas tiene una ventaja
> demostrable sobre exposición simple al mercado.**

---

## 1. El resultado en una frase

El proyecto ha producido **infraestructura sólida y auditorías rigurosas**, pero
**ninguna señal con edge demostrado**. De nueve resultados que se presentaban
como hallazgos, ocho no resistieron una comprobación honesta.

---

## 2. Qué se probó y qué salió

| Línea | Test aplicado | Resultado |
|---|---|---|
| **Momentum 120d top-30** | 500 carteras aleatorias, mismo universo y costes | 🔴 **Percentil 57** (mediana del azar). El inverso no es peor. El equal-weight gana |
| **IC del momentum** | Cross-sectional + purged CV con embargo + t honesto | 🔴 **+0,032 no significativo** (120d), **≈0** (60d). El 0,066 no existía |
| **Vol-targeting sobre EW** | Control de misma exposición + bootstrap + crisis por crisis | 🟡 **Sharpe p=0,48** (no significativo). Drawdown **+17,5pp pero de un solo evento** |
| **Filtro PEAD negativo** | Embudo de condiciones sobre 292 tickers | 🔴 **2 candidatos de 292**. No puede activarse por diseño |
| **PEAD (señal positiva)** | Cobertura temporal de los datos | 🔴 **No backtesteable**: Yahoo solo da 1 año (615/670 tickers con 4 trimestres) |
| **SFM v8 (crypto)** | Pipeline v9 causal sin leaks | 🔴 **3 leaks**: Sharpe 2,17 → 0,27. La señal era el leak |
| **Vol-gate** | Re-verificación + arquitectura E3 real | 🟡 Efecto en drawdown (−41,0% → −33,4%), **Sharpe +0,017 = ruido** |
| **`momentum_vt` (Sharpe 1,07)** | Import del módulo | 🔴 **No ejecutable**: `toni.vol_target_strategy` no existe |
| **CSI300 (14-31% anual)** | Búsqueda de los runs de MLflow | 🔴 **No verificable** + contradicción de 10x entre documentos |
| **Jev (sizing por régimen)** | 7 fórmulas sobre probabilidades | 🔴 **Descartado**: mejor Sharpe 0,91 vs 0,97 del vol-gate |

---

## 3. El resultado más importante: el vol-targeting

Es la única línea que mostró un efecto real, y hay que explicar por qué **aun
así no se sostiene**.

### Lo que dicen los números

| Variante | CAGR | vol | Sharpe | maxDD | Calmar |
|---|---:|---:|---:|---:|---:|
| EW puro | 11,3% | 18,7% | 0,67 | −38,7% | 0,29 |
| Control (escalado 0,91 constante) | 10,3% | 17,0% | 0,67 | −35,6% | 0,29 |
| **VT win20 tgt15% lev≤1** | 8,8% | 13,1% | **0,71** | **−18,0%** | **0,49** |

- **Sharpe:** delta +0,049, bootstrap p=**0,482** (IC95 −0,242 .. +0,321).
  No significativo, ni siquiera con el signo bien determinado.
- **Drawdown:** −18,0% vs −35,6% del control a **igual exposición media**.
  Mejora de **17,5pp**. Calmar 0,29 → **0,49**.

### Por qué no basta: descomposición por crisis

| Crisis | DD control | DD VT | Mejora |
|---|---:|---:|---:|
| **COVID (2019-04 → 2020-03)** | −35,6% | −18,0% | **+17,5pp** |
| 2022 (ago-sep) | −17,3% | −15,0% | +2,3pp |
| 2018 Q4 | −17,1% | −17,8% | **−0,7pp** |
| 2020-2022 | −15,5% | −14,1% | +1,3pp |
| 2023-2025 | −15,0% | −13,8% | +1,2pp |

**Todo el efecto es un único evento.** En las otras cuatro crisis la mejora
está entre −0,7 y +2,3pp: ruido.

### La explicación económica

El vol-targeting protege en **crashes rápidos**, donde la volatilidad se dispara
antes de que el precio caiga del todo (COVID: el VIX pasó de 15 a 82 en tres
semanas). En **mercados bajistas lentos** (2022) no aporta: la volatilidad sube
despacio y la exposición se mantiene moderada mientras el mercado cae.

Es coherente con Moreira & Muir (2017), pero implica que **la protección cubre
el tipo de crisis menos frecuente**. El bajista lento es el más común.

### Veredicto sobre el vol-targeting

> **No hay evidencia suficiente para sostenerlo como seguro de drawdown.**
> El efecto existe, es económicamente sensato y coincide con la medición previa
> del vol-gate (−41,0% → −33,4%), pero **descansa en un solo episodio**.

Es el mismo problema de potencia que invalidó el momentum, ahora aplicado a mi
propio resultado. Aplicar un estándar y no otro sería deshonesto.

**Uso defendible:** si alguien quiere protección específica ante crashes
rápidos y acepta ceder 1,5pp anuales por ella, el mecanismo está documentado.
**No es** un sistema con ventaja demostrada.

---

## 4. La causa raíz: potencia estadística

Este es el hallazgo que explica los otros nueve.

| Horizonte | Observaciones independientes en 8,8 años |
|---|---:|
| 30 días | ~69 |
| 60 días | ~34 |
| 120 días | ~17 |

Para detectar un IC de 0,03 con significancia hacen falta **cientos**. El
proyecto lleva desde mayo buscando efectos de ese tamaño con una muestra que no
puede distinguirlos de cero.

**Consecuencia:** cualquier iteración sobre estos datos produce ruido con
apariencia de señal. Los ocho falsos positivos no fueron ocho errores
independientes — fueron ocho manifestaciones del mismo problema.

Y no se arregla con más análisis: haría falta **más historia** o **más mercados
independientes**, no más variantes.

---

## 5. Los tres fallos de proceso (la parte reutilizable)

Ninguno de los ocho falsos positivos se habría detectado leyendo los documentos.
Todos requirieron **ir a comprobar**. Los tres huecos concretos:

### 5.1 No había hipótesis nula

Nunca se comparó contra carteras aleatorias. Se comparaba contra un índice, que
mezcla selección con beta y con diferencias de volatilidad.

**Regla:** toda estrategia de selección se compara contra **N carteras aleatorias
del mismo universo y tamaño**, mismo calendario y mismos costes. El percentil es
la métrica, no el Sharpe a secas.

### 5.2 No había holdout

El backtest de momentum corrió 2022-01-01 → 2026-08-07, la ventana donde
funciona. No por mala fe: es el sesgo natural de mirar los datos. En el periodo
completo (2018-2026) el Sharpe cae de 0,98 a **0,59**.

**Regla:** reservar un periodo que **no se mira** hasta tener la conclusión
escrita. Si hace falta ajustar algo, se usa otro tramo.

### 5.3 No se contaban los intentos

Se probaron decenas de variantes: ventanas de momentum, topk, PEAD como filtro y
como señal, vol-gate con 4 umbrales, low-vol, Jev con 7 fórmulas, SFM v8/v9,
CSI300 con múltiples configs. Con suficientes intentos, alguna sale bien por azar.

**Regla:** llevar un registro de hipótesis probadas. Sin ese contador, un
resultado aislado no es interpretable.

---

## 6. Qué sobrevive, y no es poco

### 6.1 Infraestructura

- qlib funcionando con datos US (1,3 GB, 1.180 tickers) y crypto (9 monedas)
- `rutas_entorno.py`: resolución de rutas con protección contra leer crypto en
  una estrategia de acciones
- Pipeline de backtest propio, vectorizado (300 carteras aleatorias en ~9 s)
- Paper-trading con estado persistido (E1/E2/E3)

### 6.2 Herramientas de auditoría

| Script | Qué hace |
|---|---|
| `audit_momentum_ic.py` | IC cross-sectional + purged CV con embargo + t honesto + barrido de horizontes |
| `audit_momentum_alpha.py` | Test contra carteras aleatorias (hipótesis nula) |
| `audit_vol_target.py` | Control de misma exposición + bootstrap + descomposición por crisis |
| `auditoria_v8.py` | Cuantificación de leaks en pipelines ML |

Estas herramientas son **reutilizables para cualquier estrategia futura**, y son
más valiosas que los resultados que produjeron.

### 6.3 La disciplina

Saber leer un IC, detectar un leak, construir una hipótesis nula, desconfiar de
un Sharpe de 1,07 y reconocer un resultado propio como artefacto (el caso
`vol_pct`, el signo del drawdown, el look-ahead de `simulate`). Eso no se aprende
leyendo.

---

## 7. Recomendación

### Si el objetivo es rentabilidad

**Equal-weight del universo y nada más.** Sharpe 0,67 en 8,8 años, 1,04 en
2022-2026, sin rotación, sin investigación, sin coste de mantenimiento. Es beta,
y la beta es lo que puedes obtener con ventaja demostrada.

Si se quiere protección ante crashes rápidos: añadir vol-targeting, sabiendo que
la evidencia es de un solo evento y cuesta 1,5pp anuales.

### Si el objetivo es aprender investigación cuantitativa

**El proyecto ya lo ha conseguido.** Diez auditorías, ocho falsos positivos
encontrados en trabajo propio, tres fallos de proceso identificados con su
remedio. Eso es más formación que cualquier curso.

### Lo que no hacer

- Otra variante de momentum sobre los mismos datos
- Backtestear PEAD con datos de un año
- Abrir una línea nueva sin aplicar las tres reglas del punto 5

---

## 8. Balance de las diez auditorías

| # | Artefacto | Fallo encontrado |
|---|---|---|
| 1 | Config SP500 | No existía |
| 2 | `vol_pct` (mi aviso) | **Falso positivo mío** — era causal |
| 3 | Entorno qlib | xgboost roto |
| 4 | `vol_gate` | Mecanismo inerte (`self.topk` no cambia el ranking) |
| 5 | SFM v8 | 3 leaks de futuro |
| 6 | `momentum_vt` | Import roto |
| 7 | CSI300 | Contradicción documental de 10x |
| 8 | IC 0,066 | No reproducible; el real es 0,032 y no significativo |
| 9 | Ranking de momentum | Percentil 57 vs aleatorias |
| 10 | **Vol-targeting** | **El +17,5pp es un solo evento** |

**Nueve de diez** presentaban un número que no resistía una comprobación. Y dos
de los errores encontrados fueron míos.

---

## 9. Lección final

El patrón que se repite en las diez auditorías:

> **El fallo más peligroso no es el que rompe. Es el que devuelve un número
> creíble.**

Un `ModuleNotFoundError` se ve. Un Sharpe de 1,07 con un import roto, un IC de
0,066 que nadie calculó, un drawdown que mejora por un solo evento — eso no se
ve. Se acepta.

La única defensa es **ir a comprobar**, siempre, incluso cuando el resultado
confirma lo que uno espera. Sobre todo entonces.

---

*Cierre del 2026-10-27. Scripts: `work/estrategias/audit_momentum_ic.py`,
`audit_momentum_alpha.py`, `audit_vol_target.py`. Auditorías individuales en
`work/qlib_work/`.*
