
"""
Auditoría de integridad y calidad de la base de datos
del proyecto de proyección del desempleo en Chile.

La base se abre en modo de solo lectura.

Se comprueba:
- Integridad física y referencial.
- Duplicados y valores nulos.
- Fechas y valores inválidos.
- Continuidad mensual y trimestral.
- Estadísticas descriptivas.
- Coherencia económica básica.
- Disponibilidad de metadatos locales.

No se modifican ni eliminan observaciones.
"""

from pathlib import Path
from contextlib import closing

import sqlite3
import numpy as np
import pandas as pd


# CONFIGURACIÓN


ROOT = Path(__file__).resolve().parent.parent

DB = ROOT / "base_datos" / "desempleo_chile.db"

OUT = ROOT / "resultados"

FRECUENCIAS = {
    "M": "M",
    "MENSUAL": "M",
    "T": "Q-DEC",
    "Q": "Q-DEC",
    "TRIMESTRAL": "Q-DEC",
    "QUARTERLY": "Q-DEC"
}


# FUNCIONES AUXILIARES


def contar(conexion, consulta):

    return conexion.execute(
        consulta
    ).fetchone()[0]


def registrar(resultados, prueba, cantidad, detalle=""):

    resultados.append({
        "comprobacion": prueba,
        "incidencias": cantidad,
        "estado": "OK" if cantidad == 0 else "REVISAR",
        "detalle": detalle
    })


def obtener_metadato(fila, opciones):

    for columna in opciones:

        valor = fila.get(columna)

        if pd.notna(valor) and str(valor).strip():
            return str(valor).strip()

    return ""



# AUDITORÍA GENERAL DE SQLITE


