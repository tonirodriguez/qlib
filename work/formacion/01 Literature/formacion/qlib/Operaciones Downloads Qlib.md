# Operaciones Downloads Qlib

Para obtener la lista de compras a realizar:

```jsx
python conf/daily_scanner.py --signal-date 2026-04-01 --execution-date 2026-04-02 --n-top 10
```

> **Atención al nombre del experimento definido en el script daily_scanner.py**
> 

entonces el flujo es:

- el dataset se reconfigura para llegar hasta **2026-04-01**
- el segmento test queda solo en **2026-04-01**
- model.predict(...) genera la señal para esa fecha
- esa señal es la que usas antes de abrir el mercado el **2026-04-02**

O sea:

- **cierre 2026-04-01** -> calculas ranking/señal
- **preapertura 2026-04-02** -> preparas órdenes
- **apertura 2026-04-02** -> ejecutas

El hecho de que el **backtest** termine el 2026-03-31 no cambia eso. El backtest es una cosa; el scanner está haciendo **inferencia nueva** con datos extendidos hasta 2026-04-01.

# Operativa

## 10-04-2026

Lanzado en Ubuntu Work: ./update_us_qlib_rebuild.sh

- Iniciado a las 10:51:09
- Getting data de 7014 activos

Lanzado en ITN-ToniRodriguez: ./update_us_qlib_daily.sh (Desde 2026-03-31)

- Iniciado a las 10:23:26
- Getting data de 10358 activos
- Acaba download a las 17:54:40 (1 hora apagado por desplazamiento a casa)
- Normalize 12029 activos
- Finaliza a las 18:21:13 habiendo actualizado 5853 activos

> **¿Porqué la diferencia entre uno y otro? Tendremos que actualizar como lo regeneramos periódicamente para no perder activos que por lo que sea no pueda descargar en un momento determinado. Aquellos que por lo que sea se han caido del universo.**
> 

 ****

Lanzado en Acer-Toni: /updata_us_qlib_daily.sh (Desde 2026-03-31)

- Iniciado a las 17:49:53
- Getting data de 12794 activos