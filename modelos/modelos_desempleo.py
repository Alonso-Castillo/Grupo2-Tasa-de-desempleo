
"""Modelación y evaluación reproducible de la tasa de desempleo.

Compara pronósticos de un mes fuera de muestra mediante ventana expansiva:
- Benchmark ingenuo: último valor observado.
- - ARIMA(1,1,1): modelo univariado seleccionado a partir del diagnóstico de estacionariedad.
  La prueba ADF mostró que la tasa de desempleo no es estacionaria en nivel, pero sí en primera
  diferencia, justificando d=1. Los gráficos ACF y PACF sugieren una dinámica de bajo orden.
- Ridge: predictores macroeconómicos rezagados y crecimiento del IMACEC
  con dos meses de rezago.

Además estima un pronóstico ARIMA(1,1,1) a 12 meses con intervalos del 95%.
"""

from __future__ import annotations

import argparse
import sqlite3
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.arima.model import ARIMA


ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"
OUT = ROOT / "resultados"
FIG = ROOT / "graficos"

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


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--inicio-evaluacion",
        default="2022-02",
        help="Primer mes de evaluación, AAAA-MM"
    )
    return parser.parse_args()


def load_data() -> pd.DataFrame:

    if not DB.exists():
        raise FileNotFoundError(
            f"No existe {DB}. Ejecuta primero la carga de datos."
        )

    with sqlite3.connect(DB) as con:
        raw = pd.read_sql_query(SQL, con)

    if raw.empty:
        raise ValueError("La consulta SQL no devolvió datos.")

    raw["fecha"] = pd.to_datetime(
        raw["fecha"], errors="coerce"
    ).dt.to_period("M")

    raw["valor"] = pd.to_numeric(
        raw["valor"], errors="coerce"
    )

    wide = raw.pivot_table(
        index="fecha",
        columns="nombre",
        values="valor",
        aggfunc="last"
    )

    full_index = pd.period_range(
        wide.index.min(),
        wide.index.max(),
        freq="M"
    )

    wide = wide.reindex(full_index)
    wide.index.name = "mes"

    if TARGET not in wide or wide[TARGET].dropna().empty:
        raise ValueError(
            "No se encontró la serie objetivo de desempleo."
        )

    return wide.sort_index()


def rmse(y, pred):
    return float(
        np.sqrt(
            np.mean(
                (np.asarray(y) - np.asarray(pred)) ** 2
            )
        )
    )


def mae(y, pred):
    return float(
        np.mean(
            np.abs(np.asarray(y) - np.asarray(pred))
        )
    )


