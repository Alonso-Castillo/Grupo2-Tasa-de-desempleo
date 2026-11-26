
"""
Evaluación comparativa de modelos de desempleo.

Se realiza una evaluación retrospectiva a un mes
mediante una ventana expansiva de entrenamiento.

La configuración de Ridge se selecciona exclusivamente
con información anterior al período de evaluación.
"""

import sqlite3
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
import sklearn.preprocessing
from statsmodels.tsa.arima.model import ARIMA

# Importar la configuración utilizada en la optimización.
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

    # Mantener una secuencia mensual regular.
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

    # Selección según los resultados de validación interna.
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

    # Variable objetivo.
    y = data[TARGET].dropna().astype(float)

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

    # CONSTRUCCIÓN DE PREDICTORES

    # Mantener la misma construcción de variables
    # utilizada durante la optimización de Ridge.
    #
    # El rezago de dos meses busca reducir el riesgo
    # de utilizar indicadores aún no publicados.

    features = data[PREDICTORS].shift(2)

    crecimiento = (
        data["IMACEC total"]
        .pct_change(12, fill_method=None) * 100
    )

    for k in REZAGOS:

        features[f"imacec_yoy_lag{k}"] = (
            crecimiento.shift(k)
        )

    # Muestra común para mantener consistencia
    # con el procedimiento de optimización.
    muestra = features.join(
        y.rename("objetivo")
    ).dropna()

    # PERÍODO DE EVALUACIÓN

    # Comenzar la evaluación después de finalizar
    # la selección de hiperparámetros.
    meses = y.index[y.index >= CORTE]

    if len(meses) < 12:
        raise ValueError(
            "Menos de 12 meses de evaluación."
        )

    faltan = meses.difference(muestra.index)

    if len(faltan):
        raise ValueError(
            f"Predictores incompletos en: {list(faltan)}"
        )

    print("\nCONFIGURACIÓN SELECCIONADA DE RIDGE")

    print(f"Predictores: {nombre}")
    print(f"Alpha: {alpha}")
    print(f"Rezago IMACEC: {lag} meses")

    print("\nPERÍODO DE EVALUACIÓN")

    print(f"Inicio: {meses[0]}")
    print(f"Término: {meses[-1]}")

    registros = []

    # VENTANA EXPANSIVA

    for mes in meses:

        # Utilizar únicamente observaciones anteriores
        # al mes que se desea pronosticar.
        train_y = y.loc[y.index < mes]

        train_reg = muestra.loc[
            muestra.index < mes
        ]

        if (
            len(train_reg) < MIN_TRAIN
            or len(train_y) < 60
        ):
            raise ValueError(
                f"Entrenamiento insuficiente en {mes}"
            )

        # MODELO 1: BENCHMARK INGENUO

        ingenuo = float(train_y.iloc[-1])

        # MODELO 2: ARIMA (1,1,1)

        ajuste = ARIMA(
            train_y,
            order=(1, 1, 1)
        ).fit()

        arima = float(
            np.asarray(
                ajuste.forecast(steps=1)
            )[0]
        )

        # Registrar problemas de convergencia
        # en lugar de ocultar las advertencias.
        convergio = bool(
            ajuste.mle_retvals.get(
                "converged", False
            )
        )

        # MODELO 3: RIDGE

        ridge = make_pipeline(
            sklearn.preprocessing.StandardScaler(),
            Ridge(alpha=alpha)
        )

        # El escalamiento se estima exclusivamente
        # utilizando la muestra de entrenamiento.
        ridge.fit(
            train_reg[columnas],
            train_reg["objetivo"]
        )

        pred_ridge = float(
            ridge.predict(
                features.loc[[mes], columnas]
            )[0]
        )

        # REGISTRO DE RESULTADOS

        registros.append({

            "mes": str(mes),

            "observado": float(y.loc[mes]),

            "benchmark_ingenuo": ingenuo,

            "ARIMA_111": arima,

            "Ridge_mejorado": pred_ridge,

            "arima_convergio": convergio

        })

    evaluacion = pd.DataFrame(registros)

    # MÉTRICAS DE EVALUACIÓN

    resultados = []

    for col, etiqueta in [

        (
            "benchmark_ingenuo",
            "Benchmark ingenuo"
        ),

        (
            "ARIMA_111",
            "ARIMA(1,1,1)"
        ),

        (
            "Ridge_mejorado",
            f"Ridge alpha {alpha:g}, IMACEC lag {lag}"
        )

    ]:

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
    ).sort_values("RMSE")

    return evaluacion, metricas, y

# EXPORTACIÓN Y PRESENTACIÓN DE RESULTADOS

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

    print("\nDIAGNÓSTICO DE CONVERGENCIA ARIMA")

    print(
        "Ajustes sin convergencia:",
        int(
            (~evaluacion["arima_convergio"]).sum()
        )
    )

    print("\nARCHIVOS GENERADOS:")

    print(
        "resultados/evaluacion_comparativa_temporal.csv"
    )

    print(
        "resultados/metricas_comparacion_temporal.csv"
    )

    print("\nEVALUACIÓN FINALIZADA.")


if __name__ == "__main__":
    main()
