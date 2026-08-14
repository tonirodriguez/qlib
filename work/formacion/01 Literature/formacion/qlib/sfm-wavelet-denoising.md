# SFM — Preprocesamiento con Wavelet Denoising

## Motivación

Las series temporales de criptomonedas contienen **ruido blanco diario** que puede confundir los componentes de frecuencia del modelo SFM. Si el SFM intenta aprender de los movimientos aleatorios diarios, las frecuencias que extrae no reflejarán la estructura subyacente del mercado.

La solución es aplicar un **filtrado wavelet** (DWT + thresholding + IDWT) como paso previo a la normalización y al entrenamiento.

## Algoritmo

1. Descomposición de la señal en coeficientes de **aproximación** (tendencia) y **detalle** (ruido) usando una wavelet madre (`db4`)
2. Estimación del umbral universal **Donoho-Johnstone**: $\sigma \cdot \sqrt{2 \cdot \log(N)}$
3. Umbralizado **soft** de los coeficientes de detalle: elimina todo lo que esté por debajo del umbral
4. Reconstrucción de la señal limpia mediante Transformada Wavelet Inversa (IDWT)

## Implementación

```python
import pywt
import numpy as np

def wavelet_denoise_series(series, wavelet="db4", level=None, method="soft"):
    """
    Aplica wavelet denoising (DWT + thresholding + IDWT) a una serie 1D.
    """
    if level is None:
        level = int(np.floor(np.log2(len(series)))) - 2
        level = max(1, min(level, 6))

    coeffs = pywt.wavedec(series, wavelet, level=level)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(series)))

    coeffs_th = list(coeffs)
    for i in range(1, len(coeffs_th)):
        coeffs_th[i] = pywt.threshold(coeffs_th[i], threshold, mode=method)

    return pywt.waverec(coeffs_th, wavelet)[:len(series)]
```

## Aplicación a la matriz multivariable

```python
def denoise_market_matrix(matrix, method="wavelet", wavelet="db4", window_length=11):
    """Aplica denoising columna a columna sobre la matriz de mercado."""
    denoised = np.zeros_like(matrix)
    for f in range(matrix.shape[1]):
        col = matrix[:, f].copy()
        if method == "wavelet":
            denoised[:, f] = wavelet_denoise_series(col, wavelet=wavelet)
        else:
            from scipy.signal import savgol_filter
            denoised[:, f] = savgol_filter(col, window_length=window_length, polyorder=2)
    return denoised
```

## Fallback sin PyWavelets

Si `pywt` no está disponible, se usa un filtro **Savitzky–Golay** (suavizado polinómico sobre ventana deslizante). Es menos sofisticado pero elimina ruido de alta frecuencia de forma aceptable.

```bash
pip install PyWavelets
```

## Pipeline completo (v2)

El script `scripts/crypto/qlib_sfm_pipeline.v2.py` integra el denoising como primer paso:

1. Carga de datos desde Qlib
2. **Wavelet denoising** sobre todas las features (close, return_1d, mean_ratio_5)
3. MinMaxScaler (-1, 1)
4. Ventanas deslizantes (lookback=30)
5. Entrenamiento SFM con early stopping

## Efecto esperado

- Menos retraso temporal en las predicciones
- Mejor identificación de frecuencias cíclicas por parte del SFM
- MAPE más bajo que entrenando sobre datos sin filtrar
- Curvas de equity más suaves en backtesting
