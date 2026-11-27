
"""
Diagnóstico y especificación del modelo ARIMA
para la tasa de desempleo nacional.

La comparación de especificaciones se realiza
exclusivamente con datos anteriores a enero de 2024.

Se analiza:
- ACF y PACF de la primera diferencia.
- Comparación de modelos mediante AIC y BIC.
- Posible estacionalidad de frecuencia anual.
- Convergencia de las estimaciones.
- Autocorrelación de residuos mediante Ljung-Box.

Este script no modifica automáticamente el modelo
de pronóstico utilizado en el proyecto.
"""

from pathlib import Path
from itertools import product

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import (
    plot_acf,
    plot_pacf
)
from statsmodels.stats.diagnostic import acorr_ljungbox

# Reutilizar la carga y validación de la serie.
from estacionariedad_desempleo import (
    cargar_serie,
    CORTE
)


# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent

OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

ORDEN_REFERENCIA = (1, 1, 1)

SIGNIFICANCIA = 0.05

REZAGOS_GRAFICOS = 36

REZAGOS_LJUNG_BOX = [6, 12, 24]


# GRÁFICOS ACF Y PACF

def graficar_acf_pacf(serie):

    diferencia = serie.diff().dropna()

    fig, ax = plt.subplots(figsize=(11, 5))

    plot_acf(
        diferencia,
        lags=REZAGOS_GRAFICOS,
        alpha=0.05,
        zero=False,
        ax=ax
    )

    ax.set_title(
        "ACF de la primera diferencia del desempleo\n"
        "Muestra de entrenamiento: anterior a 2024"
    )

    ax.set_xlabel("Rezago mensual")
    ax.set_ylabel("Autocorrelación")

    ax.axvline(12, color="gray", linestyle="--")
    ax.axvline(24, color="gray", linestyle="--")

    fig.tight_layout()

    fig.savefig(
        FIG / "14_acf_desempleo.png",
        dpi=170
    )

    plt.close(fig)

    # PACF

    fig, ax = plt.subplots(figsize=(11, 5))

    plot_pacf(
        diferencia,
        lags=REZAGOS_GRAFICOS,
        alpha=0.05,
        method="ywm",
        zero=False,
        ax=ax
    )

    ax.set_title(
        "PACF de la primera diferencia del desempleo\n"
        "Muestra de entrenamiento: anterior a 2024"
    )

    ax.set_xlabel("Rezago mensual")
    ax.set_ylabel("Autocorrelación parcial")

    ax.axvline(12, color="gray", linestyle="--")
    ax.axvline(24, color="gray", linestyle="--")

    fig.tight_layout()

    fig.savefig(
        FIG / "15_pacf_desempleo.png",
        dpi=170
    )

    plt.close(fig)


# OBTENER RESIDUOS ESTANDARIZADOS

def obtener_residuos(ajuste):

    # Utilizar errores de predicción estandarizados.
    # Excluir observaciones iniciales afectadas por
    # la inicialización del modelo.

    residuos = np.asarray(
        ajuste.filter_results
        .standardized_forecasts_error[0],
        dtype=float
    )

    burn = max(
        int(ajuste.loglikelihood_burn),
        int(
            getattr(
                ajuste.filter_results,
                "nobs_diffuse",
                0
            )
        )
    )

    residuos = residuos[burn:]

    if not np.isfinite(residuos).all():
        raise ValueError(
            "Residuos no finitos después de inicialización."
        )

    return residuos


# PRUEBA LJUNG-BOX

def diagnosticar_residuos(
    ajuste,
    orden,
    orden_estacional
):

    residuos = obtener_residuos(ajuste)

    p, d, q = orden
    P, D, Q, s = orden_estacional

    # Ajustar los grados de libertad según
    # los términos AR y MA estimados.

    grados = p + q + P + Q

    prueba = acorr_ljungbox(
        residuos,
        lags=REZAGOS_LJUNG_BOX,
        model_df=grados,
        return_df=True
    )

    return residuos, prueba


# COMPARACIÓN DE ESPECIFICACIONES

