# Interpretación económica del pronóstico de desempleo

El modelo ARIMA(1,1,1) proyecta la tasa de desempleo nacional para los próximos 12 meses, desde septiembre de 2026 hasta agosto de 2027.

La trayectoria proyectada se mantiene relativamente estable, en torno a 9,7%–9,8% durante todo el horizonte. Esto sugiere que, bajo el escenario base del modelo, no se anticipa una disminución importante del desempleo en el corto plazo.

El benchmark ingenuo, que mantiene constante el último valor observado, se ubica en torno a 9,64%. El pronóstico del modelo ARIMA se encuentra levemente por sobre ese nivel durante la mayor parte del horizonte.

La evaluación fuera de muestra mostró que el ARIMA(1,1,1) presenta un mejor desempeño predictivo que el benchmark ingenuo y que el modelo Ridge, al obtener menores valores de RMSE y MAE. Por esta razón, se utiliza como modelo principal para realizar la proyección a 12 meses.

Los intervalos de predicción al 95% se amplían a medida que aumenta el horizonte de pronóstico. Esto refleja que la incertidumbre es mayor para los meses más alejados y, por lo tanto, las proyecciones deben interpretarse como un escenario base y no como valores ciertos.

Desde una perspectiva económica, la persistencia de una tasa de desempleo cercana al 9,7%–9,8% sería consistente con un mercado laboral que continúa mostrando dificultades para reducir de manera significativa el desempleo durante el período proyectado.

Sin embargo, el escenario puede modificarse ante cambios en la actividad económica, las condiciones del mercado laboral, la política monetaria o factores externos. Por esta razón, el pronóstico debe complementarse con el análisis de coyuntura y con la evolución de los indicadores macroeconómicos incluidos en el proyecto.