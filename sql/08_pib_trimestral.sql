
-- HITO 2
-- Analisis del PIB real trimestral
-- Calculo de variacion interanual

WITH pib AS (

    SELECT
        o.fecha,
        o.valor AS pib_real

    FROM observaciones AS o

    INNER JOIN series AS s
        ON o.id_serie = s.id_serie

    WHERE s.nombre = 'PIB total real'

),

pib_rezagos AS (

    SELECT
        fecha,
        pib_real,

        LAG(pib_real, 4) OVER (
            ORDER BY fecha
        ) AS pib_anio_anterior

    FROM pib

)

SELECT
    fecha,

    ROUND(pib_real, 2) AS pib_real,

    ROUND(
        100.0 *
        (pib_real / NULLIF(pib_anio_anterior, 0) - 1),
        2
    ) AS variacion_interanual

FROM pib_rezagos

ORDER BY fecha;
