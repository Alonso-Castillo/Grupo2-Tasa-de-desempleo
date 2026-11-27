
# Interpretación económica del pronóstico de desempleo

## 1. Objetivo del pronóstico

El objetivo de esta etapa es proyectar la tasa de desempleo nacional de Chile a un horizonte de 12 meses, utilizando modelos de series de tiempo y evaluando su desempeño predictivo frente a un benchmark de referencia.

La proyección se construye utilizando una serie mensual comprendida entre marzo de 2010 y agosto de 2026, con un total de 198 observaciones.

El último valor observado de la tasa de desempleo corresponde a agosto de 2026 y alcanza un 9,6403%.

El horizonte de proyección comprende desde septiembre de 2026 hasta agosto de 2027.

Este horizonte se define a partir de la última observación de la muestra utilizada y no de la fecha actual de publicación del informe.

## 2. Modelos considerados

El proyecto considera cuatro alternativas predictivas:

- Benchmark ingenuo.
- ARIMA(1,1,1).
- ARIMA(0,1,2).
- Regresión Ridge con predictores macroeconómicos rezagados.

El benchmark ingenuo utiliza el último valor observado de la tasa de desempleo como pronóstico para los períodos siguientes.

El modelo ARIMA(1,1,1) corresponde a la especificación econométrica considerada inicialmente en el proyecto.

El modelo ARIMA(0,1,2) se incorpora como una especificación alternativa, respaldada por el análisis de estacionariedad, las funciones de autocorrelación y el diagnóstico realizado sobre la muestra de entrenamiento.

El modelo Ridge permite evaluar si la incorporación de indicadores macroeconómicos rezagados contribuye a mejorar la capacidad predictiva respecto de los modelos univariados.

## 3. Evaluación predictiva a un mes

La evaluación retrospectiva a un mes comprende el período entre enero de 2024 y agosto de 2026.

Los cuatro modelos se comparan utilizando las mismas 32 observaciones de evaluación.

| Modelo | Pronósticos | RMSE | MAE | Sesgo |
|---|---:|---:|---:|---:|
| ARIMA(0,1,2) | 32 | 0,1755 | 0,1394 | -0,0236 |
| ARIMA(1,1,1) | 32 | 0,2076 | 0,1583 | -0,0240 |
| Benchmark ingenuo | 32 | 0,2180 | 0,1724 | -0,0364 |
| Ridge, alpha = 1 | 32 | 1,2985 | 1,1219 | 1,0983 |

Los errores se expresan en puntos porcentuales de la tasa de desempleo.

El modelo ARIMA(0,1,2) presenta el menor RMSE y MAE entre las alternativas evaluadas a un mes.

En términos de RMSE, esta especificación obtiene una reducción del error de aproximadamente 19,49% respecto del benchmark ingenuo.

El modelo ARIMA(1,1,1) también supera al benchmark a este horizonte, aunque con una mejora inferior, cercana al 4,78%.

Por su parte, el modelo Ridge, cuya configuración seleccionada utiliza alpha = 1 y un rezago de dos meses para el IMACEC, presenta errores considerablemente superiores.

Estos resultados indican que, bajo las configuraciones y la muestra evaluadas, la incorporación de predictores macroeconómicos mediante Ridge no mejora la capacidad predictiva a un mes.

Sin embargo, este resultado no implica que los indicadores macroeconómicos carezcan de relevancia económica o predictiva bajo otras especificaciones.

## 4. Evaluación multihorizonte

Dado que el objetivo principal del proyecto consiste en proyectar la tasa de desempleo a 12 meses, no resulta suficiente seleccionar un modelo exclusivamente a partir de su desempeño predictivo a un mes.

Por esta razón, se realiza una evaluación retrospectiva para horizontes de 1, 3, 6 y 12 meses.

| Horizonte | Pronósticos por modelo | Benchmark ingenuo | ARIMA(0,1,2) | ARIMA(1,1,1) |
|---|---:|---:|---:|---:|
| 1 mes | 32 | 0,2180 | 0,1755 | 0,2076 |
| 3 meses | 30 | 0,4897 | 0,4962 | 0,5273 |
| 6 meses | 27 | 0,6381 | 0,6938 | 0,7391 |
| 12 meses | 21 | 0,4337 | 0,5230 | 0,5338 |

Los valores de la tabla corresponden al RMSE.

La comparación muestra que ARIMA(0,1,2) obtiene el menor RMSE a un mes, mientras que el benchmark ingenuo presenta el menor RMSE a los horizontes de 3, 6 y 12 meses.

La cantidad de pronósticos disponibles disminuye a medida que aumenta el horizonte, debido a la necesidad de contar con observaciones efectivas para evaluar las predicciones.

Por esta razón, las comparaciones de desempeño deben realizarse principalmente entre modelos dentro de un mismo horizonte.

