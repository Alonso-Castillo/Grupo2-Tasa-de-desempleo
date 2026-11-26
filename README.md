# Grupo 2 — Proyección de la tasa de desempleo en Chile

Proyecto del curso **Ciencia de Datos para Economía (ICO09425)**.

El objetivo del proyecto es construir un monitor de coyuntura y evaluar la capacidad predictiva de distintos indicadores macroeconómicos para proyectar la **tasa de desempleo nacional de Chile durante los próximos 12 meses**.

## Variable objetivo y pregunta de investigación

La variable objetivo es la **tasa de desempleo nacional de Chile**.

La pregunta de proyección es:

> ¿Cómo evolucionará la tasa de desempleo nacional durante los próximos 12 meses y qué capacidad predictiva tienen los indicadores de actividad económica, mercado laboral, política monetaria y condiciones externas para anticipar su trayectoria?

## Fuente de datos

Los datos provienen principalmente de la **Base de Datos Estadísticos (BDE) del Banco Central de Chile**, utilizando la API Siete.

El catálogo del proyecto contiene 12 series económicas relacionadas con:

- mercado laboral;
- actividad económica;
- precios;
- política monetaria;
- sector externo.

El catálogo se encuentra en:

`src/config.py`

Cada serie contiene su código de la API, nombre, tema, unidad, fecha inicial y justificación económica.

La fecha de corte utilizada en el desarrollo actual es:

`2026-09-30`

Algunas series pueden tener una última observación anterior debido a su calendario oficial de publicación.

## Requisitos

- Python 3.10 o superior.
- Acceso a internet.
- Token de acceso a la API Siete del Banco Central de Chile.
- Git.
- Dependencias incluidas en `requirements.txt`.

## Instalación

Clonar el repositorio y abrir una terminal en la carpeta raíz.

### Windows

Crear entorno virtual:

```powershell
py -m venv .venv
```

Activarlo:

```powershell
.venv\Scripts\Activate.ps1
```

Si PowerShell no permite activarlo:

```cmd
.venv\Scripts\activate.bat
```

Actualizar pip:

```powershell
python -m pip install --upgrade pip
```

Instalar dependencias:

```powershell
pip install -r requirements.txt
```

### macOS / Linux

Crear entorno virtual:

```bash
python3 -m venv .venv
```

Activarlo:

```bash
source .venv/bin/activate
```

Actualizar pip:

