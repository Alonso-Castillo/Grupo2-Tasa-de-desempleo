"""Carga segura de series BDE en SQLite.

Por defecto simula. --aplicar autoriza escritura y revisiones históricas.
--permitir-recorte autoriza eliminar fechas posteriores al corte.
El corte se refiere al período observado, no a la fecha de publicación.
"""

from __future__ import annotations

import argparse
import calendar
import csv
import math
import os
import sqlite3
import sys

from contextlib import closing
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

RUTA_PROYECTO = Path(__file__).resolve().parent.parent

RUTA_DB = (
    RUTA_PROYECTO
    / "base_datos"
    / "desempleo_chile.db"
)

CODIGO_TPM_DIARIA = "F022.TPM.TIN.D001.NO.Z.D"

TOLERANCIA = 1e-6


# ============================================================
# ARGUMENTOS DE EJECUCIÓN
# ============================================================

def argumentos():

    parser = argparse.ArgumentParser(
        description=__doc__
    )

    parser.add_argument(
        "--hasta",
        required=True,
        help="Fecha de corte AAAA-MM-DD (fin de mes)."
    )

    modo = parser.add_mutually_exclusive_group()

    modo.add_argument(
        "--simular",
        action="store_true",
        help="Solo lectura (modo predeterminado)."
    )

    modo.add_argument(
        "--aplicar",
        action="store_true",
        help="Autoriza actualizar SQLite y valores históricos."
    )

    parser.add_argument(
        "--permitir-recorte",
        action="store_true",
        help=(
            "Autoriza eliminar observaciones posteriores "
            "al corte al aplicar."
        )
    )

    return parser.parse_args()


# ============================================================
# VALIDACIÓN DE LA FECHA DE CORTE
# ============================================================

def validar_corte(texto):

    corte = date.fromisoformat(texto)

    if corte >= date.today():
        raise ValueError(
            "El corte debe ser anterior a hoy."
        )

    ultimo_dia = calendar.monthrange(
        corte.year,
        corte.month
    )[1]

    if corte.day != ultimo_dia:
        raise ValueError(
            "Utiliza el último día de un mes cerrado."
        )

    return corte


# ============================================================
# DESCARGA Y VALIDACIÓN DE SERIES ECONÓMICAS
# ============================================================

def descargar(siete, serie, corte):

    codigo = serie["codigo"]
    columna = serie["columna"]

    frecuencia = serie.get("frecuencia", "M")

    if frecuencia not in {"M", "T"}:
        raise ValueError(
            f"Frecuencia no admitida: {frecuencia}"
        )

    es_tpm = columna == "TPM"

    inicio = pd.Timestamp(serie["desde"])
    fin = pd.Timestamp(corte)

    codigo_descarga = (
        CODIGO_TPM_DIARIA
        if es_tpm
        else codigo
    )

    datos = siete.cuadro(
        series=[codigo_descarga],
        desde=serie["desde"],
        hasta=corte.isoformat(),
        nombres=[columna]
    )

    if (
        datos is None
        or datos.empty
        or columna not in datos.columns
    ):
        raise ValueError(
            "La API no devolvió la columna esperada con datos."
        )

    fechas = pd.to_datetime(
        datos.index,
        errors="raise"
    )

    if fechas.hasnans:
        raise ValueError(
            "Fechas ausentes en la respuesta API."
        )

    if fechas.tz is not None:
        fechas = fechas.tz_localize(None)

    valores = pd.Series(
        datos[columna].to_numpy(),
        index=fechas.normalize()
    )

    valores = valores.loc[
        (valores.index >= inicio)
        & (valores.index <= fin)
    ].sort_index()

    if valores.index.has_duplicates:
        raise ValueError(
            "Fechas duplicadas en la respuesta API."
        )

    numericos = pd.to_numeric(
        valores,
        errors="coerce"
    )

    if (
        valores.notna()
        & numericos.isna()
    ).any():
        raise ValueError(
            "Se detectaron valores no numéricos."
        )

    if not all(
        math.isfinite(float(v))
        for v in numericos.dropna()
    ):
        raise ValueError(
            "Se detectaron valores infinitos."
        )

    # La TPM mensual se construye mediante el promedio
    # de las observaciones diarias disponibles.
    # No se imputan días faltantes.

    if es_tpm:
        numericos = numericos.resample("MS").mean()

    periodo = (
        "M"
        if frecuencia == "M"
        else "Q-DEC"
    )

    numericos.index = numericos.index.to_period(
        periodo
    )

    if numericos.index.has_duplicates:
        raise ValueError(
            "Más de una observación para el mismo período."
        )

    validos = numericos.dropna()

    if validos.empty:
        raise ValueError(
            "No hay observaciones válidas dentro del corte."
        )

    # Excluir períodos que todavía no han finalizado.

    validos = validos.loc[
        validos.index.end_time.normalize() <= fin
    ]

    if validos.empty:
        raise ValueError(
            "No hay períodos cerrados con datos válidos."
        )

    esperados = pd.period_range(
        inicio.to_period(periodo),
        validos.index.max(),
        freq=periodo
    )

    faltantes = esperados.difference(
        validos.index
    )

    if len(faltantes):

        detalle = list(
            map(str, faltantes[:12])
        )

        raise ValueError(
            f"Períodos faltantes desde el inicio: {detalle}"
        )

    # Los períodos finales sin observaciones pueden
    # corresponder a rezagos de publicación.

    pendientes = pd.period_range(
        validos.index.max() + 1,
        fin.to_period(periodo),
        freq=periodo
    )

    pendientes = pendientes[
        pendientes.end_time.normalize() <= fin
    ]

    if len(pendientes):

        detalle = ", ".join(
            map(str, pendientes)
        )

        print(
            "  Aviso: períodos cerrados finales "
            f"sin dato API: {detalle}"
        )

    return {
        p.start_time.date().isoformat(): float(v)
        for p, v in validos.items()
    }


