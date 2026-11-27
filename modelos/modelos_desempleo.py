
"""
Modelación y proyección de la tasa de desempleo en Chile.

Se reutiliza la evaluación comparativa a un mes.

Modelo econométrico seleccionado: ARIMA(0,1,2).
Referencia principal a 12 meses: benchmark ingenuo.
Modelo econométrico original: ARIMA(1,1,1).

Se generan pronósticos e intervalos de predicción
del 95% para las distintas especificaciones.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA

from evaluacion_comparativa import (
    evaluar_modelos,
    cargar_configuracion
)



# CONFIGURACIÓN


ROOT = Path(__file__).resolve().parent.parent

OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

HORIZONTE = 12

ORDEN_ARIMA = (0, 1, 2)
ORDEN_ORIGINAL = (1, 1, 1)

ALPHA_INTERVALO = 0.05



# ESTIMACIÓN ARIMA CON CONTROL DE CONVERGENCIA


def estimar_arima(serie, orden):

    optimizadores = [
        ("lbfgs", 200),
        ("powell", 1000)
    ]

    for metodo, iteraciones in optimizadores:

        ajuste = ARIMA(
            serie.astype(float),
            order=orden
        ).fit(
            method="statespace",
            method_kwargs={
                "method": metodo,
                "maxiter": iteraciones,
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
                f"ARIMA{orden}: convergió "
                f"mediante {metodo}"
            )

            return ajuste

        print(
            f"ARIMA{orden}: "
            f"sin convergencia mediante {metodo}"
        )

    raise RuntimeError(
        f"No se obtuvo convergencia en ARIMA{orden}"
    )



# OBTENER PRONÓSTICOS E INTERVALOS


def obtener_pronostico(ajuste):

    fc = ajuste.get_forecast(
        steps=HORIZONTE
    )

    media = np.asarray(
        fc.predicted_mean,
        dtype=float
    )

    intervalos = np.asarray(
        fc.conf_int(alpha=ALPHA_INTERVALO),
        dtype=float
    )

    return (
        media,
        intervalos[:, 0],
        intervalos[:, 1]
    )



# PROYECCIÓN A 12 MESES


def proyectar_desempleo(y):

    # Estimar el modelo econométrico seleccionado.

    ajuste_nuevo = estimar_arima(
        y,
        ORDEN_ARIMA
    )

    nuevo, inferior_nuevo, superior_nuevo = (
        obtener_pronostico(ajuste_nuevo)
    )

    # Conservar la especificación original.

    ajuste_original = estimar_arima(
        y,
        ORDEN_ORIGINAL
    )

    original, inferior_original, superior_original = (
        obtener_pronostico(ajuste_original)
    )


    # BENCHMARK INGENUO


    # El pronóstico puntual corresponde al último
    # valor observado de la tasa de desempleo.

    benchmark = np.repeat(
        float(y.iloc[-1]),
        HORIZONTE
    )

    # Intervalos bajo el supuesto de caminata
    # aleatoria sin deriva, con innovaciones
    # independientes y aproximadamente normales.

    diferencias = y.diff().dropna().to_numpy()

    sigma = np.sqrt(
        np.mean(diferencias ** 2)
    )

    horizontes = np.arange(
        1, HORIZONTE + 1
    )

    amplitud = (
        1.95996398454
        * sigma
        * np.sqrt(horizontes)
    )

    inferior_benchmark = benchmark - amplitud

    superior_benchmark = benchmark + amplitud


    # CONSTRUIR TABLA DE PROYECCIÓN


    futuro = pd.period_range(
        y.index[-1] + 1,
        periods=HORIZONTE,
        freq="M"
    )

    pronostico = pd.DataFrame({

        "mes": futuro.astype(str),

        # Mantener las columnas originales para
        # conservar compatibilidad con el proyecto.

        "pronostico_ARIMA_111": original,

        "limite_inferior_95": inferior_original,

        "limite_superior_95": superior_original,

        "benchmark_ingenuo": benchmark,

        # Nuevo modelo econométrico.

        "pronostico_ARIMA_012": nuevo,

        "limite_inferior_ARIMA_012_95":
            inferior_nuevo,

        "limite_superior_ARIMA_012_95":
            superior_nuevo,

        # Intervalos del benchmark.

        "limite_inferior_benchmark_95":
            inferior_benchmark,

        "limite_superior_benchmark_95":
            superior_benchmark

    })


    # VALIDACIÓN DE RESULTADOS


    if len(pronostico) != HORIZONTE:

        raise ValueError(
            "Horizonte de pronóstico incorrecto."
        )

    numericas = pronostico.drop(
        columns="mes"
    ).to_numpy(dtype=float)

    if not np.isfinite(numericas).all():

        raise ValueError(
            "El pronóstico contiene valores inválidos."
        )

    grupos = [

        (
            "pronostico_ARIMA_111",
            "limite_inferior_95",
            "limite_superior_95"
        ),

        (
            "pronostico_ARIMA_012",
            "limite_inferior_ARIMA_012_95",
            "limite_superior_ARIMA_012_95"
        ),

        (
            "benchmark_ingenuo",
            "limite_inferior_benchmark_95",
            "limite_superior_benchmark_95"
        )

    ]

    for media, inferior, superior in grupos:

        validos = (
            (pronostico[inferior] <= pronostico[media])
            &
            (pronostico[media] <= pronostico[superior])
        )

        if not validos.all():

            raise ValueError(
                f"Intervalos inconsistentes: {media}"
            )

    return pronostico, ajuste_nuevo, ajuste_original


# GRÁFICO DE EVALUACIÓN FUERA DE MUESTRA


def graficar_evaluacion(evaluacion):

    fechas = pd.PeriodIndex(
        evaluacion["mes"],
        freq="M"
    ).to_timestamp()

    fig, ax = plt.subplots(
        figsize=(12, 6)
    )

    ax.plot(
        fechas,
        evaluacion["observado"],
        label="Observado",
        color="black",
        linewidth=2.3
    )

    ax.plot(
        fechas,
        evaluacion["ARIMA_012"],
        label="ARIMA(0,1,2)",
        color="tab:blue",
        linewidth=2
    )

    ax.plot(
        fechas,
        evaluacion["ARIMA_111"],
        label="ARIMA(1,1,1)",
        linestyle="-.",
        color="tab:orange"
    )

    ax.plot(
        fechas,
        evaluacion["benchmark_ingenuo"],
        label="Benchmark ingenuo",
        linestyle="--",
        color="tab:green"
    )

    ax.plot(
        fechas,
        evaluacion["Ridge_mejorado"],
        label="Ridge",
        linestyle=":",
        color="tab:red"
    )

    ax.set(
        title=(
            "Chile: evaluación fuera de muestra "
            "a un mes"
        ),
        xlabel="Mes",
        ylabel="Tasa de desempleo (%)"
    )

    ax.grid(alpha=0.25)

    ax.legend(ncol=2)

    fig.tight_layout()

    fig.savefig(
        FIG / "12_evaluacion_modelos.png",
        dpi=170
    )

    plt.close(fig)



# GRÁFICO DE PROYECCIÓN


def graficar_pronostico(y, pronostico):

    historia = y.iloc[-60:]

    fechas_historia = (
        historia.index.to_timestamp()
    )

    fechas_futuras = pd.PeriodIndex(
        pronostico["mes"],
        freq="M"
    ).to_timestamp()

    fig, ax = plt.subplots(
        figsize=(12, 6)
    )

    # Serie histórica.

    ax.plot(
        fechas_historia,
        historia.to_numpy(),
        label="Desempleo observado",
        color="black",
        linewidth=2.2
    )

    # Benchmark: referencia principal a 12 meses.

    ax.plot(
        fechas_futuras,
        pronostico["benchmark_ingenuo"],
        color="tab:green",
        linestyle="--",
        linewidth=2.3,
        label="Benchmark ingenuo"
    )

    ax.fill_between(

        fechas_futuras,

        pronostico["limite_inferior_benchmark_95"]
        .to_numpy(dtype=float),

        pronostico["limite_superior_benchmark_95"]
        .to_numpy(dtype=float),

        color="tab:green",

        alpha=0.12,

        label="Intervalo benchmark 95%"

    )

    # Alternativa econométrica seleccionada.

    ax.plot(
        fechas_futuras,
        pronostico["pronostico_ARIMA_012"],
        color="tab:blue",
        linewidth=2,
        label="ARIMA(0,1,2)"
    )

    ax.fill_between(

        fechas_futuras,

        pronostico["limite_inferior_ARIMA_012_95"]
        .to_numpy(dtype=float),

        pronostico["limite_superior_ARIMA_012_95"]
        .to_numpy(dtype=float),

        color="tab:blue",

        alpha=0.15,

        label="Intervalo ARIMA 95%"

    )

    ax.axvline(
        fechas_historia[-1],
        color="gray",
        linestyle=":",
        linewidth=1.2
    )

    ax.set(
        title=(
            "Chile: proyección de la tasa "
            "de desempleo a 12 meses"
        ),
        xlabel="Mes",
        ylabel="Tasa de desempleo (%)"
    )

    ax.grid(alpha=0.25)

    ax.legend(ncol=2)

    fig.tight_layout()

    fig.savefig(
        FIG / "13_pronostico_12_meses.png",
        dpi=170
    )

    plt.close(fig)


# PROGRAMA PRINCIPAL


def main():

    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)

    # Reutilizar la evaluación comparativa.

    evaluacion, metricas, y = evaluar_modelos()

    nombre, alpha, lag, columnas = (
        cargar_configuracion()
    )

    # Verificar convergencia de ambos ARIMA.

    fallos_original = int(
        (~evaluacion["arima_convergio"]).sum()
    )

    fallos_nuevo = int(
        (~evaluacion["arima_012_convergio"]).sum()
    )

    if fallos_original + fallos_nuevo > 0:

        raise RuntimeError(
            "Existen ajustes sin convergencia."
        )

    # Estimar y proyectar ambos ARIMA.

    pronostico, ajuste_nuevo, ajuste_original = (
        proyectar_desempleo(y)
    )


    # EXPORTACIÓN DE RESULTADOS


    for archivo in [

        "predicciones_oos_modelos.csv",

        "evaluacion_comparativa_temporal.csv"

    ]:

        evaluacion.to_csv(
            OUT / archivo,
            index=False,
            encoding="utf-8-sig"
        )

    metricas.to_csv(

        OUT / "metricas_comparacion_temporal.csv",

        index=False,

        encoding="utf-8-sig"

    )

    metricas.rename(columns={

        "RMSE": "RMSE_pp",

        "MAE": "MAE_pp"

    }).to_csv(

        OUT / "metricas_modelos.csv",

        index=False,

        encoding="utf-8-sig"

    )

    pronostico.to_csv(

        OUT / "pronostico_desempleo_12m.csv",

        index=False,

        encoding="utf-8-sig"

    )


    # GENERACIÓN DE GRÁFICOS


    graficar_evaluacion(evaluacion)

    graficar_pronostico(y, pronostico)


    # PRESENTACIÓN DE RESULTADOS


    print("\nEVALUACIÓN FUERA DE MUESTRA A UN MES")

    print(
        metricas.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\nCONFIGURACIÓN RIDGE")

    print(f"Predictores: {nombre}")
    print(f"Alpha: {alpha}")
    print(f"Rezago IMACEC: {lag} meses")

    print("\nSERIE OBJETIVO")

    print(f"Inicio: {y.index.min()}")
    print(f"Término: {y.index.max()}")
    print(f"Observaciones: {len(y)}")

    print(
        f"Último dato observado: {y.iloc[-1]:.4f}%"
    )

    print("\nDIAGNÓSTICO DE CONVERGENCIA")

    print(
        f"ARIMA(1,1,1) sin convergencia: "
        f"{fallos_original}"
    )

    print(
        f"ARIMA(0,1,2) sin convergencia: "
        f"{fallos_nuevo}"
    )

    print("\nMODELO ECONOMÉTRICO SELECCIONADO")

    print(f"ARIMA{ORDEN_ARIMA}")

    print(f"AIC: {ajuste_nuevo.aic:.4f}")

    print(f"BIC: {ajuste_nuevo.bic:.4f}")

    print("\nCoeficientes estimados:")

    print(ajuste_nuevo.params.to_string())

    print("\nP-valores de los coeficientes:")

    print(ajuste_nuevo.pvalues.to_string())

    print("\nPROYECCIÓN A 12 MESES")

    columnas_resumen = [

        "mes",

        "benchmark_ingenuo",

        "pronostico_ARIMA_012",

        "limite_inferior_ARIMA_012_95",

        "limite_superior_ARIMA_012_95"

    ]

    print(

        pronostico[columnas_resumen].to_string(

            index=False,

            float_format=lambda x: f"{x:.4f}"

        )

    )

    ultimo = pronostico.iloc[-1]

    print("\nRESUMEN DEL PRONÓSTICO")

    print(f"Mes proyectado: {ultimo['mes']}")

    print("\nBENCHMARK INGENUO")

    print(
        f"Tasa proyectada: "
        f"{ultimo['benchmark_ingenuo']:.4f}%"
    )

    print(
        f"Intervalo inferior 95%: "
        f"{ultimo['limite_inferior_benchmark_95']:.4f}%"
    )

    print(
        f"Intervalo superior 95%: "
        f"{ultimo['limite_superior_benchmark_95']:.4f}%"
    )

    print("\nARIMA(0,1,2)")

    print(
        f"Tasa proyectada: "
        f"{ultimo['pronostico_ARIMA_012']:.4f}%"
    )

    print(
        f"Intervalo inferior 95%: "
        f"{ultimo['limite_inferior_ARIMA_012_95']:.4f}%"
    )

    print(
        f"Intervalo superior 95%: "
        f"{ultimo['limite_superior_ARIMA_012_95']:.4f}%"
    )

    print("\nARIMA(1,1,1) ORIGINAL")

    print(
        f"Tasa proyectada: "
        f"{ultimo['pronostico_ARIMA_111']:.4f}%"
    )

    print("\nARCHIVOS GENERADOS")

    print("resultados/predicciones_oos_modelos.csv")

    print("resultados/metricas_modelos.csv")

    print("resultados/evaluacion_comparativa_temporal.csv")

    print("resultados/metricas_comparacion_temporal.csv")

    print("resultados/pronostico_desempleo_12m.csv")

    print("graficos/12_evaluacion_modelos.png")

    print("graficos/13_pronostico_12_meses.png")

    print("\nMODELACIÓN FINALIZADA.")

    print(

        "El benchmark obtuvo el menor RMSE "
        "en la evaluación retrospectiva a 12 meses."

    )

    print(

        "ARIMA(0,1,2) se mantiene como alternativa "
        "econométrica y obtuvo el menor RMSE a un mes."

    )

    print(

        "Los intervalos del benchmark suponen una "
        "caminata aleatoria sin deriva."

    )

    print(

        "La evaluación utiliza datos históricos "
        "disponibles actualmente y no corresponde "
        "a un test completamente inexplorado."

    )


if __name__ == "__main__":
    main()
