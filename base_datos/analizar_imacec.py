
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Definir rutas
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

RUTA_SQL = RUTA_PROYECTO / "sql" / "03_variacion_imacec.sql"

# 2. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Ejecutar la consulta
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 4. Mostrar resultados
print("\nVARIACION INTERANUAL DEL IMACEC Y DESEMPLEO")

print("\nPrimeras observaciones:")
print(datos.head())

print("\nUltimas observaciones:")
print(datos.tail(10))

print("\nTotal de observaciones:", len(datos))
