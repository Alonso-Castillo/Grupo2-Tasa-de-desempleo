
from pathlib import Path
import sqlite3
import os
import bcchapi
from dotenv import load_dotenv

# 1. Rutas del proyecto
RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"

# 2. Cargar las credenciales
load_dotenv(RUTA_PROYECTO / ".env")
token = os.getenv("BCCH_API_TOKEN")

if not token:
    raise ValueError("No se encontró el token del Banco Central")

if not RUTA_DB.exists():
    raise FileNotFoundError("Primero debes ejecutar crear_base.py")

# 3. Conectarse a la API
siete = bcchapi.Siete(token=token)

# 4. Catálogo de series que vamos a cargar
SERIES = [
    {
        "codigo": "F049.DES.TAS.INE9.10.M",
        "nombre": "Tasa de desempleo nacional",
        "columna": "Desempleo_nacional",
        "tema_id": 1,
        "tema": "Mercado laboral",
        "unidad": "Porcentaje",
        "desde": "2010-03-01"
    },
    {
        "codigo": "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M",
        "nombre": "IMACEC total",
        "columna": "IMACEC_total",
        "tema_id": 2,
        "tema": "Actividad económica",
        "unidad": "Índice 2018=100",
        "desde": "2010-01-01"
    },
    
{
    "codigo": "F049.OCU.PMT.INE9.01.M",
    "nombre": "Personas ocupadas, total nacional",
    "columna": "Ocupados_total",
    "tema_id": 1,
    "tema": "Mercado laboral",
    "unidad": "Miles de personas",
    "desde": "2010-03-01"
},

{
    "codigo": "F049.FTR.PMT.INE9.01.M",
    "nombre": "Fuerza de trabajo nacional",
    "columna": "Fuerza_trabajo",
    "tema_id": 1,
    "tema": "Mercado laboral",
    "unidad": "Miles de personas",
    "desde": "2010-03-01"
},

{
    "codigo": "F049.POB.PMT.INE9.01.M",
    "nombre": "Población de 15 años y más",
    "columna": "Poblacion_15_mas",
    "tema_id": 1,
    "tema": "Mercado laboral",
    "unidad": "Miles de personas",
    "desde": "2010-03-01"
},

{
    "codigo": "F049.AVS.IND.BCC1.01.M",
    "nombre": "Índice de Avisos Laborales de Internet (IALI)",
    "columna": "IALI_total",
    "tema_id": 1,
    "tema": "Mercado laboral",
    "unidad": "Índice 2018=100",
    "desde": "2017-01-01"
},

{
    "codigo": "F034.PRM.IND.INE.2018.0.M",
    "nombre": "Índice de Producción Manufacturera",
    "columna": "Produccion_manufacturera",
    "tema_id": 2,
    "tema": "Actividad económica",
    "unidad": "Índice 2018=100",
    "desde": "2010-01-01"
},

{
    "codigo": "F074.IPC.V12.Z.EP23.C.M",
    "nombre": "Inflación IPC anual",
    "columna": "Inflacion_IPC_anual",
    "tema_id": 3,
    "tema": "Precios",
    "unidad": "Porcentaje",
    "desde": "2011-01-01"
},

{
    "codigo": "F022.TPM.TIN.D001.NO.Z.M",
    "nombre": "Tasa de Política Monetaria (TPM)",
    "columna": "TPM",
    "tema_id": 4,
    "tema": "Política monetaria",
    "unidad": "Porcentaje",
    "desde": "2010-01-01"
},

{
    "codigo": "F019.PPB.PRE.40.M",
    "nombre": "Precio del cobre refinado BML",
    "columna": "Precio_cobre",
    "tema_id": 5,
    "tema": "Sector externo",
    "unidad": "USD por libra",
    "desde": "2010-01-01"
},

{
    "codigo": "F073.TCO.PRE.HIST.M",
    "nombre": "Tipo de cambio observado (CLP/USD)",
    "columna": "Tipo_cambio",
    "tema_id": 5,
    "tema": "Sector externo",
    "unidad": "CLP por USD",
    "desde": "2010-01-01"
},

{
    "codigo": "F032.PIB.FLU.R.CLP.EP18.Z.Z.0.T",
    "nombre": "PIB total real",
    "columna": "PIB_total",
    "tema_id": 2,
    "tema": "Actividad económica",
    "unidad": "Miles de millones de pesos encadenados",
    "frecuencia": "T",
    "desde": "2010-01-01"
}

]

# 5. Conectarse a SQLite
with sqlite3.connect(RUTA_DB) as conexion:

    conexion.execute("PRAGMA foreign_keys = ON")

    # 6. Recorrer cada serie del catálogo
    for serie in SERIES:

        print(f"\nProcesando: {serie['nombre']}")

        # Descargar datos desde el Banco Central
        datos = siete.cuadro(
            series=[serie["codigo"]],
            desde=serie["desde"],
            nombres=[serie["columna"]]
        )

        # Registrar la clasificación temática
        conexion.execute("""
            INSERT OR IGNORE INTO temas
            (id_tema, tema)
            VALUES (?, ?)
        """, (serie["tema_id"], serie["tema"]))

        # Registrar la serie económica
        conexion.execute("""
            INSERT OR IGNORE INTO series
            (id_serie, nombre, fuente, frecuencia, unidad, id_tema)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            serie["codigo"],
            serie["nombre"],
            "BDE Banco Central de Chile",
            serie.get("frecuencia", "M"),
            serie["unidad"],
            serie["tema_id"]
        ))

        # Preparar fechas y valores
        registros = [
            (
                serie["codigo"],
                fecha.strftime("%Y-%m-%d"),
                float(valor)
            )
            for fecha, valor in datos[serie["columna"]].dropna().items()
        ]

        # Guardar las observaciones
        conexion.executemany("""
            INSERT INTO observaciones
            (id_serie, fecha, valor)
            VALUES (?, ?, ?)
            ON CONFLICT(id_serie, fecha)
            DO UPDATE SET valor = excluded.valor
        """, registros)

        # Verificar los registros almacenados
        total = conexion.execute("""
            SELECT COUNT(*)
            FROM observaciones
            WHERE id_serie = ?
        """, (serie["codigo"],)).fetchone()[0]

        print("Observaciones descargadas:", len(registros))
        print("Observaciones almacenadas:", total)

print("\nCarga de series finalizada correctamente.")
