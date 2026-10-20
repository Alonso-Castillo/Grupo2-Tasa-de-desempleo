"""Descarga las series del catálogo desde la API Siete del Banco Central.

Ejemplo:
    python base_datos/cargar_series.py --hasta 2026-09-30
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
from datetime import date
from pathlib import Path

import bcchapi
from dotenv import load_dotenv

RUTA_PROYECTO = Path(__file__).resolve().parent.parent
RUTA_DB = RUTA_PROYECTO / "base_datos" / "desempleo_chile.db"
sys.path.insert(0, str(RUTA_PROYECTO))
from src.config import SERIES_BCCH  # noqa: E402


def argumentos():
    parser = argparse.ArgumentParser(description="Carga series oficiales de la BDE del Banco Central de Chile.")
    parser.add_argument("--hasta", required=True, help="Fecha de corte en formato AAAA-MM-DD.")
    return parser.parse_args()


def main():
    args = argumentos()
    try:
        fecha_corte = date.fromisoformat(args.hasta)
    except ValueError as exc:
        raise SystemExit("Fecha inválida. Usa el formato AAAA-MM-DD, por ejemplo 2026-09-30.") from exc
    if fecha_corte > date.today():
        raise SystemExit("La fecha de corte no puede estar en el futuro.")

    load_dotenv(RUTA_PROYECTO / ".env")
    token = os.getenv("BCCH_API_TOKEN", "").strip()
    if not token or token == "PEGA_AQUI_TU_TOKEN":
        raise SystemExit(
            "Falta BCCH_API_TOKEN. Soliciten/obtengan el token de acceso a la API Siete, "
            "cópienlo en el archivo .env y vuelvan a ejecutar el comando."
        )
    if not RUTA_DB.exists():
        raise SystemExit("No existe la base de datos. Ejecuta primero: python base_datos/crear_base.py")

    siete = bcchapi.Siete(token=token)
    errores = 0
    total_ok = 0

    with sqlite3.connect(RUTA_DB) as conexion:
        conexion.execute("PRAGMA foreign_keys = ON")
        for serie in SERIES_BCCH:
            nombre = serie["nombre"]
            print(f"\nProcesando: {nombre}")
            try:
                kwargs = {
                    "series": [serie["codigo"]],
                    "desde": serie["desde"],
                    "hasta": fecha_corte.isoformat(),
                    "nombres": [serie["columna"]],
                }
                datos = siete.cuadro(**kwargs)
                if datos is None or serie["columna"] not in datos.columns:
                    raise ValueError("La API no devolvió la columna esperada.")
                registros = []
                for fecha, valor in datos[serie["columna"]].dropna().items():
                    fecha_texto = fecha.strftime("%Y-%m-%d") if hasattr(fecha, "strftime") else str(fecha)[:10]
                    if fecha_texto > fecha_corte.isoformat():
                        continue
                    registros.append((serie["codigo"], fecha_texto, float(valor)))
                if not registros:
                    raise ValueError("La descarga no devolvió observaciones dentro del período solicitado.")

                conexion.execute(
                    "INSERT OR IGNORE INTO temas (id_tema, tema) VALUES (?, ?)",
                    (serie["tema_id"], serie["tema"]),
                )
                conexion.execute(
                    """INSERT INTO series (id_serie, nombre, fuente, frecuencia, unidad, id_tema)
                       VALUES (?, ?, ?, ?, ?, ?)
                       ON CONFLICT(id_serie) DO UPDATE SET
                         nombre=excluded.nombre, fuente=excluded.fuente,
                         frecuencia=excluded.frecuencia, unidad=excluded.unidad,
                         id_tema=excluded.id_tema""",
                    (serie["codigo"], nombre, "BDE Banco Central de Chile",
                     serie.get("frecuencia", "M"), serie["unidad"], serie["tema_id"]),
                )
                # Elimina observaciones posteriores al corte para evitar que una base
                # reutilizada conserve datos de una ejecución anterior con otra fecha.
                conexion.execute(
                    "DELETE FROM observaciones WHERE id_serie = ? AND fecha > ?",
                    (serie["codigo"], fecha_corte.isoformat()),
                )
                conexion.executemany(
                    """INSERT INTO observaciones (id_serie, fecha, valor) VALUES (?, ?, ?)
                       ON CONFLICT(id_serie, fecha) DO UPDATE SET valor=excluded.valor""",
                    registros,
                )
                conexion.commit()
                total = conexion.execute(
                    "SELECT COUNT(*) FROM observaciones WHERE id_serie = ?", (serie["codigo"],)
                ).fetchone()[0]
                print(f"[OK] {nombre}: {len(registros)} observaciones descargadas; {total} almacenadas.")
                total_ok += 1
            except Exception as exc:  # sigue con las demás series y reporta fallas
                conexion.rollback()
                errores += 1
                print(f"[ERROR] {nombre} ({serie['codigo']}): {exc}")

    print(f"\nResultado de carga: {total_ok}/{len(SERIES_BCCH)} series OK; {errores} errores.")
    print(f"Fecha de corte solicitada: {fecha_corte.isoformat()}")
    if errores:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
