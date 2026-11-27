
"""
Diagnóstico final del modelo ARIMA(0,1,2).

Se analiza la muestra de entrenamiento y la muestra
completa mediante:

- Significancia de los coeficientes.
- Criterios de información AIC y BIC.
- Invertibilidad del componente MA.
- Prueba Ljung-Box.
- Gráficos de residuos estandarizados.
- ACF de los residuos.

Se reutilizan las funciones existentes del proyecto.
"""

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from statsmodels.graphics.tsaplots import plot_acf

from estacionariedad_desempleo import (
    cargar_serie,
    CORTE
)

from modelos_desempleo import (
    estimar_arima,
    ORDEN_ARIMA,
    OUT,
    FIG
)

from acf_pacf_desempleo import (
    diagnosticar_residuos,
    REZAGOS_LJUNG_BOX
)



# CONFIGURACIÓN


SIGNIFICANCIA = 0.05

REZAGOS_GRAFICO = 36


# PROGRAMA PRINCIPAL


def main():

    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)

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

    coeficientes = []

    fig, axes = plt.subplots(
        2, 2,
        figsize=(13, 8)
    )

    print("\nDIAGNÓSTICO FINAL ARIMA")

    print(f"Especificación: {ORDEN_ARIMA}")


    # ESTIMACIÓN Y DIAGNÓSTICO


    for i, (nombre, datos) in enumerate(
        muestras.items()
    ):

        print("\n" + "=" * 60)

        print(nombre.upper())

        print("=" * 60)

        print(
            f"Período: {datos.index.min()} "
            f"a {datos.index.max()}"
        )

        print(
            f"Observaciones: {len(datos)}"
        )

        # Reutilizar el procedimiento de estimación
        # con control de convergencia.

        ajuste = estimar_arima(
            datos,
            ORDEN_ARIMA
        )

        # Reutilizar el diagnóstico de residuos
        # previamente implementado.

        residuos, prueba = diagnosticar_residuos(

            ajuste,

            ORDEN_ARIMA,

            (0, 0, 0, 0)

        )


        # INVERTIBILIDAD


        raices = np.abs(
            ajuste.maroots
        )

        invertible = bool(
            np.isfinite(raices).all()
            and (raices > 1).all()
        )

        print(f"\nAIC: {ajuste.aic:.4f}")

        print(f"BIC: {ajuste.bic:.4f}")

        print(
            "Módulo de las raíces MA:",
            raices
        )

        print(
            f"Componente MA invertible: {invertible}"
        )


        # COEFICIENTES ESTIMADOS


        print("\nCOEFICIENTES ESTIMADOS")

        tabla_coef = pd.DataFrame({

            "coeficiente": ajuste.params,

            "error_estandar": ajuste.bse,

            "p_valor": ajuste.pvalues

        })

        print(
            tabla_coef.to_string()
        )

        for parametro, fila in tabla_coef.iterrows():

            coeficientes.append({

                "muestra": nombre,

                "modelo": "ARIMA(0,1,2)",

                "parametro": parametro,

                "coeficiente":
                    fila["coeficiente"],

                "error_estandar":
                    fila["error_estandar"],

                "p_valor":
                    fila["p_valor"]

            })


        # PRUEBA LJUNG-BOX


        print("\nPRUEBA LJUNG-BOX")

        print(
            prueba.to_string()
        )

        if not np.isfinite(
            prueba["lb_pvalue"]
        ).all():

            raise ValueError(
                "P-valores Ljung-Box inválidos."
            )

        for lag in REZAGOS_LJUNG_BOX:

            p_valor = float(
                prueba.loc[lag, "lb_pvalue"]
            )

            rechazo = p_valor < SIGNIFICANCIA

            if rechazo:

                conclusion = (
                    "Se rechaza ausencia "
                    "de autocorrelación"
                )

            else:

                conclusion = (
                    "No se rechaza ausencia "
                    "de autocorrelación"
                )

            resultados.append({

                "muestra": nombre,

                "modelo": "ARIMA(0,1,2)",

                "observaciones": len(datos),

                "observaciones_residuos":
                    len(residuos),

                "convergio": True,

                "invertible": invertible,

                "AIC": ajuste.aic,

                "BIC": ajuste.bic,

                "rezago": lag,

                "estadistico_Ljung_Box":
                    prueba.loc[lag, "lb_stat"],

                "p_valor": p_valor,

                "rechaza_h0": rechazo,

                "conclusion": conclusion

            })


        # GRÁFICO TEMPORAL DE RESIDUOS


        fechas = datos.index[
            -len(residuos):
        ].to_timestamp()

        axes[i, 0].plot(

            fechas,

            residuos,

            linewidth=0.9

        )

        axes[i, 0].axhline(

            0,

            color="gray",

            linestyle="--"

        )

        axes[i, 0].set_title(
            f"Residuos estandarizados\n{nombre}"
        )

        axes[i, 0].set_ylabel(
            "Residuo estandarizado"
        )

        axes[i, 0].grid(alpha=0.20)


        # ACF DE LOS RESIDUOS


        plot_acf(

            residuos,

            lags=REZAGOS_GRAFICO,

            zero=False,

            alpha=0.05,

            ax=axes[i, 1]

        )

        axes[i, 1].set_title(
            f"ACF de residuos\n{nombre}"
        )

        axes[i, 1].set_xlabel(
            "Rezago mensual"
        )

        axes[i, 1].axvline(
            12,
            color="gray",
            linestyle="--"
        )

        axes[i, 1].axvline(
            24,
            color="gray",
            linestyle="--"
        )


    # EXPORTACIÓN DE RESULTADOS


    tabla = pd.DataFrame(resultados)

    tabla_coeficientes = pd.DataFrame(
        coeficientes
    )

    tabla.to_csv(

        OUT / "diagnostico_residuos_arima_012.csv",

        index=False,

        encoding="utf-8-sig"

    )

    tabla_coeficientes.to_csv(

        OUT / "coeficientes_arima_012.csv",

        index=False,

        encoding="utf-8-sig"

    )

    fig.suptitle(
        "Diagnóstico residual del ARIMA(0,1,2)"
    )

    fig.tight_layout()

    fig.savefig(

        FIG / "19_diagnostico_residuos_arima_012.png",

        dpi=170

    )

    plt.close(fig)


    # RESUMEN FINAL

    print("\nRESUMEN DEL DIAGNÓSTICO")

    columnas = [

        "muestra",

        "invertible",

        "rezago",

        "p_valor",

        "rechaza_h0"

    ]

    print(

        tabla[columnas].to_string(

            index=False,

            float_format=lambda x: f"{x:.6g}"

        )

    )

    print("\nINTERPRETACIÓN POR MUESTRA")

    for nombre, grupo in tabla.groupby(
        "muestra"
    ):

        if grupo["rechaza_h0"].any():

            print(

                f"{nombre}: existe evidencia "
                "de autocorrelación residual "
                "en al menos un rezago evaluado."

            )

        else:

            print(

                f"{nombre}: no se rechaza "
                "la ausencia de autocorrelación "
                "en los rezagos evaluados."

            )

    print("\nARCHIVOS GENERADOS")

    print(
        "resultados/"
        "diagnostico_residuos_arima_012.csv"
    )

    print(
        "resultados/coeficientes_arima_012.csv"
    )

    print(
        "graficos/"
        "19_diagnostico_residuos_arima_012.png"
    )

    print("\nDIAGNÓSTICO FINALIZADO.")

    print(

        "No rechazar la hipótesis nula de Ljung-Box "
        "no demuestra que los residuos sean "
        "perfectamente ruido blanco."

    )

    print(

        "El diagnóstico de la muestra completa "
        "tiene carácter descriptivo."

    )


if __name__ == "__main__":
    main()
