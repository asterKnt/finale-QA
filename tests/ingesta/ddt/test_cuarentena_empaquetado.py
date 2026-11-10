"""Pruebas dirigidas por datos (DDT) para enrutamiento a cuarentena y empaquetado de errores."""

import json
from pathlib import Path
from typing import Any

from src.ingesta.enrutador import EnrutadorIngesta


def test_enrutamiento_evento_valido_a_crudo(tmp_datos_dir: Path, muestra_evento_clic_valido: dict[str, Any]) -> None:
    """Verifica que un evento valido se guarde en la zona cruda append-only."""
    dir_crudo = tmp_datos_dir / "crudo"
    dir_cuarentena = tmp_datos_dir / "cuarentena"

    enrutador = EnrutadorIngesta(dir_crudo=dir_crudo, dir_cuarentena=dir_cuarentena)
    destino, ruta_archivo = enrutador.procesar_y_enrutar(muestra_evento_clic_valido)

    assert destino == "crudo"
    assert ruta_archivo.exists()
    assert "crudo" in str(ruta_archivo)

    # Verificar que el archivo contenga la linea JSON enriquecida
    with open(ruta_archivo, encoding="utf-8") as f:
        linea = json.loads(f.readline())
        assert linea["evento_id"] == muestra_evento_clic_valido["evento_id"]
        assert "_ingest_ts" in linea


def test_enrutamiento_evento_invalido_a_cuarentena(tmp_datos_dir: Path) -> None:
    """Verifica que un evento con campos faltantes se envie a cuarentena con su metadato de error."""
    dir_crudo = tmp_datos_dir / "crudo"
    dir_cuarentena = tmp_datos_dir / "cuarentena"

    enrutador = EnrutadorIngesta(dir_crudo=dir_crudo, dir_cuarentena=dir_cuarentena)

    # Evento de clic sin ip ni dispositivo_id
    evento_corrupto = {
        "evento_id": "evt-mal-001",
        "tipo": "clic",
        "version": 1,
        "clic_id": "c-mal",
        "costo": "0.50",
    }

    destino, ruta_archivo = enrutador.procesar_y_enrutar(evento_corrupto)

    assert destino == "cuarentena"
    assert ruta_archivo.exists()
    assert "cuarentena" in str(ruta_archivo)

    with open(ruta_archivo, encoding="utf-8") as f:
        linea = json.loads(f.readline())
        assert linea["_error_tipo"] == "ValidationError"
        assert "_error_detalle" in linea
        assert linea["payload_original"]["evento_id"] == "evt-mal-001"
