"""Inyeccion de dependencias para la Capa de Servicio (FastAPI + DuckDB)."""

from collections.abc import Generator

from duckdb import DuckDBPyConnection

from src.batch.motor import MotorDuckDB

_motor_global: MotorDuckDB | None = None


def obtener_motor() -> MotorDuckDB:
    """Retorna una instancia singleton del motor DuckDB."""
    global _motor_global
    if _motor_global is None:
        _motor_global = MotorDuckDB()
    return _motor_global


def obtener_conexion_db() -> Generator[DuckDBPyConnection]:
    """Generador de sesion DuckDB para inyeccion en rutas FastAPI."""
    motor = obtener_motor()
    con = motor.conectar()
    try:
        yield con
    finally:
        pass
