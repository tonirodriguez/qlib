# ROADMAP TRABAJO — Estrategia Cuantitativa Rentable con Operativa Diaria

> **Fecha:** Septiembre 2026 (revisado)
> **Última actualización:** 1 Septiembre 2026
> **Cronjob:** ✅ Configurado — `0 9 * * *` (ejecución automática diaria a las 9:00 AM)
> **Objetivo:** Generar una estrategia de inversión cuantitativa rentable con señales diarias, basada en Microsoft Qlib.

---

## 📊 RESUMEN DE EXPERIMENTOS REALIZADOS

### 🇨🇳 Mercado Chino (CSI300) — LightGBM + alpha158

| Experimento | Label | TopK | Ann Return | Std | Rank IC | Rank ICIR |
|------------|:-----:|:----:|:----------:|:---:|:------:|:---------:|
| **Baseline** | 1d | 50 | 14.73% | 0.0055 | 0.0487 | 0.4057 |
| **Label 5d** | 5d | 50 | 20.52% | 0.0049 | 0.0793 | 0.6141 |
| **Tuned (default 50)** | 1d | 50 | 11.06% | 0.0059 | 0.0495 | 0.3897 |
| **Tuned Top20** | 1d | 20 | 17.25% | 0.0087 | 0.0495 | 0.3897 |
| **Tuned Top30** | 1d | 30 | 15.19% | 0.0073 | 0.0495 | 0.3897 |
| **Tuned SoftTopk20** | 1d | 20 | 31.40% | 0.0081 | 0.0495 | 0.3897 |

- **Periodo:** Train 2008-2014 / Valid 2015-2016 / Test 2017-2020
- **Features:** alpha158 (158 factores técnicos)
- **Modelo:** LightGBM
- **Estrategia:** TopkDropoutStrategy / SoftTopkStrategy
- **Simulador:** diario, con costes de transacción (limit_threshold 0.095)

### 🇨🇳 Mercado Chino (CSI500)

| Experimento | Label | TopK | Ann Return | Std | Rank IC | Rank ICIR |
|------------|:-----:|:----:|:----------:|:---:|:------:|:---------:|
| **CSI500 Baseline** | 1d | 50 | 13.33% | 0.0052 | 0.0459 | 0.4722 |

- Mismo periodo y modelo, sobre 500 valores chinos mid-cap

### 🇺🇸 Mercado USA (S&P 500)

| Experimento | Estado | Periodo |
|------------|:------:|:-------:|
| **SP500 Baseline alpha158** | ⏳ Config listo, no ejecutado | 2008-2025 |
| **SP500 Label 5d** | ⏳ Config listo, no ejecutado | 2008-2025 |

- **Región:** US
- **Benchmark:** ^GSPC
- **Features:** alpha158
- **Modelo:** LightGBM
- **TopK:** 30

### 🔮 Mercado Crypto (SFM — Stochastic Factor Model) ✅ COMPLETADO

| Versión | Estado | Sharpe Test | Equity Test |
|:-------:|:------:|:-----------:|:-----------:|
| **v4** | ✅ Walk-Forward + Denoising | +1.24 | 1.46x |
| **v5 (SP500)** | ⚠️ Señal más débil | +0.51 | 1.43x |
| **v6** | ❌ Sin denoising ni walk-forward | −0.67 | 0.22x |
| **v7** | ❌ Label 5d + sin denoising | −1.03 | 0.02x |
| **v8** | 🚀 **Modelo definitivo** | **+2.17** | **10.49x** |

### 🧪 Otras configs pendientes

| Config | Estado |
|--------|:------:|
| **alpha360** (CSI300, más features) | ⏳ Config lista, no ejecutada |
| **SP500 US label5d** | ⏳ Config lista, no ejecutado |

---

## 🎯 NUEVA HOJA DE RUTA — Hacia Producción (Septiembre 2026)

Con el éxito de **SFM v8** (Sharpe +2.17, Equity 10.49x), el objetivo cambia: **llevar el modelo crypto a señal diaria operativa**.

