
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Definir las rutas
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = (
    RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
)

RUTA_SQL = (
    RUTA_PROYECTO / "sql" / "06_inflacion_tpm.sql"
)

# 2. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Consultar la base de datos
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 4. Mostrar resultados
print("\nANALISIS DE INFLACION Y POLITICA MONETARIA")
print("-" * 60)

print("\nPrimeras observaciones:")
print(datos.head().to_string(index=False))

print("\nUltimas 12 observaciones:")
print(datos.tail(12).to_string(index=False))

print("\nTotal de observaciones:", len(datos))

print("\nDatos faltantes:")
print(datos.isna().sum())

print("\nAnalisis finalizado correctamente.")
