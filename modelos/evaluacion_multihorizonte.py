
"""
Evaluación predictiva a distintos horizontes.

Se comparan:
- Benchmark ingenuo.
- ARIMA(1,1,1): modelo original.
- ARIMA(0,1,2): candidato seleccionado mediante BIC
  y diagnóstico de residuos en entrenamiento.

Horizontes de evaluación: 1, 3, 6 y 12 meses.

Se utiliza una ventana expansiva de entrenamiento.
Los modelos se comparan sobre los mismos orígenes
y fechas objetivo dentro de cada horizonte.

La evaluación es retrospectiva y utiliza las series
históricas disponibles actualmente.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA

from estacionariedad_desempleo import (
    cargar_serie,
    CORTE
)


# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent

OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

HORIZONTES = [1, 3, 6, 12]

MODELOS = {

    "ARIMA(1,1,1)": (1, 1, 1),

    "ARIMA(0,1,2)": (0, 1, 2)

}


# EVALUACIÓN MULTIHORIZONTE

def evaluar_multihorizonte(serie):

    registros = []

    ajustes = []

    # El primer origen corresponde a diciembre
    # de 2023, antes del período de evaluación.

    origen_inicial = CORTE - 1

    origen_final = serie.index.max() - 1

    origenes = pd.period_range(

        origen_inicial,

        origen_final,

        freq="M"

    )

    for origen in origenes:

        entrenamiento = serie.loc[
            serie.index <= origen
        ]

        # Evaluar únicamente horizontes para los
        # cuales existe un valor observado.

        horizontes_validos = [

            h for h in HORIZONTES

            if origen + h <= serie.index.max()

        ]

        if not horizontes_validos:
            continue

        max_h = max(horizontes_validos)

        print(f"Evaluando origen: {origen}")


        # BENCHMARK INGENUO

        predicciones = {

            "Benchmark ingenuo": np.repeat(

                float(entrenamiento.iloc[-1]),

                max_h

            )

        }

        # MODELOS ARIMA

        # Cada modelo se estima una sola vez
        # por origen de pronóstico.

        for nombre, orden in MODELOS.items():

                        # Primera estimación: optimizador L-BFGS.
            optimizador = "lbfgs"

            ajuste = ARIMA(
                entrenamiento,
                order=orden
            ).fit(
                method="statespace",
                method_kwargs={
                    "method": "lbfgs",
                    "maxiter": 200,
                    "disp": False
                }
            )

            convergio = (
                bool(
                    ajuste.mle_retvals.get(
                        "converged", False
                    )
                )
                and np.isfinite(ajuste.llf)
                and np.isfinite(ajuste.params).all()
            )

            # Si la primera estimación falla,
            # utilizar el optimizador alternativo Powell.
            if not convergio:

                print(
                    f"Reintentando {nombre} en "
                    f"{origen} mediante Powell..."
                )

                optimizador = "powell"

                ajuste = ARIMA(
                    entrenamiento,
                    order=orden
                ).fit(
                    method="statespace",
                    method_kwargs={
                        "method": "powell",
                        "maxiter": 1000,
                        "disp": False
                    }
                )

                convergio = (
                    bool(
                        ajuste.mle_retvals.get(
                            "converged", False
                        )
                    )
                    and np.isfinite(ajuste.llf)
                    and np.isfinite(ajuste.params).all()
                )

                if convergio:
                    print(
                        "Convergencia recuperada "
                        "correctamente."
                    )

            ajustes.append({

                "origen": str(origen),

                "modelo": nombre,

                "convergio": convergio,

                "optimizador": optimizador,

                "observaciones_entrenamiento":
                    len(entrenamiento)

            })

            if not convergio:

                print(
                    f"ADVERTENCIA: {nombre} "
                    f"no convergió en {origen}"
                )

            predicciones[nombre] = np.asarray(

                ajuste.forecast(steps=max_h),

                dtype=float

            )

        # REGISTRAR PRONÓSTICOS

        for h in horizontes_validos:

            fecha_objetivo = origen + h

            observado = float(
                serie.loc[fecha_objetivo]
            )

            for nombre, valores in predicciones.items():

                pronostico = float(
                    valores[h - 1]
                )

                if not np.isfinite(pronostico):

                    raise ValueError(

                        f"Pronóstico inválido: "
                        f"{nombre}, {origen}, h={h}"

                    )

                error = pronostico - observado

                registros.append({

                    "origen": str(origen),

                    "mes_objetivo": str(
                        fecha_objetivo
                    ),

                    "horizonte_meses": h,

                    "modelo": nombre,

                    "observado": observado,

                    "pronostico": pronostico,

                    "error": error

                })

    evaluacion = pd.DataFrame(registros)

    convergencia = pd.DataFrame(ajustes)

    return evaluacion, convergencia


# VALIDAR COMPARABILIDAD

def validar_evaluacion(evaluacion):

    nombres = [
        "Benchmark ingenuo"
    ] + list(MODELOS)

    for h in HORIZONTES:

        sub = evaluacion.loc[
            evaluacion["horizonte_meses"] == h
        ]

        referencia = sub.loc[

            sub["modelo"] == "Benchmark ingenuo",

            ["origen", "mes_objetivo"]

        ].reset_index(drop=True)

        if referencia.empty:

            raise ValueError(
                f"No existen pronósticos para h={h}"
            )

        for nombre in nombres:

            fechas = sub.loc[

                sub["modelo"] == nombre,

                ["origen", "mes_objetivo"]

            ].reset_index(drop=True)

            if not fechas.equals(referencia):

                raise ValueError(

                    f"Muestras diferentes en "
                    f"{nombre}, horizonte {h}"

                )

    print(
        "\nComparabilidad de muestras: correcta"
    )


# MÉTRICAS DE EVALUACIÓN

def calcular_metricas(evaluacion):

    filas = []

    grupos = evaluacion.groupby([

        "horizonte_meses",

        "modelo"

    ])

    for (h, modelo), grupo in grupos:

        error = grupo["error"].to_numpy()

        filas.append({

            "horizonte_meses": h,

            "modelo": modelo,

            "n_pronosticos": len(grupo),

            "RMSE": np.sqrt(
                np.mean(error ** 2)
            ),

            "MAE": np.mean(
                np.abs(error)
            ),

            "sesgo": np.mean(error)

        })

    metricas = pd.DataFrame(filas)

    # Calcular la mejora del RMSE respecto
    # del benchmark para cada horizonte.

    referencia = metricas.loc[

        metricas["modelo"]
        == "Benchmark ingenuo",

        ["horizonte_meses", "RMSE"]

    ].rename(columns={

        "RMSE": "RMSE_benchmark"

    })

    metricas = metricas.merge(

        referencia,

        on="horizonte_meses",

        validate="many_to_one"

    )

    metricas["mejora_RMSE_pct"] = np.where(

        metricas["RMSE_benchmark"] > 0,

        100 * (

            1 - metricas["RMSE"]

            / metricas["RMSE_benchmark"]

        ),

        np.nan

    )

    return metricas.sort_values([

        "horizonte_meses",

        "RMSE"

    ]).reset_index(drop=True)


# GRÁFICO DE RESULTADOS

def graficar_metricas(metricas):

    fig, axes = plt.subplots(

        1, 2,

        figsize=(13, 5)

    )

    for ax, metrica in zip(

        axes,

        ["RMSE", "MAE"]

    ):

        for nombre, grupo in metricas.groupby(
            "modelo"
        ):

            grupo = grupo.sort_values(
                "horizonte_meses"
            )

            ax.plot(

                grupo["horizonte_meses"],

                grupo[metrica],

                marker="o",

                linewidth=2,

                label=nombre

            )

        ax.set_title(

            f"{metrica} por horizonte"

        )

        ax.set_xlabel(
            "Horizonte de pronóstico (meses)"
        )

        ax.set_ylabel(
            f"{metrica} (puntos porcentuales)"
        )

        ax.set_xticks(HORIZONTES)

        ax.grid(alpha=0.25)

        ax.legend()

    fig.suptitle(

        "Chile: evaluación predictiva "
        "de la tasa de desempleo"

    )

    fig.tight_layout()

    fig.savefig(

        FIG / "18_evaluacion_multihorizonte.png",

        dpi=170

    )

    plt.close(fig)


# PROGRAMA PRINCIPAL

def main():

    OUT.mkdir(exist_ok=True)

    FIG.mkdir(exist_ok=True)

    serie = cargar_serie()

    print("\nEVALUACIÓN MULTIHORIZONTE")

    print(
        f"Serie: {serie.index.min()} "
        f"a {serie.index.max()}"
    )

    print(
        f"Observaciones: {len(serie)}"
    )

    print(
        f"Primer origen: {CORTE - 1}"
    )

    print(
        f"Horizontes: {HORIZONTES}"
    )

    evaluacion, convergencia = (
        evaluar_multihorizonte(serie)
    )

    validar_evaluacion(evaluacion)

    # Guardar el diagnóstico de convergencia.

    convergencia.to_csv(

        OUT / "convergencia_multihorizonte.csv",

        index=False,

        encoding="utf-8-sig"

    )

    fallos = convergencia.loc[
        ~convergencia["convergio"]
    ]

    print("\nDIAGNÓSTICO DE CONVERGENCIA")

    print(
        f"Ajustes realizados: {len(convergencia)}"
    )

    print(
        f"Ajustes sin convergencia: {len(fallos)}"
    )

    # No presentar resultados como válidos
    # si existen estimaciones sin convergencia.

    if not fallos.empty:

        print(fallos.to_string(index=False))

        raise RuntimeError(

            "Revisar problemas de convergencia "
            "antes de exportar las métricas."

        )

    metricas = calcular_metricas(evaluacion)

    # EXPORTACIÓN

    evaluacion.to_csv(

        OUT / "predicciones_multihorizonte.csv",

        index=False,

        encoding="utf-8-sig"

    )

    metricas.to_csv(

        OUT / "metricas_multihorizonte.csv",

        index=False,

        encoding="utf-8-sig"

    )

    graficar_metricas(metricas)

    # ==================================================
    # PRESENTACIÓN DE RESULTADOS
    # ==================================================

    print("\nRESULTADOS POR HORIZONTE")

    print(

        metricas.to_string(

            index=False,

            float_format=lambda x: f"{x:.4f}"

        )

    )

    print("\nEVALUACIÓN A 12 MESES")

    print(

        metricas.loc[

            metricas["horizonte_meses"] == 12

        ].to_string(

            index=False,

            float_format=lambda x: f"{x:.4f}"

        )

    )

    print("\nARCHIVOS GENERADOS")

    print(
        "resultados/predicciones_multihorizonte.csv"
    )

    print(
        "resultados/metricas_multihorizonte.csv"
    )

    print(
        "resultados/convergencia_multihorizonte.csv"
    )

    print(
        "graficos/18_evaluacion_multihorizonte.png"
    )

    print("\nEVALUACIÓN FINALIZADA.")

    print(

        "La selección del candidato ARIMA(0,1,2) "
        "se fundamenta en el diagnóstico previo "
        "sobre la muestra de entrenamiento."

    )

    print(

        "La evaluación es retrospectiva y no "
        "constituye un test completamente inexplorado "
        "ni una evaluación con datos en tiempo real."

    )

    print(

        "No se modifica automáticamente "
        "el modelo de proyección."

    )


if __name__ == "__main__":
    main()