### ✅ Logros alcanzados

1. **SFM v8 validado** — Sharpe test +2.17, mejor equity 20.03x
2. **Modelo entrenado** — `sfm_top3.pth` con mejores parámetros
3. **Pipeline de datos** — `download_crypto_coingecko.py` funcional
4. **Documentación completa** — evolución v1→v8, resultados, comparativas

---

### 🔴 Fase 0 — Señal Diaria (Inmediata, esta semana)

| # | Tarea | Esfuerzo | Estado |
|:-:|-------|:--------:|:------:|
| 1 | 🔴 **Script de señal diaria** (`sfm_daily_signal.py`) — carga modelo v8, descarga datos, genera predicción para hoy | Bajo (2h) | ✅ **HECHO** |
| 2 | 🔴 **Script de actualización de datos** (`download_crypto_coingecko.py`) — fix del manifest.json aplicado | Bajo (30min) | ✅ **HECHO** |
| 3 | 🟡 **Cronjob diario** — `run_daily_pipeline.sh` ejecuta descarga → dump → señal → paper trading | Bajo (30min) | ✅ **HECHO** (`0 9 * * *`) |
| 4 | 🟡 **Paper trading** — simula operaciones automáticamente y registra historial | Medio (4-5h) | ✅ **HECHO** |
| 5 | 🟡 **Dump incremental Qlib** — `dump_coingecko_to_qlib.py` añade solo días nuevos sin regenerar todo | Bajo (1h) | ✅ **HECHO** |

#### 📋 Especificación de la señal diaria

```
Flujo:
  1. python download_crypto_coingecko.py   → Actualiza datos hasta ayer
  2. python sfm_daily_signal.py             → Genera predicción para hoy
  3. Salida: ranking de criptos con score, señal COMPRA/VENTA/ESPERAR

Formato de salida:
  📊 SEÑAL DIARIA SFM — 2026-09-02
  ========================================
  🥇 COMPRA:  BTC  | Score: +0.0351 | Confianza: ALTA
  🥈 COMPRA:  ETH  | Score: +0.0284 | Confianza: ALTA
  🥉 ESPERAR: SOL  | Score: +0.0082 | Confianza: BAJA
  ...
```

#### 📝 Registro de Implementación — Señal Diaria

| Fecha | Archivo | Descripción | Estado |
|:-----:|---------|-------------|:------:|
| 2026-09-01 | `work/crypto/sfm_daily_signal.py` | Script que carga modelo sfm_top3.pth, procesa features, genera predicción y ranking | ✅ **Implementado** |
| 2026-09-01 | `work/crypto/output/sfm_v8/signal_*.json` | Output JSON de la señal diaria (fecha, scores, señales) | ✅ **Generado automáticamente** |
| 2026-09-01 | `work/crypto/dump_coingecko_to_qlib.py` | Convierte CSVs de CoinGecko a Qlib binario (incremental, solo días nuevos) | ✅ **Implementado** |
| 2026-09-01 | `crontab -e` → `0 9 * * *` | Ejecución automática cada día a las 9:00 AM | ✅ **Configurado** |

**Detalles de implementación:**
- **Modelo por defecto:** `sfm_top3.pth` (Sharpe test 2.74, Equity 20.03x)
- **Parámetros:** hidden_dim=96, freq_components=20, lookback=20, dropout=0.30
- **Uso:** `conda run -n qlib python work/crypto/sfm_daily_signal.py`
- **Modelo alternativo:** `--model=top1` para usar otro del Top-5
- **Salida:** consola + JSON en `output/sfm_v8/signal_YYYY-MM-DD.json`
- **Escalado:** guarda scaler.pkl automáticamente en primera ejecución
- **Denoising:** Wavelet (db2, level=2) como en v8

```bash
# Ejemplo de ejecución
cd /mnt/c/Users/trodriguez/src/qlib
conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top3

# Para usar ensemble manual de Top-3:
# conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top3
# conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top1
# conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top4
# Luego combinar scores (media ponderada)
```

---