def auditar_sqlite(conexion):

    resultados = []

    tablas = pd.read_sql_query(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """,
        conexion
    )["name"].tolist()

    print("\nTABLAS EXISTENTES")

    for tabla in tablas:
        print("-", tabla)

    if not {"series", "observaciones"}.issubset(tablas):

        raise ValueError(
            "Faltan tablas necesarias en la base."
        )

    # Integridad física de SQLite.

    integridad = conexion.execute(
        "PRAGMA integrity_check"
    ).fetchall()

    registrar(
        resultados,
        "Integridad SQLite",
        0 if integridad == [("ok",)] else len(integridad),
        " | ".join(str(x[0]) for x in integridad)
    )

    # Claves foráneas.

    claves = conexion.execute(
        "PRAGMA foreign_key_check"
    ).fetchall()

    registrar(
        resultados,
        "Violaciones de claves foráneas",
        len(claves)
    )

    consultas = {

        "Grupos de observaciones duplicadas": """
            SELECT COUNT(*)
            FROM (
                SELECT id_serie, fecha
                FROM observaciones
                GROUP BY id_serie, fecha
                HAVING COUNT(*) > 1
            )
        """,

        "Observaciones con datos nulos": """
            SELECT COUNT(*)
            FROM observaciones
            WHERE fecha IS NULL
               OR valor IS NULL
               OR id_serie IS NULL
        """,

        "Observaciones sin serie asociada": """
            SELECT COUNT(*)
            FROM observaciones o
            LEFT JOIN series s
                ON o.id_serie = s.id_serie
            WHERE s.id_serie IS NULL
        """,

        "Valores almacenados como no numéricos": """
            SELECT COUNT(*)
            FROM observaciones
            WHERE valor IS NOT NULL
              AND typeof(valor) NOT IN ('integer', 'real')
        """,

        "Identificadores de serie duplicados": """
            SELECT COUNT(*)
            FROM (
                SELECT id_serie
                FROM series
                GROUP BY id_serie
                HAVING COUNT(*) > 1
            )
        """,

        "Series sin identificador o nombre": """
            SELECT COUNT(*)
            FROM series
            WHERE id_serie IS NULL
               OR TRIM(id_serie) = ''
               OR nombre IS NULL
               OR TRIM(nombre) = ''
        """,

        "Series sin observaciones": """
            SELECT COUNT(*)
            FROM series s
            WHERE NOT EXISTS (
                SELECT 1
                FROM observaciones o
                WHERE o.id_serie = s.id_serie
            )
        """

    }

    for prueba, consulta in consultas.items():

        registrar(
            resultados,
            prueba,
            contar(conexion, consulta)
        )

    return resultados


# AUDITORÍA INDIVIDUAL DE LAS SERIES


def auditar_series(series, observaciones):

    filas = []

    for _, fila in series.iterrows():

        codigo = fila["id_serie"]
        nombre = fila["nombre"]

        frecuencia = obtener_metadato(
            fila,
            ["frecuencia", "frequency"]
        ).upper()

        periodo = FRECUENCIAS.get(frecuencia)

        unidad = obtener_metadato(
            fila,
            ["unidad", "unidad_medida", "unidad_de_medida"]
        )

        fuente = obtener_metadato(
            fila,
            ["fuente", "source"]
        )

        tema = obtener_metadato(
            fila,
            ["tema", "categoria"]
        )

        datos = observaciones.loc[
            observaciones["id_serie"] == codigo
        ].copy()

        fechas_validas = datos["fecha_dt"].dropna()

        valores_validos = datos.loc[
            np.isfinite(datos["valor_num"]),
            "valor_num"
        ]

        invalidas = int(
            datos["fecha_dt"].isna().sum()
        )

        valores_invalidos = int(
            (~np.isfinite(datos["valor_num"])).sum()
        )

        duplicados = int(
            datos.duplicated(
                subset=["fecha"]
            ).sum()
        )

        faltantes = []
        duplicados_periodo = None
        total_esperado = None
        periodos_observados = None
        periodos_sin_valor = None


        # CONTINUIDAD TEMPORAL


        if periodo is not None and not fechas_validas.empty:

            indice = pd.PeriodIndex(
                fechas_validas.dt.to_period(periodo)
            )

            periodos_unicos = indice.unique().sort_values()

            calendario = pd.period_range(
                start=indice.min(),
                end=indice.max(),
                freq=periodo
            )

            faltantes = calendario.difference(
                periodos_unicos
            ).astype(str).tolist()

            total_esperado = len(calendario)

            periodos_observados = len(periodos_unicos)

            duplicados_periodo = int(
                indice.duplicated().sum()
            )

            # Comprobar períodos que tienen fecha,
            # pero carecen de un valor numérico válido.

            mascara = (
                datos["fecha_dt"].notna()
                & np.isfinite(datos["valor_num"])
            )

            periodos_con_valor = pd.PeriodIndex(
                datos.loc[mascara, "fecha_dt"]
                .dt.to_period(periodo)
            ).unique()

            periodos_sin_valor = len(
                periodos_unicos.difference(
                    periodos_con_valor
                )
            )


        # COHERENCIA ECONÓMICA BÁSICA


        fuera_rango = 0
        regla = "Sin regla específica aplicada"

        if nombre == "Tasa de desempleo nacional":

            regla = "Tasa entre 0 y 100 por ciento"

            fuera_rango = int(
                (
                    (valores_validos < 0)
                    | (valores_validos > 100)
                ).sum()
            )

        elif nombre in [
            "IMACEC total",
            "Índice de Producción Manufacturera",
            "Tipo de cambio observado (CLP/USD)",
            "Precio del cobre refinado BML"
        ]:

            regla = "Valores estrictamente positivos"

            fuera_rango = int(
                (valores_validos <= 0).sum()
            )

        # No se eliminan valores extremos.
        # Una observación extraordinaria puede
        # representar un acontecimiento económico real.

        problemas = (
            len(datos) == 0
            or invalidas > 0
            or valores_invalidos > 0
            or duplicados > 0
            or len(faltantes) > 0
            or duplicados_periodo not in [None, 0]
            or periodos_sin_valor not in [None, 0]
            or fuera_rango > 0
            or periodo is None
        )

        estado = "REVISAR" if problemas else "OK"


        # RESUMEN POR SERIE


        filas.append({

            "id_serie": codigo,

            "nombre": nombre,

            "tema": tema,

            "frecuencia": frecuencia,

            "unidad_registrada": unidad,

            "fuente_registrada": fuente,

            "observaciones": len(datos),

            "inicio": (
                fechas_validas.min().strftime("%Y-%m-%d")
                if not fechas_validas.empty else ""
            ),

            "fin": (
                fechas_validas.max().strftime("%Y-%m-%d")
                if not fechas_validas.empty else ""
            ),

            "periodos_esperados": total_esperado,

            "periodos_observados": periodos_observados,

            "periodos_faltantes": (
                len(faltantes)
                if total_esperado is not None else None
            ),

            "detalle_faltantes": "; ".join(faltantes),

            "periodos_sin_valor_valido": periodos_sin_valor,

            "duplicados_fecha": duplicados,

            "duplicados_periodo": duplicados_periodo,

            "fechas_invalidas": invalidas,

            "valores_invalidos": valores_invalidos,

            "minimo": valores_validos.min(),

            "maximo": valores_validos.max(),

            "media": valores_validos.mean(),

            "desviacion_estandar": valores_validos.std(),

            "regla_economica": regla,

            "valores_fuera_rango": fuera_rango,

            "estado": estado

        })

    return pd.DataFrame(filas)



# PROGRAMA PRINCIPAL


def main():

    if not DB.is_file():

        raise FileNotFoundError(
            f"No existe la base: {DB}"
        )

    OUT.mkdir(exist_ok=True)

    print("\nAUDITORÍA DE INTEGRIDAD Y CALIDAD")
    print("=" * 60)

    # Abrir la base exclusivamente en modo lectura.

    uri = DB.resolve().as_uri() + "?mode=ro"

    with closing(sqlite3.connect(uri, uri=True)) as conexion:

        conexion.execute("BEGIN")

        resultados = auditar_sqlite(conexion)

        series = pd.read_sql_query(
            "SELECT * FROM series ORDER BY nombre",
            conexion
        )

        observaciones = pd.read_sql_query(
            """
            SELECT id_serie, fecha, valor
            FROM observaciones
            ORDER BY id_serie, fecha
            """,
            conexion
        )


    # VALIDACIÓN DE FECHAS Y VALORES


    observaciones["fecha_dt"] = pd.to_datetime(
        observaciones["fecha"],
        format="%Y-%m-%d",
        errors="coerce"
    )

    observaciones["valor_num"] = pd.to_numeric(
        observaciones["valor"],
        errors="coerce"
    ).astype(float)

    registrar(
        resultados,
        "Fechas inválidas o ausentes",
        int(observaciones["fecha_dt"].isna().sum())
    )

    registrar(
        resultados,
        "Valores nulos, no convertibles o infinitos",
        int(
            (~np.isfinite(observaciones["valor_num"])).sum()
        )
    )

    resumen = auditar_series(
        series,
        observaciones
    )

    registrar(
        resultados,
        "Series con incidencias",
        int((resumen["estado"] == "REVISAR").sum())
    )

    general = pd.DataFrame(resultados)


    # EXPORTACIÓN DE EVIDENCIA


    general.to_csv(
        OUT / "auditoria_integridad_general.csv",
        index=False,
        encoding="utf-8-sig"
    )

    resumen.to_csv(
        OUT / "auditoria_integridad_series.csv",
        index=False,
        encoding="utf-8-sig"
    )


    # RESULTADOS EN TERMINAL


    print("\nRESUMEN GENERAL")
    print("=" * 60)

    print(f"Total de series: {len(series)}")

    print(
        f"Total de observaciones: {len(observaciones)}"
    )

    print("\nCOLUMNAS DE METADATOS DISPONIBLES")

    print(", ".join(series.columns))

    print("\nCOMPROBACIONES DE INTEGRIDAD")

    print(
        general.to_string(index=False)
    )

    print("\nCONTINUIDAD TEMPORAL POR SERIE")

    columnas = [
        "nombre",
        "frecuencia",
        "observaciones",
        "inicio",
        "fin",
        "periodos_esperados",
        "periodos_faltantes",
        "duplicados_periodo",
        "estado"
    ]

    print(
        resumen[columnas].to_string(index=False)
    )

    print("\nESTADÍSTICAS DESCRIPTIVAS")

    columnas = [
        "nombre",
        "minimo",
        "maximo",
        "media",
        "desviacion_estandar",
        "valores_fuera_rango"
    ]

    print(
        resumen[columnas].to_string(
            index=False,
            float_format=lambda x: f"{x:.4f}"
        )
    )

    print("\nINVENTARIO DE METADATOS LOCALES")

    print(
        resumen[[
            "id_serie",
            "nombre",
            "frecuencia",
            "unidad_registrada",
            "fuente_registrada"
        ]].to_string(index=False)
    )

    print("\nDETALLE DE INCIDENCIAS")

    incidencias = resumen.loc[
        resumen["estado"] == "REVISAR"
    ]

    if incidencias.empty:

        print(
            "No se detectaron incidencias por serie "
            "en los controles aplicados."
        )

    else:

        print(
            incidencias[[
                "nombre",
                "detalle_faltantes",
                "fechas_invalidas",
                "valores_invalidos",
                "duplicados_fecha",
                "duplicados_periodo",
                "periodos_sin_valor_valido",
                "valores_fuera_rango"
            ]].to_string(index=False)
        )


    # CONCLUSIÓN

    print("\nRESULTADO DE LA AUDITORÍA")

    if (general["estado"] == "REVISAR").any():

        print(
            "Se detectaron incidencias que "
            "requieren revisión."
        )

    else:

        print(
            "Controles internos de integridad "
            "superados."
        )

    print("\nARCHIVOS GENERADOS")

    print("resultados/auditoria_integridad_general.csv")

    print("resultados/auditoria_integridad_series.csv")

    print("\nAUDITORÍA FINALIZADA.")

    print(
        "La base de datos no fue modificada."
    )

    print(
        "La continuidad se comprueba entre la "
        "primera y última fecha de cada serie."
    )

    print(
        "La ausencia de incidencias internas no "
        "certifica la exactitud de los datos originales."
    )

    print(
        "Pendiente: contrastar códigos, unidades, "
        "fuentes y fechas de publicación oficiales."
    )


if __name__ == "__main__":
    main()
