"""Gestor de conexion y sesiones analiticas de DuckDB para la Capa Batch."""

from pathlib import Path
from typing import Any

import duckdb
from duckdb import DuckDBPyConnection

from src.core.config import DUCKDB_MEMORY_LIMIT, DUCKDB_THREADS


class MotorDuckDB:
    """Administra sesiones vectorizadas de DuckDB optimizadas para Parquet y ZSTD."""

    def __init__(
        self,
        base_datos: str | Path = ":memory:",
        limite_memoria: str = DUCKDB_MEMORY_LIMIT,
        hilos: int = DUCKDB_THREADS,
    ) -> None:
        self.base_datos = str(base_datos)
        self.limite_memoria = limite_memoria
        self.hilos = hilos
        self._con: DuckDBPyConnection | None = None

    def conectar(self) -> DuckDBPyConnection:
        """Inicializa o retorna la conexion activa con configuracion de rendimiento."""
        if self._con is None:
            self._con = duckdb.connect(database=self.base_datos)
            self._con.execute(f"SET max_memory = '{self.limite_memoria}';")
            self._con.execute(f"SET threads = {self.hilos};")
            self._con.execute("SET preserve_insertion_order = false;")
        return self._con

    def ejecutar(self, sql: str, params: list[Any] | None = None) -> Any:
        """Ejecuta una consulta SQL en la sesion actual."""
        con = self.conectar()
        if params is not None:
            return con.execute(sql, params)
        return con.execute(sql)

    def cerrar(self) -> None:
        """Cierra la conexion liberando buffers de memoria."""
        if self._con is not None:
            self._con.close()
            self._con = None
