
-- HITO 2
-- Analisis de inflacion y politica monetaria
-- Relacionar IPC anual, TPM y desempleo por fecha

WITH indicadores AS (

    SELECT
        o.fecha,

        MAX(CASE
            WHEN s.nombre = 'Inflación IPC anual'
            THEN o.valor
        END) AS inflacion_anual,

        MAX(CASE
            WHEN s.nombre = 'Tasa de Política Monetaria (TPM)'
            THEN o.valor
        END) AS tpm,

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

    ROUND(inflacion_anual, 2) AS inflacion_anual,
    ROUND(tpm, 2) AS tpm,
    ROUND(desempleo, 2) AS tasa_desempleo

FROM indicadores

WHERE inflacion_anual IS NOT NULL
  AND tpm IS NOT NULL

ORDER BY fecha;
