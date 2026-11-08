"""Rutas de la API para consulta de catalogos y dimensiones."""

from typing import Any

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import DIR_LIMPIO

router = APIRouter(prefix="/api/v1/catalogos", tags=["Catalogos"])


@router.get("/paises", summary="Catalogo de Paises")
def obtener_paises(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna los paises de operacion (Guatemala, El Salvador, Honduras, Costa Rica)."""
    archivo = DIR_LIMPIO / "dimensiones/paises.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension paises no disponible.")
    filas = con.execute(f"SELECT code, descripcion FROM '{archivo}' ORDER BY code").fetchall()
    return [{"code": f[0], "descripcion": f[1]} for f in filas]


@router.get("/categorias", summary="Catalogo de Categorias de Anunciantes")
def obtener_categorias(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna las categorias comerciales de anunciantes."""
    archivo = DIR_LIMPIO / "dimensiones/categorias.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension categorias no disponible.")
    filas = con.execute(f"SELECT code, descripcion FROM '{archivo}' ORDER BY code").fetchall()
    return [{"code": f[0], "descripcion": f[1]} for f in filas]


@router.get("/sitios", summary="Catalogo de Sitios Web y Aplicaciones")
def obtener_sitios(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna los 421 sitios publicadores."""
    archivo = DIR_LIMPIO / "dimensiones/sitios.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension sitios no disponible.")
    columnas = ["sitio_id", "nombre", "tipo_code", "pais_code", "reparto_pct"]
    filas = con.execute(f"SELECT * FROM '{archivo}' ORDER BY sitio_id LIMIT 100").fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]