Los resultados no permiten concluir que un modelo sea universalmente superior, sino que su desempeño depende del horizonte de proyección y de la muestra evaluada.

## 5. Selección del modelo para la proyección a 12 meses

La evaluación específica a 12 meses entrega los siguientes resultados:

| Modelo | Pronósticos | RMSE | MAE | Sesgo |
|---|---:|---:|---:|---:|
| Benchmark ingenuo | 21 | 0,4337 | 0,3403 | -0,1785 |
| ARIMA(0,1,2) | 21 | 0,5230 | 0,4136 | -0,1899 |
| ARIMA(1,1,1) | 21 | 0,5338 | 0,4251 | -0,1899 |

El benchmark ingenuo obtiene los menores valores de RMSE y MAE entre los tres modelos evaluados a 12 meses.

El RMSE de ARIMA(0,1,2) es aproximadamente un 20,58% superior al del benchmark, mientras que el RMSE de ARIMA(1,1,1) es aproximadamente un 23,08% superior.

En consecuencia, se utiliza el benchmark ingenuo como escenario central de la proyección a 12 meses.

El modelo ARIMA(0,1,2) se mantiene como alternativa econométrica, debido a su mejor desempeño a un mes y a su capacidad para representar parte de la dinámica temporal de la serie.

La selección del benchmark responde a un criterio empírico de desempeño predictivo asociado al horizonte objetivo del proyecto, y no a una afirmación de superioridad general sobre los modelos econométricos.

El modelo Ridge no se incorpora a la comparación a 12 meses, por lo que no se establece una conclusión sobre su desempeño relativo a dicho horizonte.

## 6. Diagnóstico econométrico de ARIMA(0,1,2)

La especificación ARIMA(0,1,2) utiliza una primera diferencia de la tasa de desempleo y dos términos de media móvil.

La representación del modelo es:

Delta u(t) = e(t) + theta1 * e(t-1) + theta2 * e(t-2)

Donde:

- u(t) corresponde a la tasa de desempleo.
- Delta u(t) representa su primera diferencia.
- e(t) corresponde a la innovación del período.
- theta1 y theta2 corresponden a los parámetros de media móvil.

La estimación sobre la muestra completa entrega los siguientes coeficientes:

| Parámetro | Coeficiente |
|---|---:|
| MA(1) | 0,610234 |
| MA(2) | 0,632366 |
| Varianza de las innovaciones | 0,059105 |

Los dos coeficientes de media móvil presentan significancia estadística individual bajo los supuestos de estimación del modelo.

El modelo estimado sobre la muestra completa obtiene:

- AIC: 9,0402.
- BIC: 18,8898.
- Componente de media móvil invertible.

Los criterios de información corresponden al ajuste sobre la muestra completa y deben compararse con especificaciones estimadas sobre una muestra equivalente.

### 6.1. Diagnóstico de residuos

Se aplica la prueba de Ljung-Box sobre los residuos del modelo, considerando rezagos de 6, 12 y 24 períodos.

| Rezago | p-valor entrenamiento anterior a 2024 | p-valor muestra completa |
|---|---:|---:|
| 6 | 0,215130 | 0,145713 |
| 12 | 0,163791 | 0,087082 |
| 24 | 0,054253 | 0,018682 |

Para la muestra de entrenamiento anterior a 2024, no se rechaza la hipótesis nula de ausencia de autocorrelación conjunta hasta los rezagos evaluados, utilizando un nivel de significancia del 5%.

No obstante, el resultado correspondiente a 24 rezagos se encuentra próximo al umbral de significancia.

En la muestra completa, la prueba de Ljung-Box rechaza la hipótesis nula para el contraste que considera hasta 24 rezagos.

Esto constituye evidencia de que el modelo no captura completamente toda la dependencia temporal de la serie.

Por lo tanto, ARIMA(0,1,2) debe interpretarse como una aproximación econométrica útil, pero sujeta a limitaciones de especificación.

La ausencia de rechazo de la hipótesis nula en algunos rezagos no demuestra que los residuos constituyan perfectamente un proceso de ruido blanco.

### 6.2. Convergencia

Durante la evaluación temporal se identificó una dificultad inicial de convergencia para ARIMA(0,1,2) en julio de 2025.

El ajuste se realizó nuevamente utilizando el método de optimización Powell, recuperándose correctamente la convergencia.

La evaluación multihorizonte finalizó con 64 ajustes econométricos y ningún caso de falta de convergencia sin resolver.

Esto permite mantener la comparabilidad de las muestras utilizadas en la evaluación.

## 7. Pronóstico para agosto de 2027

Los principales resultados para el último mes del horizonte proyectado son:

| Modelo | Tasa proyectada | Límite inferior 95% | Límite superior 95% |
|---|---:|---:|---:|
| Benchmark ingenuo | 9,6403% | 7,5275% | 11,7531% |
| ARIMA(0,1,2) | 9,8128% | 6,3149% | 13,3106% |

