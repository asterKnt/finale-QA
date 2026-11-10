"""Pruebas dirigidas por datos (DDT) para evolucion de versiones y multiversion de contratos."""

from typing import Any

from src.core.contratos import ValidadorContratos


def test_version_no_registrada_retorna_schema_evolution_error() -> None:
    """Verifica que solicitar una version no registrada para un tipo valido retorne SchemaEvolutionError."""
    validador = ValidadorContratos()
    evento_v2_inexistente: dict[str, Any] = {
        "evento_id": "evt-v2-001",
        "tipo": "clic",
        "version": 99,
        "clic_id": "c-999",
    }

    es_valido, tipo, error_tipo, error_detalle = validador.validar_evento(evento_v2_inexistente)

    assert es_valido is False
    assert tipo == "clic"
    assert error_tipo == "SchemaEvolutionError"
    assert "La version 99 para el tipo 'clic' no tiene un contrato registrado" in str(error_detalle)


def test_propiedad_versiones_registradas() -> None:
    """Verifica que el validador registre correctamente los pares (tipo, version) disponibles."""
    validador = ValidadorContratos()
    versiones = validador.versiones_registradas

    assert ("clic", 1) in versiones
    assert ("impresion", 1) in versiones
