
-- HITO 2
-- Analisis de coyuntura del mercado laboral
-- Se relacionan los indicadores por fecha

WITH indicadores AS (

    SELECT
        o.fecha,

        MAX(CASE
            WHEN s.nombre = 'Tasa de desempleo nacional'
            THEN o.valor
        END) AS desempleo,

        MAX(CASE
            WHEN s.nombre = 'Personas ocupadas, total nacional'
            THEN o.valor
        END) AS ocupados,

        MAX(CASE
            WHEN s.nombre = 'Fuerza de trabajo nacional'
            THEN o.valor
        END) AS fuerza_trabajo,

        MAX(CASE
            WHEN s.nombre = 'Población de 15 años y más'
            THEN o.valor
        END) AS poblacion,

        MAX(CASE
            WHEN s.nombre = 'Índice de Avisos Laborales de Internet (IALI)'
            THEN o.valor
        END) AS iali

    FROM observaciones AS o

    INNER JOIN series AS s
        ON o.id_serie = s.id_serie

    GROUP BY o.fecha
)

SELECT
    fecha,

    ROUND(desempleo, 2) AS tasa_desempleo,

    ROUND(ocupados, 2) AS personas_ocupadas,

    ROUND(fuerza_trabajo, 2) AS fuerza_trabajo,

    ROUND(
        (fuerza_trabajo * 100.0)
        / NULLIF(poblacion, 0),
        2
    ) AS tasa_participacion,

    ROUND(iali, 2) AS iali

FROM indicadores

WHERE desempleo IS NOT NULL

ORDER BY fecha;
