"""Enrutador de eventos hacia la Zona Cruda inmutable o a la Zona de Cuarentena."""

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.core.config import DIR_CRUDO, DIR_CUARENTENA, TIMEZONE_OFFSET_HOURS
from src.core.contratos import ValidadorContratos

TZ_LOCAL = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))


class EnrutadorIngesta:
    """Valida y enruta eventos hacia almacenamiento crudo particionado o cuarentena."""

    def __init__(
        self,
        dir_crudo: Path = DIR_CRUDO,
        dir_cuarentena: Path = DIR_CUARENTENA,
        validador: ValidadorContratos | None = None,
    ) -> None:
        self.dir_crudo = dir_crudo
        self.dir_cuarentena = dir_cuarentena
        self.validador = validador or ValidadorContratos()

    def procesar_y_enrutar(self, payload: dict[str, Any]) -> tuple[str, Path]:
        """Evalua el contrato del evento y lo escribe en la zona correspondiente.

        Returns:
            Tuple con el destino ("crudo" o "cuarentena") y la ruta del archivo destino.
        """
        ingest_ts = int(time.time())
        es_valido, tipo, error_tipo, error_detalle = self.validador.validar_evento(payload)

        if es_valido:
            # Evento conforme: persistencia en Capa Bronze Cruda
            ts_evento = payload.get("ts", ingest_ts)
            dt = datetime.fromtimestamp(ts_evento, tz=TZ_LOCAL)
            ruta_carpeta = (
                self.dir_crudo
                / tipo
                / f"anio={dt.year}"
                / f"mes={dt.month:02d}"
                / f"dia={dt.day:02d}"
                / f"hora={dt.hour:02d}"
            )
            ruta_carpeta.mkdir(parents=True, exist_ok=True)
            ruta_archivo = ruta_carpeta / "eventos.jsonl"

            # Enriquecimiento append-only sin alterar los campos contractuales
            registro_crudo = payload.copy()
            registro_crudo["_ingest_ts"] = ingest_ts

            with open(ruta_archivo, "a", encoding="utf-8") as f:
                f.write(json.dumps(registro_crudo, ensure_ascii=False) + "\n")

            return ("crudo", ruta_archivo)

        # Evento corrupto o no conforme: empaquetado para Cuarentena
        dt_cuarentena = datetime.fromtimestamp(ingest_ts, tz=TZ_LOCAL)
        ruta_carpeta_q = (
            self.dir_cuarentena
            / tipo
            / f"anio={dt_cuarentena.year}"
            / f"mes={dt_cuarentena.month:02d}"
            / f"dia={dt_cuarentena.day:02d}"
        )
        ruta_carpeta_q.mkdir(parents=True, exist_ok=True)
        ruta_archivo_q = ruta_carpeta_q / "cuarentena.jsonl"

        paquete_cuarentena = {
            "_ingest_ts": ingest_ts,
            "_error_tipo": error_tipo or "UnknownError",
            "_error_detalle": error_detalle or "Contrato violado",
            "payload_original": payload.copy(),
        }

        with open(ruta_archivo_q, "a", encoding="utf-8") as f:
            f.write(json.dumps(paquete_cuarentena, ensure_ascii=False) + "\n")

        return ("cuarentena", ruta_archivo_q)