```bash
python -m pip install --upgrade pip
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Credenciales

1. Obtener un token para la API Siete del Banco Central de Chile.
2. Copiar `.env.example`.
3. Renombrar la copia como `.env`.
4. Reemplazar el valor de ejemplo por el token personal.

El archivo debe mantener una estructura similar a:

```text
BCCH_API_TOKEN=PEGA_AQUI_TU_TOKEN
```

Cada integrante debe configurar sus propias credenciales localmente.

**Nunca deben subirse tokens, contraseñas ni el archivo `.env` a GitHub.**

## Carga y verificación de datos

Desde la carpeta raíz del proyecto:

### 1. Comprobar acceso a la API y disponibilidad de las series

```bash
python base_datos/probar_api.py --hasta 2026-09-30
```

La comprobación debe finalizar con las 12 series disponibles y sin errores.

### 2. Crear la base SQLite

```bash
python base_datos/crear_base.py
```

### 3. Cargar las series reales

```bash
python base_datos/cargar_series.py --hasta 2026-09-30
```

La carga informa `[OK]` o `[ERROR]` por serie.

No se considera completa mientras exista algún `[ERROR]`.

### 4. Verificar la base

```bash
python base_datos/verificar_base.py
```

La base contiene las tablas relacionales de temas, series y observaciones.

## Consultas SQL

Las consultas se encuentran en:

`sql/`

Incluyen:

- JOIN entre tablas;
- agregaciones mediante `GROUP BY`;
- funciones de ventana;
- variaciones interanuales;
- rezagos;
- análisis de mercado laboral;
- actividad económica;
- inflación y política monetaria;
- sector externo;
- PIB trimestral.

Las funciones de ventana se calculan separando correctamente cada serie mediante `PARTITION BY`.

## Análisis y modelación

El proyecto utiliza Python para el análisis estadístico, económico y predictivo.

### Estacionariedad

Ejecutar:

```bash
python modelos/estacionariedad_desempleo.py
```

La prueba ADF muestra que la tasa de desempleo no es estacionaria en nivel, pero sí en primera diferencia.

Esto respalda el uso de integración de orden 1 en el modelo ARIMA.

### ACF y PACF

Ejecutar:

```bash
python modelos/acf_pacf_desempleo.py
```

Los gráficos ACF y PACF se utilizan como apoyo para analizar la dinámica temporal de la primera diferencia de la tasa de desempleo.

### Modelo ARIMA

El modelo temporal seleccionado es:

**ARIMA(1,1,1)**

La especificación se fundamenta en:

- diagnóstico de estacionariedad;
- primera diferencia de la serie;
- análisis de ACF y PACF;
- desempeño fuera de muestra.

### Modelo Ridge

Se utiliza también un modelo Ridge con predictores macroeconómicos rezagados.

La optimización puede ejecutarse mediante:

```bash
python modelos/optimizar_ridge.py
```

El modelo considerado en la comparación final utiliza:

**Ridge alpha = 500**

Además, se incorpora el crecimiento interanual del IMACEC con rezago de dos meses, respaldado por el análisis de correlaciones entre actividad económica y desempleo.

### Evaluación comparativa

Ejecutar:

```bash
python modelos/evaluacion_comparativa.py
```

Se comparan:

- ARIMA(1,1,1);
- benchmark ingenuo;
- Ridge alpha 500.

La evaluación utiliza ventanas temporales y pronósticos fuera de muestra.

Resultados principales:

| Modelo | RMSE | MAE | Sesgo |
|---|---:|---:|---:|
| ARIMA(1,1,1) | 0.1938 | 0.1524 | -0.0208 |
| Benchmark ingenuo | 0.2038 | 0.1597 | -0.0431 |
| Ridge alpha 500 | 0.4068 | 0.3145 | -0.2080 |

De acuerdo con RMSE y MAE, **ARIMA(1,1,1) presenta el mejor desempeño fuera de muestra entre los modelos comparados**.

## Pronóstico final

El script principal de modelación genera una proyección de la tasa de desempleo para los próximos 12 meses:

```bash
python modelos/modelos_desempleo.py
```

El archivo de resultados se almacena en:

`resultados/pronostico_desempleo_12m.csv`

El horizonte actual comprende:

`2026-09` a `2027-08`

El archivo contiene:

- pronóstico ARIMA;
- límite inferior del intervalo de confianza al 95%;
- límite superior del intervalo de confianza al 95%;
- benchmark ingenuo.

## Interpretación económica

La interpretación del pronóstico se encuentra en:

`informes/interpretacion_pronostico.md`

El escenario central proyecta una tasa de desempleo relativamente estable durante el horizonte analizado.

Los intervalos de confianza aumentan con el horizonte de proyección, reflejando la mayor incertidumbre asociada a pronósticos más alejados en el tiempo.

Las relaciones encontradas entre variables se interpretan como asociaciones predictivas y no como relaciones causales.

## Dashboard reproducible en Python

Para generar el monitor gráfico desde los datos y resultados del proyecto:

```bash
python dashboard/dashboard_desempleo.py
```

El resultado se almacena en:

`dashboard/dashboard_desempleo.png`

El script utiliza información proveniente de la base SQLite y los resultados de modelación.

## Power BI

El proyecto incluye además un monitor desarrollado en Power BI.

Actualmente contiene, entre otras visualizaciones:

### Pronóstico de desempleo

- pronóstico ARIMA a 12 meses;
- benchmark ingenuo;
- intervalo de confianza al 95%;
- pronóstico promedio del horizonte;
- benchmark de referencia.

### Evaluación de modelos

- tabla comparativa de RMSE, MAE y sesgo;
- gráfico de RMSE por modelo.

La versión final del monitor debe mantener coherencia con los resultados generados por los scripts de Python y la base de datos del proyecto.

## Estructura del proyecto

```text
Grupo2-Tasa-de-desempleo/
│
├── analisis/
│   └── scripts de análisis de coyuntura y relaciones económicas
│
├── base_datos/
│   ├── crear_base.py
│   ├── cargar_series.py
│   ├── probar_api.py
│   └── verificar_base.py
│
├── dashboard/
│   ├── dashboard_desempleo.py
│   └── dashboard_desempleo.png
│
├── extraccion/
│   └── scripts asociados a extracción de datos
│
├── graficos/
│   └── visualizaciones generadas por Python
│
├── informes/
│   ├── analisis_coyuntura...
│   └── interpretacion_pronostico.md
│
├── modelos/
│   ├── estacionariedad_desempleo.py
│   ├── acf_pacf_desempleo.py
│   ├── optimizar_ridge.py
│   ├── evaluacion_comparativa.py
│   └── modelos_desempleo.py
│
├── resultados/
│   ├── correlaciones_rezagos_imacec.csv
│   ├── evaluacion_comparativa_temporal.csv
│   ├── metricas_comparacion_temporal.csv
│   ├── optimizacion_ridge.csv
│   └── pronostico_desempleo_12m.csv
│
├── sql/
│   └── consultas SQL del proyecto
│
├── src/
│   └── config.py
│
├── .env.example
├── .gitignore
├── README.md
└── requirements.txt
```

## Seguridad y control de versiones

No deben subirse a GitHub:

- `.env`;
- tokens o credenciales;
- entornos virtuales como `.venv`;
- archivos sensibles;
- bases locales que deban mantenerse fuera del repositorio.

El archivo `.env.example` contiene únicamente una plantilla y nunca una credencial real.

Los cambios relevantes deben registrarse mediante commits descriptivos.

## Flujo general del proyecto

El flujo de trabajo es:

```text
API Banco Central
        ↓