El benchmark ingenuo mantiene constante el último valor observado de la tasa de desempleo durante todo el horizonte de proyección.

Por su parte, ARIMA(0,1,2) proyecta un incremento inicial moderado, alcanzando aproximadamente un 9,81% a partir de octubre de 2026 y manteniéndose posteriormente en ese nivel.

El modelo ARIMA(1,1,1), correspondiente a la especificación original, proyecta una tasa de desempleo de aproximadamente 9,77% para agosto de 2027.

Las tres estimaciones puntuales presentan trayectorias compatibles con un escenario de persistencia de la tasa de desempleo.

Sin embargo, la similitud entre las proyecciones puntuales no elimina la incertidumbre asociada a su evolución futura.

## 8. Interpretación de los intervalos de predicción

Los intervalos de predicción al 95% se amplían conforme aumenta el horizonte de proyección.

En el caso del benchmark ingenuo, los intervalos se construyen bajo el supuesto de una caminata aleatoria sin deriva, utilizando una aproximación basada en la variabilidad histórica de los cambios de la tasa de desempleo.

En el caso de ARIMA(0,1,2), los intervalos se obtienen a partir de la incertidumbre predictiva estimada por el modelo.

Los intervalos de ARIMA(0,1,2) son más amplios a 12 meses que los del benchmark ingenuo.

Esto refleja diferencias en la dinámica y los supuestos utilizados para representar la incertidumbre de los pronósticos.

Los intervalos no constituyen límites garantizados para la evolución futura de la tasa de desempleo.

Su interpretación depende de la validez de los supuestos estadísticos empleados y de la capacidad de los modelos para representar la dinámica de la serie.

La presencia de autocorrelación residual y posibles cambios estructurales constituye una limitación adicional para interpretar su cobertura efectiva.

## 9. Interpretación económica

El escenario central proyecta una tasa de desempleo relativamente estable, cercana al 9,64% durante el horizonte analizado.

La especificación econométrica alternativa presenta un resultado similar, aunque ligeramente superior, cercano al 9,81%.

Desde una perspectiva económica, estas trayectorias serían compatibles con un escenario de persistencia del desempleo, sin una reducción significativa anticipada por los modelos univariados.

No obstante, el benchmark ingenuo no incorpora mecanismos económicos explícitos.

Su proyección constante responde a la persistencia del último valor observado y no demuestra que las condiciones económicas permanecerán efectivamente constantes.

La evolución futura del desempleo puede verse influida por distintos factores, entre ellos:

- El crecimiento de la actividad económica.
- La creación y destrucción de puestos de trabajo.
- Los cambios en la participación laboral.
- La evolución de la inversión y del consumo.
- Las condiciones monetarias y financieras.
- La demanda externa y el precio de las exportaciones.
- Eventuales perturbaciones económicas no anticipadas.

Una recuperación sostenida de la actividad económica podría favorecer la creación de empleo y contribuir a reducir la tasa de desempleo.

Sin embargo, la magnitud y velocidad de esta respuesta dependen también de la evolución de la fuerza de trabajo, la productividad, la composición sectorial y otras condiciones del mercado laboral.

Por esta razón, el pronóstico debe complementarse con el seguimiento de los indicadores macroeconómicos incorporados en el monitor de coyuntura.

## 10. Aporte de los indicadores macroeconómicos

El proyecto incorpora indicadores relacionados con la actividad económica, el mercado laboral, la inflación, la política monetaria y el sector externo.

Estas variables permiten contextualizar la evolución del desempleo y estudiar asociaciones temporales potencialmente relevantes.

El análisis de rezagos del IMACEC busca identificar relaciones entre la actividad económica y los cambios posteriores del mercado laboral.

La regresión Ridge permite explorar si estas relaciones contribuyen a mejorar la capacidad predictiva del modelo.

No obstante, los resultados obtenidos muestran que la configuración Ridge evaluada a un mes no supera a los modelos univariados ni al benchmark ingenuo.

En consecuencia, no existe evidencia suficiente, bajo la especificación utilizada, para afirmar que la incorporación conjunta de estos indicadores mejora la precisión de los pronósticos.

Esto no invalida su utilidad para el análisis de coyuntura, la interpretación económica o el desarrollo de futuras especificaciones predictivas.

Las asociaciones estadísticas identificadas no deben interpretarse como relaciones causales.

## 11. Limitaciones metodológicas

### 11.1. Evaluación retrospectiva

La evaluación utiliza pronósticos generados a partir de distintos orígenes temporales, respetando la estructura cronológica de las series.

Sin embargo, se realiza utilizando las versiones históricas de los datos disponibles actualmente.

Por consiguiente, no constituye una evaluación estrictamente en tiempo real ni un conjunto de prueba completamente inexplorado.

