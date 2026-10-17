
-- Hito 2: Relacion entre IMACEC y desempleo
-- Se calculan variaciones interanuales y rezagos

WITH imacec_base AS (
    SELECT
        fecha,
        valor,
        LAG(valor, 12) OVER (
            ORDER BY fecha
        ) AS valor_anterior
    FROM observaciones
    WHERE id_serie = 'F032.IMC.IND.Z.Z.EP18.Z.Z.0.M'
),

imacec_crecimiento AS (
    SELECT
        fecha,
        (valor / NULLIF(valor_anterior, 0) - 1) * 100
            AS crecimiento_imacec
    FROM imacec_base
),

imacec_rezagos AS (
    SELECT
        fecha,
        crecimiento_imacec AS imacec_actual,
        LAG(crecimiento_imacec, 3) OVER (
            ORDER BY fecha
        ) AS imacec_rezago_3,
        LAG(crecimiento_imacec, 6) OVER (
            ORDER BY fecha
        ) AS imacec_rezago_6,
        LAG(crecimiento_imacec, 12) OVER (
            ORDER BY fecha
        ) AS imacec_rezago_12
    FROM imacec_crecimiento
),

desempleo AS (
    SELECT
        fecha,
        valor AS tasa_desempleo,
        valor - LAG(valor, 12) OVER (
            ORDER BY fecha
        ) AS variacion_desempleo_pp
    FROM observaciones
    WHERE id_serie = 'F049.DES.TAS.INE9.10.M'
)

SELECT
    d.fecha,
    d.tasa_desempleo,
    d.variacion_desempleo_pp,
    i.imacec_actual,
    i.imacec_rezago_3,
    i.imacec_rezago_6,
    i.imacec_rezago_12

FROM desempleo AS d
INNER JOIN imacec_rezagos AS i
    ON d.fecha = i.fecha

WHERE d.variacion_desempleo_pp IS NOT NULL
  AND i.imacec_actual IS NOT NULL

ORDER BY d.fecha;
