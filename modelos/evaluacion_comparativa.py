
"""
Evaluación comparativa de modelos de desempleo.

Modelos evaluados:
- Benchmark ingenuo.
- ARIMA(1,1,1): especificación original.
- ARIMA(0,1,2): especificación seleccionada mediante BIC.
- Ridge: configuración seleccionada mediante validación interna.

Se realiza una evaluación retrospectiva a un mes
mediante ventanas expansivas de entrenamiento.

Se reutiliza la evaluación multihorizonte para
garantizar la consistencia de los resultados.
"""

import sqlite3

import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from optimizar_ridge import (
    DB,
    OUT,
    CORTE,
    MIN_TRAIN,
    TARGET,
    PREDICTORS,
    ALPHAS,
    REZAGOS,
    SQL
)

from evaluacion_multihorizonte import (
    evaluar_multihorizonte,
    validar_evaluacion
)


# CARGA DE DATOS


def cargar_datos():

    if not DB.is_file():
        raise FileNotFoundError(DB)

    with sqlite3.connect(DB) as con:

        raw = pd.read_sql_query(
            SQL,
            con,
            params=[TARGET] + PREDICTORS
        )

    raw["mes"] = pd.to_datetime(
        raw["fecha"]
    ).dt.to_period("M")

    data = raw.pivot(
        index="mes",
        columns="nombre",
        values="valor"
    ).sort_index()

    faltantes = (
        set([TARGET] + PREDICTORS)
        - set(data.columns)
    )

    if faltantes:
        raise ValueError(
            f"Series faltantes: {faltantes}"
        )


    data = data.reindex(
        pd.period_range(
            data.index.min(),
            data.index.max(),
            freq="M"
        )
    )

    return data


# CONFIGURACIÓN ÓPTIMA DE RIDGE


def cargar_configuracion():

    tabla = pd.read_csv(
        OUT / "optimizacion_ridge.csv"
    )

    mejor = tabla.sort_values(
        ["RMSE", "MAE"]
    ).iloc[0]

    nombre = mejor["configuracion"]

    alpha = float(mejor["alpha"])

    lag = int(mejor["rezago_imacec"])

    sets = {

        "Todos los predictores": PREDICTORS,

        "IMACEC e indicadores laborales": [
            PREDICTORS[0],
            PREDICTORS[1],
            PREDICTORS[4]
        ]

    }

    if (
        nombre not in sets
        or alpha not in ALPHAS
        or lag not in REZAGOS
    ):

        raise ValueError(
            "Configuración Ridge incompatible."
        )

    columnas = sets[nombre] + [
        f"imacec_yoy_lag{lag}"
    ]

    return nombre, alpha, lag, columnas


# EVALUACIÓN FUERA DE MUESTRA

