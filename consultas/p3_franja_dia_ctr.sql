-- ============================================================================
-- Pregunta 3: Franja horaria y dia de la semana con mayor tasa de clics (CTR)
-- Solicitante: Camila (Atencion a Comercios) | Frecuencia: Mensual | Capa: Batch
-- ============================================================================
SELECT
    dia_semana,
    dia_nombre,
    franja_id,
    franja_horaria,
    total_impresiones,
    total_clics,
    tasa_ctr_pct
FROM read_parquet('datos/modelado/p3_franja_dia_ctr.parquet')
ORDER BY tasa_ctr_pct DESC;
