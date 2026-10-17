
from pathlib import Path
import sqlite3

# 1. Identificar las rutas
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

RUTA_SQL = RUTA_PROYECTO / "sql" / "01_resumen_carga.sql"

# 2. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Conectarse y ejecutar la consulta
with sqlite3.connect(RUTA_DB) as conexion:
    resultado = conexion.execute(consulta).fetchall()

# 4. Mostrar los resultados
print("\nRESUMEN DE SERIES ALMACENADAS")
print("-" * 65)

for tema, indicador, frecuencia, total, inicio, fin in resultado:
    print(f"\nIndicador: {indicador}")
    print(f"Tema: {tema}")
    print(f"Frecuencia: {frecuencia}")
    print(f"Observaciones: {total}")
    print(f"Periodo: {inicio} a {fin}")

print("\nTotal de series:", len(resultado))
print("Total de observaciones:", sum(fila[3] for fila in resultado))
