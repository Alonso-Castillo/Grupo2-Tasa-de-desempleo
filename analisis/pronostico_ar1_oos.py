"""Hito 3 - Primer experimento reproducible de pronostico de desempleo.

Lee la tasa de desempleo directamente de SQLite mediante JOIN SQL.
Evalua PRONOSTICOS A UN MES fuera de muestra con ventana expansiva:
  - Benchmark ingenuo: valor de la ultima observacion disponible.
  - AR(1): reestimado en cada origen utilizando solo informacion anterior.

No es todavia la proyeccion final a 12 meses ni la evaluacion completa del proyecto.
Ejecutar desde la raiz: .\\.venv\\Scripts\\python.exe analisis/pronostico_ar1_oos.py
"""
from pathlib import Path
import sqlite3

import matplotlib
matplotlib.use("Agg")  # Permite guardar graficos sin abrir ventanas.
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg

RAIZ = Path(__file__).resolve().parent.parent
DB = RAIZ / "base_datos" / "desempleo_chile.db"
CARPETA_RESULTADOS = RAIZ / "resultados"
CARPETA_GRAFICOS = RAIZ / "graficos"
INICIO_EVALUACION = "2024-01"  # Corte previo al ejercicio, sin barajar fechas.

SQL_DESEMPLEO = """
-- Se usa SQL sobre las tablas relacionadas; NO se carga un archivo manual.
SELECT o.fecha, o.valor AS tasa_desempleo
FROM observaciones AS o
JOIN series AS s ON s.id_serie = o.id_serie
WHERE s.nombre = 'Tasa de desempleo nacional'
ORDER BY o.fecha;
"""


def cargar_serie():
    if not DB.is_file():
        raise FileNotFoundError(f"No se encontro la base de datos: {DB}")

    with sqlite3.connect(DB) as conexion:
        datos = pd.read_sql_query(SQL_DESEMPLEO, conexion)

    if datos.empty:
        raise ValueError("No se encontraron observaciones de desempleo en SQLite.")

    datos["fecha"] = pd.to_datetime(datos["fecha"], errors="raise")
    datos["mes"] = datos["fecha"].dt.to_period("M")
    if datos["mes"].duplicated().any():
        raise ValueError("Hay mas de una observacion por mes de desempleo.")

    serie = pd.Series(
        pd.to_numeric(datos["tasa_desempleo"], errors="coerce").to_numpy(dtype=float),
        index=pd.PeriodIndex(datos["mes"], freq="M"),
        name="desempleo",
    ).sort_index()
    if serie.isna().any():
        raise ValueError("La tasa de desempleo contiene valores faltantes.")
    esperados = pd.period_range(serie.index.min(), serie.index.max(), freq="M")
    faltantes = esperados.difference(serie.index)
    if len(faltantes):
        raise ValueError(f"Faltan meses en la serie de desempleo: {list(map(str, faltantes))}")
    return serie


def metricas(y_real, y_pred):
    error = np.asarray(y_real, dtype=float) - np.asarray(y_pred, dtype=float)
    return float(np.sqrt(np.mean(error ** 2))), float(np.mean(np.abs(error)))


def main():
    y = cargar_serie()
    prueba_desde = pd.Period(INICIO_EVALUACION, freq="M")
    meses_test = y.index[y.index >= prueba_desde]
    if len(meses_test) < 12:
        raise ValueError("Menos de 12 meses disponibles para evaluar desde " + INICIO_EVALUACION)
    if len(y[y.index < prueba_desde]) < 36:
        raise ValueError("El entrenamiento previo a la evaluacion es muy corto.")

    filas = []
    for mes in meses_test:
        # Ventana expansiva: para estimar t, solo se usa hasta t-1.
        entrenamiento = y.loc[y.index < mes]
        # Benchmark: mantener la ultima tasa observada.
        ingenuo = float(entrenamiento.iloc[-1])
        # Modelo AR(1): valor esperado condicional en el rezago 1.
        estimacion = AutoReg(entrenamiento, lags=1, trend="c").fit()
        ar1 = float(estimacion.predict(start=len(entrenamiento), end=len(entrenamiento)).iloc[0])
        filas.append({
            "mes": str(mes),
            "observado": float(y.loc[mes]),
            "ingenuo": ingenuo,
            "AR1": ar1,
        })

    evaluacion = pd.DataFrame(filas)
    comparacion = []
    for nombre in ["ingenuo", "AR1"]:
        rmse, mae = metricas(evaluacion["observado"], evaluacion[nombre])
        comparacion.append({"modelo": nombre, "RMSE_pp": rmse, "MAE_pp": mae})
    comparacion = pd.DataFrame(comparacion).sort_values("RMSE_pp")

    CARPETA_RESULTADOS.mkdir(exist_ok=True)
    CARPETA_GRAFICOS.mkdir(exist_ok=True)
    evaluacion.to_csv(CARPETA_RESULTADOS / "predicciones_oos_ar1.csv", index=False, encoding="utf-8-sig")
    comparacion.to_csv(CARPETA_RESULTADOS / "metricas_oos_ar1.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(11, 5))
    fechas = pd.PeriodIndex(evaluacion["mes"], freq="M").to_timestamp()
    ax.plot(fechas, evaluacion["observado"], label="Observado", linewidth=2.3)
    ax.plot(fechas, evaluacion["ingenuo"], label="Benchmark ingenuo", linestyle="--")
    ax.plot(fechas, evaluacion["AR1"], label="AR(1)", linestyle=":", linewidth=2)
    ax.set(title="Chile: desempleo y pronosticos fuera de muestra (1 mes)",
           xlabel="Mes", ylabel="Tasa de desempleo (%)")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(CARPETA_GRAFICOS / "11_pronostico_oos_ar1.png", dpi=160)
    plt.close(fig)

    print("\nHITO 3 - PRIMERA EVALUACION FUERA DE MUESTRA")
    print(f"Serie: {len(y)} meses ({y.index.min()} a {y.index.max()})")
    print(f"Entrenamiento inicial: {y.index.min()} a {prueba_desde - 1}")
    print(f"Evaluacion: {meses_test.min()} a {meses_test.max()} ({len(meses_test)} pronosticos)")
    print("Horizonte evaluado: 1 mes. Reestimacion AR(1) en cada origen.")
    print("\nMETRICAS (puntos porcentuales; menor es mejor)")
    print(comparacion.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    print("\nArchivos creados:")
    print(" - resultados/predicciones_oos_ar1.csv")
    print(" - resultados/metricas_oos_ar1.csv")
    print(" - graficos/11_pronostico_oos_ar1.png")
    print("\nNOTA: ejercicio ex post con ultimas observaciones de cada mes; para una")
    print("evaluacion estrictamente en tiempo real hay que considerar rezagos de publicacion.")
    print("Esta prueba de un mes NO es el pronostico final a 12 meses.")


if __name__ == "__main__":
    main()
