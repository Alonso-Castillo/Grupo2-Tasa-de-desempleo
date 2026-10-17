
from pathlib import Path
import sqlite3
import pandas as pd

# Identificar las rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

RUTA_SQL = RUTA_PROYECTO / "sql" / "02_tasa_participacion.sql"

# Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# Ejecutar SQL y obtener un DataFrame
with sqlite3.connect(RUTA_DB) as conexion:
    participacion = pd.read_sql_query(consulta, conexion)

# Mostrar resultados
print("\nPRIMERAS OBSERVACIONES")
print(participacion.head())

print("\nÚLTIMAS OBSERVACIONES")
print(participacion.tail())

print("\nTotal de observaciones:", len(participacion))
print("Promedio histórico:", participacion["tasa_participacion"].mean().round(2))
