import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf

# Ruta a la base de datos
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"
FIG = ROOT / "graficos"

# Conexión a la base
con = sqlite3.connect(DB)

# Leer la tasa de desempleo
query = """
SELECT o.fecha, o.valor
FROM observaciones AS o
JOIN series AS s
    ON o.id_serie = s.id_serie
WHERE s.nombre = 'Tasa de desempleo nacional'
ORDER BY o.fecha;
"""

desempleo = pd.read_sql_query(query, con)
con.close()

# Preparar la serie
desempleo["fecha"] = pd.to_datetime(desempleo["fecha"])
desempleo = desempleo.set_index("fecha")

serie = desempleo["valor"].dropna()

# Como el ADF mostró que la serie es estacionaria en primera diferencia,
# trabajamos con la primera diferencia para analizar ACF y PACF.
serie_diff = serie.diff().dropna()

# Crear carpeta de gráficos si no existe
FIG.mkdir(exist_ok=True)

# Gráfico ACF
fig, ax = plt.subplots(figsize=(10, 5))
plot_acf(serie_diff, lags=24, ax=ax)
ax.set_title("ACF - Primera diferencia de la tasa de desempleo")
ax.set_xlabel("Rezago")
ax.set_ylabel("Autocorrelación")
plt.tight_layout()
plt.savefig(FIG / "14_acf_desempleo.png", dpi=300)
plt.close()

# Gráfico PACF
fig, ax = plt.subplots(figsize=(10, 5))
plot_pacf(serie_diff, lags=24, ax=ax, method="ywm")
ax.set_title("PACF - Primera diferencia de la tasa de desempleo")
ax.set_xlabel("Rezago")
ax.set_ylabel("Autocorrelación parcial")
plt.tight_layout()
plt.savefig(FIG / "15_pacf_desempleo.png", dpi=300)
plt.close()

print("Gráficos ACF y PACF generados correctamente.")
print("Archivos:")
print("graficos/14_acf_desempleo.png")
print("graficos/15_pacf_desempleo.png")