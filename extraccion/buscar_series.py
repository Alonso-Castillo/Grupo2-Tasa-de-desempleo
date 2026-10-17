
from pathlib import Path
import os
import bcchapi
import pandas as pd
from dotenv import load_dotenv

# 1. Cargar el token
RUTA_PROYECTO = Path(__file__).resolve().parent.parent
load_dotenv(RUTA_PROYECTO / ".env")

token = os.getenv("BCCH_API_TOKEN")

if not token:
    raise ValueError("No se encontró el token")

# 2. Conectarnos al Banco Central
siete = bcchapi.Siete(token=token)


# Buscar indicadores relacionados con participación
resultado = siete.buscar("participación")

# Verificar cuántas coincidencias encontramos
print("Total de series encontradas:", len(resultado))

# Mostrar los resultados sin aplicar filtros
columnas = [
    "seriesId",
    "spanishTitle",
    "frequencyCode",
    "firstObservation",
    "lastObservation"
]

if resultado.empty:
    print("La búsqueda no encontró coincidencias.")
else:
    print("\nSeries relacionadas con participación:")
    print(resultado[columnas].head(50).to_string(index=False))