# ============================================================
# CONTROL DE INTEGRIDAD SQLITE
# ============================================================

def comprobar_integridad(con):

    resultado = con.execute(
        "PRAGMA integrity_check"
    ).fetchall()

    if resultado != [("ok",)]:
        raise ValueError(
            "SQLite no supera integrity_check."
        )

    relaciones = con.execute(
        "PRAGMA foreign_key_check"
    ).fetchone()

    if relaciones is not None:
        raise ValueError(
            "Existen violaciones de claves foráneas."
        )


# ============================================================
# COMPARACIÓN ENTRE API Y BASE LOCAL
# ============================================================

def comparar(con, descargas, corte):

    cambios = []
    problemas = []

    recortes = 0

    for serie, nuevos in descargas:

        codigo = serie["codigo"]

        actuales = dict(
            con.execute(
                """
                SELECT fecha, valor
                FROM observaciones
                WHERE id_serie = ?
                """,
                (codigo,)
            )
        )

        altas = 0
        revisiones = 0
        menores = 0
        iguales = 0
        bajas = 0
        faltan = 0

        for fecha, valor in sorted(nuevos.items()):

            if fecha not in actuales:

                altas += 1

                cambios.append(
                    (
                        codigo,
                        fecha,
                        "nueva",
                        None,
                        valor
                    )
                )

                continue

            anterior = actuales[fecha]

            if anterior == valor:

                iguales += 1

            else:

                if (
                    anterior is None
                    or not math.isfinite(float(anterior))
                    or abs(valor - float(anterior)) > TOLERANCIA
                ):

                    tipo = "revision"
                    revisiones += 1

                else:

                    tipo = "diferencia_menor"
                    menores += 1

                cambios.append(
                    (
                        codigo,
                        fecha,
                        tipo,
                        anterior,
                        valor
                    )
                )

        for fecha, valor in sorted(actuales.items()):

            if fecha > corte.isoformat():

                bajas += 1

                cambios.append(
                    (
                        codigo,
                        fecha,
                        "recorte",
                        valor,
                        None
                    )
                )

            elif fecha not in nuevos:

                faltan += 1

                cambios.append(
                    (
                        codigo,
                        fecha,
                        "local_no_devuelta",
                        valor,
                        None
                    )
                )

        if faltan:

            problemas.append(
                f"{codigo}: {faltan} fechas locales "
                "dentro del corte no devueltas por API"
            )

        recortes += bajas

        print(
            f"{serie['nombre']}: "
            f"API={len(nuevos)}, "
            f"locales={len(actuales)}, "
            f"iguales={iguales}, "
            f"nuevas={altas}, "
            f"revisiones={revisiones}, "
            f"diferencias menores={menores}, "
            f"recortes={bajas}, "
            f"locales no devueltas={faltan}"
        )

    return cambios, problemas, recortes


# ============================================================
# RESPALDO Y REGISTRO DE CAMBIOS
# ============================================================

