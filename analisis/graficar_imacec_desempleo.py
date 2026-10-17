
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Definir las rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
RUTA_SQL = RUTA_PROYECTO / "sql" / "03_variacion_imacec.sql"
RUTA_GRAFICOS = RUTA_PROYECTO / "graficos"

# Crear carpeta para guardar los gráficos
RUTA_GRAFICOS.mkdir(exist_ok=True)

# 2. Leer y ejecutar nuestra consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 3. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])
datos = datos.sort_values("fecha")

# 4. Gráfico del crecimiento interanual del IMACEC
fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos["fecha"],
    datos["variacion_interanual"],
    linewidth=1.8
)

ax.axhline(0, linestyle="--", linewidth=1, color="gray")

ax.set_title("Chile: Variación interanual del IMACEC")
ax.set_xlabel("Fecha")
ax.set_ylabel("Variación interanual (%)")
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "01_variacion_imacec.png",
    dpi=150
)

plt.close(fig)

# 5. Gráfico de la tasa de desempleo nacional
fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos["fecha"],
    datos["tasa_desempleo"],
    linewidth=1.8
)

ax.set_title("Chile: Tasa de desempleo nacional")
ax.set_xlabel("Fecha")
ax.set_ylabel("Tasa de desempleo (%)")
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "02_tasa_desempleo.png",
    dpi=150
)

plt.close(fig)

print("Gráficos creados correctamente.")
print("Ubicación:", RUTA_GRAFICOS)
print("Observaciones utilizadas:", len(datos))
