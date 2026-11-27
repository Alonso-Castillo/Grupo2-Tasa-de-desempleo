
"""
Análisis de estacionariedad de la tasa de desempleo.

Se aplica la prueba Dickey-Fuller Aumentada (ADF)
en nivel y primera diferencia.

Se analizan dos muestras:
- Entrenamiento: observaciones anteriores a enero de 2024.
- Completa: todas las observaciones disponibles.

El diagnóstico de entrenamiento permite fundamentar
la especificación sin utilizar el período de evaluación.

La muestra completa se utiliza con fines descriptivos
y de diagnóstico del modelo final.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from statsmodels.tsa.stattools import adfuller


# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent

DB = ROOT / "base_datos" / "desempleo_chile.db"
OUT = ROOT / "resultados"

CORTE = pd.Period("2024-01", freq="M")

SIGNIFICANCIA = 0.05


# CONSULTA SQL

SQL = """
SELECT
    o.fecha,
    o.valor

FROM observaciones o

JOIN series s
    ON o.id_serie = s.id_serie

WHERE s.nombre = 'Tasa de desempleo nacional'

ORDER BY o.fecha
"""

# CARGA Y VALIDACIÓN DE DATOS

def cargar_serie():

    if not DB.is_file():
        raise FileNotFoundError(DB)

    with sqlite3.connect(DB) as con:

        datos = pd.read_sql_query(
            SQL,
            con
        )

    if datos.empty:

        raise ValueError(
            "No se encontraron datos de desempleo."
        )

    datos["mes"] = pd.to_datetime(
        datos["fecha"]
    ).dt.to_period("M")

    # Verificar que no existan meses duplicados.
    if datos["mes"].duplicated().any():

        raise ValueError(
            "Existen meses duplicados."
        )

    serie = datos.set_index(
        "mes"
    )["valor"].sort_index().astype(float)

    # Verificar valores faltantes o no finitos.
    if not np.isfinite(
        serie.to_numpy()
    ).all():

        raise ValueError(
            "La serie contiene valores inválidos."
        )

    # Verificar continuidad mensual.
    calendario = pd.period_range(

        serie.index.min(),

        serie.index.max(),

        freq="M"

    )

    faltantes = calendario.difference(
        serie.index
    )

    if len(faltantes) > 0:

        raise ValueError(

            f"Meses faltantes: {list(faltantes)}"

        )

    return serie

# PRUEBA DICKEY-FULLER AUMENTADA

def aplicar_adf(
    serie,
    muestra,
    transformacion
):

    # H0: la serie presenta una raíz unitaria.
    # H1: la serie es estacionaria alrededor
    # de una constante.
    #
    # Se utiliza una constante sin tendencia
    # determinística y se seleccionan los
    # rezagos mediante el criterio AIC.

    resultado = adfuller(

        serie,

        regression="c",

        autolag="AIC"

    )

    estadistico = resultado[0]

    p_valor = resultado[1]

    rezagos = resultado[2]

    nobs = resultado[3]

    criticos = resultado[4]

    mejor_aic = resultado[5]

    rechazo = p_valor < SIGNIFICANCIA

    if rechazo:

        conclusion = (
            "Se rechaza H0 de raíz unitaria"
        )

    else:

        conclusion = (
            "No se rechaza H0 de raíz unitaria"
        )

    return {

        "muestra": muestra,

        "transformacion": transformacion,

        "inicio": str(serie.index.min()),

        "fin": str(serie.index.max()),

        "observaciones_serie": len(serie),

        "observaciones_adf": nobs,

        "estadistico_adf": estadistico,

        "p_valor": p_valor,

        "rezagos_adf": rezagos,

        "valor_critico_1": criticos["1%"],

        "valor_critico_5": criticos["5%"],

        "valor_critico_10": criticos["10%"],

        "aic_seleccion_rezagos": mejor_aic,

        "significancia": SIGNIFICANCIA,

        "rechaza_h0": rechazo,

        "conclusion": conclusion

    }


# INTERPRETACIÓN ECONOMÉTRICA

def interpretar(nivel, diferencia):

    if (

        not nivel["rechaza_h0"]

        and diferencia["rechaza_h0"]

    ):

        return (

            "No se rechaza la presencia de raíz "
            "unitaria en nivel, pero sí en primera "
            "diferencia. El resultado es compatible "
            "con una serie integrada de orden uno "
            "y respalda considerar d=1 en ARIMA."

        )

    elif nivel["rechaza_h0"]:

        return (

            "Se rechaza la hipótesis de raíz "
            "unitaria en nivel. Corresponde revisar "
            "si la diferenciación es necesaria y "
            "considerar especificaciones con d=0."

        )

    else:

        return (

            "No se rechaza la hipótesis de raíz "
            "unitaria en nivel ni en primera "
            "diferencia. Se requieren diagnósticos "
            "adicionales antes de justificar d=1."

        )


# PROGRAMA PRINCIPAL

def main():

    serie = cargar_serie()

    entrenamiento = serie.loc[
        serie.index < CORTE
    ]

    muestras = {

        "Entrenamiento anterior a 2024":
            entrenamiento,

        "Completa":
            serie

    }

    resultados = []

    print(
        "\nANÁLISIS DE ESTACIONARIEDAD"
    )

    print(
        "\nVariable: tasa de desempleo nacional"
    )

    print(
        f"Observaciones totales: {len(serie)}"
    )

    print(
        f"Período: {serie.index.min()} "
        f"a {serie.index.max()}"
    )

    print(
        "Continuidad mensual: correcta"
    )

    # EVALUAR AMBAS MUESTRAS

    for nombre, muestra in muestras.items():

        diferencia = muestra.diff().dropna()

        adf_nivel = aplicar_adf(

            muestra,

            nombre,

            "Nivel"

        )

        adf_diferencia = aplicar_adf(

            diferencia,

            nombre,

            "Primera diferencia"

        )

        resultados.extend([

            adf_nivel,

            adf_diferencia

        ])

        print("\n" + "=" * 60)

        print(nombre.upper())

        print("=" * 60)

        print(
            f"Observaciones: {len(muestra)}"
        )

        print(
            f"Período: {muestra.index.min()} "
            f"a {muestra.index.max()}"
        )

        for resultado in [

            adf_nivel,

            adf_diferencia

        ]:

            print(
                "\nTRANSFORMACIÓN:",
                resultado["transformacion"]
            )

            print(
                "Estadístico ADF:",
                f"{resultado['estadistico_adf']:.6f}"
            )

            print(
                "P-valor:",
                f"{resultado['p_valor']:.8g}"
            )

            print(
                "Rezagos seleccionados:",
                resultado["rezagos_adf"]
            )

            print(
                "Observaciones efectivas ADF:",
                resultado["observaciones_adf"]
            )

            print("\nValores críticos:")

            for nivel in [1, 5, 10]:

                valor = resultado[
                    f"valor_critico_{nivel}"
                ]

                print(
                    f"{nivel}%: {valor:.6f}"
                )

            print(
                "\nConclusión:",
                resultado["conclusion"]
            )

        print("\nINTERPRETACIÓN PARA ARIMA")

        print(
            interpretar(
                adf_nivel,
                adf_diferencia
            )
        )

    # EXPORTACIÓN

    tabla = pd.DataFrame(resultados)

    OUT.mkdir(exist_ok=True)

    archivo = OUT / "estacionariedad_desempleo.csv"

    tabla.to_csv(

        archivo,

        index=False,

        encoding="utf-8-sig"

    )

    print("\n" + "=" * 60)

    print("RESUMEN DE RESULTADOS")

    print("=" * 60)

    columnas = [

        "muestra",

        "transformacion",

        "estadistico_adf",

        "p_valor",

        "rezagos_adf",

        "rechaza_h0"

    ]

    print(

        tabla[columnas].to_string(

            index=False,

            float_format=lambda x: f"{x:.6g}"

        )

    )

    print("\nARCHIVO GENERADO")

    print(
        "resultados/estacionariedad_desempleo.csv"
    )

    print("\nANÁLISIS FINALIZADO.")

    print(

        "Nota: la prueba ADF no permite por sí "
        "sola determinar los órdenes p y q "
        "ni descartar estacionalidad o "
        "quiebres estructurales."

    )


if __name__ == "__main__":
    main()
