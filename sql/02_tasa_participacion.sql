
-- Hito 2: Calcular la tasa de participación laboral
-- Fuente: series oficiales del Banco Central
-- Fórmula: Fuerza de trabajo / Población 15+ * 100

SELECT
    f.fecha,
    ROUND(
        (f.valor * 100.0) / NULLIF(p.valor, 0),
        2
    ) AS tasa_participacion

FROM observaciones AS f

INNER JOIN observaciones AS p
    ON f.fecha = p.fecha

WHERE f.id_serie = 'F049.FTR.PMT.INE9.01.M'
  AND p.id_serie = 'F049.POB.PMT.INE9.01.M'
  AND f.valor IS NOT NULL
  AND p.valor > 0

ORDER BY f.fecha ASC;
