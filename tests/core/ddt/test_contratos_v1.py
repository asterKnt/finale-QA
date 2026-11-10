"""Pruebas dirigidas por datos (DDT) para validacion de contratos v1 (clic e impresion)."""

from typing import Any

import pytest

from src.core.contratos import ValidadorContratos


@pytest.fixture
def validador() -> ValidadorContratos:
    """Instancia del validador de contratos con los esquemas cargados."""
    return ValidadorContratos()


def test_validar_evento_clic_valido(validador: ValidadorContratos, muestra_evento_clic_valido: dict[str, Any]) -> None:
    """Verifica que un evento de clic valido pase la validacion del contrato v1."""
    es_valido, tipo, error_tipo, error_detalle = validador.validar_evento(muestra_evento_clic_valido)
    assert es_valido is True
    assert tipo == "clic"
    assert error_tipo is None
    assert error_detalle is None


def test_validar_evento_impresion_valida(
    validador: ValidadorContratos, muestra_evento_impresion_valido: dict[str, Any]
) -> None:
    """Verifica que un evento de impresion valido pase la validacion del contrato v1."""
    es_valido, tipo, error_tipo, error_detalle = validador.validar_evento(muestra_evento_impresion_valido)
    assert es_valido is True
    assert tipo == "impresion"
    assert error_tipo is None
    assert error_detalle is None


@pytest.mark.parametrize(
    "campo_faltante",
    ["evento_id", "clic_id", "impresion_id", "campania_id", "sitio_id", "dispositivo_id", "ip", "costo", "ts"],
)
def test_validar_clic_campos_requeridos(
    validador: ValidadorContratos, muestra_evento_clic_valido: dict[str, Any], campo_faltante: str
) -> None:
    """Valida que remover cualquier campo obligatorio falle la validacion con ValidationError."""
    evento = muestra_evento_clic_valido.copy()
    del evento[campo_faltante]

    es_valido, tipo, error_tipo, error_detalle = validador.validar_evento(evento)
    assert es_valido is False
    assert tipo == "clic"
    assert error_tipo == "ValidationError"
    assert error_detalle is not None


def test_validar_tipo_evento_desconocido(validador: ValidadorContratos) -> None:
    """Verifica el descarte con DiscriminatorError cuando el tipo de evento no existe."""
    evento = {"tipo": "tipo_inexistente", "version": 1}
    es_valido, tipo, error_tipo, error_detalle = validador.validar_evento(evento)

    assert es_valido is False
    assert tipo == "tipo_inexistente"
    assert error_tipo == "DiscriminatorError"
    assert "no reconocido" in str(error_detalle)
