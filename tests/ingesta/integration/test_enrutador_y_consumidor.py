"""Pruebas de integracion para el consumidor y enrutador de ingesta en vivo."""

from pathlib import Path
from typing import Any

from src.ingesta.consumidor import ConsumidorEventos
from src.ingesta.enrutador import EnrutadorIngesta


def test_consumidor_procesar_iterador_metricas(tmp_datos_dir: Path) -> None:
    """Verifica que el consumidor procese iteradores de eventos y genere metricas correctas."""
    dir_crudo = tmp_datos_dir / "crudo"
    dir_cuarentena = tmp_datos_dir / "cuarentena"

    enrutador = EnrutadorIngesta(dir_crudo=dir_crudo, dir_cuarentena=dir_cuarentena)
    consumidor = ConsumidorEventos(enrutador=enrutador)

    lote_eventos: list[dict[str, Any]] = [
        # Evento 1: Clic valido
        {
            "evento_id": "evt-001",
            "tipo": "clic",
            "version": 1,
            "clic_id": "c-100",
            "impresion_id": "imp-100",
            "campania_id": 1,
            "sitio_id": 2,
            "dispositivo_id": "d-123",
            "ip": "10.0.0.1",
            "costo": "0.15",
            "ts": 1761026400,
        },
        # Evento 2: Impresion valida
        {
            "evento_id": "evt-002",
            "tipo": "impresion",
            "version": 1,
            "impresion_id": "imp-100",
            "campania_id": 1,
            "sitio_id": 2,
            "dispositivo_id": "d-123",
            "ts": 1761026400,
        },
        # Evento 3: Clic invalido (falta ip)
        {
            "evento_id": "evt-003",
            "tipo": "clic",
            "version": 1,
            "clic_id": "c-101",
            "costo": "0.15",
            "ts": 1761026400,
        },
    ]

    metricas = consumidor.procesar_iterador(lote_eventos)

    assert metricas["total_procesados"] == 3
    assert metricas["total_validos"] == 2
    assert metricas["total_cuarentena"] == 1
    assert metricas["nuevos_procesados"] == 3