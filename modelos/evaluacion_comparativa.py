
"""Evaluación comparativa temporal de tres modelos de desempleo."""

from pathlib import Path
import sqlite3
import warnings

import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

from statsmodels.tsa.arima.model import ARIMA


ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"
OUT = ROOT / "resultados"

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

SQL = """
SELECT o.fecha, s.nombre, o.valor
FROM observaciones o
JOIN series s ON s.id_serie = o.id_serie
WHERE s.nombre IN (
    'Tasa de desempleo nacional',
    'IMACEC total',
    'Índice de Avisos Laborales de Internet (IALI)',
    'Inflación IPC anual',
    'Tasa de Política Monetaria (TPM)',
    'Índice de Producción Manufacturera',
    'Tipo de cambio observado (CLP/USD)',
    'Precio del cobre refinado BML'
)
ORDER BY o.fecha
"""


def main():

    print("\nCARGANDO BASE DE DATOS...")

    with sqlite3.connect(DB) as con:
        raw = pd.read_sql_query(SQL, con)

    raw["fecha"] = pd.to_datetime(raw["fecha"])
    raw["mes"] = raw["fecha"].dt.to_period("M")

    data = raw.pivot_table(
        index="mes",
        columns="nombre",
        values="valor",
        aggfunc="last"
    ).sort_index()

    data = data.reindex(
        pd.period_range(
            data.index.min(),
            data.index.max(),
            freq="M"
        )
    )

    y = data[TARGET].astype(float)

    available = [
        c for c in PREDICTORS if c in data.columns
    ]

    # Predictores disponibles con un mes de rezago
    features = data[available].shift(1)

    # Crecimiento interanual del IMACEC con dos meses de rezago
    features["IMACEC_crecimiento_interanual_lag2"] = (
        data["IMACEC total"].pct_change(12).shift(2) * 100
    )

    # Muestra común para los tres modelos
    supervised = features.join(
        y.rename("objetivo")
    ).dropna()

    months = supervised.index

    if len(months) < 90:
        raise ValueError(
            "No existen suficientes observaciones comunes."
        )

    # Cinco ventanas temporales expansivas
    splitter = TimeSeriesSplit(n_splits=5)

    records = []

    print("\nINICIANDO EVALUACIÓN COMPARATIVA...")

    for fold, (train_idx, test_idx) in enumerate(
        splitter.split(months), start=1
    ):

        test_months = months[test_idx]

        print(f"\nVENTANA {fold}")

        for month in test_months:

            train_y = y.loc[y.index < month]

            train_reg = supervised.loc[
                supervised.index < month
            ]

            if len(train_y) < 60 or len(train_reg) < 60:
                continue

            observed = float(y.loc[month])

            # 1. Benchmark ingenuo
            naive_pred = float(train_y.iloc[-1])

            # 2. ARIMA
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                arima = ARIMA(
                    train_y,
                    order=(1, 1, 1)
                ).fit()

            arima_pred = float(
                np.asarray(arima.forecast(steps=1))[0]
            )

            # 3. Ridge optimizado
            x_now = features.loc[[month]]

            ridge = make_pipeline(
                StandardScaler(),
                Ridge(alpha=500)
            )

            ridge.fit(
                train_reg[features.columns],
                train_reg["objetivo"]
            )

            ridge_pred = float(
                ridge.predict(
                    x_now[features.columns]
                )[0]
            )

            records.append({
                "ventana": fold,
                "mes": str(month),
                "observado": observed,
                "benchmark_ingenuo": naive_pred,
                "ARIMA_111": arima_pred,
                "Ridge_alpha500": ridge_pred
            })

    evaluation = pd.DataFrame(records)

    if evaluation.empty:
        raise ValueError("No se generaron pronósticos.")

    # Métricas sobre exactamente los mismos meses
    results = []

    for column, name in [
        ("benchmark_ingenuo", "Benchmark ingenuo"),
        ("ARIMA_111", "ARIMA(1,1,1)"),
        ("Ridge_alpha500", "Ridge alpha 500")
    ]:

        error = (
            evaluation[column] - evaluation["observado"]
        )

        results.append({
            "modelo": name,
            "n_pronosticos": len(error),
            "RMSE": np.sqrt(np.mean(error ** 2)),
            "MAE": np.mean(np.abs(error)),
            "sesgo": np.mean(error)
        })

    metrics = pd.DataFrame(results).sort_values("RMSE")

    OUT.mkdir(exist_ok=True)

    evaluation.to_csv(
        OUT / "evaluacion_comparativa_temporal.csv",
        index=False,
        encoding="utf-8-sig"
    )

    metrics.to_csv(
        OUT / "metricas_comparacion_temporal.csv",
        index=False,
        encoding="utf-8-sig"
    )

    print("\nRESULTADOS DE EVALUACIÓN COMPARATIVA")
    print(
        metrics.to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\nPERÍODO EVALUADO:")
    print(evaluation["mes"].iloc[0], "a", evaluation["mes"].iloc[-1])

    print("\nPRONÓSTICOS POR VENTANA:")
    print(
        evaluation.groupby("ventana")
        .agg(
            inicio=("mes", "min"),
            fin=("mes", "max"),
            observaciones=("mes", "count")
        ).to_string()
    )

    print("\nARCHIVOS GENERADOS:")
    print("resultados/evaluacion_comparativa_temporal.csv")
    print("resultados/metricas_comparacion_temporal.csv")

    print("\nEVALUACIÓN FINALIZADA.")


if __name__ == "__main__":
    main()
