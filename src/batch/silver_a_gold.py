"""Generador de Capa Gold (Modelos analiticos, baselines de 8/4 semanas, incidente 15-sep y watermark)."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.batch.motor import MotorDuckDB
from src.core.config import (
    CORTE_HISTORICO_TS,
    DIR_LIMPIO,
    DIR_MODELADO,
    VENTANA_4_SEMANAS_S,
    VENTANA_8_SEMANAS_S,
)


class AgregadorSilverGold:
    """Precomputa vistas Gold (P1, P2, P3, P7, P8, P9, P10, 15-sep) con escritura atomica."""

    def __init__(
        self,
        dir_limpio: Path = DIR_LIMPIO,
        dir_modelado: Path = DIR_MODELADO,
        motor: MotorDuckDB | None = None,
    ) -> None:
        self.dir_limpio = dir_limpio
        self.dir_modelado = dir_modelado
        self.motor = motor or MotorDuckDB()

    def _copiar_atomico(self, sql_query: str, ruta_destino: Path) -> None:
        """Ejecuta COPY hacia un archivo .tmp.parquet y reemplaza atomicamente el destino."""
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        ruta_tmp = ruta_destino.with_suffix(".tmp.parquet")
        self.motor.ejecutar(f"COPY ({sql_query}) TO '{ruta_tmp}' (FORMAT 'PARQUET', COMPRESSION 'ZSTD');")
        ruta_tmp.replace(ruta_destino)

    def _obtener_max_ts(self) -> int:
        """Obtiene el maximo timestamp consolidado en Silver (o CORTE_HISTORICO_TS por defecto)."""
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        con = self.motor.conectar()
        fila = con.execute(
            f"SELECT COALESCE(MAX(ts), {CORTE_HISTORICO_TS})::BIGINT "
            f"FROM read_parquet('{ruta_clics}', hive_partitioning=true)"
        ).fetchone()
        return int(fila[0]) if fila and fila[0] is not None else CORTE_HISTORICO_TS

    def generar_p1_ingresos_mensuales(self) -> dict[str, Any]:
        """P1: Clics validos e ingreso por mes y pais (ultimos 12 meses).

        Regla Aclaraciones: Meses calendario en hora local. El primer y el ultimo mes del
        periodo son parciales y se marcan dinamicamente como tales.
        """
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_paises = self.dir_limpio / "dimensiones/paises.parquet"
        ruta_salida = self.dir_modelado / "p1_ingresos_mensuales.parquet"

        sql = f"""
            WITH clics_validos AS (
                SELECT
                    c.pais_code,
                    p.descripcion AS pais_nombre,
                    c.anio,
                    c.mes,
                    printf('%04d-%02d', c.anio, c.mes) AS anio_mes,
                    c.costo
                FROM read_parquet('{ruta_clics}', hive_partitioning=true) c
                LEFT JOIN read_parquet('{ruta_paises}') p ON c.pais_code = p.code
                WHERE c.valido_code = 1
            ),
            limites AS (
                SELECT MIN(anio_mes) AS min_mes, MAX(anio_mes) AS max_mes FROM clics_validos
            )
            SELECT
                v.pais_code,
                v.pais_nombre,
                v.anio,
                v.mes,
                v.anio_mes,
                COUNT(*)::BIGINT AS total_clics_validos,
                CAST(SUM(v.costo) AS DECIMAL(12, 2)) AS ingreso_usd,
                CASE
                    WHEN v.anio_mes = l.min_mes OR v.anio_mes = l.max_mes THEN true
                    ELSE false
                END AS mes_parcial
            FROM clics_validos v
            CROSS JOIN limites l
            GROUP BY 1, 2, 3, 4, 5, 8
            ORDER BY v.anio, v.mes, v.pais_code
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p1_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_p2_top_sitios(self) -> dict[str, Any]:
        """P2: Top 10 sitios por ingreso en 12 meses y porcentaje de clics invalidos.

        Regla Empates (Guia pag. 10): En los rankings, los empates se ordenan por el
        identificador de menor a mayor (sitio_id ASC).
        """
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_sitios = self.dir_limpio / "dimensiones/sitios.parquet"
        ruta_paises = self.dir_limpio / "dimensiones/paises.parquet"
        ruta_salida = self.dir_modelado / "p2_top_sitios.parquet"

        sql = f"""
            WITH metricas_sitios AS (
                SELECT
                    c.sitio_id,
                    s.nombre AS sitio_nombre,
                    p.descripcion AS pais_nombre,
                    COUNT(*)::BIGINT AS total_clics,
                    COUNT(*) FILTER (WHERE c.valido_code = 1)::BIGINT AS clics_validos,
                    COUNT(*) FILTER (WHERE c.valido_code = 2)::BIGINT AS clics_invalidos,
                    CAST(SUM(CASE WHEN c.valido_code = 1 THEN c.costo ELSE 0 END) AS DECIMAL(12, 2)) AS ingreso_usd
                FROM read_parquet('{ruta_clics}', hive_partitioning=true) c
                LEFT JOIN read_parquet('{ruta_sitios}') s ON c.sitio_id = s.sitio_id
                LEFT JOIN read_parquet('{ruta_paises}') p ON s.pais_code = p.code
                GROUP BY 1, 2, 3
            )
            SELECT
                sitio_id,
                sitio_nombre,
                pais_nombre,
                ingreso_usd,
                total_clics,
                clics_validos,
                clics_invalidos,
                ROUND((clics_invalidos * 100.0) / NULLIF(total_clics, 0), 2) AS pct_clics_invalidos
            FROM metricas_sitios
            ORDER BY ingreso_usd DESC, sitio_id ASC
            LIMIT 10
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p2_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_p3_franja_dia_ctr(self) -> dict[str, Any]:
        """P3: Franja horaria y dia de la semana con mayor tasa de clics (CTR y por 1,000)."""
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_imp = self.dir_limpio / "impresiones_hora/**/*.parquet"
        ruta_salida = self.dir_modelado / "p3_franja_dia_ctr.parquet"

        sql = f"""
            WITH dias AS (
                SELECT unnest(range(0, 7))::INTEGER AS dia_semana
            ),
            franjas AS (
                SELECT unnest(range(0, 12))::INTEGER AS franja_id
            ),
            grid AS (
                SELECT d.dia_semana, f.franja_id
                FROM dias d
                CROSS JOIN franjas f
            ),
            clics_agg AS (
                SELECT
                    dia_semana,
                    franja_id,
                    COUNT(*)::BIGINT AS total_clics
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                GROUP BY 1, 2
            ),
            imp_agg AS (
                SELECT
                    dia_semana,
                    franja_id,
                    SUM(impresiones)::BIGINT AS total_impresiones
                FROM read_parquet('{ruta_imp}', hive_partitioning=true)
                GROUP BY 1, 2
            )
            SELECT
                g.dia_semana,
                CASE g.dia_semana
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Lunes'
                    WHEN 2 THEN 'Martes'
                    WHEN 3 THEN 'Miercoles'
                    WHEN 4 THEN 'Jueves'
                    WHEN 5 THEN 'Viernes'
                    WHEN 6 THEN 'Sabado'
                END AS dia_nombre,
                g.franja_id,
                printf('%02d:00 - %02d:00', g.franja_id * 2, (g.franja_id * 2) + 2) AS franja_horaria,
                COALESCE(i.total_impresiones, 0)::BIGINT AS total_impresiones,
                COALESCE(c.total_clics, 0)::BIGINT AS total_clics,
                ROUND(
                    (COALESCE(c.total_clics, 0) * 100.0) / NULLIF(COALESCE(i.total_impresiones, 0), 0), 4
                ) AS tasa_ctr_pct,
                ROUND(
                    (COALESCE(c.total_clics, 0) * 1000.0) / NULLIF(COALESCE(i.total_impresiones, 0), 0), 4
                ) AS tasa_clics_por_mil
            FROM grid g
            LEFT JOIN imp_agg i ON g.dia_semana = i.dia_semana AND g.franja_id = i.franja_id
            LEFT JOIN clics_agg c ON g.dia_semana = c.dia_semana AND g.franja_id = c.franja_id
            ORDER BY tasa_ctr_pct DESC NULLS LAST, g.dia_semana ASC, g.franja_id ASC
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p3_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_baselines_historicos(self, max_ts: int) -> dict[str, Any]:
        """Precomputa baselines de 8 y 4 semanas con fallback por grupo (P7, P8, P9, P10, 15-sep)."""
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_imp = self.dir_limpio / "impresiones_hora/**/*.parquet"
        ruta_campanias = self.dir_limpio / "dimensiones/campanias.parquet"
        ruta_anunciantes = self.dir_limpio / "dimensiones/anunciantes.parquet"
        ruta_sitios = self.dir_limpio / "dimensiones/sitios.parquet"

        ts_inicio_8sem = max_ts - VENTANA_8_SEMANAS_S
        ts_inicio_4sem = max_ts - VENTANA_4_SEMANAS_S

        # 1. Lista negra de dispositivos con historial de clics invalidos (P9)
        sql_fraude = f"""
            SELECT
                dispositivo_id,
                ANY_VALUE(ip) AS ip,
                COUNT(*)::INTEGER AS clics_invalidos_historicos
            FROM read_parquet('{ruta_clics}', hive_partitioning=true)
            WHERE valido_code = 2
            GROUP BY 1
            ORDER BY clics_invalidos_historicos DESC, dispositivo_id ASC
        """
        self._copiar_atomico(sql_fraude, self.dir_modelado / "dispositivos_fraude_historico.parquet")

        # 2. Baselines de campanias (P7 y API): ventana estricta de 8 semanas + fallback por categoria_code
        sql_baselines_camp = f"""
            WITH camp_meta AS (
                SELECT
                    c.campania_id,
                    c.inicio_ts,
                    COALESCE(a.categoria_code, 6) AS categoria_code,
                    (c.inicio_ts IS NOT NULL AND ({max_ts} - c.inicio_ts) >= {VENTANA_4_SEMANAS_S}) AS antiguedad_4sem
                FROM read_parquet('{ruta_campanias}') c
                LEFT JOIN read_parquet('{ruta_anunciantes}') a ON c.anunciante_id = a.anunciante_id
            ),
            conteo_cat AS (
                SELECT categoria_code, COUNT(*)::DOUBLE AS num_campanias_cat
                FROM camp_meta
                GROUP BY 1
            ),
            gasto_8sem AS (
                SELECT
                    campania_id,
                    dia_semana,
                    hora,
                    SUM(costo) AS suma_gasto_8sem,
                    COUNT(*)::BIGINT AS casos_8sem
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                WHERE ts > {ts_inicio_8sem} AND ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            slots_activos AS (
                SELECT DISTINCT dia_semana, hora FROM gasto_8sem
            ),
            malla AS (
                SELECT
                    cm.campania_id,
                    cm.categoria_code,
                    cm.antiguedad_4sem,
                    s.dia_semana,
                    s.hora,
                    COALESCE(g.suma_gasto_8sem, 0.00) AS suma_gasto_8sem,
                    COALESCE(g.casos_8sem, 0) AS casos_8sem
                FROM camp_meta cm
                CROSS JOIN slots_activos s
                LEFT JOIN gasto_8sem g
                    ON cm.campania_id = g.campania_id
                   AND s.dia_semana = g.dia_semana
                   AND s.hora = g.hora
            ),
            prom_categoria AS (
                SELECT
                    m.categoria_code,
                    m.dia_semana,
                    m.hora,
                    CAST(ROUND(SUM(m.suma_gasto_8sem) / (8.0 * MAX(cc.num_campanias_cat)), 2) AS DECIMAL(10, 2))
                        AS gasto_promedio_categoria
                FROM malla m
                JOIN conteo_cat cc ON m.categoria_code = cc.categoria_code
                GROUP BY 1, 2, 3
            )
            SELECT
                m.campania_id,
                m.categoria_code,
                m.dia_semana,
                m.hora,
                CAST(ROUND(m.suma_gasto_8sem / 8.0, 2) AS DECIMAL(10, 2)) AS gasto_promedio_historico,
                pc.gasto_promedio_categoria,
                (m.antiguedad_4sem AND m.casos_8sem > 0) AS tiene_historia_suficiente,
                CASE
                    WHEN m.antiguedad_4sem AND m.casos_8sem > 0
                        THEN CAST(ROUND(m.suma_gasto_8sem / 8.0, 2) AS DECIMAL(10, 2))
                    ELSE pc.gasto_promedio_categoria
                END AS baseline_efectivo
            FROM malla m
            JOIN prom_categoria pc
                ON m.categoria_code = pc.categoria_code
               AND m.dia_semana = pc.dia_semana
               AND m.hora = pc.hora
            ORDER BY m.campania_id, m.dia_semana, m.hora
        """
        self._copiar_atomico(sql_baselines_camp, self.dir_modelado / "baselines_campanias.parquet")

        # 3. Baselines de sitios (P8): suma de clics y suma de impresiones en 8 semanas divididas una sola vez
        sql_baselines_sitios = f"""
            WITH clics_8sem AS (
                SELECT
                    sitio_id,
                    dia_semana,
                    hora,
                    COUNT(*)::BIGINT AS clics_8sem
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                WHERE ts > {ts_inicio_8sem} AND ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            imp_8sem AS (
                SELECT
                    sitio_id,
                    dia_semana,
                    hora,
                    SUM(impresiones)::BIGINT AS impresiones_8sem
                FROM read_parquet('{ruta_imp}', hive_partitioning=true)
                WHERE hora_ts > {ts_inicio_8sem} AND hora_ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            sitios_base AS (
                SELECT
                    s.sitio_id,
                    s.pais_code,
                    i.dia_semana,
                    i.hora,
                    COALESCE(c.clics_8sem, 0) AS clics_8sem,
                    i.impresiones_8sem,
                    ROUND((COALESCE(c.clics_8sem, 0) * 1000.0) / NULLIF(i.impresiones_8sem, 0), 4)
                        AS tasa_clics_por_mil_historica
                FROM imp_8sem i
                JOIN read_parquet('{ruta_sitios}') s ON i.sitio_id = s.sitio_id
                LEFT JOIN clics_8sem c
                    ON i.sitio_id = c.sitio_id AND i.dia_semana = c.dia_semana AND i.hora = c.hora
            ),
            pais_fallback AS (
                SELECT
                    pais_code,
                    dia_semana,
                    hora,
                    ROUND((SUM(clics_8sem) * 1000.0) / NULLIF(SUM(impresiones_8sem), 0), 4)
                        AS tasa_pais_por_mil
                FROM sitios_base
                GROUP BY 1, 2, 3
            )
            SELECT
                sb.sitio_id,
                sb.pais_code,
                sb.dia_semana,
                sb.hora,
                sb.clics_8sem,
                sb.impresiones_8sem,
                sb.tasa_clics_por_mil_historica,
                pf.tasa_pais_por_mil,
                CASE
                    WHEN sb.impresiones_8sem > 0 AND sb.clics_8sem > 0 THEN sb.tasa_clics_por_mil_historica
                    ELSE pf.tasa_pais_por_mil
                END AS tasa_baseline_efectiva
            FROM sitios_base sb
            JOIN pais_fallback pf
                ON sb.pais_code = pf.pais_code
               AND sb.dia_semana = pf.dia_semana
               AND sb.hora = pf.hora
            ORDER BY sb.sitio_id, sb.dia_semana, sb.hora
        """
        self._copiar_atomico(sql_baselines_sitios, self.dir_modelado / "baselines_sitios.parquet")

        # 4. Curva acumulada de 4 semanas por minuto del dia y pais (P10)
        sql_curva_p10 = f"""
            WITH gasto_minuto_4sem AS (
                SELECT
                    pais_code,
                    dia_semana,
                    (hora * 60 + EXTRACT(MINUTE FROM fecha_local)::INTEGER) AS minuto_dia,
                    SUM(costo) AS gasto_minuto_4sem
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                WHERE ts > {ts_inicio_4sem} AND ts <= {max_ts}
                GROUP BY 1, 2, 3
            )
            SELECT
                pais_code,
                dia_semana,
                minuto_dia,
                CAST(ROUND(gasto_minuto_4sem / 4.0, 2) AS DECIMAL(12, 2)) AS promedio_minuto_4sem,
                CAST(
                    ROUND(
                        SUM(gasto_minuto_4sem) OVER (
                            PARTITION BY pais_code, dia_semana
                            ORDER BY minuto_dia ASC
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                        ) / 4.0,
                        2
                    ) AS DECIMAL(12, 2)
                ) AS facturacion_acumulada_promedio_4sem
            FROM gasto_minuto_4sem
            ORDER BY pais_code, dia_semana, minuto_dia
        """
        self._copiar_atomico(sql_curva_p10, self.dir_modelado / "curva_4semanas_minuto.parquet")

        # 5. Radiografia forense del Incidente del 15 de Septiembre de 2026
        sql_incidente = f"""
            SELECT
                c.anio,
                c.mes,
                c.dia,
                c.hora,
                c.sitio_id,
                s.nombre AS sitio_nombre,
                COUNT(*)::BIGINT AS total_clics,
                COUNT(*) FILTER (WHERE c.valido_code = 2)::BIGINT AS clics_invalidos,
                ROUND((COUNT(*) FILTER (WHERE c.valido_code = 2) * 100.0) / NULLIF(COUNT(*), 0), 2)
                    AS pct_invalidos,
                COUNT(DISTINCT c.dispositivo_id)::BIGINT AS dispositivos_atacantes,
                COUNT(DISTINCT c.campania_id)::BIGINT AS campanias_afectadas,
                CAST(SUM(c.costo) AS DECIMAL(12, 2)) AS gasto_bruto_usd,
                CAST(SUM(CASE WHEN c.valido_code = 2 THEN c.costo ELSE 0 END) AS DECIMAL(12, 2))
                    AS monto_defraudado_usd
            FROM read_parquet('{ruta_clics}', hive_partitioning=true) c
            LEFT JOIN read_parquet('{ruta_sitios}') s ON c.sitio_id = s.sitio_id
            WHERE c.anio = 2026 AND c.mes = 9 AND c.dia = 15
            GROUP BY 1, 2, 3, 4, 5, 6
            ORDER BY clics_invalidos DESC, c.hora ASC, c.sitio_id ASC
        """
        self._copiar_atomico(sql_incidente, self.dir_modelado / "incidente_15_septiembre.parquet")

        return {"baselines_generados": True, "segundos": round(time.perf_counter() - t0, 3)}

    def registrar_watermark_batch(self, max_ts: int) -> dict[str, Any]:
        """Persiste atomicamente ultimo_corte_batch_ts.json para el corte sin doble conteo."""
        ruta_wm = self.dir_modelado / "ultimo_corte_batch_ts.json"
        ruta_tmp = ruta_wm.with_suffix(".tmp.json")
        datos_wm = {
            "ultimo_corte_batch_ts": max_ts,
            "actualizado_en_utc": datetime.now(tz=UTC).isoformat(),
        }
        with open(ruta_tmp, "w", encoding="utf-8") as f:
            json.dump(datos_wm, f, indent=2)
        ruta_tmp.replace(ruta_wm)
        return datos_wm

    def ejecutar_todo(self) -> dict[str, Any]:
        """Ejecuta la generacion de todos los modelos de la Capa Gold y actualiza el watermark."""
        self.dir_modelado.mkdir(parents=True, exist_ok=True)
        max_ts = self._obtener_max_ts()
        r_p1 = self.generar_p1_ingresos_mensuales()
        r_p2 = self.generar_p2_top_sitios()
        r_p3 = self.generar_p3_franja_dia_ctr()
        r_base = self.generar_baselines_historicos(max_ts=max_ts)
        wm = self.registrar_watermark_batch(max_ts=max_ts)

        return {
            "p1": r_p1,
            "p2": r_p2,
            "p3": r_p3,
            "baselines": r_base,
            "ultimo_corte_batch_ts": wm["ultimo_corte_batch_ts"],
            "total_segundos": round(r_p1["segundos"] + r_p2["segundos"] + r_p3["segundos"] + r_base["segundos"], 3),
        }
