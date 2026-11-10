"""Pruebas de integracion para la ingesta incremental basada en offsets."""

import json
from pathlib import Path

from src.ingesta.consumidor import ConsumidorEventos
from src.ingesta.enrutador import EnrutadorIngesta


def test_consumidor_procesar_directorio_incremental_offsets(tmp_datos_dir: Path) -> None:
    """Verifica que la lectura por directorio guarde offsets y evite duplicar eventos en corridas sucesivas."""
    dir_crudo = tmp_datos_dir / "crudo"
    dir_cuarentena = tmp_datos_dir / "cuarentena"
    dir_eventos = tmp_datos_dir / "eventos_vivo" / "clic"
    dir_eventos.mkdir(parents=True, exist_ok=True)
    archivo_offsets = tmp_datos_dir / "offsets.json"

    enrutador = EnrutadorIngesta(dir_crudo=dir_crudo, dir_cuarentena=dir_cuarentena)
    consumidor = ConsumidorEventos(enrutador=enrutador)

    archivo_jsonl = dir_eventos / "20260915-10.jsonl"
    evento1 = {
        "evento_id": "evt-inc-001",
        "tipo": "clic",
        "version": 1,
        "clic_id": "c-inc-1",
        "impresion_id": "imp-1",
        "campania_id": 5,
        "sitio_id": 3,
        "dispositivo_id": "dev-1",
        "ip": "1.1.1.1",
        "costo": "0.10",
        "ts": 1761026400,
    }

    # 1. Escribir primer evento
    with open(archivo_jsonl, "w", encoding="utf-8") as f:
        f.write(json.dumps(evento1) + "\n")

    # Primera corrida del consumidor
    m1 = consumidor.procesar_directorio_incremental(tmp_datos_dir / "eventos_vivo", ruta_offsets=archivo_offsets)
    assert m1["nuevos_procesados"] == 1
    assert m1["nuevos_validos"] == 1

    # Segunda corrida sin nuevos datos en el archivo
    m2 = consumidor.procesar_directorio_incremental(tmp_datos_dir / "eventos_vivo", ruta_offsets=archivo_offsets)
    assert m2["nuevos_procesados"] == 0

    # 2. Agregar un segundo evento al mismo archivo
    evento2 = {
        "evento_id": "evt-inc-002",
        "tipo": "clic",
        "version": 1,
        "clic_id": "c-inc-2",
        "impresion_id": "imp-2",
        "campania_id": 5,
        "sitio_id": 3,
        "dispositivo_id": "dev-2",
        "ip": "2.2.2.2",
        "costo": "0.20",
        "ts": 1761026401,
    }
    with open(archivo_jsonl, "a", encoding="utf-8") as f:
        f.write(json.dumps(evento2) + "\n")

    # Tercera corrida: solo debe procesar el evento nuevo agregado tras el offset
    m3 = consumidor.procesar_directorio_incremental(tmp_datos_dir / "eventos_vivo", ruta_offsets=archivo_offsets)
    assert m3["nuevos_procesados"] == 1
    assert m3["total_procesados"] == 2
