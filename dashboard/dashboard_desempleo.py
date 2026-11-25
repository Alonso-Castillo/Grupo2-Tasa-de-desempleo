"""Genera un monitor de coyuntura reproducible desde SQLite y resultados del modelo."""
from pathlib import Path
import sqlite3
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "base_datos" / "desempleo_chile.db"
FORECAST = ROOT / "resultados" / "pronostico_desempleo_12m.csv"
OUTPUT = ROOT / "dashboard" / "dashboard_desempleo.png"

SQL = """
SELECT o.fecha, s.nombre, o.valor
FROM observaciones o JOIN series s ON s.id_serie=o.id_serie
WHERE s.nombre IN ('Tasa de desempleo nacional', 'IMACEC total',
 'Inflación IPC anual', 'Tasa de Política Monetaria (TPM)',
 'Índice de Avisos Laborales de Internet (IALI)')
ORDER BY o.fecha
"""


def main():
    if not DB.exists():
        raise FileNotFoundError("No existe SQLite. Ejecuta primero la carga de datos.")
    if not FORECAST.exists():
        raise FileNotFoundError("Falta el pronóstico. Ejecuta primero modelos/modelos_desempleo.py")
    with sqlite3.connect(DB) as con:
        raw = pd.read_sql_query(SQL, con)
    raw["fecha"] = pd.to_datetime(raw["fecha"])
    wide = raw.pivot_table(index="fecha", columns="nombre", values="valor", aggfunc="last").sort_index()
    target = "Tasa de desempleo nacional"
    if target not in wide or wide[target].dropna().empty:
        raise ValueError("No hay datos de desempleo en SQLite.")
    forecast = pd.read_csv(FORECAST, parse_dates=["mes"])
    latest_date = wide[target].dropna().index[-1]
    latest = float(wide[target].dropna().iloc[-1])
    yoy = latest - float(wide[target].dropna().iloc[-13]) if len(wide[target].dropna()) >= 13 else float("nan")

    fig = plt.figure(figsize=(15, 9), constrained_layout=True)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1])
    ax1 = fig.add_subplot(gs[0, :])
    hist = wide[target].dropna().iloc[-72:]
    ax1.plot(hist.index, hist.values, linewidth=2.2, label="Tasa de desempleo")
    ax1.axhline(latest, linestyle="--", alpha=.6, label=f"Último dato: {latest:.2f}%")
    ax1.set_title("Chile | Evolución de la tasa de desempleo", loc="left", weight="bold")
    ax1.set_ylabel("Porcentaje")
    ax1.grid(alpha=.22); ax1.legend(loc="upper left")

    ax2 = fig.add_subplot(gs[1, 0])
    if "IMACEC total" in wide:
        imacec = wide["IMACEC total"].dropna().iloc[-60:]
        ax2.plot(imacec.index, imacec.values, label="IMACEC", linewidth=1.8)
        ax2.set_ylabel("Índice")
    ax2.set_title("Indicador de actividad económica", loc="left", weight="bold")
    ax2.grid(alpha=.22)

    ax3 = fig.add_subplot(gs[1, 1])
    fd = pd.to_datetime(forecast["mes"])
    ax3.plot(fd, forecast["pronostico_ARIMA_111"], label="Pronóstico ARIMA", linewidth=2)
    ax3.fill_between(fd, forecast["limite_inferior_95"], forecast["limite_superior_95"], alpha=.18, label="Intervalo 95%")
    ax3.plot(fd, forecast["benchmark_ingenuo"], linestyle="--", label="Benchmark ingenuo")
    ax3.set_title("Proyección de desempleo | 12 meses", loc="left", weight="bold")
    ax3.set_ylabel("Porcentaje"); ax3.grid(alpha=.22); ax3.legend(fontsize=8)

    fig.suptitle(f"MONITOR DE COYUNTURA LABORAL | Dato más reciente: {latest_date:%Y-%m} | Desempleo: {latest:.2f}% | Cambio interanual: {yoy:+.2f} pp",
                 fontsize=14, weight="bold")
    OUTPUT.parent.mkdir(exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print(f"Dashboard generado: {OUTPUT}")


if __name__ == "__main__":
    main()