def comparar_modelos(serie):

    candidatos = []

    # Evaluar modelos ARIMA con p y q entre 0 y 2.
    # Mantener d=1, respaldado por la prueba ADF.

    for p, q in product(range(3), repeat=2):

        candidatos.append((

            (p, 1, q),

            (0, 0, 0, 0)

        ))

    # Incorporar dos alternativas estacionales
    # con periodicidad anual de 12 meses.

    candidatos.extend([

        (
            (1, 1, 1),
            (1, 0, 0, 12)
        ),

        (
            (1, 1, 1),
            (0, 0, 1, 12)
        )

    ])

    resultados = []

    for orden, estacional in candidatos:

        if estacional == (0, 0, 0, 0):

            nombre = f"ARIMA{orden}"

        else:

            nombre = (
                f"SARIMA{orden}x{estacional}"
            )

        print(f"Estimando {nombre}...")

        fila = {

            "modelo": nombre,

            "orden": str(orden),

            "orden_estacional": str(estacional),

            "inicio": str(serie.index.min()),

            "fin": str(serie.index.max()),

            "observaciones": len(serie),

            "convergio": False,

            "AIC": np.nan,

            "BIC": np.nan,

            "Ljung_Box_p6": np.nan,

            "Ljung_Box_p12": np.nan,

            "Ljung_Box_p24": np.nan,

            "error": ""

        }

        try:

            ajuste = ARIMA(
                serie,
                order=orden,
                seasonal_order=estacional
            ).fit()

            convergio = bool(
                ajuste.mle_retvals.get(
                    "converged", False
                )
            )

            _, prueba = diagnosticar_residuos(
                ajuste,
                orden,
                estacional
            )

            fila.update({

                "convergio": convergio,

                "AIC": ajuste.aic,

                "BIC": ajuste.bic,

                "Ljung_Box_p6":
                    prueba.loc[6, "lb_pvalue"],

                "Ljung_Box_p12":
                    prueba.loc[12, "lb_pvalue"],

                "Ljung_Box_p24":
                    prueba.loc[24, "lb_pvalue"]

            })

        except Exception as error:

            # Registrar errores sin ocultarlos
            # ni eliminar candidatos de la tabla.

            fila["error"] = str(error)

            print(f"Error en {nombre}: {error}")

        resultados.append(fila)

    tabla = pd.DataFrame(resultados)

    # Priorizar estimaciones convergentes.

    tabla = tabla.sort_values(
        ["convergio", "AIC"],
        ascending=[False, True]
    ).reset_index(drop=True)

    return tabla


# DIAGNÓSTICO DEL ARIMA DE REFERENCIA

def diagnosticar_referencia(
    entrenamiento,
    completa
):

    muestras = {

        "Entrenamiento anterior a 2024":
            entrenamiento,

        "Completa":
            completa

    }

    filas = []

    fig, axes = plt.subplots(
        2, 2,
        figsize=(13, 8)
    )

    for i, (nombre, serie) in enumerate(
        muestras.items()
    ):

        ajuste = ARIMA(
            serie,
            order=ORDEN_REFERENCIA
        ).fit()

        convergio = bool(
            ajuste.mle_retvals.get(
                "converged", False
            )
        )

        residuos, prueba = diagnosticar_residuos(
            ajuste,
            ORDEN_REFERENCIA,
            (0, 0, 0, 0)
        )

        print("\n" + "=" * 60)

        print(nombre.upper())

        print("=" * 60)

        print(f"Convergencia: {convergio}")

        print(f"AIC: {ajuste.aic:.4f}")

        print(f"BIC: {ajuste.bic:.4f}")

        print("\nCoeficientes estimados:")

        print(ajuste.params.to_string())

        print("\nP-valores de los coeficientes:")

        print(ajuste.pvalues.to_string())

        print("\nPRUEBA LJUNG-BOX")

        print(prueba.to_string())

        for lag in REZAGOS_LJUNG_BOX:

            p_valor = float(
                prueba.loc[lag, "lb_pvalue"]
            )

            if p_valor < SIGNIFICANCIA:

                conclusion = (
                    "Se rechaza ausencia "
                    "de autocorrelación"
                )

            else:

                conclusion = (
                    "No se rechaza ausencia "
                    "de autocorrelación"
                )

            filas.append({

                "muestra": nombre,

                "modelo": "ARIMA(1,1,1)",

                "convergio": convergio,

                "AIC": ajuste.aic,

                "BIC": ajuste.bic,

                "rezago": lag,

                "estadistico_Ljung_Box":
                    prueba.loc[lag, "lb_stat"],

                "p_valor": p_valor,

                "conclusion": conclusion

            })

        # Gráfico temporal de residuos.

        fechas = serie.index[
            -len(residuos):
        ].to_timestamp()

        axes[i, 0].plot(
            fechas,
            residuos,
            linewidth=0.8
        )

        axes[i, 0].axhline(
            0,
            color="gray",
            linestyle="--"
        )

        axes[i, 0].set_title(
            f"Residuos estandarizados\n{nombre}"
        )

        axes[i, 0].set_ylabel("Residuo")

        # ACF de residuos.

        plot_acf(
            residuos,
            lags=REZAGOS_GRAFICOS,
            zero=False,
            alpha=0.05,
            ax=axes[i, 1]
        )

        axes[i, 1].set_title(
            f"ACF de residuos\n{nombre}"
        )

        axes[i, 1].set_xlabel("Rezago mensual")

    fig.tight_layout()

    fig.savefig(
        FIG / "17_diagnostico_residuos_arima.png",
        dpi=170
    )

    plt.close(fig)

    return pd.DataFrame(filas)

