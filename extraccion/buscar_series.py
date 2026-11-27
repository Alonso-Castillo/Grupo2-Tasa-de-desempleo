
"""
Herramienta de búsqueda de series económicas
en la Base de Datos Estadísticos del Banco Central de Chile.

Permite consultar indicadores por palabras clave
y exportar los resultados de búsqueda.

No descarga observaciones ni modifica la base SQLite.
"""

from pathlib import Path
import argparse
import os

import bcchapi
import pandas as pd

from dotenv import load_dotenv



# CONFIGURACIÓN


ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "resultados"

COLUMNAS = [
    "seriesId",
    "spanishTitle",
    "frequencyCode",
    "firstObservation",
    "lastObservation"
]
FRECUENCIAS = {
    "M": "MONTHLY",
    "MENSUAL": "MONTHLY",
    "MONTHLY": "MONTHLY",
    "T": "QUARTERLY",
    "Q": "QUARTERLY",
    "TRIMESTRAL": "QUARTERLY",
    "QUARTERLY": "QUARTERLY",
    "A": "ANNUAL",
    "ANUAL": "ANNUAL",
    "ANNUAL": "ANNUAL",
    "D": "DAILY",
    "DIARIA": "DAILY",
    "DAILY": "DAILY"
}


def normalizar_frecuencia(valor):

    valor = str(valor).strip().upper()

    return FRECUENCIAS.get(valor, valor)



# CONEXIÓN CON EL BANCO CENTRAL


def conectar_bcch():

    load_dotenv(ROOT / ".env")

    token = os.getenv("BCCH_API_TOKEN", "").strip()

    if not token:

        raise ValueError(
            "No se encontró BCCH_API_TOKEN. "
            "Revisar la configuración del archivo .env."
        )

    return bcchapi.Siete(token=token)



# BÚSQUEDA DE SERIES


def buscar_series(siete, termino):

    termino = termino.strip()

    if not termino:

        raise ValueError(
            "El término de búsqueda no puede estar vacío."
        )

    resultado = siete.buscar(termino)

    if not isinstance(resultado, pd.DataFrame):

        raise TypeError(
            "La búsqueda no devolvió un DataFrame."
        )

    if resultado.empty:

        return pd.DataFrame(columns=COLUMNAS)

    faltantes = [
        columna
        for columna in COLUMNAS
        if columna not in resultado.columns
    ]

    if faltantes:

        raise ValueError(
            f"Columnas ausentes en la respuesta: {faltantes}"
        )

    resultado = resultado[COLUMNAS].copy()

    resultado = resultado.drop_duplicates()

    resultado = resultado.sort_values(
        ["spanishTitle", "seriesId"]
    ).reset_index(drop=True)

    return resultado



# ARGUMENTOS DE EJECUCIÓN


def obtener_argumentos():

    parser = argparse.ArgumentParser(

        description=(
            "Buscar series económicas del "
            "Banco Central de Chile."
        )

    )

    parser.add_argument(

        "termino",

        nargs="?",

        default="participación",

        help="Palabra o frase que se desea buscar."

    )

    parser.add_argument(

        "--limite",

        type=int,

        default=50,

        help="Cantidad máxima de resultados en pantalla."

    )

    parser.add_argument(

        "--frecuencia",

        type=str,

        default=None,

        help="Filtrar por código de frecuencia."

    )

    parser.add_argument(

        "--exportar",

        action="store_true",

        help="Exportar las coincidencias a un archivo CSV."

    )

    args = parser.parse_args()

    if args.limite <= 0:

        parser.error(
            "El límite debe ser mayor que cero."
        )

    if not args.termino.strip():

        parser.error(
            "El término de búsqueda no puede estar vacío."
        )

    return args



# PROGRAMA PRINCIPAL


def main():

    args = obtener_argumentos()

    print("\nBÚSQUEDA DE SERIES ECONÓMICAS")
    print("=" * 60)

    print("Fuente: Banco Central de Chile")
    print(f"Término de búsqueda: {args.termino}")

    # Conectar y realizar la consulta.
    # No mostrar mensajes que puedan contener
    # credenciales o detalles sensibles de la API.

    try:

        siete = conectar_bcch()

        resultado = buscar_series(
            siete,
            args.termino
        )

    except Exception as error:

        print("\nERROR DURANTE LA CONSULTA")

        print(
            f"Tipo de error: {type(error).__name__}"
        )

        print(
            "Revisar las credenciales, la conexión "
            "y la disponibilidad de la API."
        )

        raise SystemExit(1) from None

    print(
        f"\nCoincidencias encontradas: {len(resultado)}"
    )


    # FILTRO OPCIONAL DE FRECUENCIA


    if args.frecuencia:

        frecuencia = normalizar_frecuencia(
            args.frecuencia
        )

        resultado = resultado.loc[
            resultado["frequencyCode"]
            .map(normalizar_frecuencia) == frecuencia
        ].copy()

        print(f"Frecuencia seleccionada: {frecuencia}")

        print(
            f"Coincidencias después del filtro: "
            f"{len(resultado)}"
        )


    # PRESENTACIÓN DE RESULTADOS

    if resultado.empty:

        print(
            "\nNo se encontraron series "
            "para la búsqueda seleccionada."
        )

        return

    print("\nSERIES ENCONTRADAS")
    print("=" * 60)

    print(

        resultado.head(args.limite).to_string(
            index=False
        )

    )

    if len(resultado) > args.limite:

        print(
            f"\nMostrando {args.limite} "
            f"de {len(resultado)} coincidencias."
        )


    # EXPORTACIÓN OPCIONAL


    if args.exportar:

        OUT.mkdir(exist_ok=True)

        archivo = OUT / "busqueda_series_bcch.csv"

        exportacion = resultado.copy()

        exportacion.insert(
            0,
            "termino_busqueda",
            args.termino
        )

        exportacion.to_csv(

            archivo,

            index=False,

            encoding="utf-8-sig"

        )

        print("\nARCHIVO GENERADO")

        print(
            "resultados/busqueda_series_bcch.csv"
        )

    print("\nBÚSQUEDA FINALIZADA.")

    print(
        "No se descargaron observaciones "
        "ni se modificó la base SQLite."
    )


if __name__ == "__main__":
    main()