### 🟡 Fase 1 — Robustecimiento (1-2 semanas)

| # | Tarea | Esfuerzo | Impacto |
|:-:|-------|:--------:|:-------:|
| 5 | 🟡 **Ensemble de Top-3 modelos** — combinar predicciones de sfm_top1, sfm_top3, sfm_top4 | Medio (3-4h) | Reduce varianza, Sharpe esperado +2.0-2.5 |
| 6 | 🟡 **Paper trading automático** — ejecuta la señal y registra resultados en un archivo de historial | Medio (4-5h) | Validación en vivo sin riesgo |
| 7 | 🟢 **Dashboard Streamlit** — señal diaria, equity curve, métricas en tiempo real | Medio (3-4h) | Visibilidad del rendimiento |
| 8 | 🟢 **Alertas de decaimiento** — detectar si la señal empieza a fallar (Sharpe rodante < 1.0) | Bajo (2h) | Prevención de pérdidas |

---

### 🟠 Fase 2 — Diversificación (2-4 semanas)

| # | Tarea | Esfuerzo | Por qué |
|:-:|-------|:--------:|---------|
| 9 | 🟡 **Extender a más criptos** (BNB, DOT, AVAX, etc.) | Bajo (1h) | Más oportunidades, menor concentración |
| 10 | 🟡 **Reentrenamiento automático** — ejecutar v8 cada 2-4 semanas con datos nuevos | Medio (3-4h) | Evitar decaimiento de la señal |
| 11 | 🟢 **Probar SP500 US baseline** — config ya lista, datos ya existen | Bajo (1h) | Diversificación a acciones |

---

### 🔵 Fase 3 — Producción Real (1-2 meses)

| # | Tarea | Esfuerzo | Dependencias |
|:-:|-------|:--------:|:------------|
| 12 | 🔵 **Integración con broker** (Interactive Brokers) | Alto (1-2 semanas) | Fase 1, Fase 2 |
| 13 | 🔵 **Risk management automático** — stop-loss, VaR diario, posición máxima | Medio (1 semana) | #12 |
| 14 | 🔵 **Backup y recuperación** del sistema completo | Medio (3-4 días) | #12 |

---

### 🔮 Fase 4 — Modelos Avanzados (Largo plazo)

| # | Tarea | Esfuerzo |
|:-:|-------|:--------:|
| 15 | **Ensemble multimodelo:** LightGBM + GRU + Transformer | Alto |
| 16 | **Model routing:** ligero para diario, pesado para recalibración semanal | Medio |
| 17 | **Análisis fundamental + NLP** sobre noticias | Alto |

---

## 📋 PRIORIDADES INMEDIATAS ACTUALIZADAS

| # | Tarea | Esfuerzo | Impacto | Estado |
|:-:|-------|:--------:|:-------:|:------:|
| 1 | 🔴 Señal diaria SFM v8 | Bajo | **Crítico** — primer paso a producción | ✅ **HECHO** |
| 2 | 🔴 Descarga automática de datos | Bajo | **Crítico** — datos frescos cada día | ✅ **HECHO** |
| 3 | 🟡 Cronjob diario | Bajo | **Crítico** — automatización | ✅ **HECHO** (`0 9 * * *`) |
| 4 | 🟡 Paper trading | Medio | Alto — validación en vivo | ✅ **HECHO** |
| 5 | 🟡 Dump incremental Qlib | Bajo | Alto — datos actualizados sin regenerar | ✅ **HECHO** |
| 6 | 🟢 SP500 US baseline | Bajo | Medio — diversificación | ⏳ Pendiente |
| 7 | 🟢 Dashboard monitorización | Medio | Medio — visibilidad | ⏳ Pendiente |

---

## RECURSOS DISPONIBLES

