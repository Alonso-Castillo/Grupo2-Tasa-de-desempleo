
import sqlite3
import numpy as np
import pandas as pd

from pathlib import Path
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"

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
JOIN series s ON o.id_serie = s.id_serie
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
    pd.period_range(data.index.min(), data.index.max(), freq="M")
)

y = data[TARGET].astype(float)

available = [c for c in PREDICTORS if c in data.columns]

features = data[available].shift(1)

features["IMACEC_crecimiento_interanual_lag2"] = (
    data["IMACEC total"].pct_change(12).shift(2) * 100
)

# Solo datos anteriores al período de evaluación
features = features.loc[features.index < pd.Period("2024-01")]
y = y.loc[y.index < pd.Period("2024-01")]

# Dos configuraciones de predictores
sets = {
    "Todos los predictores": list(features.columns),
    "IMACEC e indicadores laborales": [
        c for c in [
            "IMACEC total",
            "Índice de Avisos Laborales de Internet (IALI)",
            "Índice de Producción Manufacturera",
            "IMACEC_crecimiento_interanual_lag2"
        ] if c in features.columns
    ]
}

resultados = []

alphas = [0.1, 1, 10, 50, 100, 500, 1000]

for nombre, columnas in sets.items():

    muestra = features[columnas].join(
        y.rename("objetivo")
    ).dropna()

    X = muestra[columnas]
    objetivo = muestra["objetivo"]

    cv = TimeSeriesSplit(n_splits=5)

    for alpha in alphas:

        errores_rmse = []
        errores_mae = []

        for train_idx, val_idx in cv.split(X):

            X_train = X.iloc[train_idx]
            X_val = X.iloc[val_idx]

            y_train = objetivo.iloc[train_idx]
            y_val = objetivo.iloc[val_idx]

            modelo = make_pipeline(
                StandardScaler(),
                Ridge(alpha=alpha)
            )

            modelo.fit(X_train, y_train)

            pred = modelo.predict(X_val)

            errores_rmse.append(
                np.sqrt(mean_squared_error(y_val, pred))
            )

            errores_mae.append(
                mean_absolute_error(y_val, pred)
            )

        resultados.append({
            "configuracion": nombre,
            "alpha": alpha,
            "RMSE_promedio": np.mean(errores_rmse),
            "MAE_promedio": np.mean(errores_mae)
        })

tabla = pd.DataFrame(resultados).sort_values(
    "RMSE_promedio"
)

OUT = ROOT / "resultados"
OUT.mkdir(exist_ok=True)

tabla.to_csv(
    OUT / "optimizacion_ridge.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nRESULTADOS DE OPTIMIZACION RIDGE")
print(tabla.to_string(index=False, float_format=lambda x: f"{x:.4f}"))

print("\nMEJOR CONFIGURACION")
print(tabla.iloc[0].to_string())

print("\nArchivo guardado:")
print("resultados/optimizacion_ridge.csv")
