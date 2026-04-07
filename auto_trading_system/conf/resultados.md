# RESULTADOS CON config_lightgbm_improved_v2.yml

Señal calculada con datos al cierre de: 2026-04-01
Fecha objetivo de ejecución: 2026-04-02

OPORTUNIDADES DE COMPRA DETECTADAS
=================================
Ticker: LYB | Score de confianza: 0.0492
Ticker: OXY | Score de confianza: 0.0428
Ticker: APA | Score de confianza: 0.0268
Ticker: XOM | Score de confianza: 0.0246
Ticker: FIX | Score de confianza: 0.0243
Ticker: MPC | Score de confianza: 0.0216
Ticker: MPWR | Score de confianza: 0.0212
Ticker: COP | Score de confianza: 0.0202
Ticker: KLAC | Score de confianza: 0.0182
Ticker: FANG | Score de confianza: 0.0179

# Ejecutamos optuna_optimization.py y aplicamos los parámetros en config_lightgbm_optuna.yml
# y modificamos conf/daily_scanner.py para que coja los datos de este experimento.
# A continuación vemos los resultados vs Benchmark en analisis_experiment.ipynb

Mejores parámetros encontrados: 
{
    'learning_rate': 0.04761673064613082,   
    'num_boost_round': 900, 
    'early_stopping_rounds': 100, 
    'num_leaves': 17, 
    'max_depth': 7,  
    'min_data_in_leaf': 150,  
    'subsample': 0.9363801055224449, 
    'colsample_bytree': 0.8414911823303388, 
    'lambda_l1': 19.395803434674757, 
    'lambda_l2': 38.622764197429404 

Mejor IC medio en validación: 0.006850114176814374

Señal calculada con datos al cierre de: 2026-04-01
Fecha objetivo de ejecución: 2026-04-02

OPORTUNIDADES DE COMPRA DETECTADAS
=================================
Ticker: OXY | Score de confianza: 0.0364
Ticker: LYB | Score de confianza: 0.0364
Ticker: BSX | Score de confianza: 0.0328
Ticker: APA | Score de confianza: 0.0324
Ticker: NOW | Score de confianza: 0.0142
Ticker: CRM | Score de confianza: 0.0142
Ticker: INTU | Score de confianza: 0.0138
Ticker: COP | Score de confianza: 0.0121
Ticker: FANG | Score de confianza: 0.0121
Ticker: MPC | Score de confianza: 0.0121

Cuando comparo contra el Benchmark, en este caso el ^GSPC veo que utilizando Optuna, me sale por debajo del Benchmark, y que es 
mucho mejor la estrategia obtenida con config_lightgbm_improved_v2.yaml.

# CONCLUSION: continuamos con config_lightgbm_improved_v2.yaml hasta que consigamos mejorar con Optuna