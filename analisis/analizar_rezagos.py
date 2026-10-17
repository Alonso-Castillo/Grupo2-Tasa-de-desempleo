
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
RUTA_SQL = RUTA_PROYECTO / "sql" / "04_rezagos_imacec_desempleo.sql"

# 2. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Obtener datos desde SQLite
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 4. Definir variables explicativas
variables = [
    "imacec_actual",
    "imacec_rezago_3",
    "imacec_rezago_6",
    "imacec_rezago_12"
]

# 5. Calcular correlaciones
print("\nCORRELACION ENTRE IMACEC Y DESEMPLEO")
print("-" * 50)

for variable in variables:
    muestra = datos[
        [variable, "variacion_desempleo_pp"]
    ].dropna()

    correlacion = muestra[variable].corr(
        muestra["variacion_desempleo_pp"]
    )

    print(f"\nVariable: {variable}")
    print(f"Correlacion: {correlacion:.4f}")
    print(f"Observaciones: {len(muestra)}")

print("\nAnalisis finalizado correctamente.")


# 6. Preparar una muestra común para los cuatro rezagos
datos["fecha"] = pd.to_datetime(datos["fecha"])

muestra_comun = datos.dropna(
    subset=["variacion_desempleo_pp"] + variables
).copy()

# 7. Excluir 2020-2022 como prueba de sensibilidad
muestra_sin_pandemia = muestra_comun[
    ~muestra_comun["fecha"].between(
        "2020-01-01", "2022-12-31"
    )
].copy()

# 8. Comparar las correlaciones
print("\nCOMPARACION DE CORRELACIONES")
print("-" * 65)

print(
    f"{'Variable':<22} {'Muestra comun':>16} {'Sin 2020-2022':>17}"
)

for variable in variables:

    corr_comun = muestra_comun[variable].corr(
        muestra_comun["variacion_desempleo_pp"]
    )

    corr_sin_pandemia = muestra_sin_pandemia[variable].corr(
        muestra_sin_pandemia["variacion_desempleo_pp"]
    )

    print(
        f"{variable:<22} "
        f"{corr_comun:>16.4f} "
        f"{corr_sin_pandemia:>17.4f}"
    )

print("\nObservaciones muestra comun:", len(muestra_comun))
print(
    "Observaciones sin 2020-2022:",
    len(muestra_sin_pandemia)
)
