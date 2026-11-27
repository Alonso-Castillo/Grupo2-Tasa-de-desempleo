from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


# ============================================================
# RUTAS
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
RESULTADOS = ROOT / "resultados"
DASHBOARD = ROOT / "dashboard"

DASHBOARD.mkdir(exist_ok=True)


# ============================================================
# CARGA DE RESULTADOS
# ============================================================

metricas = pd.read_csv(RESULTADOS / "metricas_modelos.csv")
predicciones = pd.read_csv(RESULTADOS / "predicciones_oos_modelos.csv")
pronostico = pd.read_csv(RESULTADOS / "pronostico_desempleo_12m.csv")


print("\nCOLUMNAS DE metricas_modelos.csv")
print(metricas.columns.tolist())

print("\nCOLUMNAS DE predicciones_oos_modelos.csv")
print(predicciones.columns.tolist())

print("\nCOLUMNAS DE pronostico_desempleo_12m.csv")
print(pronostico.columns.tolist())


# ============================================================
# PREPARACIÓN DE DATOS
# ============================================================

# -----------------------------
# Predicciones fuera de muestra
# -----------------------------

fecha_col = predicciones.columns[0]

predicciones[fecha_col] = pd.to_datetime(
    predicciones[fecha_col],
    format="%Y-%m",
    errors="coerce"
)

predicciones = predicciones.dropna(subset=[fecha_col])

columnas_modelos = [
    c for c in predicciones.columns
    if c != fecha_col
]

nombres_modelos = {
    "observado": "Desempleo observado",
    "benchmark_ingenuo": "Benchmark ingenuo",
    "ARIMA_111": "ARIMA(1,1,1)",
    "Ridge_mejorado": "Ridge α=500"
}


# -----------------------------
# Métricas
# -----------------------------

modelo_col = metricas.columns[0]

rmse_col = next(
    c for c in metricas.columns
    if "RMSE" in c.upper()
)

metricas["modelo_mostrar"] = metricas[modelo_col].replace({
    "ARIMA(1,1,1)": "ARIMA(1,1,1)",
    "Benchmark ingenuo": "Benchmark ingenuo",
    "Ridge mejorado con IMACEC lag 2": "Ridge α=500"
})


# -----------------------------
# Pronóstico de 12 meses
# -----------------------------

fecha_pronostico = pronostico.columns[0]

pronostico[fecha_pronostico] = pd.to_datetime(
    pronostico[fecha_pronostico],
    format="%Y-%m",
    errors="coerce"
)

pronostico = pronostico.dropna(subset=[fecha_pronostico])

cols = pronostico.columns.tolist()

forecast_col = next(
    c for c in cols
    if "pronost" in c.lower()
    or "arima" in c.lower()
)

lower_col = next(
    (
        c for c in cols
        if "lower" in c.lower()
        or "inferior" in c.lower()
    ),
    None
)

upper_col = next(
    (
        c for c in cols
        if "upper" in c.lower()
        or "superior" in c.lower()
    ),
    None
)

benchmark_col = next(
    (
        c for c in cols
        if "benchmark" in c.lower()
        or "ingenu" in c.lower()
    ),
    None
)


# ============================================================
# DASHBOARD
# ============================================================

fig = plt.figure(figsize=(16, 11))

fig.suptitle(
    "Monitor de Coyuntura y Proyección de la Tasa de Desempleo en Chile",
    fontsize=18,
    fontweight="bold"
)


# ============================================================
# 1. EVALUACIÓN FUERA DE MUESTRA
# ============================================================

ax1 = fig.add_subplot(2, 2, 1)

for columna in columnas_modelos:
    ax1.plot(
        predicciones[fecha_col],
        predicciones[columna],
        label=nombres_modelos.get(columna, columna),
        linewidth=1.7
    )

ax1.set_title(
    "Evaluación fuera de muestra",
    fontsize=12,
    fontweight="bold"
)

ax1.set_ylabel("Tasa de desempleo (%)")
ax1.set_xlabel("Mes")

ax1.grid(alpha=0.3)

ax1.legend(
    fontsize=8,
    loc="upper left"
)


# ============================================================
# 2. COMPARACIÓN DE RMSE
# ============================================================

ax2 = fig.add_subplot(2, 2, 2)

bars = ax2.bar(
    metricas["modelo_mostrar"],
    metricas[rmse_col]
)

ax2.set_title(
    "Error de pronóstico por modelo",
    fontsize=12,
    fontweight="bold"
)

ax2.set_ylabel("RMSE (puntos porcentuales)")
ax2.set_xlabel("Modelo")

ax2.tick_params(
    axis="x",
    rotation=15
)

ax2.grid(
    axis="y",
    alpha=0.3
)

# Mostrar valor sobre cada barra
for bar, valor in zip(bars, metricas[rmse_col]):
    ax2.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height(),
        f"{valor:.3f}",
        ha="center",
        va="bottom",
        fontsize=9
    )


# ============================================================
# 3. PRONÓSTICO DE 12 MESES
# ============================================================

ax3 = fig.add_subplot(2, 1, 2)

ax3.plot(
    pronostico[fecha_pronostico],
    pronostico[forecast_col],
    marker="o",
    linewidth=2,
    label="Pronóstico ARIMA(1,1,1)"
)

if benchmark_col:
    ax3.plot(
        pronostico[fecha_pronostico],
        pronostico[benchmark_col],
        linestyle="--",
        linewidth=1.7,
        label="Benchmark ingenuo"
    )

if lower_col and upper_col:
    ax3.fill_between(
        pronostico[fecha_pronostico],
        pronostico[lower_col],
        pronostico[upper_col],
        alpha=0.2,
        label="Intervalo de confianza 95%"
    )

ax3.set_title(
    "Proyección de la tasa de desempleo a 12 meses",
    fontsize=12,
    fontweight="bold"
)

ax3.set_ylabel("Tasa de desempleo (%)")
ax3.set_xlabel("Mes")

ax3.grid(alpha=0.3)

ax3.legend(
    fontsize=9,
    loc="upper left"
)


# ============================================================
# NOTA DE FUENTE
# ============================================================

fig.text(
    0.5,
    0.015,
    (
        "Fuente: Banco Central de Chile. Elaboración propia. "
        "Evaluación fuera de muestra: feb. 2022–ago. 2026."
    ),
    ha="center",
    fontsize=9
)


# ============================================================
# GUARDAR DASHBOARD
# ============================================================

plt.tight_layout(
    rect=[0, 0.04, 1, 0.96]
)

salida = DASHBOARD / "dashboard_final_desempleo.png"

plt.savefig(
    salida,
    dpi=180,
    bbox_inches="tight"
)

plt.close()

print("\nDashboard final generado:")
print(salida)