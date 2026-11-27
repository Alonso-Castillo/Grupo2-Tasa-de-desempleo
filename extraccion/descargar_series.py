
"""
Descarga y contrastación de las series económicas principales.

Fuente: Base de Datos Estadísticos del Banco Central de Chile.

La descarga utiliza la cobertura temporal de la investigación.
La base SQLite se consulta exclusivamente en modo lectura.
"""

from pathlib import Path
import os
import sqlite3

import bcchapi
import numpy as np
import pandas as pd

from dotenv import load_dotenv


# ==================================================
# 1. CONFIGURACIÓN
# ==================================================

ROOT = Path(__file__).resolve().parent.parent

DB = ROOT / "base_datos" / "desempleo_chile.db"

FECHA_FINAL = "2026-08-31"

TOLERANCIA = 1e-6

SERIES = [
    {
        "codigo": "F049.DES.TAS.INE9.10.M",
        "nombre": "Desempleo_nacional",
        "desde": "2010-03-01",
        "observaciones_esperadas": 198
    },
    {
        "codigo": "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M",
        "nombre": "IMACEC_total",
        "desde": "2010-01-01",
        "observaciones_esperadas": 200
    }
]


# ==================================================
# 2. CONEXIÓN CON EL BANCO CENTRAL
# ==================================================

def conectar_bcch():

    load_dotenv(ROOT / ".env")

    token = os.getenv("BCCH_API_TOKEN", "").strip()

    if not token:
        raise ValueError(
            "No se encontró BCCH_API_TOKEN."
        )

    return bcchapi.Siete(token=token)


# ==================================================
# 3. VALIDACIÓN DE LAS OBSERVACIONES
# ==================================================

def validar_serie(serie, configuracion):

    nombre = configuracion["nombre"]

    if serie.empty:
        raise ValueError(f"{nombre}: serie vacía.")

    serie = serie.copy()

    if isinstance(serie.index, pd.PeriodIndex):

        serie.index = serie.index.asfreq("M")

    else:

        if pd.api.types.is_numeric_dtype(
            serie.index.dtype
        ):
            raise ValueError(
                f"{nombre}: índice sin fechas válidas."
            )

        fechas = pd.to_datetime(
            serie.index,
            errors="raise"
        )

        serie.index = fechas.to_period("M")

    if serie.index.hasnans:
        raise ValueError(
            f"{nombre}: existen fechas inválidas."
        )

    if serie.index.duplicated().any():
        raise ValueError(
            f"{nombre}: existen períodos duplicados."
        )

    serie = pd.to_numeric(
        serie,
        errors="coerce"
    )

    if not np.isfinite(serie.to_numpy()).all():
        raise ValueError(
            f"{nombre}: existen valores inválidos."
        )

    serie = serie.sort_index()

    periodos_esperados = pd.period_range(
        start=configuracion["desde"],
        end=FECHA_FINAL,
        freq="M"
    )

    faltantes = periodos_esperados.difference(
        serie.index
    )

    adicionales = serie.index.difference(
        periodos_esperados
    )

    if len(faltantes) > 0:
        raise ValueError(
            f"{nombre}: períodos faltantes: "
            f"{faltantes.tolist()}"
        )

    if len(adicionales) > 0:
        raise ValueError(
            f"{nombre}: períodos fuera de la muestra."
        )

    if len(serie) != configuracion[
        "observaciones_esperadas"
    ]:
        raise ValueError(
            f"{nombre}: cantidad incorrecta "
            "de observaciones."
        )

    return serie


# ==================================================
# 4. DESCARGA DESDE LA API
# ==================================================

def descargar_serie(siete, configuracion):

    codigo = configuracion["codigo"]
    nombre = configuracion["nombre"]

    print(f"\nDescargando: {nombre}")
    print(f"Código: {codigo}")

    try:

        datos = siete.cuadro(
            series=[codigo],
            desde=configuracion["desde"],
            hasta=FECHA_FINAL,
            nombres=[nombre]
        )

    except Exception as error:

        raise RuntimeError(
            f"Error de descarga para {nombre}: "
            f"{type(error).__name__}"
        ) from None

    if not isinstance(datos, pd.DataFrame):
        raise TypeError(
            f"{nombre}: respuesta inesperada de la API."
        )

    if nombre not in datos.columns:
        raise ValueError(
            f"{nombre}: columna no encontrada."
        )

    return validar_serie(
        datos[nombre],
        configuracion
    )