- **QLib:** `qlib/` — framework principal (datos, modelos, backtesting)
- **Modelo SFM v8:** `work/crypto/output/sfm_v8/sfm_top3.pth` (mejor modelo, Sharpe 2.74)
- **Configs:** `qlib/config/` — 14 configs YAML para distintos universos y variantes
- **MLflow runs:** `qlib/mlruns/` — 9 experimentos con métricas almacenadas
- **Notebooks:** `qlib/notebooks/` — 3 notebooks de análisis
- **Documentación SFM:** `work/formacion/01 Literature/formacion/qlib/`
  - `sfm-comparativa-scripts.md` — evolución v1→v8
  - `sfm-v8-resultados.md` — resultados detallados de v8
  - `Estrategia Qlib 7 SFM v8.md` — diseño y pseudocódigo

---

---

## 📋 INSTRUCCIONES DIARIAS — Operativa Paso a Paso

### 🕐 Rutina diaria (9:00 AM)

Cada día de trading, ejecutar en este orden:

```
PASO 1 — Descargar datos CoinGecko   (~6 min)
PASO 2 — Dump incremental a Qlib     (~2 seg)
PASO 3 — Generar señal               (~7 seg)
PASO 4 — Paper trading               (~3 seg)
PASO 5 — Leer reporte                (~2 min)
PASO 6 — Decidir operaciones         (~5 min)
```

---

### 🔄 PASO 1 — Actualizar datos desde CoinGecko

```bash
cd /mnt/c/Users/trodriguez/src/qlib
conda run -n qlib python work/crypto/download_crypto_coingecko.py
```

**Qué hace:** Descarga OHLCV diario de las 9 criptos desde CoinGecko y los guarda en `data/qlib/` en formato Qlib binario.

**Duración:** ~6 minutos (9 criptos × ~40 seg cada una).

**Salida esperada:**
```
Descarga completada desde CoinGecko
  output_dir: data/qlib
  BTC: 3301 filas, 2017-08-17 -> 2026-09-01
  ETH: 3301 filas, 2017-08-17 -> 2026-09-01
  ...
```

---

### 🔄 PASO 2 — Dump incremental a Qlib binario

```bash
conda run -n qlib python work/crypto/dump_coingecko_to_qlib.py
```

**Qué hace:** Lee los CSVs descargados por CoinGecko y AÑADE solo los días nuevos al dataset Qlib binario (`data/qlib/`). No regenera todo desde cero — es incremental.

**Duración:** ~2 segundos.

**Salida esperada:**
```
🔄 Actualización incremental Qlib desde CoinGecko
   📅 Calendario actual: 3301 días (2017-08-17 → 2026-08-30)
     btc... ✅ +1 días [2026-08-31 → 2026-08-31]
     eth... ✅ +1 días [2026-08-31 → 2026-08-31]
     ...
   📅 Calendario actualizado: 3302 días (+9)
✅ Completado: 9 criptos actualizados, 9 días nuevos
```

---

### 📊 PASO 3 — Generar señal diaria

```bash
conda run -n qlib python work/crypto/sfm_daily_signal.py
```

**Qué hace:**
1. Carga el modelo `sfm_top3.pth` (Sharpe 2.74, el mejor de v8)
2. Toma los últimos 20 días de datos (lookback)
3. Aplica denoising wavelet
4. Predice el retorno esperado para mañana de cada cripto
5. Ordena por score descendente

**Opciones:**
```bash
# Usar otro modelo del Top-5
conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top1   # Sharpe 1.90
conda run -n qlib python work/crypto/sfm_daily_signal.py --model=top4   # Sharpe 2.37
```

**Salida esperada:**
```
📊 SEÑAL DIARIA SFM v8 — 2026-09-01
#    Señal      Cripto  Score     Retorno  Confianza
1   🟢 COMPRA   BTC     +0.0325   +3.25%   ALTA
2   🟡 ESPERAR  LTC     +0.0141   +1.41%   BAJA
3   🟡 ESPERAR  ETH     +0.0084   +0.84%   BAJA
4   🔻 VENTA    XLM     -0.0338   -3.38%   MEDIA
...
```

**Salida JSON:** `work/crypto/output/sfm_v8/signal_YYYY-MM-DD.json`

---

### 💰 PASO 4 — Ejecutar paper trading

