
"""
Análisis de correlaciones y rezagos entre el IMACEC
y la tasa de desempleo nacional.

Se evalúan los rezagos de 0 a 12 meses utilizando
una muestra común para garantizar la comparabilidad.

Se consideran tres muestras:
- Muestra histórica completa.
- Muestra sin el período 2020-2022.
- Muestra anterior a enero de 2024.

El análisis es descriptivo y no modifica la
configuración de Ridge seleccionada previamente.
"""

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt


# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent

DB = ROOT / "base_datos" / "desempleo_chile.db"
OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

CORTE = pd.Period("2024-01", freq="M")

REZAGOS = range(13)

COD_IMACEC = "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M"
COD_DESEMPLEO = "F049.DES.TAS.INE9.10.M"

# CONSULTA SQL

SQL = """
SELECT
    o.fecha,
    s.id_serie,
    o.valor

FROM observaciones o

JOIN series s
    ON s.id_serie = o.id_serie

WHERE s.id_serie IN (?, ?)

ORDER BY o.fecha
"""

# CARGA Y PREPARACIÓN DE DATOS

def cargar_datos():

    if not DB.is_file():
        raise FileNotFoundError(DB)

    with sqlite3.connect(DB) as con:

        raw = pd.read_sql_query(
            SQL,
            con,
            params=[
                COD_IMACEC,
                COD_DESEMPLEO
            ]
        )

    raw["mes"] = pd.to_datetime(
        raw["fecha"]
    ).dt.to_period("M")

    datos = raw.pivot(
        index="mes",
        columns="id_serie",
        values="valor"
    ).sort_index()

    # Verificar que ambas series existan.
    if not {
        COD_IMACEC,
        COD_DESEMPLEO
    }.issubset(datos.columns):

        raise ValueError(
            "Faltan series en la base de datos."
        )

    datos = datos.rename(columns={

        COD_IMACEC: "imacec",

        COD_DESEMPLEO: "desempleo"

    })

    # Construir una secuencia mensual regular.
    # Así, cada rezago representa meses calendario
    # y no simplemente posiciones consecutivas.

    datos = datos.reindex(

        pd.period_range(
            datos.index.min(),
            datos.index.max(),
            freq="M"
        )

    )

    datos = datos.replace(
        [np.inf, -np.inf],
        np.nan
    )

    # Crecimiento interanual del IMACEC.
    # No se rellenan automáticamente datos faltantes.

    datos["imacec_yoy"] = (

        datos["imacec"]
        / datos["imacec"].shift(12).replace(
            0, np.nan
        )

        - 1

    ) * 100

    # Variación interanual del desempleo
    # expresada en puntos porcentuales.

    datos["desempleo_yoy_pp"] = (
        datos["desempleo"].diff(12)
    )

    # Construir rezagos de 0 a 12 meses.

    for k in REZAGOS:

        datos[f"lag_{k}"] = (
            datos["imacec_yoy"].shift(k)
        )

    columnas = [
        f"lag_{k}"
        for k in REZAGOS
    ]

    # Utilizar una muestra común para todos
    # los rezagos y ambas variables objetivo.

    muestra = datos.dropna(

        subset=[
            "desempleo",
            "desempleo_yoy_pp"
        ] + columnas

    )

    return muestra

# CÁLCULO DE CORRELACIONES

def correlaciones(
    muestra,
    nombre,
    objetivo
):

    if len(muestra) < 3:

        raise ValueError(
            f"Muestra insuficiente: {nombre}"
        )

    filas = []

    for k in REZAGOS:

        r = muestra[f"lag_{k}"].corr(
            muestra[objetivo]
        )

        if not np.isfinite(r):

            raise ValueError(
                f"Correlación indefinida: "
                f"{nombre}, rezago {k}"
            )

        filas.append({

            "muestra": nombre,

            "objetivo": objetivo,

            "rezago_meses": k,

            "correlacion": r,

            "observaciones": len(muestra),

            "inicio": str(
                muestra.index.min()
            ),

            "fin": str(
                muestra.index.max()
            )

        })

    return pd.DataFrame(filas)


# PROGRAMA PRINCIPAL

