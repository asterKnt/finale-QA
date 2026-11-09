"""Pruebas de arquitectura, SLA y benchmarks de rendimiento para Clic Justo."""

import time
from pathlib import Path
from src.ingesta.enrutador import EnrutadorIngesta


def test_sla_ingesta_sub_segundo(tmp_datos_dir: Path) -> None:
    """Valida que el procesamiento y enrutamiento individual de un evento tome menos de 50ms (SLA)."""
    dir_crudo = tmp_datos_dir / "crudo"
    dir_cuarentena = tmp_datos_dir / "cuarentena"
    enrutador = EnrutadorIngesta(dir_crudo=dir_crudo, dir_cuarentena=dir_cuarentena)

    evento_prueba = {
        "evento_id": "evt-sla-001",
        "tipo": "clic",
        "version": 1,
        "clic_id": "c-sla-1",
        "impresion_id": "imp-sla-1",
        "campania_id": 10,
        "sitio_id": 5,
        "dispositivo_id": "dev-sla",
        "ip": "192.168.1.1",
        "costo": "0.25",
        "ts": 1761026400,
    }

    inicio = time.perf_counter()
    enrutador.procesar_y_enrutar(evento_prueba)
    duracion = time.perf_counter() - inicio

    # El SLA establece que el enrutamiento unitario no debe superar 50 milisegundos
    assert duracion < 0.05, f"La ingesta tomo {duracion:.4f}s, superando el SLA de 0.05s"