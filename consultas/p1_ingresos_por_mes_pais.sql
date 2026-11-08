-- ============================================================================
-- Pregunta 1: Clics validos e ingreso por mes y por pais en los ultimos 12 meses
-- Solicitante: Ricardo (CEO) | Frecuencia: Semanal / Mensual | Capa: Batch
-- ============================================================================
SELECT
    pais_code,
    pais_nombre,
    anio_mes,
    total_clics_validos,
    ingreso_usd,
    mes_parcial
FROM read_parquet('datos/modelado/p1_ingresos_mensuales.parquet')
ORDER BY anio_mes, pais_code;