def evaluar_modelos():

    data = cargar_datos()

    nombre, alpha, lag, columnas = (
        cargar_configuracion()
    )

    y = data[TARGET].dropna().astype(float)

    if not np.isfinite(y.to_numpy()).all():

        raise ValueError(
            "La serie de desempleo contiene "
            "valores inválidos."
        )

    # Verificar continuidad temporal.

    esperado = pd.period_range(
        y.index.min(),
        y.index.max(),
        freq="M"
    )

    if not y.index.equals(esperado):

        raise ValueError(
            "Hay meses faltantes en desempleo."
        )


    # CONSTRUCCIÓN DE PREDICTORES RIDGE


    # Mantener exactamente las transformaciones
    # utilizadas en la optimización interna.

    features = data[PREDICTORS].shift(2)

    crecimiento = (
        data["IMACEC total"]
        .pct_change(12, fill_method=None) * 100
    )

    for k in REZAGOS:

        features[f"imacec_yoy_lag{k}"] = (
            crecimiento.shift(k)
        )

    muestra = features.join(
        y.rename("objetivo")
    ).dropna()

    # PERÍODO DE EVALUACIÓN


    meses = y.index[y.index >= CORTE]

    if len(meses) < 12:

        raise ValueError(
            "Menos de 12 meses de evaluación."
        )

    faltan = meses.difference(muestra.index)

    if len(faltan):

        raise ValueError(
            f"Predictores incompletos: {list(faltan)}"
        )

    print("\nCONFIGURACIÓN SELECCIONADA DE RIDGE")

    print(f"Predictores: {nombre}")
    print(f"Alpha: {alpha}")
    print(f"Rezago IMACEC: {lag} meses")

    print("\nPERÍODO DE EVALUACIÓN")

    print(f"Inicio: {meses[0]}")
    print(f"Término: {meses[-1]}")

    # REUTILIZAR EVALUACIÓN MULTIHORIZONTE


    print("\nEVALUANDO MODELOS DE SERIES DE TIEMPO")

    multi, convergencia = (
        evaluar_multihorizonte(y)
    )

    validar_evaluacion(multi)

    fallos = convergencia.loc[
        ~convergencia["convergio"]
    ]

    if not fallos.empty:

        print(fallos.to_string(index=False))

        raise RuntimeError(
            "Existen estimaciones ARIMA "
            "sin convergencia."
        )

    # Extraer exclusivamente los pronósticos
    # correspondientes al horizonte de un mes.

    un_mes = multi.loc[
        multi["horizonte_meses"] == 1
    ].copy()

    predicciones = un_mes.pivot(
        index="mes_objetivo",
        columns="modelo",
        values="pronostico"
    )

    predicciones.index = pd.PeriodIndex(
        predicciones.index,
        freq="M"
    )

    predicciones = predicciones.sort_index()

    if not predicciones.index.equals(meses):

        raise ValueError(
            "Los períodos de evaluación no coinciden."
        )

    modelos_esperados = [

        "Benchmark ingenuo",

        "ARIMA(1,1,1)",

        "ARIMA(0,1,2)"

    ]

    if not set(modelos_esperados).issubset(
        predicciones.columns
    ):

        raise ValueError(
            "Faltan modelos de series de tiempo."
        )

    # EVALUACIÓN TEMPORAL DE RIDGE

    registros = []

    for mes in meses:

        train_reg = muestra.loc[
            muestra.index < mes
        ]

        if len(train_reg) < MIN_TRAIN:

            raise ValueError(
                f"Entrenamiento insuficiente: {mes}"
            )

        ridge = make_pipeline(
            StandardScaler(),
            Ridge(alpha=alpha)
        )

        ridge.fit(

            train_reg[columnas],

            train_reg["objetivo"]

        )

        pred_ridge = float(

            ridge.predict(
                features.loc[[mes], columnas]
            )[0]

        )

        registros.append({

            "mes": str(mes),

            "observado": float(y.loc[mes]),

            "benchmark_ingenuo": float(
                predicciones.loc[
                    mes, "Benchmark ingenuo"
                ]
            ),

            "ARIMA_111": float(
                predicciones.loc[
                    mes, "ARIMA(1,1,1)"
                ]
            ),

            "ARIMA_012": float(
                predicciones.loc[
                    mes, "ARIMA(0,1,2)"
                ]
            ),

            "Ridge_mejorado": pred_ridge,

            # Todos los ajustes fueron verificados
            # antes de llegar a esta etapa.

            "arima_convergio": True,

            "arima_012_convergio": True

        })

    evaluacion = pd.DataFrame(registros)

    # MÉTRICAS DE EVALUACIÓN

    resultados = []

    modelos = [

        (
            "benchmark_ingenuo",
            "Benchmark ingenuo"
        ),

        (
            "ARIMA_111",
            "ARIMA(1,1,1)"
        ),

        (
            "ARIMA_012",
            "ARIMA(0,1,2)"
        ),

        (
            "Ridge_mejorado",
            f"Ridge alpha {alpha:g}, IMACEC lag {lag}"
        )

    ]

    for col, etiqueta in modelos:

        error = (
            evaluacion[col]
            - evaluacion["observado"]
        )

        if not np.isfinite(error).all():

            raise ValueError(
                f"Pronósticos inválidos: {etiqueta}"
            )

        resultados.append({

            "modelo": etiqueta,

            "n_pronosticos": len(error),

            "RMSE": np.sqrt(
                np.mean(error ** 2)
            ),

            "MAE": np.mean(
                np.abs(error)
            ),

            "sesgo": np.mean(error)

        })

    metricas = pd.DataFrame(
        resultados
    ).sort_values("RMSE").reset_index(drop=True)

    # Comparar el desempeño de cada modelo
    # respecto al benchmark ingenuo.

    rmse_benchmark = float(

        metricas.loc[

            metricas["modelo"] == "Benchmark ingenuo",

            "RMSE"

        ].iloc[0]

    )

    if rmse_benchmark > 0:

        metricas["mejora_RMSE_pct"] = (

            100 * (

                1 - metricas["RMSE"]
                / rmse_benchmark

            )

        )

    else:

        metricas["mejora_RMSE_pct"] = np.nan

    return evaluacion, metricas, y


# EXPORTACIÓN DE RESULTADOS

def main():

    evaluacion, metricas, _ = evaluar_modelos()

    OUT.mkdir(exist_ok=True)

    evaluacion.to_csv(

        OUT / "evaluacion_comparativa_temporal.csv",

        index=False,

        encoding="utf-8-sig"

    )

    metricas.to_csv(

        OUT / "metricas_comparacion_temporal.csv",

        index=False,

        encoding="utf-8-sig"

    )

    print("\nRESULTADOS DE EVALUACIÓN COMPARATIVA")

    print(

        metricas.to_string(

            index=False,

            float_format=lambda x: f"{x:.4f}"

        )

    )

    print("\nDIAGNÓSTICO DE CONVERGENCIA")

    print(

        "ARIMA(1,1,1) sin convergencia:",

        int(
            (~evaluacion["arima_convergio"]).sum()
        )

    )

    print(

        "ARIMA(0,1,2) sin convergencia:",

        int(
            (~evaluacion["arima_012_convergio"]).sum()
        )

    )

    print("\nARCHIVOS GENERADOS")

    print(
        "resultados/evaluacion_comparativa_temporal.csv"
    )

    print(
        "resultados/metricas_comparacion_temporal.csv"
    )

    print("\nEVALUACIÓN FINALIZADA.")

    print(

        "La evaluación es retrospectiva y utiliza "
        "las series históricas disponibles actualmente."

    )

    print(

        "El desempeño a un mes no garantiza "
        "superioridad predictiva a doce meses."

    )


if __name__ == "__main__":
    main()