Base de datos SQLite
        ↓
Consultas SQL
        ↓
Análisis y modelación en Python
        ↓
Evaluación de pronósticos
        ↓
Pronóstico final
        ↓
Dashboard / Power BI
        ↓
Interpretación económica
```
## Reproducción final del proyecto

Para reproducir el análisis completo del proyecto desde cero, se recomienda seguir el siguiente orden:

1. Clonar el repositorio y acceder a la carpeta del proyecto.

2. Crear y activar un entorno virtual de Python.

3. Instalar las dependencias necesarias:

```bash
pip install -r requirements.txt
```

4. Crear el archivo `.env` utilizando `.env.example` como referencia e ingresar las credenciales personales necesarias para acceder a las APIs oficiales. Las credenciales no deben subirse al repositorio.

5. Ejecutar la carga programática de los datos para generar y poblar la base de datos relacional con las series económicas utilizadas en el proyecto.

6. Verificar la correcta carga de las series y ejecutar las consultas SQL documentadas en la carpeta `sql/`.

7. Ejecutar el análisis de estacionariedad de la tasa de desempleo:

```bash
python modelos/estacionariedad_desempleo.py
```

8. Generar el análisis ACF y PACF:

```bash
python modelos/acf_pacf_desempleo.py
```

9. Ejecutar la optimización interna del modelo Ridge:

```bash
python modelos/optimizar_ridge.py
```

La optimización interna evalúa diferentes configuraciones y valores de `alpha`. La especificación definitiva del modelo se determina posteriormente mediante la evaluación comparativa común.

10. Ejecutar la evaluación fuera de muestra de los modelos:

```bash
python modelos/evaluacion_comparativa.py
```

En esta etapa se comparan el modelo ARIMA(1,1,1), el modelo Ridge con `alpha = 500` y un benchmark ingenuo utilizando el mismo período de evaluación.

11. Ejecutar el modelo final y generar el pronóstico de desempleo:

```bash
python modelos/modelos_desempleo.py
```

12. Generar el dashboard en Python:

```bash
python dashboard/dashboard_desempleo.py
```

Los principales resultados, métricas, predicciones y gráficos generados durante este proceso se almacenan en las carpetas `resultados/`, `graficos/` y `dashboard/`.

Este flujo permite reproducir desde la obtención de los datos hasta la evaluación de modelos y la generación del pronóstico final.



## Integrantes

- Luis Briceño
- Alonso Castillo
- Martina Gonzalez
- Ignacia Severino