```bash
conda run -n qlib python work/crypto/sfm_paper_trading.py
```

**Qué hace:**
1. Lee la señal del día (último `signal_*.json`)
2. Obtiene precios actuales desde Qlib
3. **Vende** posiciones cuya señal ya no es COMPRA
4. **Compra** nuevas posiciones según el ranking (máximo 2, solo confianza ALTA)
5. Calcula P&L de la cartera
6. Guarda estado y historial

**Salida esperada:**
```
📊 PAPER TRADING SFM v8 — 2026-09-01

💰 CAPITAL: $9,996.67  ($6,663.33 cash + $3,333.33 posiciones)
   Ganancia total: -0.03%  |  Pico: $10,000.00
   Operaciones: 1  |  Wins: 0  |  Losses: 0

📈 POSICIONES ACTIVAS (1):
Symbol   Shares   Entry      Current    Value      P&L       P&L%
BTC      0.0429   $77,682    $77,682    $3,333.33  $+0.00    +0.00%

🔄 OPERACIONES DE HOY (1):
   🟢 COMPRA BTC  0.0429 sh  @ $77,682  Coste: $3,336.67
```

---

### 📈 PASO 5 — Leer reporte y estado de la cartera

**Ver solo el estado actual sin ejecutar operaciones:**
```bash
conda run -n qlib python work/crypto/sfm_paper_trading.py --report
```

**Ver el historial completo de operaciones:**
```bash
cat work/crypto/output/sfm_v8/history_paper_trading.csv
```

**Ver el estado detallado (JSON):**
```bash
cat work/crypto/output/sfm_v8/state_paper_trading.json
```

**Ver el último log del pipeline:**
```bash
ls -t work/crypto/output/sfm_v8/logs/ | head -1 | xargs -I{} cat work/crypto/output/sfm_v8/logs/{}
```

**Reiniciar la cartera desde cero (si se quiere empezar de nuevo):**
```bash
conda run -n qlib python work/crypto/sfm_paper_trading.py --reset
```

---

### 🎯 PASO 6 — Interpretar la señal y decidir

#### Reglas de decisión

| Señal | Score | Confianza | Acción recomendada |
|:-----:|:-----:|:---------:|--------------------|
| 🟢 **COMPRA** | > +0.015 | ALTA si > +0.025 | **Entrar en posición** |
| 🟢 **COMPRA** | > +0.015 | MEDIA | **Valorar entrada** (50% de posición) |
| 🟡 **ESPERAR** | > 0 | BAJA | **No entrar**, mantener vigilancia |
| ⚪ **NEUTRAL** | > -0.01 | BAJA | **Mantenerse fuera** |
| 🔻 **VENTA** | < -0.01 | MEDIA | **Salir o reducir posición** |
| 🔴 **VENTA FUERTE** | < -0.02 | ALTA | **Salir inmediatamente** |

#### Gestión de posiciones (máximo 2 abiertas)

| Situación | Acción |
|-----------|--------|
| **0 posiciones, 1 COMPRA ALTA** | Entrar con ~33% del capital |
| **0 posiciones, 2+ COMPRAS ALTAS** | Entrar en las 2 mejores, ~33% cada una |
| **1 posición, nueva COMPRA ALTA** | Si la actual sigue siendo COMPRA → mantener. Si no → vender y comprar la nueva |
| **2 posiciones, nueva COMPRA ALTA** | Vender la peor de las 2 actuales y comprar la nueva |
| **Cualquier VENTA en una posición activa** | Vender esa posición |
| **Sin COMPRAS ni VENTAS** | No hacer nada, mantener posiciones |

#### Ejemplo práctico con la señal de hoy

```
Señal:
  🥇 BTC:  COMPRA ALTA  (+3.25%)  →  ENTRAR en BTC (33% del capital)
  🥈 LTC:  ESPERAR BAJA (+1.41%)  →  NO ENTRAR
  🥉 ETH:  ESPERAR BAJA (+0.84%)  →  NO ENTRAR
  Resto:   VENTA (-3% a -5%)      →  NO ENTRAR en altcoins

Decisión: Comprar BTC únicamente. El modelo ve mercado bajista en altcoins.
```