def main():

    datos = cargar_datos()

    # Excluir las fechas de la variable objetivo
    # comprendidas entre enero de 2020 y diciembre
    # de 2022 como prueba de sensibilidad.

    pandemia = (

        (
            datos.index
            >= pd.Period("2020-01", freq="M")
        )

        &

        (
            datos.index
            <= pd.Period("2022-12", freq="M")
        )

    )

    muestras = {

        "Completa": datos,

        "Sin 2020-2022": datos.loc[
            ~pandemia
        ],

        "Anterior a 2024": datos.loc[
            datos.index < CORTE
        ]

    }

    # Analizar dos relaciones diferentes:
    # 1. IMACEC y cambio interanual del desempleo.
    # 2. IMACEC y tasa de desempleo en nivel.

    tabla = pd.concat(

        [

            correlaciones(m, n, o)

            for n, m in muestras.items()

            for o in [

                "desempleo_yoy_pp",

                "desempleo"

            ]

        ],

        ignore_index=True

    )

    # EXPORTACIÓN DE RESULTADOS

    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)

    tabla.to_csv(

        OUT / "correlaciones_rezagos_detalle.csv",

        index=False,

        encoding="utf-8-sig"

    )

    # Mantener el archivo original del repositorio
    # con sus mismos nombres de columnas.

    original = tabla.loc[

        (
            tabla["muestra"]
            == "Completa"
        )

        &

        (
            tabla["objetivo"]
            == "desempleo_yoy_pp"
        ),

        [
            "rezago_meses",
            "correlacion",
            "observaciones"
        ]

    ]

    original.to_csv(

        OUT / "correlaciones_rezagos_imacec.csv",

        index=False,

        encoding="utf-8-sig"

    )

    # GRÁFICOS

    fig, axes = plt.subplots(

        2, 1,

        figsize=(10, 8),

        sharex=True

    )

    objetivos = [

        "desempleo_yoy_pp",

        "desempleo"

    ]

    titulos = [

        "Cambio interanual del desempleo (pp.)",

        "Tasa de desempleo en nivel (%)"

    ]

    for ax, objetivo, titulo in zip(
        axes,
        objetivos,
        titulos
    ):

        for nombre in muestras:

            sub = tabla[

                (
                    tabla["muestra"] == nombre
                )

                &

                (
                    tabla["objetivo"] == objetivo
                )

            ]

            ax.plot(

                sub["rezago_meses"],

                sub["correlacion"],

                marker="o",

                label=nombre

            )

        ax.axhline(

            0,

            color="gray",

            linestyle="--"

        )

        ax.set_title(titulo)

        ax.set_ylabel(
            "Correlación de Pearson"
        )

        ax.set_ylim(-1.05, 1.05)

        ax.grid(alpha=0.25)

        ax.legend()

    axes[-1].set_xlabel(

        "Rezago del crecimiento interanual "
        "del IMACEC (meses)"

    )

    axes[-1].set_xticks(
        list(REZAGOS)
    )

    fig.tight_layout()

    fig.savefig(

        FIG / "16_correlaciones_rezagos.png",

        dpi=170

    )

    plt.close(fig)

    # PRESENTACIÓN DE RESULTADOS

    print("\nCORRELACIONES POR REZAGO")

    comparacion = tabla.pivot(

        index="rezago_meses",

        columns=[
            "objetivo",
            "muestra"
        ],

        values="correlacion"

    )

    print(
        comparacion.round(4).to_string()
    )

    print(
        "\nMENOR CORRELACIÓN POR MUESTRA "
        "Y VARIABLE OBJETIVO"
    )

    mejores = tabla.loc[

        tabla.groupby(
            ["muestra", "objetivo"]
        )["correlacion"].idxmin()

    ]

    print(

        mejores.to_string(

            index=False,

            float_format=lambda x: f"{x:.4f}"

        )

    )

    print("\nARCHIVOS GENERADOS")

    print(
        "resultados/correlaciones_rezagos_imacec.csv"
    )

    print(
        "resultados/correlaciones_rezagos_detalle.csv"
    )

    print(
        "graficos/16_correlaciones_rezagos.png"
    )

    print("\nANÁLISIS FINALIZADO.")

    print(
        "Las correlaciones son descriptivas "
        "y no implican causalidad."
    )

    print(
        "Este análisis no modifica la "
        "configuración seleccionada de Ridge."
    )


if __name__ == "__main__":
    main()
