
"""
Optimización del modelo Ridge para pronosticar la tasa de desempleo.

La selección de predictores, rezagos e hiperparámetros se realiza
exclusivamente con observaciones anteriores a enero de 2024.

Se utiliza una ventana expansiva de entrenamiento y se comparan
todas las configuraciones sobre los mismos meses de validación.

El período de evaluación final no interviene en esta optimización.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

import sklearn.linear_model
from sklearn.pipeline import make_pipeline
import sklearn.preprocessing
from sklearn.metrics import mean_squared_error, mean_absolute_error


# CONFIGURACIÓN

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"
OUT = ROOT / "resultados"

CORTE = pd.Period("2024-01", freq="M")
MIN_TRAIN = 36

TARGET = "Tasa de desempleo nacional"

PREDICTORS = [
    "IMACEC total",
    "Índice de Avisos Laborales de Internet (IALI)",
    "Inflación IPC anual",
    "Tasa de Política Monetaria (TPM)",
    "Índice de Producción Manufacturera",
    "Tipo de cambio observado (CLP/USD)",
    "Precio del cobre refinado BML",
]

ALPHAS = [0.1, 1, 10, 50, 100, 500, 1000]

REZAGOS = [2, 3, 4, 6]


# CONSULTA SQL

SQL = """
SELECT o.fecha, s.nombre, o.valor
FROM observaciones o
JOIN series s ON o.id_serie = s.id_serie
WHERE s.nombre IN ({})
ORDER BY o.fecha
""".format(",".join("?" for _ in [TARGET] + PREDICTORS))


def main():

    # CARGA DE DATOS

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

    # Excluir completamente el período de evaluación final.
    raw = raw.loc[raw["mes"] < CORTE].copy()

    if raw.empty:
        raise ValueError(
            "No hay datos anteriores al corte."
        )

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

    # Construir una secuencia mensual regular.
    data = data.reindex(
        pd.period_range(
            data.index.min(),
            CORTE - 1,
            freq="M"
        )
    )

    # CONSTRUCCIÓN DE PREDICTORES

    # Utilizar un rezago conservador de dos meses
    # para reducir el riesgo de anticipación.
    features = data[PREDICTORS].shift(2)

    # Crecimiento interanual del IMACEC sin imputación
    # automática de observaciones faltantes.
    crecimiento = (
        data["IMACEC total"]
        .pct_change(12, fill_method=None) * 100
    )

    # Evaluar distintos rezagos exclusivamente dentro
    # de la muestra de optimización.
    for lag in REZAGOS:

        features[f"imacec_yoy_lag{lag}"] = (
            crecimiento.shift(lag)
        )

    # MUESTRA COMÚN

    # Todas las configuraciones se comparan utilizando
    # exactamente las mismas observaciones.
    muestra = features.join(
        data[TARGET].rename("objetivo")
    ).dropna()

    if len(muestra) <= MIN_TRAIN:
        raise ValueError(
            "Muestra insuficiente para validar Ridge."
        )

    # CONFIGURACIONES DE PREDICTORES


    sets = {

        "Todos los predictores": PREDICTORS,

        "IMACEC e indicadores laborales": [
            PREDICTORS[0],
            PREDICTORS[1],
            PREDICTORS[4]
        ],
    }

    resultados = []

    # ==================================================
    # OPTIMIZACIÓN TEMPORAL
    # ==================================================

    for nombre, base in sets.items():

        for lag in REZAGOS:

            columnas = base + [
                f"imacec_yoy_lag{lag}"
            ]

            X = muestra[columnas]
            y = muestra["objetivo"]

            for alpha in ALPHAS:

                predicciones = []

                # Ventana expansiva:
                # entrenar exclusivamente con observaciones
                # anteriores al mes que se desea predecir.
                for i in range(
                    MIN_TRAIN,
                    len(muestra)
                ):

                    X_train = X.iloc[:i]
                    y_train = y.iloc[:i]

                    X_val = X.iloc[[i]]

                    # El escalamiento se estima únicamente
                    # utilizando la muestra de entrenamiento.
                    modelo = make_pipeline(
                        sklearn.preprocessing.StandardScaler(),
                        sklearn.linear_model.Ridge(alpha=alpha)
                    )

                    modelo.fit(X_train, y_train)

                    prediccion = modelo.predict(X_val)[0]

                    predicciones.append(prediccion)

                observado = y.iloc[MIN_TRAIN:]

                rmse = np.sqrt(
                    mean_squared_error(
                        observado,
                        predicciones
                    )
                )

                mae = mean_absolute_error(
                    observado,
                    predicciones
                )

                resultados.append({

                    "configuracion": nombre,

                    "rezago_imacec": lag,

                    "alpha": alpha,

                    "n_pronosticos": len(observado),

                    "RMSE": rmse,

                    "MAE": mae

                })

    # SELECCIÓN DE LA MEJOR CONFIGURACIÓN
  
    # Se selecciona el menor RMSE de validación interna.
    # El MAE actúa como criterio secundario.
    tabla = pd.DataFrame(resultados).sort_values(
        ["RMSE", "MAE"]
    ).reset_index(drop=True)

    # EXPORTACIÓN DE RESULTADOS

    OUT.mkdir(exist_ok=True)

    tabla.to_csv(
        OUT / "optimizacion_ridge.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # PRESENTACIÓN DE RESULTADOS

    print("\nOPTIMIZACIÓN TEMPORAL DEL MODELO RIDGE")

    print(
        "\nMuestra común:",
        muestra.index[0],
        "a",
        muestra.index[-1]
    )

    print(
        "Período de validación:",
        muestra.index[MIN_TRAIN],
        "a",
        muestra.index[-1]
    )

    print(
        "\nNúmero de configuraciones evaluadas:",
        len(tabla)
    )

    print(
        tabla.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print(
        "\nMEJOR CONFIGURACIÓN "
        "(SOLO VALIDACIÓN INTERNA)"
    )

    print(tabla.iloc[0].to_string())

    print("\nArchivo guardado:")
    print("resultados/optimizacion_ridge.csv")


if __name__ == "__main__":
    main()
