"""Transformador de Capa Bronze (CSVs historicos + Crudo en vivo) a Capa Silver y Cuarentena Batch."""

import shutil
import time
from pathlib import Path
from typing import Any

from src.batch.motor import MotorDuckDB
from src.core.config import (
    DIR_CRUDO,
    DIR_CUARENTENA,
    DIR_ESTADO_PRODUCTOR,
    DIR_HISTORICO,
    DIR_LIMPIO,
    MAX_TS_RAZONABLE_SEGUNDOS,
)


class TransformadorBronzeSilver:
    """Ejecuta la auditoria de calidad, cuarentena historica, deduplicacion y particionado Hive en Silver."""

    def __init__(
        self,
        dir_historico: Path = DIR_HISTORICO,
        dir_limpio: Path = DIR_LIMPIO,
        dir_cuarentena: Path = DIR_CUARENTENA,
        dir_crudo: Path = DIR_CRUDO,
        dir_estado_productor: Path = DIR_ESTADO_PRODUCTOR,
        motor: MotorDuckDB | None = None,
    ) -> None:
        self.dir_historico = dir_historico
        self.dir_limpio = dir_limpio
        self.dir_cuarentena = dir_cuarentena
        self.dir_crudo = dir_crudo
        self.dir_estado_productor = dir_estado_productor
        self.motor = motor or MotorDuckDB()

    def _copiar_parquet_atomico(self, sql_query: str, ruta_destino: Path) -> None:
        """Escribe un archivo Parquet de forma atomica mediante archivo temporal .tmp.parquet."""
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        ruta_tmp = ruta_destino.with_suffix(".tmp.parquet")
        self.motor.ejecutar(f"COPY ({sql_query}) TO '{ruta_tmp}' (FORMAT 'PARQUET', COMPRESSION 'ZSTD');")
        ruta_tmp.replace(ruta_destino)

    def procesar_dimensiones(self) -> dict[str, Any]:
        """Deduplica, normaliza y convierte catalogos y tablas dimensionales a Parquet."""
        dir_dim = self.dir_limpio / "dimensiones"
        dir_dim.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()

        # 1. Sitios: deduplicar por sitio_id (corrige sitio 406 duplicado) y normalizar tipo_code (corrige tipo 3)
        archivo_sitios = self.dir_historico / "sitios_raw.csv"
        sql_sitios = f"""
            SELECT
                TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                CAST(nombre AS VARCHAR) AS nombre,
                CASE
                    WHEN TRY_CAST(tipo_code AS INTEGER) IN (1, 2) THEN TRY_CAST(tipo_code AS INTEGER)
                    ELSE 1
                END AS tipo_code,
                CASE
                    WHEN TRY_CAST(pais_code AS INTEGER) BETWEEN 1 AND 4 THEN TRY_CAST(pais_code AS INTEGER)
                    ELSE 1
                END AS pais_code,
                TRY_CAST(REPLACE(CAST(reparto_pct AS VARCHAR), ',', '.') AS DECIMAL(5, 2)) AS reparto_pct
            FROM read_csv_auto('{archivo_sitios}', header=true, all_varchar=true)
            WHERE TRY_CAST(sitio_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TRY_CAST(sitio_id AS BIGINT) ORDER BY nombre ASC) = 1
        """
        self._copiar_parquet_atomico(sql_sitios, dir_dim / "sitios.parquet")

        # 2. Campanias: unificar con entidades_nuevas si existen, deduplicar (corrige campania 9111)
        #    y normalizar fin_ts < inicio_ts (corrige campania 2430)
        archivo_campanias = self.dir_historico / "campanias_raw.csv"
        archivo_camp_nuevas = self.dir_estado_productor / "entidades_nuevas" / "campanias.csv"
        fuente_campanias = f"SELECT * FROM read_csv_auto('{archivo_campanias}', header=true, all_varchar=true)"
        if archivo_camp_nuevas.exists():
            fuente_campanias += (
                f" UNION ALL SELECT * FROM read_csv_auto('{archivo_camp_nuevas}', header=true, all_varchar=true)"
            )

        sql_campanias = f"""
            WITH raw_camp AS (
                {fuente_campanias}
            )
            SELECT
                TRY_CAST(campania_id AS BIGINT) AS campania_id,
                TRY_CAST(anunciante_id AS BIGINT) AS anunciante_id,
                TRY_CAST(
                    REPLACE(CAST(presupuesto_diario AS VARCHAR), ',', '.') AS DECIMAL(10, 2)
                ) AS presupuesto_diario,
                TRY_CAST(
                    REPLACE(CAST(costo_por_clic AS VARCHAR), ',', '.') AS DECIMAL(10, 2)
                ) AS costo_por_clic,
                CASE
                    WHEN TRY_CAST(estado_code AS INTEGER) IN (1, 2, 3) THEN TRY_CAST(estado_code AS INTEGER)
                    ELSE 1
                END AS estado_code,
                TRY_CAST(inicio_ts AS BIGINT) AS inicio_ts,
                CASE
                    WHEN TRY_CAST(fin_ts AS BIGINT) IS NOT NULL
                         AND TRY_CAST(fin_ts AS BIGINT) >= TRY_CAST(inicio_ts AS BIGINT)
                    THEN TRY_CAST(fin_ts AS BIGINT)
                    ELSE NULL
                END AS fin_ts
            FROM raw_camp
            WHERE TRY_CAST(campania_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY TRY_CAST(campania_id AS BIGINT)
                ORDER BY TRY_CAST(inicio_ts AS BIGINT) DESC NULLS LAST
            ) = 1
        """
        self._copiar_parquet_atomico(sql_campanias, dir_dim / "campanias.parquet")

        # 3. Anunciantes: excluir email_contacto (PII), deduplicar (6 anunciantes duplicados)
        #    y normalizar categoria_code fuera de [1..6] hacia 6 ('Otro')
        archivo_anunciantes = self.dir_historico / "anunciantes_raw.csv"
        sql_anunciantes = f"""
            SELECT
                TRY_CAST(anunciante_id AS BIGINT) AS anunciante_id,
                CAST(nombre AS VARCHAR) AS nombre,
                CASE
                    WHEN TRY_CAST(categoria_code AS INTEGER) BETWEEN 1 AND 6 THEN TRY_CAST(categoria_code AS INTEGER)
                    ELSE 6
                END AS categoria_code,
                CASE
                    WHEN TRY_CAST(pais_code AS INTEGER) BETWEEN 1 AND 4 THEN TRY_CAST(pais_code AS INTEGER)
                    ELSE 1
                END AS pais_code,
                TRY_CAST(alta_ts AS BIGINT) AS alta_ts
            FROM read_csv_auto('{archivo_anunciantes}', header=true, all_varchar=true)
            WHERE TRY_CAST(anunciante_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY TRY_CAST(anunciante_id AS BIGINT)
                ORDER BY TRY_CAST(alta_ts AS BIGINT) DESC NULLS LAST
            ) = 1
        """
        self._copiar_parquet_atomico(sql_anunciantes, dir_dim / "anunciantes.parquet")

        # 4. Catalogos auxiliares
        dir_catalogos = self.dir_historico / "catalogos"
        catalogos = [
            ("categorias.csv", "categorias.parquet"),
            ("estados_campania.csv", "estados_campania.parquet"),
            ("paises.csv", "paises.parquet"),
            ("tipos_sitio.csv", "tipos_sitio.parquet"),
            ("validez_clic.csv", "validez_clic.parquet"),
        ]
        for csv_nom, prq_nom in catalogos:
            ruta_csv = dir_catalogos / csv_nom
            if ruta_csv.exists():
                self._copiar_parquet_atomico(
                    f"SELECT * FROM read_csv_auto('{ruta_csv}', header=true)",
                    dir_dim / prq_nom,
                )

        return {"dimensiones_procesadas": True, "segundos": round(time.perf_counter() - t0, 3)}

    def procesar_clics(self) -> dict[str, Any]:
        """Audita anomalias historicas a cuarentena, unifica con crudo en vivo, deduplica y particiona."""
        dir_clics = self.dir_limpio / "clics"
        self.dir_cuarentena.mkdir(parents=True, exist_ok=True)
        archivo_clics = self.dir_historico / "clics_raw.csv"
        ruta_sitios = self.dir_limpio / "dimensiones" / "sitios.parquet"
        ruta_campanias = self.dir_limpio / "dimensiones" / "campanias.parquet"
        ruta_cuarentena_clics = self.dir_cuarentena / "historico_clics_rechazados.parquet"
        t0 = time.perf_counter()
        audit_ts = int(time.time())

        sql_clasificacion = f"""
            WITH raw_clics AS (
                SELECT
                    CAST(clic_id AS VARCHAR) AS clic_id,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    CAST(dispositivo_id AS VARCHAR) AS dispositivo_id,
                    CAST(ip AS VARCHAR) AS ip,
                    CAST(costo AS VARCHAR) AS costo_raw,
                    TRY_CAST(REPLACE(CAST(costo AS VARCHAR), ',', '.') AS DECIMAL(10, 2)) AS costo_num,
                    CAST(ts AS VARCHAR) AS ts_raw,
                    TRY_CAST(ts AS BIGINT) AS ts_num,
                    CAST(valido_code AS VARCHAR) AS valido_raw,
                    TRY_CAST(valido_code AS INTEGER) AS valido_num
                FROM read_csv_auto('{archivo_clics}', header=true, all_varchar=true)
            ),
            evaluados AS (
                SELECT
                    r.*,
                    CASE
                        WHEN r.clic_id IS NULL OR TRIM(r.clic_id) = '' THEN 'FALTA_CLIC_ID'
                        WHEN r.dispositivo_id IS NULL OR TRIM(r.dispositivo_id) = '' THEN 'FALTA_DISPOSITIVO_ID'
                        WHEN r.ip IS NULL OR TRIM(r.ip) = '' THEN 'FALTA_IP'
                        WHEN r.ts_num IS NULL OR r.ts_num <= 0 OR r.ts_num > {MAX_TS_RAZONABLE_SEGUNDOS}
                            THEN 'TIMESTAMP_CORRUPTO_O_MS'
                        WHEN r.valido_num IS NULL OR r.valido_num NOT IN (1, 2) THEN 'VALIDO_CODE_FUERA_CATALOGO'
                        WHEN r.costo_num IS NULL OR r.costo_num <= 0 THEN 'COSTO_INVALIDO'
                        WHEN c.campania_id IS NULL THEN 'CAMPANIA_HUERFANA'
                        WHEN s.sitio_id IS NULL THEN 'SITIO_HUERFANO'
                        ELSE NULL
                    END AS _error_motivo
                FROM raw_clics r
                LEFT JOIN read_parquet('{ruta_campanias}') c ON r.campania_id = c.campania_id
                LEFT JOIN read_parquet('{ruta_sitios}') s ON r.sitio_id = s.sitio_id
            )
        """

        # 1. Escribir registros rechazados en cuarentena batch
        sql_cuarentena = f"""
            {sql_clasificacion}
            SELECT
                clic_id,
                campania_id,
                sitio_id,
                dispositivo_id,
                ip,
                costo_raw AS costo,
                ts_raw AS ts,
                valido_raw AS valido_code,
                _error_motivo,
                {audit_ts}::BIGINT AS _audit_ts
            FROM evaluados
            WHERE _error_motivo IS NOT NULL
        """
        self._copiar_parquet_atomico(sql_cuarentena, ruta_cuarentena_clics)

        # 2. Unificar clics historicos validos con clics de datos/crudo/clic/*.jsonl (si existen)
        dir_crudo_clic = self.dir_crudo / "clic"
        archivos_crudo_clic = list(dir_crudo_clic.glob("*.jsonl")) if dir_crudo_clic.exists() else []
        union_vivo_sql = ""
        if archivos_crudo_clic:
            patron_crudo_clic = str(self.dir_crudo / "clic" / "*.jsonl")
            union_vivo_sql = f"""
                UNION ALL
                SELECT
                    CAST(clic_id AS VARCHAR) AS clic_id,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    CAST(dispositivo_id AS VARCHAR) AS dispositivo_id,
                    CAST(ip AS VARCHAR) AS ip,
                    TRY_CAST(REPLACE(CAST(costo AS VARCHAR), ',', '.') AS DECIMAL(10, 2)) AS costo,
                    TRY_CAST(ts AS BIGINT) AS ts,
                    1::INTEGER AS valido_code
                FROM read_json_auto('{patron_crudo_clic}')
                WHERE clic_id IS NOT NULL
                  AND dispositivo_id IS NOT NULL
                  AND ip IS NOT NULL
                  AND TRY_CAST(ts AS BIGINT) BETWEEN 1 AND {MAX_TS_RAZONABLE_SEGUNDOS}
            """

        if dir_clics.exists():
            shutil.rmtree(dir_clics, ignore_errors=True)
        dir_clics.mkdir(parents=True, exist_ok=True)

        sql_silver_clics = f"""
            COPY (
                {sql_clasificacion},
                unificados AS (
                    SELECT
                        clic_id,
                        campania_id,
                        sitio_id,
                        dispositivo_id,
                        ip,
                        costo_num AS costo,
                        ts_num AS ts,
                        valido_num AS valido_code
                    FROM evaluados
                    WHERE _error_motivo IS NULL
                    {union_vivo_sql}
                ),
                deduplicados AS (
                    SELECT
                        u.clic_id,
                        u.campania_id,
                        u.sitio_id,
                        s.pais_code,
                        u.dispositivo_id,
                        u.ip,
                        u.costo,
                        u.ts,
                        u.valido_code,
                        (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR) AS fecha_local,
                        EXTRACT(YEAR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS anio,
                        EXTRACT(MONTH FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS mes,
                        EXTRACT(DAY FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia,
                        EXTRACT(HOUR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS hora,
                        FLOOR(
                            EXTRACT(HOUR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR)) / 2
                        )::INTEGER AS franja_id,
                        EXTRACT(DOW FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia_semana
                    FROM unificados u
                    INNER JOIN read_parquet('{ruta_sitios}') s ON u.sitio_id = s.sitio_id
                    INNER JOIN read_parquet('{ruta_campanias}') c ON u.campania_id = c.campania_id
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY u.clic_id ORDER BY u.ts ASC) = 1
                )
                SELECT * FROM deduplicados
            ) TO '{dir_clics}' (
                FORMAT 'PARQUET',
                PARTITION_BY (pais_code, anio, mes),
                COMPRESSION 'ZSTD',
                OVERWRITE_OR_IGNORE true
            );
        """
        self.motor.ejecutar(sql_silver_clics)
        return {"clics_procesados": True, "segundos": round(time.perf_counter() - t0, 3)}

    def procesar_impresiones_hora(self) -> dict[str, Any]:
        """Audita anomalias en impresiones, deduplica, agrega eventos en vivo y particiona en Silver."""
        dir_impresiones = self.dir_limpio / "impresiones_hora"
        self.dir_cuarentena.mkdir(parents=True, exist_ok=True)
        archivo_imp = self.dir_historico / "impresiones_hora_raw.csv"
        ruta_sitios = self.dir_limpio / "dimensiones" / "sitios.parquet"
        ruta_campanias = self.dir_limpio / "dimensiones" / "campanias.parquet"
        ruta_cuarentena_imp = self.dir_cuarentena / "historico_impresiones_rechazadas.parquet"
        t0 = time.perf_counter()
        audit_ts = int(time.time())

        sql_clasificacion_imp = f"""
            WITH raw_imp AS (
                SELECT
                    CAST(hora_ts AS VARCHAR) AS hora_ts_raw,
                    TRY_CAST(hora_ts AS BIGINT) AS hora_ts_num,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    CAST(impresiones AS VARCHAR) AS impresiones_raw,
                    TRY_CAST(impresiones AS BIGINT) AS impresiones_num
                FROM read_csv_auto('{archivo_imp}', header=true, all_varchar=true)
            ),
            evaluadas AS (
                SELECT
                    r.*,
                    CASE
                        WHEN r.hora_ts_num IS NULL OR r.hora_ts_num <= 0 OR r.hora_ts_num > {MAX_TS_RAZONABLE_SEGUNDOS}
                            THEN 'TIMESTAMP_CORRUPTO_O_MS'
                        WHEN r.hora_ts_num % 3600 != 0 THEN 'HORA_TS_DESALINEADO'
                        WHEN r.impresiones_num IS NULL OR r.impresiones_num <= 0 THEN 'IMPRESIONES_NO_POSITIVAS'
                        WHEN c.campania_id IS NULL THEN 'CAMPANIA_HUERFANA'
                        WHEN s.sitio_id IS NULL THEN 'SITIO_HUERFANO'
                        ELSE NULL
                    END AS _error_motivo
                FROM raw_imp r
                LEFT JOIN read_parquet('{ruta_campanias}') c ON r.campania_id = c.campania_id
                LEFT JOIN read_parquet('{ruta_sitios}') s ON r.sitio_id = s.sitio_id
            )
        """

        # 1. Guardar cuarentena de impresiones historicas rechazadas
        sql_cuarentena_imp = f"""
            {sql_clasificacion_imp}
            SELECT
                hora_ts_raw AS hora_ts,
                campania_id,
                sitio_id,
                impresiones_raw AS impresiones,
                _error_motivo,
                {audit_ts}::BIGINT AS _audit_ts
            FROM evaluadas
            WHERE _error_motivo IS NOT NULL
        """
        self._copiar_parquet_atomico(sql_cuarentena_imp, ruta_cuarentena_imp)

        # 2. Agregar impresiones en vivo desde datos/crudo/impresion/*.jsonl (si existen)
        archivos_crudo_imp = (
            list((self.dir_crudo / "impresion").glob("*.jsonl")) if (self.dir_crudo / "impresion").exists() else []
        )
        union_imp_vivo_sql = ""
        if archivos_crudo_imp:
            patron_crudo_imp = str(self.dir_crudo / "impresion" / "*.jsonl")
            union_imp_vivo_sql = f"""
                UNION ALL
                SELECT
                    ((TRY_CAST(ts AS BIGINT) // 3600) * 3600)::BIGINT AS hora_ts,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    COUNT(*)::BIGINT AS impresiones
                FROM (
                    SELECT
                        CAST(impresion_id AS VARCHAR) AS impresion_id,
                        campania_id,
                        sitio_id,
                        ts
                    FROM read_json_auto('{patron_crudo_imp}')
                    WHERE impresion_id IS NOT NULL
                      AND TRY_CAST(ts AS BIGINT) BETWEEN 1 AND {MAX_TS_RAZONABLE_SEGUNDOS}
                    QUALIFY ROW_NUMBER() OVER (
                        PARTITION BY CAST(impresion_id AS VARCHAR)
                        ORDER BY TRY_CAST(ts AS BIGINT) ASC
                    ) = 1
                )
                GROUP BY 1, 2, 3
            """

        if dir_impresiones.exists():
            shutil.rmtree(dir_impresiones, ignore_errors=True)
        dir_impresiones.mkdir(parents=True, exist_ok=True)

        sql_silver_imp = f"""
            COPY (
                {sql_clasificacion_imp},
                hist_dedup AS (
                    SELECT
                        hora_ts_num AS hora_ts,
                        campania_id,
                        sitio_id,
                        impresiones_num AS impresiones
                    FROM evaluadas
                    WHERE _error_motivo IS NULL
                    QUALIFY ROW_NUMBER() OVER (
                        PARTITION BY hora_ts_num, campania_id, sitio_id
                        ORDER BY impresiones_num DESC
                    ) = 1
                ),
                unificadas AS (
                    SELECT * FROM hist_dedup
                    {union_imp_vivo_sql}
                ),
                consolidadas AS (
                    SELECT
                        u.hora_ts,
                        u.campania_id,
                        u.sitio_id,
                        s.pais_code,
                        SUM(u.impresiones)::BIGINT AS impresiones,
                        (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR) AS fecha_hora_local,
                        EXTRACT(YEAR FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS anio,
                        EXTRACT(MONTH FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS mes,
                        EXTRACT(DAY FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia,
                        EXTRACT(HOUR FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS hora,
                        FLOOR(
                            EXTRACT(HOUR FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR)) / 2
                        )::INTEGER AS franja_id,
                        EXTRACT(DOW FROM (epoch_ms(u.hora_ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia_semana
                    FROM unificadas u
                    INNER JOIN read_parquet('{ruta_sitios}') s ON u.sitio_id = s.sitio_id
                    INNER JOIN read_parquet('{ruta_campanias}') c ON u.campania_id = c.campania_id
                    GROUP BY 1, 2, 3, 4
                )
                SELECT * FROM consolidadas
            ) TO '{dir_impresiones}' (
                FORMAT 'PARQUET',
                PARTITION_BY (pais_code, anio, mes),
                COMPRESSION 'ZSTD',
                OVERWRITE_OR_IGNORE true
            );
        """
        self.motor.ejecutar(sql_silver_imp)
        return {"impresiones_procesadas": True, "segundos": round(time.perf_counter() - t0, 3)}

    def ejecutar_todo(self) -> dict[str, Any]:
        """Ejecuta la transformacion completa de Bronze a Silver con cuarentena de anomalias."""
        r_dim = self.procesar_dimensiones()
        r_clics = self.procesar_clics()
        r_imp = self.procesar_impresiones_hora()
        return {
            "dimensiones": r_dim,
            "clics": r_clics,
            "impresiones": r_imp,
            "total_segundos": round(r_dim["segundos"] + r_clics["segundos"] + r_imp["segundos"], 3),
        }
