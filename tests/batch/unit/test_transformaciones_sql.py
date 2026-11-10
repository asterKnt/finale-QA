"""Pruebas unitarias para consultas y transformaciones SQL ejecutadas en DuckDB."""

from duckdb import DuckDBPyConnection

from src.batch.motor import MotorDuckDB


def test_motor_duckdb_conexion_y_ejecucion(conexion_duckdb: DuckDBPyConnection) -> None:
    """Verifica la ejecucion basica de consultas SQL en el motor DuckDB en memoria."""
    resultado = conexion_duckdb.execute("SELECT 42 AS respuesta").fetchone()
    assert resultado is not None
    assert resultado[0] == 42


def test_motor_duckdb_recursos_cerrar() -> None:
    """Verifica que el motor administre el ciclo de vida de la conexion sin fugas de memoria."""
    motor = MotorDuckDB(base_datos=":memory:")
    con = motor.conectar()
    assert con is not None

    motor.cerrar()
    assert motor._con is None
