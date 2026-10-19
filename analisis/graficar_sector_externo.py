
from pathlib import Path
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

# 1. Definir las rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = (
    RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
)

RUTA_SQL = (
    RUTA_PROYECTO / "sql" / "07_sector_externo_actividad.sql"
)

RUTA_GRAFICOS = RUTA_PROYECTO / "graficos"
RUTA_GRAFICOS.mkdir(exist_ok=True)

# 2. Leer la consulta SQL
consulta = RUTA_SQL.read_text(encoding="utf-8")

# 3. Obtener datos desde SQLite
with sqlite3.connect(RUTA_DB) as conexion:
    datos = pd.read_sql_query(consulta, conexion)

# 4. Preparar las fechas
datos["fecha"] = pd.to_datetime(datos["fecha"])
datos = datos.sort_values("fecha")

# 5. Crear una funcion reutilizable
def crear_grafico(columna, titulo, unidad, archivo):

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.plot(
        datos["fecha"],
        datos[columna],
        linewidth=2
    )

    ax.set_title(titulo)
    ax.set_xlabel("Fecha")
    ax.set_ylabel(unidad)
    ax.grid(True, alpha=0.3)

    fig.autofmt_xdate()
    fig.tight_layout()

    fig.savefig(
        RUTA_GRAFICOS / archivo,
        dpi=150
    )

    plt.close(fig)

    print("Grafico creado:", archivo)


# ---------------------------------------
# GRAFICO 7: PRECIO DEL COBRE
# ---------------------------------------

crear_grafico(
    columna="precio_cobre",
    titulo="Chile: Precio del cobre refinado BML",
    unidad="USD por libra",
    archivo="07_precio_cobre.png"
)

# ---------------------------------------
# GRAFICO 8: TIPO DE CAMBIO
# ---------------------------------------

crear_grafico(
    columna="tipo_cambio",
    titulo="Chile: Tipo de cambio observado",
    unidad="Pesos chilenos por dolar (CLP/USD)",
    archivo="08_tipo_cambio.png"
)

# ---------------------------------------
# GRAFICO 9: PRODUCCION MANUFACTURERA
# ---------------------------------------

crear_grafico(
    columna="produccion_manufacturera",
    titulo="Chile: Indice de Produccion Manufacturera",
    unidad="Indice",
    archivo="09_produccion_manufacturera.png"
)

print("\nGraficos creados correctamente.")
print("Ubicacion:", RUTA_GRAFICOS)
print("Observaciones utilizadas:", len(datos))
print("Primera fecha:", datos["fecha"].min())
print("Ultima fecha:", datos["fecha"].max())
