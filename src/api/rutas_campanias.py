"""Rutas de la API para consultas operativas de campanias (/campanias/{id}/resumen)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import (
    DIR_LIMPIO,
    DIR_MODELADO,
    TIMEZONE_OFFSET_HOURS,
    convertir_weekday_a_duckdb_dow,
)
from src.core.modelos import CampaniaResumenResponse

router = APIRouter(prefix="/api/v1/campanias", tags=["Campanias Operativas"])

TZ_LOCAL = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))


def evaluar_regla_accion_campania(
    presupuesto_diario: Decimal,
    gasto_hoy: Decimal,
    gasto_ultima_hora: Decimal,
    promedio_historico: Decimal,
    pct_invalidos_hora: float,
) -> Literal["normal", "revisar", "pausar"]:
    """Evalua la regla contractual de accion sugerida para atencion a comercios.

    Reglas (Guia pag. 13 y docs/aclaraciones.md):
    - pausar: si ya gasto el presupuesto del dia, o si mas del 30% de sus clics de la
      ultima hora vienen de dispositivos con historial de clics invalidos.
    - revisar: si su gasto de la ultima hora triplica (al menos 3 veces, >= 3x) lo normal.
    - normal: en cualquier otro caso.
    """
    if (presupuesto_diario > Decimal("0.00") and gasto_hoy >= presupuesto_diario) or pct_invalidos_hora > 30.0:
        return "pausar"
    if promedio_historico > Decimal("0.00") and gasto_ultima_hora >= (Decimal("3") * promedio_historico):
        return "revisar"
    return "normal"


class ProveedorDeltasSpeed:
    """Interfaz desacoplada para inyeccion de deltas en tiempo real desde la Speed Layer.

    Por defecto opera con deltas neutros; se conecta al estado en memoria de la Speed Layer.
    """

    @staticmethod
    def obtener_deltas_campania(campania_id: int) -> dict[str, Any]:
        return {
            "gasto_en_vivo_hoy": Decimal("0.00"),
            "gasto_en_vivo_ultima_hora": Decimal("0.00"),
            "pct_invalidos_ultima_hora": 0.0,
        }


@router.get("/{campania_id}/resumen", response_model=CampaniaResumenResponse, summary="Resumen Operativo de Campaña")
def obtener_resumen_campania(
    campania_id: int,
    con: DuckDBPyConnection = Depends(obtener_conexion_db),
) -> CampaniaResumenResponse:
    """Devuelve las 5 metricas operativas y la accion sugerida (normal / revisar / pausar)."""
    archivo_campanias = DIR_LIMPIO / "dimensiones/campanias.parquet"
    archivo_baselines = DIR_MODELADO / "baselines_campanias.parquet"

    if not archivo_campanias.exists():
        raise HTTPException(status_code=503, detail="Capa dimensional no inicializada.")

    # 1. Obtener datos de la campania
    sql_camp = f"""
        SELECT anunciante_id, presupuesto_diario
        FROM '{archivo_campanias}'
        WHERE campania_id = {campania_id}
    """
    fila_camp = con.execute(sql_camp).fetchone()
    if fila_camp is None:
        raise HTTPException(status_code=404, detail=f"Campania {campania_id} no encontrada.")

    anunciante_id = int(fila_camp[0])
    presupuesto_diario = Decimal(str(fila_camp[1]))

    # 2. Obtener baseline historico para la hora y dia actuales (alineado con DOW de DuckDB: 0=Domingo..6=Sabado)
    ahora_local = datetime.now(tz=TZ_LOCAL)
    dia_semana_duckdb = convertir_weekday_a_duckdb_dow(ahora_local.weekday())
    hora = ahora_local.hour

    promedio_historico = Decimal("0.00")
    if archivo_baselines.exists():
        columnas_disp = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{archivo_baselines}'").fetchall()]
        col_objetivo = "baseline_efectivo" if "baseline_efectivo" in columnas_disp else "gasto_promedio_historico"
        sql_base = f"""
            SELECT {col_objetivo}
            FROM '{archivo_baselines}'
            WHERE campania_id = {campania_id}
              AND dia_semana = {dia_semana_duckdb}
              AND hora = {hora}
        """
        fila_base = con.execute(sql_base).fetchone()
        if fila_base is not None and fila_base[0] is not None:
            promedio_historico = Decimal(str(fila_base[0]))

    # 3. Deltas Speed Layer (desacoplados)
    deltas = ProveedorDeltasSpeed.obtener_deltas_campania(campania_id)
    gasto_hoy = deltas["gasto_en_vivo_hoy"]
    gasto_ultima_hora = deltas["gasto_en_vivo_ultima_hora"]
    pct_invalidos_hora = float(deltas["pct_invalidos_ultima_hora"])

    presupuesto_restante = max(Decimal("0.00"), presupuesto_diario - gasto_hoy)

    # 4. Regla de decision de negocio
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=presupuesto_diario,
        gasto_hoy=gasto_hoy,
        gasto_ultima_hora=gasto_ultima_hora,
        promedio_historico=promedio_historico,
        pct_invalidos_hora=pct_invalidos_hora,
    )

    return CampaniaResumenResponse(
        campania_id=campania_id,
        anunciante_id=anunciante_id,
        presupuesto_diario=presupuesto_diario,
        gasto_hoy=gasto_hoy,
        presupuesto_restante=presupuesto_restante,
        gasto_ultima_hora=gasto_ultima_hora,
        promedio_historico_hora=promedio_historico,
        pct_dispositivos_invalidos_ultima_hora=pct_invalidos_hora,
        accion_sugerida=accion,
    )
