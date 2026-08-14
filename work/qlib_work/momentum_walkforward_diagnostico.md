# 🧪 Momentum Walk-Forward — Resultado (IC negativo en tech_giants)

> **Fecha:** 2026-08-14
> **Proyecto:** Qlib Work — búsqueda de alpha en el universo tech_giants
> **Contexto:** tras confirmar que Alpha158+LightGBM daba IC OOS 0.0078 (sin alpha), probamos momentum puro como la alternativa con mayor respaldo empírico (Jegadeesh-Titman 1993, George-Hwang 2004, Moskowitz et al. 2012).

---

## 1. Método

- **Señal:** momentum = retorno acumulado pasado en 4 ventanas (20, 60, 120, 250 días)
- **Target:** retorno futuro a 10 días (label)
- **Universo:** tech_giants (16 megacaps del mismo sector)
- **Validación:** walk-forward por año (2019-2026), midiendo IC (correlación momentum→retorno futuro) y long-short del decil

## 2. Resultados — IC por ventana y año

| Año | mom20 | mom60 | mom120 | mom250 | L/S(60d) |
|---|---|---|---|---|---|
| 2019 | −0.059 | −0.042 | −0.118 | −0.001 | −0.06% |
| 2020 | −0.057 | −0.008 | +0.051 | +0.119 | +1.87% |
| 2021 | −0.048 | −0.099 | −0.124 | −0.071 | +0.75% |
| 2022 | −0.072 | −0.185 | −0.122 | −0.161 | −0.16% |
| 2023 | −0.099 | −0.110 | −0.081 | −0.096 | −0.18% |
| 2024 | −0.032 | −0.002 | +0.022 | +0.081 | +2.40% |
| 2025 | +0.021 | −0.042 | −0.071 | −0.062 | −0.03% |
| 2026 | +0.186 | −0.012 | +0.008 | +0.142 | +2.24% |
| **IC medio** | **−0.020** | **−0.063** | **−0.054** | **−0.006** | |

## 3. Veredicto

**❌ El momentum NO muestra alpha robusto out-of-sample en este universo.**

- **IC medios NEGATIVOS** en las 4 ventanas (mom60: −0.063, mom120: −0.054, mom20: −0.020, mom250: −0.006)
- Los ICs son **consistentemente negativos o ≈0** año tras año (no ruido alrededor de cero, sino sesgo negativo)
- El long-short del momentum a 60d es ~0 la mayoría de los años
- Solo en **2026** aparece alpha positivo en mom20 (+0.19) y mom250 (+0.14) — sugerente de que la dinámica depende del **régimen de mercado**, no es estable

## 4. Interpretación

**En 16 megacaps del mismo sector, el momentum transversal está INVERTIDO o es inexistente.**

Esto es **coherente con la literatura**: el momentum transversal funciona entre *muchas* acciones de *distintos* sectores, no entre pocas primas hermanas **altamente correlacionadas**. Con solo 16 nombres tech que se mueven casi juntos, la señal de momentum se diluye o invierte.

## 5. Conclusión global de la búsqueda de alpha en tech_giants

| Enfoque | IC OOS | Veredicto |
|---|---|---|
| Alpha158 + LightGBM | +0.0078 | ❌ Sin alpha (ruido) |
| Momentum puro (20-250d) | **negativo** (−0.02 a −0.06) | ❌ Invertido/inexistente |

**Conclusión honesta (coincide con la hipótesis de Quinn):** el universo de 16 megacaps del mismo sector **no ofrece alpha transversal explotable**. El problema es estructural: universo demasiado concentrado y correlacionado. No es hiperparámetros ni ejecución — es la fuente de señal sobre este universo.

**Esto valida el giro de enfoque:** hay que **AMPLIAR el universo** (a miles de acciones de distintos sectores) donde los factores sí funcionan, o aceptar **beta de calidad + gestión de riesgo**.

---

*Documento de referencia del proyecto Qlib Work. Se actualiza con cada experimento.*