---

### 🤖 Automatización total (cronjob) ✅ CONFIGURADO

El pipeline se ejecuta automáticamente cada día a las **9:00 AM**:

```bash
# Verificar que el cronjob está activo
crontab -l
# Debe mostrar:
# 0 9 * * * /mnt/c/Users/trodriguez/src/qlib/work/crypto/run_daily_pipeline.sh
```

**Lo que ejecuta el cronjob (4 pasos en orden):**
1. `download_crypto_coingecko.py` — descarga datos frescos desde CoinGecko
2. `dump_coingecko_to_qlib.py` — convierte solo los días nuevos a Qlib binario (incremental)
3. `sfm_daily_signal.py` — genera la señal del día
4. `sfm_paper_trading.py` — ejecuta paper trading y guarda historial

**Para ver el resultado de la ejecución automática:**
```bash
# Ver el último log
ls -t work/crypto/output/sfm_v8/logs/ | head -1 | xargs -I{} cat work/crypto/output/sfm_v8/logs/{}

# Ver el estado de la cartera
conda run -n qlib python work/crypto/sfm_paper_trading.py --report
```

---

### 📊 Reporte de paper trading

#### Reporte rápido (diario)

```bash
# Ver el estado actual de la cartera
conda run -n qlib python work/crypto/sfm_paper_trading.py --report
```

**Salida:**
```
📊 PAPER TRADING SFM v8 — 2026-09-01
💰 CAPITAL: $10,023.45  ($6,690.12 cash + $3,333.33 posiciones)
   Ganancia total: +0.23%  |  Pico: $10,023.45
   Operaciones: 2  |  Wins: 1  |  Losses: 0
   Win Rate: 100.0%

📈 POSICIONES ACTIVAS (1):
Symbol   Shares   Entry      Current    Value      P&L       P&L%
BTC      0.0429   $77,689    $78,200    $3,355.69  +$22.36   +0.67%
```

#### Reporte detallado (historial completo)

```bash
# Ver el historial completo de operaciones
cat work/crypto/output/sfm_v8/history_paper_trading.csv
```

**Formato del CSV:**
```
date,total_value,cash,positions_value,n_positions,total_gain_pct,peak_capital,total_trades,wins,losses,n_trades_today
2026-09-01,9996.67,6663.33,3333.33,1,-0.03,10000.0,1,0,0,1
2026-09-02,10023.45,6690.12,3333.33,1,0.23,10023.45,2,1,0,1
...
```

#### Reporte estadístico completo

```bash
conda run -n qlib python -c "
import pandas as pd
import numpy as np

df = pd.read_csv('work/crypto/output/sfm_v8/history_paper_trading.csv')
total_days = len(df)
total_value = df['total_value'].iloc[-1]
total_gain = df['total_gain_pct'].iloc[-1]
total_trades = df['total_trades'].iloc[-1]
total_wins = df['wins'].iloc[-1]
total_losses = df['losses'].iloc[-1]
win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0.0

# Rentabilidad diaria
df['daily_return'] = df['total_value'].pct_change().fillna(0)
sharpe = df['daily_return'].mean() / df['daily_return'].std() * np.sqrt(365) if df['daily_return'].std() > 0 else 0.0

# Drawdown
df['peak'] = df['total_value'].cummax()
df['drawdown'] = (df['total_value'] - df['peak']) / df['peak'] * 100
max_dd = df['drawdown'].min()

print('='*50)
print('📊 REPORTE COMPLETO PAPER TRADING SFM v8')
print('='*50)
print(f'Período:           {df[\"date\"].iloc[0]} → {df[\"date\"].iloc[-1]} ({total_days} días)')
print(f'Capital inicial:   \$10,000.00')
print(f'Capital actual:    \${total_value:,.2f}')
print(f'Rentabilidad total: {total_gain:+.2f}%')
print(f'Rentabilidad diaria: {df[\"daily_return\"].mean()*100:+.4f}%')
print(f'Sharpe Ratio:      {sharpe:+.2f}')
print(f'Máximo drawdown:   {max_dd:.2f}%')
print(f'Operaciones totales: {total_trades}')
print(f'Wins:              {total_wins}  ({win_rate:.1f}%)')
print(f'Losses:            {total_losses}  ({(100-win_rate):.1f}%)')
print(f'Posiciones activas: {df[\"n_positions\"].iloc[-1]}')
print(f'Pico de capital:   \${df[\"peak_capital\"].iloc[-1]:,.2f}')
print('='*50)

# Resumen de operaciones recientes
print(f'\n📋 Últimas operaciones:')
print(f'{\"Fecha\":<12} {\"Acción\":<8} {\"Valor\":<12} {\"P&L\":<10}')
print('-'*42)
for _, row in df.tail(5).iterrows():
    print(f'{row[\"date\"]:<12} {\"CARTERA\":<8} \${row[\"total_value\"]:<9,.2f} {row[\"total_gain_pct\"]:+6.2f}%')
"
```

