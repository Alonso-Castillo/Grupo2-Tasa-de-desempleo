
from pathlib import Path
import sqlite3
import pandas as pd

# 1. Identificar la carpeta principal
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

# 2. Definir las rutas
RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

RUTA_SQL = RUTA_PROYECTO / "sql" / "05_coyuntura_mercado_laboral.sql"

# 3. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 4. Obtener los datos desde SQLite
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 5. Mostrar los resultados
print("\nANALISIS DEL MERCADO LABORAL CHILENO")
print("-" * 60)

print("\nPrimeras observaciones:")
print(datos.head().to_string(index=False))

print("\nUltimas 12 observaciones:")
print(datos.tail(12).to_string(index=False))

print("\nTotal de observaciones:", len(datos))

print("\nDatos faltantes por indicador:")
print(datos.isna().sum())

print("\nAnalisis finalizado correctamente.")
