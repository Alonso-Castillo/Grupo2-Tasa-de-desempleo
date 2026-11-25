import sqlite3
from pathlib import Path

import pandas as pd
from statsmodels.tsa.stattools import adfuller

# Ruta a la base de datos
ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"

# Conexión a la base
con = sqlite3.connect(DB)

# Leer la tasa de desempleo desde la base
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

# Convertir fecha y preparar serie
desempleo["fecha"] = pd.to_datetime(desempleo["fecha"])
desempleo = desempleo.set_index("fecha")
serie = desempleo["valor"].dropna()

print("ANÁLISIS DE ESTACIONARIEDAD - TASA DE DESEMPLEO")
print(f"Observaciones disponibles: {len(serie)}")
print(f"Período: {serie.index.min().date()} a {serie.index.max().date()}")

# -------------------------------------------------
# 1. Prueba ADF en nivel
# -------------------------------------------------
adf_nivel = adfuller(serie)

print("\nADF EN NIVEL")
print(f"Estadístico ADF: {adf_nivel[0]:.4f}")
print(f"p-valor: {adf_nivel[1]:.4f}")

if adf_nivel[1] < 0.05:
    print("Conclusión: se rechaza H0. La serie en nivel es estacionaria.")
else:
    print("Conclusión: no se rechaza H0. La serie en nivel no es estacionaria.")

# -------------------------------------------------
# 2. Primera diferencia
# -------------------------------------------------
serie_diff = serie.diff().dropna()

adf_diff = adfuller(serie_diff)

print("\nADF EN PRIMERA DIFERENCIA")
print(f"Estadístico ADF: {adf_diff[0]:.4f}")
print(f"p-valor: {adf_diff[1]:.4f}")

if adf_diff[1] < 0.05:
    print("Conclusión: se rechaza H0. La primera diferencia es estacionaria.")
else:
    print("Conclusión: no se rechaza H0. La primera diferencia no es estacionaria.")

# -------------------------------------------------
# 3. Interpretación para el ARIMA
# -------------------------------------------------
print("\nINTERPRETACIÓN")

if adf_nivel[1] >= 0.05 and adf_diff[1] < 0.05:
    print(
        "La tasa de desempleo no es estacionaria en nivel, "
        "pero sí en primera diferencia. Esto respalda usar d=1 "
        "en el modelo ARIMA."
    )
elif adf_nivel[1] < 0.05:
    print(
        "La tasa de desempleo ya es estacionaria en nivel. "
        "Por lo tanto, habría que revisar si realmente se necesita d=1."
    )
else:
    print(
        "La serie tampoco resulta estacionaria en primera diferencia. "
        "Se requieren pruebas o transformaciones adicionales."
    )