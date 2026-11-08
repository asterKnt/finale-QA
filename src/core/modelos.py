"""Modelos de datos y DTOs estructurados para Clic Justo."""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventoImpresionV1(BaseModel):
    """Modelo formal para eventos de impresion conforme a impresion.v1.json."""

    evento_id: str = Field(..., min_length=1)
    tipo: Literal["impresion"] = "impresion"
    version: Literal[1] = 1
    impresion_id: str = Field(..., min_length=1)
    campania_id: int = Field(..., ge=1)
    sitio_id: int = Field(..., ge=1)
    dispositivo_id: str = Field(..., min_length=1)
    ts: int = Field(..., ge=0)


class EventoClicV1(BaseModel):
    """Modelo formal para eventos de clic conforme a clic.v1.json."""

    evento_id: str = Field(..., min_length=1)
    tipo: Literal["clic"] = "clic"
    version: Literal[1] = 1
    clic_id: str = Field(..., min_length=1)
    impresion_id: str = Field(..., min_length=1)
    campania_id: int = Field(..., ge=1)
    sitio_id: int = Field(..., ge=1)
    dispositivo_id: str = Field(..., min_length=1)
    ip: str = Field(..., min_length=1)
    costo: str = Field(..., pattern=r"^[0-9]+(\.[0-9]+)?$")
    ts: int = Field(..., ge=0)


class RegistroCuarentena(BaseModel):
    """Estructura de auditoria para registros desviados a cuarentena."""

    ingest_ts: int = Field(..., alias="_ingest_ts")
    error_tipo: str = Field(..., alias="_error_tipo")
    error_detalle: str = Field(..., alias="_error_detalle")
    payload_original: dict[str, Any]


class CampaniaResumenResponse(BaseModel):
    """Respuesta del endpoint operativo de atencion al cliente (/campanias/{id}/resumen)."""

    campania_id: int
    anunciante_id: int
    presupuesto_diario: Decimal
    gasto_hoy: Decimal
    presupuesto_restante: Decimal
    gasto_ultima_hora: Decimal
    promedio_historico_hora: Decimal
    pct_dispositivos_invalidos_ultima_hora: float
    accion_sugerida: Literal["normal", "revisar", "pausar"]