**Salida del reporte completo:**
```
==================================================
📊 REPORTE COMPLETO PAPER TRADING SFM v8
==================================================
Período:           2026-09-01 → 2026-09-07 (7 días)
Capital inicial:   $10,000.00
Capital actual:    $10,123.45
Rentabilidad total: +1.23%
Rentabilidad diaria: +0.1762%
Sharpe Ratio:      +2.15
Máximo drawdown:   -0.03%
Operaciones totales: 3
Wins:              2  (66.7%)
Losses:            1  (33.3%)
Posiciones activas: 1
Pico de capital:   $10,123.45
==================================================

📋 Últimas operaciones:
Fecha        Acción   Valor        P&L       
------------------------------------------
2026-09-01  CARTERA  $9,996.67  -0.03%
2026-09-02  CARTERA  $10,023.45  +0.23%
2026-09-03  CARTERA  $10,045.12  +0.45%
2026-09-06  CARTERA  $10,089.34  +0.89%
2026-09-07  CARTERA  $10,123.45  +1.23%
```

#### Reporte de posiciones actuales

```bash
cat work/crypto/output/sfm_v8/state_paper_trading.json
```

**Salida:**
```json
{
  "capital_usd": 10023.45,
  "cash_usd": 6690.12,
  "positions": {
    "BTC": {
      "shares": 0.0429,
      "entry_price": 77689.0,
      "entry_date": "2026-09-01"
    }
  },
  "total_trades": 2,
  "wins": 1,
  "losses": 0,
  "total_fees_paid": 6.67,
  "peak_capital": 10023.45,
  "last_updated": "2026-09-07T09:05:23",
  "created_at": "2026-09-01T18:36:45"
}
```

#### Alertas automáticas (configuración recomendada)

Configurar alertas en el sistema para notificar cuando:

| Alerta | Condición | Acción |
|--------|-----------|--------|
| 🟢 **Compra ejecutada** | Señal COMPRA ALTA | Notificar nueva posición |
| 🔴 **Venta ejecutada** | Se vende una posición | Notificar cierre + P&L |
| ⚠️ **Drawdown > 10%** | Capital < $9,000 | Revisar estrategia |
| 🚨 **Drawdown > 20%** | Capital < $8,000 | Detener paper trading |
| 📉 **3 pérdidas consecutivas** | 3 sells con pérdida | Revisar modelo |

**Indicadores a monitorizar semanalmente:**
- **Rentabilidad acumulada** → objetivo: > 0%
- **Número de operaciones** → objetivo: 5-10 por semana
- **Win rate** → objetivo: > 50%
- **Sharpe Ratio** → objetivo: > 1.0 (ideal > 2.0 como en backtest)
- **Drawdown máximo** → alerta si > 15%

---

*Documento generado: 30 Junio 2026*
*Última revisión: 1 Septiembre 2026 — añadidas instrucciones diarias, paper trading y reporting*
*Próxima revisión sugerida: tras completar Fase 0 y Fase 1*