### 11.2. Revisiones de datos

Las series macroeconómicas pueden experimentar revisiones posteriores a su publicación original.

La verificación realizada mediante la API del Banco Central identificó diferencias entre algunos valores históricos almacenados localmente y los valores disponibles en la API.

La base utilizada para generar los resultados de este informe se mantiene sin modificaciones, con el propósito de preservar la consistencia de los resultados existentes.

La tasa de desempleo nacional presentó coincidencia en sus 198 observaciones al compararse con la API para el mismo período.

La existencia de revisiones o diferencias en otros indicadores puede afectar la reproducibilidad exacta de los resultados obtenidos mediante nuevas descargas.

### 11.3. Disponibilidad de información

La fecha correspondiente a una observación económica no necesariamente coincide con su fecha efectiva de publicación.

Aunque el uso de predictores rezagados busca reducir el riesgo de utilizar información que no habría estado disponible en el momento del pronóstico, no garantiza por sí solo una evaluación en tiempo real.

Una evaluación de este tipo requeriría disponer de las versiones históricas de los datos y sus respectivos calendarios de publicación.

### 11.4. Tamaño de la muestra de evaluación

La comparación a 12 meses utiliza 21 pronósticos por modelo.

Esta cantidad permite realizar una comparación empírica dentro de la muestra analizada, pero limita la generalización de los resultados a otros períodos económicos.

Adicionalmente, los pronósticos a horizontes múltiples pueden presentar errores temporalmente dependientes debido a la superposición de sus períodos de evaluación.

Las diferencias de RMSE y MAE deben interpretarse como resultados descriptivos y no como evidencia concluyente de superioridad predictiva estadísticamente significativa.

### 11.5. Especificación econométrica

Los modelos ARIMA representan la dinámica histórica de la tasa de desempleo mediante sus componentes temporales.

No incorporan directamente cambios estructurales, acontecimientos extraordinarios ni mecanismos causales asociados a las variables macroeconómicas.

Asimismo, ARIMA(0,1,2) presenta evidencia de autocorrelación residual en la muestra completa, lo que indica que existe espacio para mejorar su especificación.

La posible presencia de componentes estacionales o cambios de régimen constituye una línea de investigación futura.

### 11.6. Alcance del pronóstico

Los resultados corresponden a proyecciones estadísticas condicionadas a los datos, modelos y supuestos considerados.

No representan predicciones garantizadas ni permiten descartar escenarios económicos alternativos.

## 12. Conclusiones

La evaluación predictiva realizada muestra que el desempeño de los modelos depende del horizonte de proyección.

ARIMA(0,1,2) presenta el mejor desempeño a un mes, reduciendo el RMSE aproximadamente un 19,49% respecto del benchmark ingenuo.

Sin embargo, para el horizonte objetivo de 12 meses, el benchmark ingenuo obtiene los menores errores entre los tres modelos comparados.

Por esta razón, se selecciona el benchmark como escenario central de la proyección, con una tasa de desempleo de 9,64% para agosto de 2027.

ARIMA(0,1,2) se mantiene como alternativa econométrica, proyectando una tasa de aproximadamente 9,81% para el mismo período.

Los resultados sugieren un escenario de persistencia del desempleo, acompañado de una incertidumbre creciente a medida que aumenta el horizonte de proyección.

La utilización de un benchmark simple como escenario principal responde al criterio de seleccionar el modelo con mejor desempeño observado para el horizonte de interés, evitando asumir que una mayor complejidad estadística implica necesariamente una mayor precisión predictiva.

Finalmente, el pronóstico debe entenderse como un componente del monitor de coyuntura económica, complementado con el análisis de los indicadores macroeconómicos, las condiciones del mercado laboral y las limitaciones metodológicas identificadas.

## 13. Archivos de respaldo

Los resultados de esta interpretación se sustentan en los siguientes archivos:

### Evaluación predictiva

- `resultados/metricas_comparacion_temporal.csv`
- `resultados/evaluacion_comparativa_temporal.csv`
- `resultados/metricas_multihorizonte.csv`
- `resultados/predicciones_multihorizonte.csv`
- `resultados/convergencia_multihorizonte.csv`

### Diagnóstico econométrico

- `resultados/coeficientes_arima_012.csv`
- `resultados/diagnostico_residuos_arima_012.csv`

### Pronóstico

- `resultados/pronostico_desempleo_12m.csv`

### Calidad de los datos

- `resultados/auditoria_integridad_general.csv`
- `resultados/auditoria_integridad_series.csv`

### Visualizaciones

- `graficos/12_evaluacion_modelos.png`
- `graficos/13_pronostico_12_meses.png`
- `graficos/18_evaluacion_multihorizonte.png`
- `graficos/19_diagnostico_residuos_arima_012.png`
