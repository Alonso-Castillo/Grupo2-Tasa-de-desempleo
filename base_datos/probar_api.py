"""Comprueba acceso al API Siete y disponibilidad de las series sin modificar SQLite.

Ejemplo desde la raíz del proyecto:
    python base_datos/probar_api.py --hasta 2026-09-30
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import date
from pathlib import Path

import bcchapi
from dotenv import load_dotenv

RUTA_PROYECTO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RUTA_PROYECTO))
from src.config import SERIES_BCCH  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Prueba el token y la disponibilidad de las series BDE.")
    parser.add_argument("--hasta", required=True, help="Fecha de corte AAAA-MM-DD.")
    args = parser.parse_args()
    try:
        corte = date.fromisoformat(args.hasta)
    except ValueError:
        print("Fecha inválida. Usa AAAA-MM-DD, por ejemplo 2026-09-30.")
        return 2
    if corte > date.today():
        print("La fecha de corte no puede estar en el futuro.")
        return 2

    load_dotenv(RUTA_PROYECTO / ".env")
    token = os.getenv("BCCH_API_TOKEN", "").strip()
    if not token or token == "PEGA_AQUI_TU_TOKEN":
        print("[ERROR] No se encontró un token válido en el archivo .env.")
        print("Copia .env.example a .env y agrega BCCH_API_TOKEN localmente; no compartas el token.")
        return 2

    siete = bcchapi.Siete(token=token)
    errores = 0
    print(f"Probando {len(SERIES_BCCH)} series hasta {corte.isoformat()} (no escribe en la base de datos).")
    for serie in SERIES_BCCH:
        try:
            datos = siete.cuadro(
                series=[serie["codigo"]],
                desde=serie["desde"],
                hasta=corte.isoformat(),
                nombres=[serie["columna"]],
            )
            if datos is None or serie["columna"] not in datos.columns:
                raise ValueError("la API no devolvió la columna esperada")
            valores = datos[serie["columna"]].dropna()
            if valores.empty:
                raise ValueError("no se recibieron observaciones en el período")
            inicio = valores.index.min()
            fin = valores.index.max()
            inicio_txt = inicio.strftime("%Y-%m-%d") if hasattr(inicio, "strftime") else str(inicio)[:10]
            fin_txt = fin.strftime("%Y-%m-%d") if hasattr(fin, "strftime") else str(fin)[:10]
            if fin_txt > corte.isoformat():
                raise ValueError(f"la respuesta contiene datos posteriores al corte ({fin_txt})")
            print(f"[OK] {serie['nombre']}: {len(valores)} observaciones; {inicio_txt} a {fin_txt}.")
        except Exception as exc:
            errores += 1
            print(f"[ERROR] {serie['nombre']} ({serie['codigo']}): {exc}")
    print(f"\nResultado de prueba: {len(SERIES_BCCH) - errores}/{len(SERIES_BCCH)} series disponibles; {errores} errores.")
    if errores:
        print("No continúes con la carga definitiva hasta revisar los errores indicados.")
        return 1
    print("Prueba superada. Puedes ejecutar base_datos/cargar_series.py con la misma fecha de corte.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
