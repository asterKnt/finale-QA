"""Pruebas unitarias para configuracion global y manejo de tiempo en Clic Justo."""

from src.core.config import (
    TIMEZONE_OFFSET_HOURS,
    VENTANA_4_SEMANAS_S,
    VENTANA_8_SEMANAS_S,
    convertir_weekday_a_duckdb_dow,
)


def test_constantes_tiempo_config() -> None:
    """Verifica que las constantes de tiempo y zonas horarias sean correctas."""
    assert TIMEZONE_OFFSET_HOURS == -6
    assert VENTANA_4_SEMANAS_S == 4 * 7 * 86_400
    assert VENTANA_8_SEMANAS_S == 8 * 7 * 86_400


def test_conversion_weekday_python_a_duckdb_dow() -> None:
    """Valida la conversion de datetime.weekday() (0=Lunes..6=Domingo) a DuckDB DOW (0=Domingo..6=Sabado)."""
    # Lunes en Python es 0 -> en DuckDB DOW debe ser 1
    assert convertir_weekday_a_duckdb_dow(0) == 1
    # Sabado en Python es 5 -> en DuckDB DOW debe ser 6
    assert convertir_weekday_a_duckdb_dow(5) == 6
    # Domingo en Python es 6 -> en DuckDB DOW debe ser 0
    assert convertir_weekday_a_duckdb_dow(6) == 0
