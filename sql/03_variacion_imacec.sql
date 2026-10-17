
-- Hito 2: Variación interanual del IMACEC
-- Se utiliza LAG() para recuperar el valor de 12 meses atrás.
-- Posteriormente se relaciona con la tasa de desempleo.

WITH imacec_historico AS (

    SELECT
        fecha,
        valor AS imacec_actual,

        LAG(valor, 12) OVER (
            ORDER BY fecha
        ) AS imacec_anterior

    FROM observaciones

    WHERE id_serie = 'F032.IMC.IND.Z.Z.EP18.Z.Z.0.M'

),

variaciones AS (

    SELECT
        fecha,
        imacec_actual,

        ROUND(
            (imacec_actual / NULLIF(imacec_anterior, 0) - 1) * 100,
            2
        ) AS variacion_interanual

    FROM imacec_historico

)

SELECT
    v.fecha,
    ROUND(v.imacec_actual, 2) AS imacec,
    v.variacion_interanual,
    ROUND(d.valor, 2) AS tasa_desempleo

FROM variaciones AS v

INNER JOIN observaciones AS d
    ON v.fecha = d.fecha
    AND d.id_serie = 'F049.DES.TAS.INE9.10.M'

WHERE v.variacion_interanual IS NOT NULL

ORDER BY v.fecha ASC;
