# Auditoría — `momentum_vt_backtest.py` (Sharpe 1.07)

> **Fecha:** 2026-10-26
> **Script:** `work/estrategias/momentum_vt_backtest.py`
> **Número en cuestión:** Sharpe 1.07, DD −18.6%
> **Veredicto:** ⚠️ **NO reproducible en este repositorio.** El script no es
> ejecutable tal cual, pero el mecanismo de la estrategia **sí es correcto**.

---

## 1. Resumen

A diferencia del `vol_gate_test.py` (cuyo mecanismo era inerte), aquí hay
**dos hallazgos de naturaleza distinta**:

| Aspecto | Estado |
|---|---|
| **Mecanismo** (`risk_degree`) | ✅ **Correcto.** Se aplica en cada decisión. |
| **Ejecutabilidad** | ❌ **Rota.** El `module_path` no resuelve. |
| **Número documentado** | ⚠️ No reproducible desde el repo. |

**Conclusión:** si alguien obtuvo Sharpe 1.07, fue en otra máquina o con el
paquete `toni` instalado en el entorno. En este repositorio el script **falla
al arrancar**.

---

## 2. Hallazgo 1 — El mecanismo SÍ funciona (buena noticia)

`VolTargetTopkStrategy` (`work/estrategias/vol_target_strategy.py`) hereda de
`TopkDropoutStrategy` y modula `self.risk_degree` en
`generate_trade_decision()`.

**Y `risk_degree` sí se usa en qlib**, a diferencia de lo que ocurría con la
multiplicación de la señal en `vol_gate_test.py`:

```python
# qlib/contrib/strategy/signal_strategy.py
L66   def get_risk_degree(self, trade_step=None):
L72       return self.risk_degree          # <- getter dinámico
L266      value = cash * self.risk_degree / len(buy)   # <- dimensiona compras
L365      risk_degree=self.get_risk_degree(trade_step) # <- se llama CADA decisión
```

**Por qué esto importa:** demuestra que el patrón "heredar de
`TopkDropoutStrategy` y modular la exposición" **puede funcionar** — lo que
fallaba en mi intento con el `vol_gate` era usar `self.topk`, no
`self.risk_degree`.

Es una distinción técnica relevante: **`risk_degree` es la vía correcta** para
modular exposición en qlib.

---

## 3. Hallazgo 2 — El script no se puede ejecutar

```python
strategy = {
    "class": "VolTargetTopkStrategy",
    "module_path": "toni.vol_target_strategy",   # <- NO RESUELVE
    ...
}
```

Verificado:

| Comprobación | Resultado |
|---|---|
| ¿Existe `toni/`? | Sí, pero contiene `mlruns/` y `mnt/` — **no es un paquete** |
| ¿Tiene `toni/__init__.py`? | **NO** |
| ¿Está el módulo en `toni/`? | **NO** — está en `work/estrategias/` |
| `import toni.vol_target_strategy` | ❌ `ModuleNotFoundError` |

**Y aquí NO hay fallback silencioso.** A diferencia de `qlib/utils/mod.py:178-184`
(que captura `TypeError` y reintenta sin kwargs), un `ModuleNotFoundError` **se
propaga** y el script muere.

Es decir: **si el script se ejecutó y dio 1.07, no fue desde este repo**.

---

## 4. Problemas adicionales

| Problema | Impacto |
|---|---|
| `MLFLOW_TRACKING_URI = sqlite:////opt/data/qlib/...` | Ruta de **otra máquina**. Puede impedir el arranque. |
| `UNIVERSE = "sp500_liquid"` por defecto | **No existe** en esta instalación (hay `sp500`). |
| `toni/mnt/c/Users/...` | Rastros de rutas Windows dentro del repo. |

Lo que **sí está bien**: `provider_uri='~/.qlib/qlib_data/us_data'` (correcto
para WSL) y `end_time="2026-08-07"` (con margen sobre el fin del calendario,
evitando el `IndexError`).

---

## 5. Implicación sobre el vol-gate

`momentum_vt_backtest.py` se citaba en `vol_gate_resultado.md` como
**confirmación independiente** del vol-gating:

> *"Consistente con `momentum_vt_backtest.py` previo (Sharpe 1.07, DD −18.6%)"*

**Esa confirmación no se sostiene**, por dos razones independientes:

1. **El script no es ejecutable** desde este repositorio (hallazgo 2).
2. Aunque lo fuera, `vol_target_strategy` implementa **vol-targeting continuo**
   (`vol_target / vol` con clip a [0.3, 1.0]), que **no es el mismo mecanismo**
   que el `vol_gate` de 3 estados con histéresis (P75/P90). Son estrategias
   distintas, no una confirmación de la otra.

---

## 6. Qué se puede salvar

**`vol_target_strategy.py` es código correcto y reutilizable.** El mecanismo
`risk_degree` está bien implementado y es la vía adecuada en qlib.

Para usarlo habría que:

```python
# opción A: corregir el script
strategy = {
    "class": "VolTargetTopkStrategy",
    "module_path": "work.estrategias.vol_target_strategy",  # ruta real
    ...
}
# (requiere que work/ y work/estrategias/ tengan __init__.py, o ejecutar
#  desde un directorio donde sean importables)

# opción B: importar la clase y pasarla directamente
import sys; sys.path.insert(0, "work/estrategias")
from vol_target_strategy import VolTargetTopkStrategy
strategy = {"class": VolTargetTopkStrategy, "kwargs": {...}}
```

Y además: cambiar `UNIVERSE` a `sp500` y quitar la dependencia de
`/opt/data/`.

---

## 7. Relación con los otros hallazgos

Este es el **sexto** artefacto auditado. El patrón se repite con variantes:

| Artefacto | Tipo de fallo |
|---|---|
| Config SP500 | No existía |
| `vol_pct` (mi aviso) | Falso positivo — era causal |
| Entorno qlib | xgboost roto |
| `vol_gate` validación | Mecanismo inerte (multiplicar señal) |
| SFM v8 | Leak de futuro (3 fugas) |
| **`momentum_vt`** | **Import roto — no ejecutable** |

**Lección específica:** un `module_path` que apunta a un paquete inexistente es
un fallo **silencioso en documentación pero ruidoso en ejecución**. El script
nunca corrió desde aquí, pero el número quedó registrado como si lo hubiera
hecho.

**Comprobación rápida** que lo habría detectado:

```bash
python -c "import importlib; importlib.import_module('toni.vol_target_strategy')"
```

---

## 8. Recomendaciones

1. 🔴 **Marcar el Sharpe 1.07 como no reproducible** en `vol_gate_resultado.md`
   (ya está invalidado el 1.136; añadir este).
2. 🟡 **Corregir el `module_path`** si se quiere medir el vol-targeting de verdad.
   El mecanismo es correcto y merece una medición honesta.
3. 🟡 **Limpiar `toni/`**: contiene artefactos de MLflow y rutas de Windows que
   no pertenecen al repo.
4. ⚪ **Nota positiva:** `risk_degree` es la vía correcta para modular exposición
   en qlib. Si se retoma el vol-gate, **usar este mecanismo**, no `self.topk`.

---

*Auditoría realizada el 2026-10-26. Script de comprobación:
`work/estrategias/auditoria_momentum_vt.py` (ejecutable sin qlib).*
