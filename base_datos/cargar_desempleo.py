
from pathlib import Path
import sqlite3
import os
import bcchapi
from dotenv import load_dotenv

# 1. Identificar las rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

# 2. Cargar el token de la API
load_dotenv(RUTA_PROYECTO / ".env")
token = os.getenv("BCCH_API_TOKEN")

if not token:
    raise ValueError("No se encontró el token del Banco Central")

# 3. Descargar nuevamente los datos de desempleo
siete = bcchapi.Siete(token=token)

codigo = "F049.DES.TAS.INE9.10.M"

desempleo = siete.cuadro(
    series=[codigo],
    desde="2010-03-01",
    nombres=["Desempleo_nacional"]
)

# 4. Preparar las observaciones para SQLite
registros = [
    (codigo, fecha.strftime("%Y-%m-%d"), float(valor))
    for fecha, valor in desempleo["Desempleo_nacional"].dropna().items()
]

# 5. Conectar con nuestra base de datos
with sqlite3.connect(RUTA_DB) as conexion:

    conexion.execute("PRAGMA foreign_keys = ON")

    # Registrar el tema económico
    conexion.execute("""
        INSERT OR IGNORE INTO temas
        (id_tema, tema, descripcion)
        VALUES (1, 'Mercado laboral',
                'Indicadores del mercado laboral chileno')
    """)

    # Registrar la serie económica
    conexion.execute("""
        INSERT OR IGNORE INTO series
        (id_serie, nombre, fuente, frecuencia, unidad, id_tema)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        codigo,
        "Tasa de desempleo nacional",
        "INE - BDE Banco Central",
        "M",
        "Porcentaje",
        1
    ))

    # Insertar las observaciones, actualizando valores existentes
    conexion.executemany("""
        INSERT INTO observaciones (id_serie, fecha, valor)
        VALUES (?, ?, ?)
        ON CONFLICT(id_serie, fecha)
        DO UPDATE SET valor = excluded.valor
    """, registros)

    # Verificar la cantidad de registros almacenados
    total = conexion.execute("""
        SELECT COUNT(*)
        FROM observaciones
        WHERE id_serie = ?
    """, (codigo,)).fetchone()[0]

print("Carga de desempleo finalizada correctamente.")
print("Observaciones descargadas:", len(registros))
print("Observaciones almacenadas:", total)
