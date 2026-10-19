
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Identificar carpeta del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

# 2. Definir rutas
RUTA_DB = (
    RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
)

RUTA_SQL = (
    RUTA_PROYECTO / "sql" / "08_pib_trimestral.sql"
)

# 3. Leer consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 4. Obtener datos
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 5. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])

datos["trimestre"] = (
    datos["fecha"].dt.to_period("Q").astype(str)
)

# 6. Organizar columnas
datos = datos[
    ["trimestre", "pib_real", "variacion_interanual"]
]

# 7. Mostrar resultados
print("\nANALISIS DEL PIB REAL TRIMESTRAL")
print("-" * 60)

print("\nPrimeras observaciones:")
print(datos.head(8).to_string(index=False))

print("\nUltimas 12 observaciones:")
print(datos.tail(12).to_string(index=False))

print("\nTotal de observaciones:", len(datos))

print("\nDatos faltantes:")
print(datos.isna().sum())

print("\nAnalisis finalizado correctamente.")
