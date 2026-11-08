-- ============================================================================
-- Pregunta 2: Top 10 sitios por ingreso en los ultimos 12 meses y % clics invalidos
-- Solicitante: Natalia (Calidad de Trafico) | Frecuencia: Mensual | Capa: Batch
-- ============================================================================
SELECT
    sitio_id,
    sitio_nombre,
    pais_nombre,
    ingreso_usd,
    total_clics,
    clics_validos,
    clics_invalidos,
    pct_clics_invalidos
FROM read_parquet('datos/modelado/p2_top_sitios.parquet')
ORDER BY ingreso_usd DESC
LIMIT 10;
