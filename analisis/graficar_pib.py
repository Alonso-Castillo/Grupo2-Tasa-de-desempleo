
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Identificar carpeta principal
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

# 2. Definir rutas
RUTA_DB = (
    RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
)

RUTA_SQL = (
    RUTA_PROYECTO / "sql" / "08_pib_trimestral.sql"
)

RUTA_GRAFICOS = RUTA_PROYECTO / "graficos"
RUTA_GRAFICOS.mkdir(exist_ok=True)

# 3. Leer consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 4. Obtener datos desde SQLite
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 5. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])
datos = datos.sort_values("fecha")

# Eliminar NaN solamente para graficar
datos_grafico = datos.dropna(
    subset=["variacion_interanual"]
)

# ---------------------------------------
# GRAFICO 10: CRECIMIENTO DEL PIB REAL
# ---------------------------------------

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos_grafico["fecha"],
    datos_grafico["variacion_interanual"],
    linewidth=2,
    label="Variacion interanual PIB real"
)

# Linea horizontal en cero
ax.axhline(
    y=0,
    linestyle="--",
    color="gray",
    alpha=0.7,
    label="Crecimiento cero"
)

ax.set_title(
    "Chile: Crecimiento interanual del PIB real"
)

ax.set_xlabel("Fecha")
ax.set_ylabel("Variacion interanual (%)")

ax.legend()
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "10_pib_real_trimestral.png",
    dpi=150
)

plt.close(fig)

print("\nGrafico del PIB creado correctamente.")
print("Ubicacion:", RUTA_GRAFICOS)
print("Trimestres graficados:", len(datos_grafico))
print("Primera fecha:", datos_grafico["fecha"].min())
print("Ultima fecha:", datos_grafico["fecha"].max())