# PROGRAMA PRINCIPAL

def main():

    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)

    serie = cargar_serie()

    entrenamiento = serie.loc[
        serie.index < CORTE
    ]

    print("\nDIAGNÓSTICO Y ESPECIFICACIÓN ARIMA")

    print(
        "\nMuestra de entrenamiento:",
        entrenamiento.index.min(),
        "a",
        entrenamiento.index.max()
    )

    print(
        "Observaciones:",
        len(entrenamiento)
    )

    # ACF y PACF utilizando entrenamiento.

    graficar_acf_pacf(entrenamiento)

    # Comparación de especificaciones.

    tabla = comparar_modelos(entrenamiento)

    tabla.to_csv(
        OUT / "comparacion_especificaciones_arima.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nCOMPARACIÓN DE ESPECIFICACIONES")

    columnas = [

        "modelo",

        "convergio",

        "AIC",

        "BIC",

        "Ljung_Box_p6",

        "Ljung_Box_p12",

        "Ljung_Box_p24"

    ]

    print(
        tabla[columnas].to_string(
            index=False,
            float_format=lambda x: f"{x:.6g}"
        )
    )

    validos = tabla.loc[
        tabla["convergio"]
        & np.isfinite(tabla["AIC"])
        & np.isfinite(tabla["BIC"])
    ]

    if validos.empty:

        raise RuntimeError(
            "Ningún candidato convergió correctamente."
        )

    print("\nMODELO CON MENOR AIC")

    print(
        validos.loc[
            validos["AIC"].idxmin(),
            columnas
        ].to_string()
    )

    print("\nMODELO CON MENOR BIC")

    print(
        validos.loc[
            validos["BIC"].idxmin(),
            columnas
        ].to_string()
    )

    # Diagnóstico específico del ARIMA actual.

    diagnostico = diagnosticar_referencia(
        entrenamiento,
        serie
    )

    diagnostico.to_csv(
        OUT / "diagnostico_residuos_arima.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nARCHIVOS GENERADOS")

    print("graficos/14_acf_desempleo.png")
    print("graficos/15_pacf_desempleo.png")
    print("graficos/17_diagnostico_residuos_arima.png")

    print(
        "resultados/"
        "comparacion_especificaciones_arima.csv"
    )

    print(
        "resultados/"
        "diagnostico_residuos_arima.csv"
    )

    print("\nDIAGNÓSTICO FINALIZADO.")

    print(
        "La comparación de especificaciones se "
        "realiza exclusivamente con entrenamiento."
    )

    print(
        "El diagnóstico sobre la muestra completa "
        "es descriptivo."
    )

    print(
        "No se modifica automáticamente "
        "el modelo de pronóstico."
    )


if __name__ == "__main__":
    main()
