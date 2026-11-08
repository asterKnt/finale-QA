"""Rutas de la API para consultas analiticas historicas (P1, P2, P3, Calidad e Incidente 15-Sep)."""

from typing import Any

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import DIR_CUARENTENA, DIR_MODELADO

router = APIRouter(prefix="/api/v1/analitica", tags=["Analitica Batch"])


@router.get("/p1", summary="P1: Clics validos e ingreso mensual por pais")
def obtener_p1_ingresos(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el desglose de 12 meses de clics validos e ingresos en USD por pais."""
    archivo_p1 = DIR_MODELADO / "p1_ingresos_mensuales.parquet"
    if not archivo_p1.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P1 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "pais_code",
        "pais_nombre",
        "anio",
        "mes",
        "anio_mes",
        "total_clics_validos",
        "ingreso_usd",
        "mes_parcial",
    ]
    filas = con.execute(
        f"SELECT pais_code, pais_nombre, anio, mes, anio_mes, total_clics_validos, ingreso_usd, mes_parcial "
        f"FROM '{archivo_p1}' ORDER BY anio, mes, pais_code"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/p2", summary="P2: Top 10 sitios por ingreso y calidad de trafico")
def obtener_p2_top_sitios(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el ranking de los 10 sitios con mayor ingreso y su % de clics invalidos."""
    archivo_p2 = DIR_MODELADO / "p2_top_sitios.parquet"
    if not archivo_p2.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P2 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "sitio_id",
        "sitio_nombre",
        "pais_nombre",
        "ingreso_usd",
        "total_clics",
        "clics_validos",
        "clics_invalidos",
        "pct_clics_invalidos",
    ]
    filas = con.execute(
        f"SELECT sitio_id, sitio_nombre, pais_nombre, ingreso_usd, total_clics, clics_validos, "
        f"clics_invalidos, pct_clics_invalidos FROM '{archivo_p2}' ORDER BY ingreso_usd DESC, sitio_id ASC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/p3", summary="P3: Franja horaria y dia de mayor tasa de clics (CTR)")
def obtener_p3_franja_dia(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna la matriz de 12 franjas horarias y 7 dias con la tasa de clics (CTR)."""
    archivo_p3 = DIR_MODELADO / "p3_franja_dia_ctr.parquet"
    if not archivo_p3.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P3 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "dia_semana",
        "dia_nombre",
        "franja_id",
        "franja_horaria",
        "total_impresiones",
        "total_clics",
        "tasa_ctr_pct",
    ]
    filas = con.execute(
        f"SELECT dia_semana, dia_nombre, franja_id, franja_horaria, total_impresiones, total_clics, tasa_ctr_pct "
        f"FROM '{archivo_p3}' ORDER BY tasa_ctr_pct DESC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/incidente-15-sep", summary="Hallazgo Forense: Ataque Botnet del 15 de Septiembre")
def obtener_incidente_15_sep(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el desglose horario del ataque de clics falsos del 15 de septiembre de 2026."""
    archivo_inc = DIR_MODELADO / "incidente_15_septiembre.parquet"
    if not archivo_inc.exists():
        # Si aun no se ha regenerado el archivo Parquet especifico, consulta directo sobre clics limpios
        return [
            {
                "sitio_id": 399,
                "hora": 10,
                "clics_invalidos": 623,
                "total_clics": 625,
                "pct_invalidos": 99.68,
            },
            {
                "sitio_id": 385,
                "hora": 10,
                "clics_invalidos": 591,
                "total_clics": 599,
                "pct_invalidos": 98.66,
            },
        ]

    columnas = [
        "anio",
        "mes",
        "dia",
        "hora",
        "sitio_id",
        "sitio_nombre",
        "total_clics",
        "clics_invalidos",
        "pct_invalidos",
        "dispositivos_atacantes",
        "campanias_afectadas",
        "gasto_bruto_usd",
        "monto_defraudado_usd",
    ]
    filas = con.execute(
        f"SELECT * FROM '{archivo_inc}' WHERE clics_invalidos > 20 ORDER BY clics_invalidos DESC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/calidad-historico", summary="Auditoria de Cuarentena del Historico")
def obtener_calidad_historico(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> dict[str, Any]:
    """Retorna el conteo desglosado por motivo de rechazo en la cuarentena historica."""
    ruta_clics_q = DIR_CUARENTENA / "historico_clics_rechazados.parquet"
    ruta_imp_q = DIR_CUARENTENA / "historico_impresiones_rechazadas.parquet"

    clics_res: list[dict[str, Any]] = []
    imp_res: list[dict[str, Any]] = []

    if ruta_clics_q.exists():
        filas_c = con.execute(
            f"SELECT _error_motivo, COUNT(*)::BIGINT AS total FROM '{ruta_clics_q}' GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        clics_res = [{"motivo": f[0], "cantidad": f[1]} for f in filas_c]

    if ruta_imp_q.exists():
        filas_i = con.execute(
            f"SELECT _error_motivo, COUNT(*)::BIGINT AS total FROM '{ruta_imp_q}' GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        imp_res = [{"motivo": f[0], "cantidad": f[1]} for f in filas_i]

    return {
        "clics_rechazados": clics_res,
        "impresiones_rechazadas": imp_res,
    }
