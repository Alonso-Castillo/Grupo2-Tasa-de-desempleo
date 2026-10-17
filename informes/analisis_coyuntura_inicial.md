# Análisis inicial de coyuntura económica: desempleo en Chile

## 1. Objetivo

El presente análisis tiene como objetivo examinar la evolución reciente de la tasa de desempleo nacional en Chile y su relación con la actividad económica, utilizando información obtenida mediante la API de la Base de Datos Estadísticos del Banco Central de Chile.

## 2. Datos y metodología

Se construyó una base de datos SQLite que contiene 12 series económicas oficiales, con un total de 2.167 observaciones almacenadas.

Para estudiar la relación entre actividad económica y desempleo, se calculó la variación interanual del IMACEC y el cambio interanual de la tasa de desempleo, expresado en puntos porcentuales.

Mediante consultas SQL con funciones de ventana `LAG()`, se construyeron rezagos de 3, 6 y 12 meses del crecimiento del IMACEC.

Posteriormente, se calcularon correlaciones de Pearson utilizando Python y una muestra común de 176 observaciones. Como prueba de sensibilidad, se repitió el análisis excluyendo el período 2020–2022, obteniendo una muestra de 140 observaciones.

## 3. Evolución reciente de la actividad y el desempleo

Los resultados muestran que durante 2020 la actividad económica experimentó una importante contracción, acompañada de un fuerte aumento del desempleo.

Posteriormente, durante 2021, se observó una recuperación significativa de la actividad económica y una disminución progresiva del desempleo.

En agosto de 2026, la variación interanual del IMACEC alcanzó -1,01 %, mientras que la tasa de desempleo nacional registró un 9,64 %.

Estos resultados muestran un escenario de debilidad de la actividad económica y del mercado laboral al cierre del período disponible para ambas variables.

## 4. Análisis de correlaciones y rezagos

El análisis inicial identifica una asociación inversa entre el crecimiento económico y los cambios en el desempleo.

La correlación más negativa se obtiene utilizando el crecimiento del IMACEC rezagado tres meses, con un coeficiente de -0,8577 en la muestra común.

Sin embargo, al excluir el período 2020–2022, la correlación disminuye a -0,5795, lo que evidencia la influencia de los movimientos extraordinarios ocurridos durante la crisis sanitaria y su recuperación.

A pesar de esta reducción, la relación continúa siendo negativa y es compatible con una respuesta rezagada del mercado laboral frente a los cambios en la actividad económica.

## 5. Conclusiones preliminares

Los resultados proporcionan evidencia descriptiva de una asociación inversa entre el crecimiento del IMACEC y la variación de la tasa de desempleo nacional.

El rezago de tres meses presenta la correlación negativa de mayor magnitud entre los períodos evaluados, tanto en la muestra completa como al excluir 2020–2022.

No obstante, las correlaciones no permiten establecer relaciones causales ni garantizar capacidad predictiva. Los resultados pueden estar afectados por factores económicos omitidos, autocorrelación y episodios extraordinarios.

En las siguientes etapas se incorporarán otros indicadores del mercado laboral, inflación, política monetaria y sector externo, junto con evaluaciones fuera de muestra para estudiar su contribución a la proyección del desempleo.