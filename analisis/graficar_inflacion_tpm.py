
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Definir rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = (
    RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
)

RUTA_SQL = (
    RUTA_PROYECTO / "sql" / "06_inflacion_tpm.sql"
)

RUTA_GRAFICOS = RUTA_PROYECTO / "graficos"
RUTA_GRAFICOS.mkdir(exist_ok=True)

# 2. Leer consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Obtener datos desde SQLite
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 4. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])
datos = datos.sort_values("fecha")

# ---------------------------------------
# GRAFICO 6: INFLACION ANUAL Y TPM
# ---------------------------------------

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos["fecha"],
    datos["inflacion_anual"],
    label="Inflacion anual IPC",
    linewidth=2
)

ax.plot(
    datos["fecha"],
    datos["tpm"],
    label="Tasa de Politica Monetaria",
    linewidth=2
)

ax.axhline(
    y=3,
    linestyle="--",
    alpha=0.7,
    label="Meta de inflacion (3%)"
)

ax.set_title(
    "Chile: Inflacion anual y Tasa de Politica Monetaria"
)

ax.set_xlabel("Fecha")
ax.set_ylabel("Porcentaje (%)")

ax.legend()
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "06_inflacion_tpm.png",
    dpi=150
)

plt.close(fig)

print("\nGrafico de inflacion y TPM creado correctamente.")
print("Ubicacion:", RUTA_GRAFICOS)
print("Observaciones utilizadas:", len(datos))
print("Primera fecha:", datos["fecha"].min())
print("Ultima fecha:", datos["fecha"].max())