# ==================================================
# 5. LECTURA DE SQLITE
# ==================================================

def leer_serie_local(conexion, configuracion):

    consulta = """
        SELECT fecha, valor
        FROM observaciones
        WHERE id_serie = ?
        ORDER BY fecha
    """

    datos = pd.read_sql_query(
        consulta,
        conexion,
        params=[configuracion["codigo"]]
    )

    serie = datos.set_index("fecha")["valor"]

    return validar_serie(
        serie,
        configuracion
    )


# ==================================================
# 6. COMPARACIÓN DE OBSERVACIONES
# ==================================================

def comparar_series(api, local, configuracion):

    comparacion = pd.DataFrame({
        "valor_api": api,
        "valor_sqlite": local
    })

    comparacion["diferencia"] = (
        comparacion["valor_api"]
        - comparacion["valor_sqlite"]
    )

    comparacion["diferencia_absoluta"] = (
        comparacion["diferencia"].abs()
    )

    distintas = comparacion.loc[
        comparacion["diferencia_absoluta"]
        > TOLERANCIA
    ]

    print("\nRESULTADOS DE LA COMPARACIÓN")
    print("-" * 60)

    print(
        "Observaciones API:",
        len(api)
    )

    print(
        "Observaciones SQLite:",
        len(local)
    )

    print(
        "Primera observación:",
        api.index.min()
    )

    print(
        "Última observación:",
        api.index.max()
    )

    print(
        "Tolerancia numérica:",
        TOLERANCIA
    )

    print(
        "Observaciones coincidentes:",
        len(comparacion) - len(distintas)
    )

    print(
        "Observaciones con diferencias:",
        len(distintas)
    )

    print(
        "Diferencia absoluta máxima:",
        f"{comparacion['diferencia_absoluta'].max():.10f}"
    )

    if distintas.empty:

        print(
            "Resultado: COINCIDENCIA DENTRO "
            "DE LA TOLERANCIA."
        )

    else:

        print(
            "Resultado: SE DETECTARON DIFERENCIAS."
        )

        print(
            "\nPrimeras observaciones con diferencias:"
        )

        print(
            distintas.head(10).to_string()
        )

    return {
        "indicador": configuracion["nombre"],
        "codigo": configuracion["codigo"],
        "observaciones": len(comparacion),
        "coincidentes": len(comparacion) - len(distintas),
        "diferencias": len(distintas),
        "diferencia_maxima": (
            comparacion["diferencia_absoluta"].max()
        )
    }


# ==================================================
# 7. PROGRAMA PRINCIPAL
# ==================================================

def main():

    print("\nVERIFICACIÓN DE SERIES ECONÓMICAS")
    print("=" * 60)

    print("Fuente: Banco Central de Chile")
    print("Fecha final de la muestra:", FECHA_FINAL)

    if not DB.is_file():
        raise FileNotFoundError(
            "No se encontró la base SQLite."
        )

    try:

        siete = conectar_bcch()

    except Exception as error:

        print(
            "Error de conexión:",
            type(error).__name__
        )

        raise SystemExit(1) from None

    resultados = []

    # Apertura exclusiva en modo lectura.

    conexion = sqlite3.connect(
        DB.resolve().as_uri() + "?mode=ro",
        uri=True
    )

    try:

        for configuracion in SERIES:

            api = descargar_serie(
                siete,
                configuracion
            )

            local = leer_serie_local(
                conexion,
                configuracion
            )

            resumen = comparar_series(
                api,
                local,
                configuracion
            )

            resultados.append(resumen)

    finally:

        conexion.close()

    resumen_final = pd.DataFrame(resultados)

    print("\nRESUMEN GENERAL")
    print("=" * 60)

    print(
        resumen_final.to_string(index=False)
    )

    print("\nVERIFICACIÓN FINALIZADA.")

    print(
        "La base SQLite no fue modificada."
    )

    print(
        "Las diferencias pueden corresponder a "
        "revisiones históricas, precisión numérica "
        "o discrepancias en la carga original."
    )

    print(
        "No se actualizan automáticamente "
        "las observaciones locales."
    )


if __name__ == "__main__":
    main()
