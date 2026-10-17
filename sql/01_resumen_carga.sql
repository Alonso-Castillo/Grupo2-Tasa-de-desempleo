
-- Hito 2: Verificar las series almacenadas
-- Se relacionan las tres tablas y se cuentan
-- las observaciones disponibles por indicador.

SELECT
    t.tema AS tema,
    s.nombre AS indicador,
    s.frecuencia,
    COUNT(o.fecha) AS total_observaciones,
    MIN(o.fecha) AS primera_fecha,
    MAX(o.fecha) AS ultima_fecha

FROM series AS s

INNER JOIN temas AS t
    ON s.id_tema = t.id_tema

LEFT JOIN observaciones AS o
    ON s.id_serie = o.id_serie

GROUP BY
    t.id_tema,
    t.tema,
    s.id_serie,
    s.nombre,
    s.frecuencia

ORDER BY s.nombre;