def guardar_respaldo(ruta, cambios, corte):

    marca = (
        datetime.now(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        + "_"
        + uuid4().hex[:8]
    )

    respaldo = ruta.with_name(
        f"desempleo_chile_respaldo_{marca}.db"
    )

    reporte = ruta.with_name(
        f"cambios_carga_{marca}.csv"
    )

    # El respaldo se realiza mediante la API de SQLite,
    # conservando el estado confirmado de la base.

    with closing(
        sqlite3.connect(
            ruta.as_uri() + "?mode=ro",
            uri=True
        )
    ) as origen:

        with closing(
            sqlite3.connect(respaldo)
        ) as destino:

            origen.backup(destino)

            comprobar_integridad(destino)

    with reporte.open(
        "x",
        encoding="utf-8-sig",
        newline=""
    ) as archivo:

        writer = csv.writer(archivo)

        writer.writerow(
            [
                "id_serie",
                "fecha",
                "tipo",
                "valor_anterior",
                "valor_api",
                "corte",
                "consulta_utc"
            ]
        )

        writer.writerows(
            [
                (*c, corte.isoformat(), marca)
                for c in cambios
            ]
        )

    print(f"\nRespaldo previo: {respaldo}")

    print(
        f"Registro de cambios propuestos: {reporte}"
    )


# ============================================================
# ESCRITURA SEGURA EN SQLITE
# ============================================================

def escribir(
    con,
    descargas,
    corte,
    permitir_recorte
):

    for serie, datos in descargas:

        codigo = serie["codigo"]

        con.execute(
            """
            INSERT OR IGNORE INTO temas (
                id_tema,
                tema
            )
            VALUES (?, ?)
            """,
            (
                serie["tema_id"],
                serie["tema"]
            )
        )

        tema = con.execute(
            """
            SELECT tema
            FROM temas
            WHERE id_tema = ?
            """,
            (serie["tema_id"],)
        ).fetchone()

        if tema != (serie["tema"],):

            raise ValueError(
                "Tema incompatible con el catálogo: "
                f"{serie['tema']}"
            )

        fuente = (
            "INE - BDE Banco Central"
            if serie["columna"] == "Desempleo_nacional"
            else "BDE Banco Central de Chile"
        )

        if serie["columna"] == "TPM":

            fuente += (
                "; promedio mensual de observaciones "
                f"diarias ({CODIGO_TPM_DIARIA})"
            )

        con.execute(
            """
            INSERT INTO series (
                id_serie,
                nombre,
                fuente,
                frecuencia,
                unidad,
                id_tema
            )
            VALUES (?, ?, ?, ?, ?, ?)

            ON CONFLICT(id_serie) DO UPDATE SET
                nombre = excluded.nombre,
                fuente = excluded.fuente,
                frecuencia = excluded.frecuencia,
                unidad = excluded.unidad,
                id_tema = excluded.id_tema
            """,
            (
                codigo,
                serie["nombre"],
                fuente,
                serie.get("frecuencia", "M"),
                serie["unidad"],
                serie["tema_id"]
            )
        )

        if permitir_recorte:

            con.execute(
                """
                DELETE FROM observaciones
                WHERE id_serie = ?
                AND fecha > ?
                """,
                (
                    codigo,
                    corte.isoformat()
                )
            )

        registros = [
            (codigo, fecha, valor)
            for fecha, valor in datos.items()
        ]

        con.executemany(
            """
            INSERT INTO observaciones (
                id_serie,
                fecha,
                valor
            )
            VALUES (?, ?, ?)

            ON CONFLICT(id_serie, fecha)
            DO UPDATE SET
                valor = excluded.valor
            """,
            registros
        )

        almacenados = dict(
            con.execute(
                """
                SELECT fecha, valor
                FROM observaciones
                WHERE id_serie = ?
                """,
                (codigo,)
            )
        )

        if almacenados != datos:

            raise ValueError(
                "Verificación posterior a la escritura "
                f"fallida: {codigo}"
            )

    comprobar_integridad(con)


# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================

def main():

    args = argumentos()

    try:

        corte = validar_corte(args.hasta)

        if not RUTA_DB.is_file():

            raise ValueError(
                "No existe la base de datos. "
                "Ejecuta primero crear_base.py "
                "en una copia de trabajo si corresponde."
            )

        from dotenv import load_dotenv
        import bcchapi

        sys.path.insert(
            0,
            str(RUTA_PROYECTO)
        )

        from src.config import SERIES_BCCH

        load_dotenv(
            RUTA_PROYECTO / ".env"
        )

        token = os.getenv(
            "BCCH_API_TOKEN",
            ""
        ).strip()

        if not token or token == "PEGA_AQUI_TU_TOKEN":

            raise ValueError(
                "Falta configurar BCCH_API_TOKEN en .env."
            )

        codigos = {
            s["codigo"]
            for s in SERIES_BCCH
        }

        if (
            len(SERIES_BCCH) != 12
            or len(codigos) != 12
        ):

            raise ValueError(
                "Se esperaban 12 códigos distintos "
                "en el catálogo actual."
            )

        siete = bcchapi.Siete(token=token)

        descargas = []
        errores = []

        modo = (
            "APLICAR"
            if args.aplicar
            else "SIMULACIÓN"
        )

        print("\nCARGA SEGURA DE SERIES ECONÓMICAS")
        print("=" * 70)

        print(f"Modo: {modo}")
        print(f"Fecha de corte: {corte}")
        print("Fuente: Banco Central de Chile")

        print("\nDESCARGA Y VALIDACIÓN")
        print("-" * 70)

        for serie in SERIES_BCCH:

            try:

                datos = descargar(
                    siete,
                    serie,
                    corte
                )

                descargas.append(
                    (serie, datos)
                )

                print(
                    f"[OK] {serie['nombre']}: "
                    f"{len(datos)} observaciones"
                )

            except Exception as exc:

                # Evitar mostrar credenciales en errores
                # producidos durante las solicitudes.

                detalle = (
                    str(exc)
                    if isinstance(exc, ValueError)
                    and token not in str(exc)
                    else type(exc).__name__
                )

                errores.append(
                    serie["codigo"]
                )

                print(
                    f"[ERROR] {serie['codigo']}: "
                    f"{detalle}"
                )

        if errores:

            raise ValueError(
                f"Fallaron {len(errores)} series. "
                "No se inició ninguna escritura."
            )

        modo_sqlite = (
            "?mode=rw"
            if args.aplicar
            else "?mode=ro"
        )

        uri = RUTA_DB.as_uri() + modo_sqlite

        with closing(
            sqlite3.connect(
                uri,
                uri=True,
                timeout=30
            )
        ) as con:

            con.execute(
                "PRAGMA foreign_keys = ON"
            )

            if not args.aplicar:

                con.execute(
                    "PRAGMA query_only = ON"
                )

            con.execute(
                "BEGIN IMMEDIATE"
                if args.aplicar
                else "BEGIN"
            )

            try:

                comprobar_integridad(con)

                print("\nCOMPARACIÓN CON SQLITE")
                print("-" * 70)

                cambios, problemas, recortes = comparar(
                    con,
                    descargas,
                    corte
                )

                print("\nDETALLE DE DIFERENCIAS")

                for (
                    codigo,
                    fecha,
                    tipo,
                    anterior,
                    nuevo
                ) in cambios:

                    if tipo in {
                        "revision",
                        "local_no_devuelta"
                    }:

                        print(
                            f"  {codigo} | "
                            f"{fecha} | "
                            f"{tipo} | "
                            f"local={anterior} | "
                            f"API={nuevo}"
                        )

                for problema in problemas:

                    print(
                        f"[BLOQUEO] {problema}"
                    )

                if recortes and not args.permitir_recorte:

                    print(
                        f"[BLOQUEO] {recortes} observaciones "
                        "posteriores al corte; se requiere "
                        "--permitir-recorte para aplicar."
                    )

                # Modo de simulación: no realizar escritura.

                if not args.aplicar:

                    con.rollback()

                    print("\nSIMULACIÓN FINALIZADA.")
                    print("SQLite no fue modificada.")

                    print(
                        "La TPM usa las observaciones "
                        "diarias disponibles; no se "
                        "certifica su cobertura diaria."
                    )

                    print(
                        "El corte no reconstruye versiones "
                        "históricas ni fechas de publicación."
                    )

                    return 1 if problemas else 0

                # Modo de aplicación: verificar condiciones
                # antes de modificar la base de datos.

                if problemas or (
                    recortes
                    and not args.permitir_recorte
                ):

                    raise ValueError(
                        "Carga bloqueada por discrepancias "
                        "de cobertura o recortes no autorizados."
                    )

                guardar_respaldo(
                    RUTA_DB,
                    cambios,
                    corte
                )

                escribir(
                    con,
                    descargas,
                    corte,
                    args.permitir_recorte
                )

                # Confirmar todas las series juntas.

                con.commit()

                print(
                    "\nCARGA FINALIZADA: "
                    "12 series confirmadas en una "
                    "única transacción."
                )

            except BaseException:

                con.rollback()

                raise

        print(
            "La TPM se calcula con las observaciones "
            "diarias disponibles; no se certifica "
            "su cobertura diaria."
        )

        print(
            "La fecha de corte no reconstruye versiones "
            "históricas ni fechas de publicación."
        )

        return 0

    except Exception as exc:

        detalle = (
            str(exc)
            if isinstance(exc, ValueError)
            else type(exc).__name__
        )

        print(
            f"[ERROR] {detalle}",
            file=sys.stderr
        )

        return 1


if __name__ == "__main__":

    raise SystemExit(main())