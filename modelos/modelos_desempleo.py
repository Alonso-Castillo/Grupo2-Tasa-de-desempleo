
"""
Modelación y proyección de la tasa de desempleo en Chile.

Este script reutiliza la evaluación comparativa de modelos
para evitar duplicar procedimientos y generar resultados
inconsistentes.

Modelos evaluados:
- Benchmark ingenuo.
- ARIMA(1,1,1).
- Ridge con configuración seleccionada mediante
  validación temporal interna.

Se genera una proyección ARIMA a 12 meses con intervalos
de predicción del 95%.

La selección definitiva del modelo para el horizonte
de 12 meses requiere una evaluación adicional.
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from statsmodels.tsa.arima.model import ARIMA

# Reutilizar la evaluación ya implementada.
from evaluacion_comparativa import (
    evaluar_modelos,
    cargar_configuracion
)

# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent

OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

HORIZONTE = 12
ORDEN_ARIMA = (1, 1, 1)


# PRONÓSTICO A 12 MESES

def proyectar_desempleo(y):

    # Estimar el modelo utilizando todas las
    # observaciones disponibles de desempleo.
    ajuste = ARIMA(
        y.astype(float),
        order=ORDEN_ARIMA
    ).fit()

    # Verificar convergencia de la estimación final.
    convergio = bool(
        ajuste.mle_retvals.get(
            "converged", False
        )
    )

    if not convergio:
        raise RuntimeError(
            "El modelo ARIMA final no convergió."
        )

    # Generar pronósticos e intervalos del 95%.
    fc = ajuste.get_forecast(
        steps=HORIZONTE
    )

    intervalos = fc.conf_int(
        alpha=0.05
    )

    futuro = pd.period_range(
        y.index[-1] + 1,
        periods=HORIZONTE,
        freq="M"
    )

    pronostico = pd.DataFrame({

        "mes": futuro.astype(str),

        "pronostico_ARIMA_111": np.asarray(
            fc.predicted_mean,
            dtype=float
        ),

        "limite_inferior_95": (
            intervalos.iloc[:, 0]
            .to_numpy(dtype=float)
        ),

        "limite_superior_95": (
            intervalos.iloc[:, 1]
            .to_numpy(dtype=float)
        ),

        "benchmark_ingenuo": float(
            y.iloc[-1]
        )

    })

    # VALIDACIÓN DEL PRONÓSTICO

    if len(pronostico) != HORIZONTE:
        raise ValueError(
            "Horizonte de pronóstico incorrecto."
        )

    columnas_numericas = [
        "pronostico_ARIMA_111",
        "limite_inferior_95",
        "limite_superior_95",
        "benchmark_ingenuo"
    ]

    if not np.isfinite(
        pronostico[columnas_numericas]
        .to_numpy()
    ).all():

        raise ValueError(
            "El pronóstico contiene valores inválidos."
        )

    if not (
        (
            pronostico["limite_inferior_95"]
            <= pronostico["pronostico_ARIMA_111"]
        )
        &
        (
            pronostico["pronostico_ARIMA_111"]
            <= pronostico["limite_superior_95"]
        )
    ).all():

        raise ValueError(
            "Intervalos de predicción inconsistentes."
        )

    return pronostico, ajuste


# GRÁFICO DE EVALUACIÓN FUERA DE MUESTRA

def graficar_evaluacion(evaluacion):

    fechas = pd.PeriodIndex(
        evaluacion["mes"],
        freq="M"
    ).to_timestamp()

    fig, ax = plt.subplots(
        figsize=(12, 5.5)
    )

    ax.plot(
        fechas,
        evaluacion["observado"],
        label="Observado",
        linewidth=2.2
    )

    ax.plot(
        fechas,
        evaluacion["benchmark_ingenuo"],
        label="Benchmark ingenuo",
        linestyle="--"
    )

    ax.plot(
        fechas,
        evaluacion["ARIMA_111"],
        label="ARIMA(1,1,1)",
        linestyle="-."
    )

    ax.plot(
        fechas,
        evaluacion["Ridge_mejorado"],
        label="Ridge",
        linestyle=":"
    )

    ax.set(
        title=(
            "Desempleo en Chile: "
            "evaluación fuera de muestra"
        ),
        xlabel="Mes",
        ylabel="Tasa de desempleo (%)"
    )

    ax.grid(alpha=0.25)
    ax.legend()

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
        figsize=(12, 5.5)
    )

    ax.plot(
        fechas_historia,
        historia.to_numpy(),
        label="Desempleo observado",
        linewidth=2.2
    )

    ax.plot(
        fechas_futuras,
        pronostico["pronostico_ARIMA_111"],
        label="Pronóstico ARIMA(1,1,1)",
        linewidth=2
    )

    ax.fill_between(

        fechas_futuras,

        pronostico["limite_inferior_95"]
        .to_numpy(dtype=float),

        pronostico["limite_superior_95"]
        .to_numpy(dtype=float),

        alpha=0.18,

        label="Intervalo de predicción 95%"
    )

    ax.plot(
        fechas_futuras,
        pronostico["benchmark_ingenuo"],
        linestyle="--",
        label="Benchmark ingenuo"
    )

    ax.axvline(
        fechas_historia[-1],
        linestyle=":",
        color="gray",
        alpha=0.7
    )

    ax.set(
        title=(
            "Chile: proyección de desempleo "
            "a 12 meses"
        ),
        xlabel="Mes",
        ylabel="Tasa de desempleo (%)"
    )

    ax.grid(alpha=0.25)
    ax.legend()

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

    # Verificar que las estimaciones ARIMA convergieron.
    sin_convergencia = int(
        (~evaluacion["arima_convergio"]).sum()
    )

    if sin_convergencia > 0:

        raise RuntimeError(
            f"Existen {sin_convergencia} "
            "estimaciones ARIMA sin convergencia."
        )

    # Generar la proyección a 12 meses.
    pronostico, ajuste = proyectar_desempleo(y)

    # EXPORTAR RESULTADOS CONSISTENTES

    # Mantener ambos archivos de predicciones para
    # conservar la estructura original del repositorio.
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

    # Mantener los nombres de columnas originales
    # del archivo metricas_modelos.csv.
    metricas.rename(columns={

        "RMSE": "RMSE_pp",

        "MAE": "MAE_pp"

    }).to_csv(

        OUT / "metricas_modelos.csv",

        index=False,

        encoding="utf-8-sig"
    )

    # Regenerar el CSV completo del pronóstico.
    pronostico.to_csv(
        OUT / "pronostico_desempleo_12m.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # GENERACIÓN DE GRÁFICOS

    graficar_evaluacion(evaluacion)

    graficar_pronostico(y, pronostico)

    # PRESENTACIÓN DE RESULTADOS

    print("\nEVALUACIÓN FUERA DE MUESTRA")

    print(
        metricas.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\nCONFIGURACIÓN DEFINITIVA DE RIDGE")

    print(f"Predictores: {nombre}")
    print(f"Alpha: {alpha}")
    print(f"Rezago IMACEC: {lag} meses")

    for variable in columnas:
        print("-", variable)

    print("\nSERIE OBJETIVO")

    print(f"Inicio: {y.index.min()}")
    print(f"Término: {y.index.max()}")
    print(f"Observaciones: {len(y)}")

    print(
        f"Último dato observado: "
        f"{y.iloc[-1]:.4f}%"
    )

    print("\nDIAGNÓSTICO DE CONVERGENCIA")

    print(
        f"Ajustes sin convergencia: "
        f"{sin_convergencia}"
    )

    print("Modelo ARIMA final: convergió")

    print("\nMODELO ARIMA FINAL")

    print(f"AIC: {ajuste.aic:.4f}")
    print(f"BIC: {ajuste.bic:.4f}")

    print("\nPROYECCIÓN A 12 MESES")

    print(
        pronostico.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\nRESUMEN DEL PRONÓSTICO")

    ultimo = pronostico.iloc[-1]

    print(
        f"Mes proyectado: {ultimo['mes']}"
    )

    print(
        "Tasa proyectada: "
        f"{ultimo['pronostico_ARIMA_111']:.4f}%"
    )

    print(
        "Intervalo inferior 95%: "
        f"{ultimo['limite_inferior_95']:.4f}%"
    )

    print(
        "Intervalo superior 95%: "
        f"{ultimo['limite_superior_95']:.4f}%"
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
        "Nota: la evaluación utiliza datos históricos "
        "disponibles actualmente. No constituye una "
        "evaluación con datos en tiempo real."
    )

    print(
        "Pendiente: validar la capacidad predictiva "
        "del modelo a 12 meses."
    )


if __name__ == "__main__":
    main()
