# Sharpe Ratio, Varianza y Desviación Típica — Apuntes

## Varianza (σ²)

Mide la **dispersión** de los datos respecto a su media. Es el promedio de las diferencias al cuadrado:

```
σ² = (1/n) × Σ (r_i - μ)²
```

**Problema**: está en unidades al cuadrado. Si los retornos son porcentajes diarios, la varianza está en "%²/día" — una unidad sin interpretación intuitiva.

## Desviación Típica (σ) — Desviación Estándar

Es la raíz cuadrada de la varianza. Vuelve a la unidad original:

```
σ = √(σ²)
```

Si los retornos están en % diarios, σ está en **% diarios**. Eso se entiende.

En finanzas, la desviación típica **es la medida de riesgo estándar**. Cuando se dice "la volatilidad del SP500 es del 15% anual", se refiere a la desviación típica anual de los retornos.

### Ejemplo

| Estrategia | Media diaria (μ) | Desv. típica diaria (σ) | Interpretación |
|-----------|:---:|:---:|----------------|
| A (bonos) | +0.04% | 0.2% | Retornos pequeños y estables |
| B (SP500) | +0.06% | 1.0% | Retornos moderados con algo de ruido |
| C (crypto hold) | +0.10% | 3.5% | Gana más pero con oscilaciones fuertes |

La desviación típica te dice cuánto se desvía tu cartera de la media en un día típico.

### Por qué importa

| σ baja | Retornos predecibles, dormir tranquilo |
| σ alta | Grandes subidas y bajadas, posible margin call |
| σ crypto diaria | ~2–5% (puedes perder un 10% en un día) |
| σ SP500 diaria | ~0.5–1.5% (un mal día es -2%) |

---

## Sharpe Ratio

Mide el **retorno ajustado por riesgo**. Fórmula completa:

```
Sharpe = (Retorno medio - Tasa libre de riesgo) / Desviación estándar de los retornos
```

### Sharpe diario

```
Sharpe_diario = μ_diario / σ_diario
```

### Anualización

Para hacerlo interpretable (todo el mundo piensa en rentabilidades anuales), se anualiza. La varianza escala linealmente con el tiempo:

| Magnitud | Fórmula |
|----------|---------|
| Retorno anual | μ_diario × 252 |
| Varianza anual | σ²_diario × 252 |
| Desviación anual | σ_diario × √252 |

Al hacer el cociente:

```
Sharpe_anual = (μ_diario × 252) / (σ_diario × √252)
             = (μ_diario / σ_diario) × √252
```

**¿Por qué 252?** Los mercados financieros tradicionales abren ~252 días al año. La volatilidad solo se acumula cuando hay trading. En crypto, que opera 24/7, algunos usan √365, pero el estándar académico es √252. Lo importante es ser consistente para poder comparar estrategias.

### Interpretación

| Sharpe | Interpretación |
|--------|----------------|
| < 0.5 | Pobre — apenas compensa el riesgo |
| 0.5 – 1.0 | Aceptable |
| 1.0 – 1.5 | Bueno |
| 1.5 – 2.0 | Excelente |
| > 2.0 | Sospechoso (probable overfitting o data leakage) |

**Más alto es mejor.** La intuición:

- **Numerador (μ)**: cuánto ganas de media
- **Denominador (σ)**: cuánta volatilidad/riesgo asumes

Un Sharpe alto significa que estás ganando dinero con poca volatilidad — el modelo es consistente, sin picos de pérdidas enormes.

Un Sharpe de 5.0 en backtesting casi siempre es **overfitting**: el modelo memorizó el pasado pero no generalizará. Por eso el early stopping + validación separada + Optuna mitigan este riesgo.

### Tasa libre de riesgo

En los scripts actuales (v2 y v3) se asume **rf = 0**:

```python
sharpe = np.mean(strategy_returns) / np.std(strategy_returns) * np.sqrt(252)
```

**En crypto** la simplificación es aceptable porque:
- Volatilidad diaria: ~2–5%
- Tasa libre de riesgo: ~2.5–3% anual (~0.01% diario)
- Impacto: despreciable (restar 0.01% frente a σ de 2–3% no cambia el resultado)

**En stocks/ETFs no sería correcto**. Ejemplo sobre SPY:

```
μ=0.04% diario, σ=1.0%, rf=4% anual (0.015% diario)

Sharpe con rf=0: 0.04 / 1.0 × √252 ≈ 0.63
Sharpe real: (0.04-0.015) / 1.0 × √252 ≈ 0.40
```

Para acciones/ETFs habría que usar:

```python
# USD
rf_rate = 0.045  # 4.5% anual (Fed Funds / SOFR 2026)
rf_daily = (1 + rf_rate) ** (1/252) - 1
sharpe = np.mean(strategy_returns - rf_daily) / np.std(strategy_returns) * np.sqrt(252)

# EUR
rf_rate = 0.025  # 2.5% anual (€STR)
```

### En el código actual (v3)

```python
# Durante la optimización con Optuna:
def evaluate_trial(model, X_test, y_test, cryptos, device):
    ...
    sharpe = np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-10) * np.sqrt(252)
```

Se añade `+ 1e-10` para evitar división entre cero si σ = 0 (extremo pero posible con pocos datos).

---

## Relación entre los tres conceptos

```
Varianza (σ²) → unidades al cuadrado, difícil de interpretar
     ↓ √
Desviación típica (σ) → unidades originales, es la volatilidad
     ↓
Sharpe = (μ - rf) / σ → retorno por unidad de riesgo
     ↓ × √252
Sharpe anualizado → interpretable, comparable entre estrategias
```

La varianza y desviación describen el **riesgo**. El Sharpe conecta el **retorno** con ese riesgo en un solo número que responde a: "¿merece la pena?"
