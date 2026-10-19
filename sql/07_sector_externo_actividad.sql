
-- HITO 2
-- Analisis del sector externo y actividad economica
-- Precio del cobre, tipo de cambio,
-- produccion manufacturera y desempleo

WITH indicadores AS (

    SELECT
        o.fecha,

        MAX(CASE
            WHEN s.nombre = 'Precio del cobre refinado BML'
            THEN o.valor
        END) AS precio_cobre,

        MAX(CASE
            WHEN s.nombre = 'Tipo de cambio observado (CLP/USD)'
            THEN o.valor
        END) AS tipo_cambio,

        MAX(CASE
            WHEN s.nombre LIKE 'Índice de Producción Manufactur%'
            THEN o.valor
        END) AS produccion_manufacturera,

        MAX(CASE
            WHEN s.nombre = 'Tasa de desempleo nacional'
            THEN o.valor
        END) AS desempleo

    FROM observaciones AS o

    INNER JOIN series AS s
        ON o.id_serie = s.id_serie

    GROUP BY o.fecha
)

SELECT
    fecha,

    ROUND(precio_cobre, 2) AS precio_cobre,
    ROUND(tipo_cambio, 2) AS tipo_cambio,
    ROUND(produccion_manufacturera, 2)
        AS produccion_manufacturera,
    ROUND(desempleo, 2) AS tasa_desempleo

FROM indicadores

WHERE precio_cobre IS NOT NULL
  AND tipo_cambio IS NOT NULL
  AND produccion_manufacturera IS NOT NULL

ORDER BY fecha;
