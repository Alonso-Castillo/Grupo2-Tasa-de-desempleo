
from pathlib import Path
import os
import bcchapi
from dotenv import load_dotenv

# 1. Identificar la carpeta principal del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent

# 2. Cargar las credenciales guardadas en .env
load_dotenv(RUTA_PROYECTO / ".env")

token = os.getenv("BCCH_API_TOKEN")

# 3. Verificar que exista el token
if not token:
    raise ValueError("No se encontró el token en el archivo .env")

# 4. Conectarnos con el Banco Central
siete = bcchapi.Siete(token=token)

print("Consultando el catálogo del Banco Central...")


# 5. Código oficial de la tasa de desempleo nacional
codigo_desempleo = "F049.DES.TAS.INE9.10.M"

# 6. Descargar las observaciones históricas
print("Descargando tasa de desempleo nacional...")

desempleo = siete.cuadro(
    series=[codigo_desempleo],
    desde="2010-03-01",
    nombres=["Desempleo_nacional"]
)

# 7. Mostrar resultados de la descarga
print("\nPrimeras observaciones:")
print(desempleo.head())

print("\nÚltimas observaciones:")
print(desempleo.tail())

print("\nTotal de observaciones:", len(desempleo))
print("Primera fecha:", desempleo.index.min())
print("Última fecha:", desempleo.index.max())

# 8. Descargar IMACEC total
codigo_imacec = "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M"

print("\nDescargando IMACEC total...")

imacec = siete.cuadro(
    series=[codigo_imacec],
    desde="2010-01-01",
    nombres=["IMACEC_total"]
)

# 9. Revisar los datos descargados
print("\nPrimeras observaciones del IMACEC:")
print(imacec.head())

print("\nÚltimas observaciones del IMACEC:")
print(imacec.tail())

print("\nTotal de observaciones IMACEC:", len(imacec))
print("Primera fecha:", imacec.index.min())
print("Última fecha:", imacec.index.max())