def main():

    args = parse_args()
    start = pd.Period(args.inicio_evaluacion, freq="M")

    data = load_data()

    y = data[TARGET].dropna().astype(float)

    expected = pd.period_range(
        y.index.min(),
        y.index.max(),
        freq="M"
    )

    if not expected.equals(y.index):
        raise ValueError(
            "La serie de desempleo tiene meses faltantes."
        )

    if len(y) < 60:
        raise ValueError(
            f"Solo hay {len(y)} observaciones. Se requieren al menos 60."
        )

    # --------------------------------------------------
    # CONSTRUCCIÓN DE PREDICTORES PARA RIDGE
    # --------------------------------------------------

    available_predictors = [
        c for c in PREDICTORS if c in data.columns
    ]

    if len(available_predictors) < 2:
        raise ValueError(
            "No hay suficientes series explicativas en SQLite."
        )

    # Predictores macroeconómicos con un mes de rezago
    features = data[available_predictors].shift(1)

    # Nueva variable: crecimiento interanual del IMACEC
    # con dos meses de rezago
    features["IMACEC_crecimiento_interanual_lag2"] = (
        data["IMACEC total"].pct_change(12).shift(2) * 100
    )

    feature_cols = list(features.columns)

    supervised = features.join(
        y.rename("objetivo")
    ).dropna()

    # --------------------------------------------------
    # EVALUACIÓN FUERA DE MUESTRA
    # --------------------------------------------------

    test_months = y.index[y.index >= start]

    if len(test_months) < 12:
        raise ValueError(
            "Se necesitan al menos 12 meses de evaluación."
        )

    records = []

    for month in test_months:

        train_y = y.loc[y.index < month]

        if len(train_y) < 36:
            continue

        observed = float(y.loc[month])

        # Benchmark ingenuo
        naive = float(train_y.iloc[-1])

        # ARIMA
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")

            arima_fit = ARIMA(
                train_y.astype(float),
                order=(1, 1, 1)
            ).fit()

        arima_pred = float(
            np.asarray(
                arima_fit.forecast(steps=1)
            )[0]
        )

        # RIDGE MEJORADO
        train_reg = supervised.loc[
            supervised.index < month
        ]

        x_now = features.loc[[month]]

        if (
            train_reg.empty
            or x_now[feature_cols].isna().any(axis=None)
        ):
            ridge_pred = np.nan

        else:

            model = make_pipeline(
                StandardScaler(),
                Ridge(alpha=500)
            )

            model.fit(
                train_reg[feature_cols],
                train_reg["objetivo"]
            )

            ridge_pred = float(
                model.predict(
                    x_now[feature_cols]
                )[0]
            )

        records.append({
            "mes": str(month),
            "observado": observed,
            "benchmark_ingenuo": naive,
            "ARIMA_111": arima_pred,
            "Ridge_mejorado": ridge_pred
        })

    evaluation = pd.DataFrame(records)

    if evaluation.empty:
        raise ValueError(
            "No fue posible construir pronósticos de evaluación."
        )

    # --------------------------------------------------
    # CÁLCULO DE MÉTRICAS
    # --------------------------------------------------

    metrics = []

    for col, label in [
        ("benchmark_ingenuo", "Benchmark ingenuo"),
        ("ARIMA_111", "ARIMA(1,1,1)"),
        ("Ridge_mejorado", "Ridge mejorado con IMACEC lag 2")
    ]:

        sample = evaluation[
            ["observado", col]
        ].dropna()

        metrics.append({
            "modelo": label,
            "n_pronosticos": len(sample),
            "RMSE_pp": rmse(
                sample["observado"],
                sample[col]
            ),
            "MAE_pp": mae(
                sample["observado"],
                sample[col]
            )
        })

    metrics_df = pd.DataFrame(
        metrics
    ).sort_values("RMSE_pp")

    # --------------------------------------------------
    # PRONÓSTICO ARIMA A 12 MESES
    # --------------------------------------------------

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")

        final_fit = ARIMA(
            y.astype(float),
            order=(1, 1, 1)
        ).fit()

    fc = final_fit.get_forecast(steps=12)

    ci = fc.conf_int(alpha=0.05)

    future = pd.period_range(
        y.index[-1] + 1,
        periods=12,
        freq="M"
    )

    forecast = pd.DataFrame({
        "mes": [str(x) for x in future],
        "pronostico_ARIMA_111": np.asarray(
            fc.predicted_mean, dtype=float
        ),
        "limite_inferior_95": ci.iloc[:, 0].to_numpy(
            dtype=float
        ),
        "limite_superior_95": ci.iloc[:, 1].to_numpy(
            dtype=float
        ),
        "benchmark_ingenuo": float(y.iloc[-1])
    })

    # --------------------------------------------------
    # GUARDAR RESULTADOS
    # --------------------------------------------------

    OUT.mkdir(exist_ok=True)
    FIG.mkdir(exist_ok=True)

    evaluation.to_csv(
        OUT / "predicciones_oos_modelos.csv",
        index=False,
        encoding="utf-8-sig"
    )

    metrics_df.to_csv(
        OUT / "metricas_modelos.csv",
        index=False,
        encoding="utf-8-sig"
    )

    forecast.to_csv(
        OUT / "pronostico_desempleo_12m.csv",
        index=False,
        encoding="utf-8-sig"
    )

    # --------------------------------------------------
    # GRÁFICO DE EVALUACIÓN
    # --------------------------------------------------

    dates = pd.PeriodIndex(
        evaluation["mes"],
        freq="M"
    ).to_timestamp()

    fig, ax = plt.subplots(figsize=(12, 5.5))

    ax.plot(
        dates,
        evaluation["observado"],
        label="Observado",
        linewidth=2.2
    )

    ax.plot(
        dates,
        evaluation["benchmark_ingenuo"],
        label="Benchmark ingenuo",
        linestyle="--"
    )

    ax.plot(
        dates,
        evaluation["ARIMA_111"],
        label="ARIMA(1,1,1)",
        linestyle="-."
    )

    ax.plot(
        dates,
        evaluation["Ridge_mejorado"],
        label="Ridge mejorado",
        linestyle=":"
    )

    ax.set(
        title="Desempleo en Chile: evaluación fuera de muestra",
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

    # --------------------------------------------------
    # GRÁFICO DE PRONÓSTICO A 12 MESES
    # --------------------------------------------------

    hist = y.iloc[-60:]

    hist_dates = hist.index.to_timestamp()
    future_dates = future.to_timestamp()

    fig, ax = plt.subplots(figsize=(12, 5.5))

    ax.plot(
        hist_dates,
        hist.values,
        label="Desempleo observado",
        linewidth=2.2
    )

    ax.plot(
        future_dates,
        forecast["pronostico_ARIMA_111"],
        label="Pronóstico ARIMA(1,1,1)",
        linewidth=2
    )

    ax.fill_between(
        future_dates,
        forecast["limite_inferior_95"],
        forecast["limite_superior_95"],
        alpha=0.18,
        label="Intervalo 95%"
    )

    ax.plot(
        future_dates,
        forecast["benchmark_ingenuo"],
        linestyle="--",
        label="Benchmark ingenuo"
    )

    ax.set(
        title="Chile: proyección de desempleo a 12 meses",
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

    # --------------------------------------------------
    # RESULTADOS EN TERMINAL
    # --------------------------------------------------

    print("\nEVALUACIÓN FUERA DE MUESTRA")
    print(
        metrics_df.to_string(
            index=False,
            float_format=lambda v: f"{v:.4f}"
        )
    )

    print(
        f"\nSerie objetivo: {y.index.min()} a {y.index.max()}"
        f" ({len(y)} observaciones)"
    )

    print(
        f"Evaluación: {evaluation.mes.iloc[0]} "
        f"a {evaluation.mes.iloc[-1]}"
    )

    print("\nPredictores utilizados por Ridge:")
    for col in feature_cols:
        print("-", col)

    print(
        "\nPronóstico ARIMA guardado en "
        "resultados/pronostico_desempleo_12m.csv"
    )

    print(
        "\nEvaluación guardada en "
        "resultados/predicciones_oos_modelos.csv"
    )

    print(
        "\nMétricas guardadas en "
        "resultados/metricas_modelos.csv"
    )

    print("\nAnálisis terminado.")
    print(
        "Advertencia: verificar disponibilidad y fechas "
        "de publicación de los predictores."
    )


if __name__ == "__main__":
    main()
