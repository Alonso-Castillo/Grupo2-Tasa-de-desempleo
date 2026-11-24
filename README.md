# Grupo 2 — Proyección de la tasa de desempleo en Chile

Proyecto del curso **Ciencia de Datos para Economía (ICO09425)**. El objetivo es construir un monitor de coyuntura y estudiar la capacidad predictiva de indicadores macroeconómicos para proyectar la tasa de desempleo nacional de Chile durante los próximos 12 meses.

## Variable objetivo y pregunta

La variable objetivo es la tasa de desempleo nacional. La pregunta de proyección es: ¿cómo evolucionará durante los próximos 12 meses y qué capacidad predictiva tienen los indicadores de actividad económica, mercado laboral, política monetaria y condiciones externas para anticipar su trayectoria?

## Catálogo de series

El catálogo se encuentra en `src/config.py` y contiene las 12 series del proyecto, con código BDE, nombre, tema, unidad, fecha inicial y justificación económica. La frecuencia se especifica explícitamente cuando corresponde y, para las series mensuales, el script de carga utiliza `M` como frecuencia por defecto. Todas las series provienen de la BDE del Banco Central de Chile.


## Requisitos

- Python 3.10 o superior (recomendado).
- Acceso a internet para descargar datos desde la API Siete del Banco Central de Chile.
- Token de acceso a la API Siete del Banco Central de Chile.

## Instalación

Primero se debe clonar el repositorio y abrir una terminal en la carpeta raíz del proyecto.

### Windows

Crear un entorno virtual:

```powershell
py -m venv .venv

Activarlo:

.venv\Scripts\Activate.ps1

Si PowerShell no permite activar el entorno, se puede utilizar CMD:

.venv\Scripts\activate.bat

Actualizar pip:

python -m pip install --upgrade pip

Instalar las dependencias:

pip install -r requirements.txt

### macOS / Linux

Crear un entorno virtual:
python3 -m venv .venv

Activarlo:
source .venv/bin/activate

Actualizar pip:

python -m pip install --upgrade pip

Instalar las dependencias:
pip install -r requirements.txt



## Credenciales

1. Obtén un token de acceso para la API Siete del Banco Central de Chile siguiendo las instrucciones oficiales del Banco Central.
2. Copia `.env.example` y renombra la copia a `.env`.
3. Reemplaza `PEGA_AQUI_TU_TOKEN` por tu token personal, sin comillas ni espacios adicionales.
4. No subas `.env` a GitHub. Cada integrante debe configurar sus propias credenciales localmente.

El repositorio no incluye credenciales. Como el grupo ya dispone de token, guárdenlo únicamente en el archivo local `.env`; nunca lo peguen en el código, en el notebook ni en GitHub.

## Ejecución reproducible

Desde la carpeta raíz, ejecuta los comandos en este orden:

```powershell
python base_datos/probar_api.py --hasta 2026-09-30
python base_datos/crear_base.py
python base_datos/cargar_series.py --hasta 2026-09-30
python base_datos/verificar_base.py
```

Reemplacen `2026-09-30` por la fecha de corte acordada para la entrega. Primero, `probar_api.py` comprueba el token y las 12 series sin modificar SQLite. Si todas muestran `[OK]`, ejecuten la carga definitiva. El cargador informa `[OK]` o `[ERROR]` por serie, actualiza los valores existentes y elimina observaciones posteriores al corte para que una base reutilizada no conserve datos fuera del período. No consideren completa la carga hasta verificar que las 12 series reporten `[OK]` y revisar el resumen final.

Para consultar la base desde SQL, ejecuten las consultas del directorio `sql/`. Los scripts de análisis del directorio `analisis/` generan tablas y gráficos a partir de la base local; vuelvan a ejecutarlos después de cada actualización de datos.

## Estructura del proyecto

- `src/config.py`: catálogo de series y justificaciones económicas.
- `base_datos/`: creación, prueba de acceso a la API, carga y verificación de la base SQLite.
- `sql/`: consultas de resumen, transformaciones y análisis de coyuntura.
- `analisis/`: scripts para estadísticas y gráficos.
- `graficos/`: gráficos generados.
- `informes/`: análisis de coyuntura inicial.
- `.env.example`: plantilla sin credenciales.

## Seguridad y control de versiones

La base SQLite y el archivo `.env` son locales y no deben subirse a GitHub. Si la base ya estaba versionada, `.gitignore` por sí solo no la elimina del historial ni del seguimiento; un integrante con acceso al repositorio debe retirarla del índice con `git rm --cached base_datos/desempleo_chile.db` y hacer commit. No ejecuten ese comando si no han comprobado que quieren retirar el archivo del repositorio.

## Integrantes

- Luis Briceño
- Alonso Castillo
- Martina Gonzalez
- Ignacia Severino
