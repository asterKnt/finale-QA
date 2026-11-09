"""Fixtures globales y configuracion base para pytest en Clic Justo."""

from collections.abc import Generator
from pathlib import Path
from typing import Any
import pytest
from duckdb import DuckDBPyConnection

from src.batch.motor import MotorDuckDB


@pytest.fixture
def tmp_datos_dir(tmp_path: Path) -> Path:
    """Proporciona un directorio de datos temporal aislado para cada prueba."""
    dir_datos = tmp_path / "datos"
    dir_datos.mkdir(parents=True, exist_ok=True)
    return dir_datos


@pytest.fixture
def motor_duckdb_memoria() -> Generator[MotorDuckDB, None, None]:
    """Crea una instancia aislada en memoria del motor DuckDB."""
    motor = MotorDuckDB(base_datos=":memory:")
    yield motor
    motor.cerrar()


@pytest.fixture
def conexion_duckdb(motor_duckdb_memoria: MotorDuckDB) -> DuckDBPyConnection:
    """Proporciona una conexion activa a la base de datos DuckDB en memoria."""
    return motor_duckdb_memoria.conectar()


@pytest.fixture
def muestra_evento_clic_valido() -> dict[str, Any]:
    """Evento de clic conforme con la definicion clic.v1.json."""
    return {
        "evento_id": "evt-clic-test-001",
        "tipo": "clic",
        "version": 1,
        "clic_id": "c-test-100",
        "impresion_id": "imp-test-100",
        "campania_id": 10,
        "sitio_id": 5,
        "dispositivo_id": "dev-user-abc12345",
        "ip": "192.168.1.50",
        "costo": "0.25",
        "ts": 1761026400,
    }


@pytest.fixture
def muestra_evento_impresion_valido() -> dict[str, Any]:
    """Evento de impresion conforme con la definicion impresion.v1.json."""
    return {
        "evento_id": "evt-imp-test-001",
        "tipo": "impresion",
        "version": 1,
        "impresion_id": "imp-test-100",
        "campania_id": 10,
        "sitio_id": 5,
        "dispositivo_id": "dev-user-abc12345",
        "ts": 1761026400,
    }