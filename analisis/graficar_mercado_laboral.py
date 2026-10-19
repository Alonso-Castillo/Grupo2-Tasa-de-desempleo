
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Definir rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

RUTA_SQL = RUTA_PROYECTO / "sql" / "05_coyuntura_mercado_laboral.sql"

RUTA_GRAFICOS = RUTA_PROYECTO / "graficos"
RUTA_GRAFICOS.mkdir(exist_ok=True)

# 2. Obtener los datos desde SQLite
consulta = RUTA_SQL.read_text(encoding="utf-8")

with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 3. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])
datos = datos.sort_values("fecha")

# ---------------------------------------
# GRAFICO 3: OCUPADOS Y FUERZA DE TRABAJO
# ---------------------------------------

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos["fecha"],
    datos["personas_ocupadas"],
    label="Personas ocupadas"
)

ax.plot(
    datos["fecha"],
    datos["fuerza_trabajo"],
    label="Fuerza de trabajo"
)

ax.set_title("Chile: Ocupados y fuerza de trabajo")
ax.set_xlabel("Fecha")
ax.set_ylabel("Miles de personas")
ax.legend()
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "03_ocupados_fuerza_trabajo.png",
    dpi=150
)

plt.close(fig)

# ---------------------------------------
# GRAFICO 4: TASA DE PARTICIPACION
# ---------------------------------------

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    datos["fecha"],
    datos["tasa_participacion"]
)

ax.set_title("Chile: Tasa de participación laboral")
ax.set_xlabel("Fecha")
ax.set_ylabel("Tasa de participación (%)")
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "04_tasa_participacion.png",
    dpi=150
)

plt.close(fig)

# ---------------------------------------
# GRAFICO 5: IALI
# ---------------------------------------

iali = datos.dropna(subset=["iali"])

fig, ax = plt.subplots(figsize=(11, 5))

ax.plot(
    iali["fecha"],
    iali["iali"]
)

ax.set_title(
    "Chile: Índice de Avisos Laborales de Internet"
)

ax.set_xlabel("Fecha")
ax.set_ylabel("Índice IALI")
ax.grid(True, alpha=0.3)

fig.autofmt_xdate()
fig.tight_layout()

fig.savefig(
    RUTA_GRAFICOS / "05_iali.png",
    dpi=150
)

plt.close(fig)

print("\nGraficos laborales creados correctamente.")
print("Ubicacion:", RUTA_GRAFICOS)
print("Observaciones laborales:", len(datos))
print("Observaciones disponibles del IALI:", len(iali))
