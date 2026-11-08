"""Consumidor para ingesta incremental de archivos horarios JSONL o streams de eventos."""

import argparse
import json
import sys
import time
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast

from src.core.config import DIR_CUARENTENA
from src.ingesta.enrutador import EnrutadorIngesta


class ConsumidorEventos:
    """Procesa flujos continuos o incrementales de eventos, midiendo rendimiento y distribucion."""

    def __init__(self, enrutador: EnrutadorIngesta | None = None) -> None:
        self.enrutador = enrutador or EnrutadorIngesta()
        self.total_procesados: int = 0
        self.total_validos: int = 0
        self.total_cuarentena: int = 0

    def procesar_iterador(self, eventos: Iterable[dict[str, Any]]) -> dict[str, Any]:
        """Procesa una secuencia de eventos en memoria o generada por generadores."""
        t0 = time.perf_counter()
        nuevos_proc = 0
        nuevos_val = 0
        nuevos_cuar = 0

        for evento in eventos:
            destino, _ = self.enrutador.procesar_y_enrutar(evento)
            self.total_procesados += 1
            nuevos_proc += 1
            if destino == "crudo":
                self.total_validos += 1
                nuevos_val += 1
            else:
                self.total_cuarentena += 1
                nuevos_cuar += 1

        delta = time.perf_counter() - t0
        tps = nuevos_proc / delta if delta > 0 else 0.0

        return {
            "nuevos_procesados": nuevos_proc,
            "nuevos_validos": nuevos_val,
            "nuevos_cuarentena": nuevos_cuar,
            "total_procesados": self.total_procesados,
            "total_validos": self.total_validos,
            "total_cuarentena": self.total_cuarentena,
            "segundos": round(delta, 4),
            "eventos_por_segundo": round(tps, 2),
        }

    def procesar_archivo_jsonl(self, ruta_archivo: Path) -> dict[str, Any]:
        """Lee linea por linea un archivo JSONL unico."""

        def generador_lineas() -> Iterable[dict[str, Any]]:
            with open(ruta_archivo, encoding="utf-8") as f:
                for linea in f:
                    linea_limpia = linea.strip()
                    if not linea_limpia:
                        continue
                    try:
                        yield cast(dict[str, Any], json.loads(linea_limpia))
                    except json.JSONDecodeError:
                        yield {"_corrupted_raw": linea_limpia, "tipo": "corrupto"}

        return self.procesar_iterador(generador_lineas())

    def procesar_directorio_incremental(
        self,
        ruta_dir: Path,
        ruta_offsets: Path | None = None,
    ) -> dict[str, Any]:
        """Barre incrementalmente <carpeta>/<tipo>/AAAAMMDD-HH.jsonl guardando el offset en bytes.

        Este metodo es 100% compatible con `--salida archivo` del productor oficial y garantiza
        procesamiento idempotente sin releer eventos ya enrutados.
        """
        archivo_offsets = ruta_offsets or (DIR_CUARENTENA.parent / ".offset_ingesta.json")
        offsets: dict[str, int] = {}
        if archivo_offsets.exists():
            try:
                with open(archivo_offsets, encoding="utf-8") as f:
                    offsets = cast(dict[str, int], json.load(f))
            except OSError, json.JSONDecodeError:
                offsets = {}

        archivos_jsonl = sorted(ruta_dir.rglob("*.jsonl")) if ruta_dir.exists() else []
        lote_eventos: list[dict[str, Any]] = []

        for archivo in archivos_jsonl:
            clave = str(archivo.resolve())
            pos_anterior = offsets.get(clave, 0)
            tamano_actual = archivo.stat().st_size
            if tamano_actual <= pos_anterior:
                continue

            with open(archivo, "rb") as fb:
                fb.seek(pos_anterior)
                Resto = fb.read()
                nueva_pos = fb.tell()

            texto = Resto.decode("utf-8", errors="replace")
            for linea in texto.splitlines():
                linea_limpia = linea.strip()
                if not linea_limpia:
                    continue
                try:
                    lote_eventos.append(cast(dict[str, Any], json.loads(linea_limpia)))
                except json.JSONDecodeError:
                    lote_eventos.append({"_corrupted_raw": linea_limpia, "tipo": "corrupto"})

            offsets[clave] = nueva_pos

        metricas = self.procesar_iterador(lote_eventos)

        archivo_offsets.parent.mkdir(parents=True, exist_ok=True)
        tmp_offsets = archivo_offsets.with_suffix(".tmp")
        with open(tmp_offsets, "w", encoding="utf-8") as f:
            json.dump(offsets, f, indent=2)
        tmp_offsets.replace(archivo_offsets)

        metricas["archivos_inspeccionados"] = len(archivos_jsonl)
        return metricas


def main() -> None:
    """Punto de entrada de consola para el worker de ingesta."""
    parser = argparse.ArgumentParser(description="Consumidor y Enrutador de Ingesta Clic Justo")
    parser.add_argument("--archivo", type=str, help="Ruta a un archivo JSONL individual a procesar")
    parser.add_argument(
        "--directorio",
        type=str,
        help="Ruta al directorio raiz de eventos horarios (--salida archivo del productor)",
    )
    parser.add_argument(
        "--intervalo",
        type=float,
        default=0.0,
        help="Si es > 0, vigila continuamente el directorio cada N segundos",
    )
    parser.add_argument("--prueba", action="store_true", help="Ejecuta una corrida con muestra sintetica")

    args = parser.parse_args()
    consumidor = ConsumidorEventos()

    if args.prueba:
        muestra: list[dict[str, Any]] = [
            {
                "evento_id": "evt-001",
                "tipo": "impresion",
                "version": 1,
                "impresion_id": "imp-100",
                "campania_id": 8596,
                "sitio_id": 260,
                "dispositivo_id": "d-5d99cc2ff365b3e2",
                "ts": int(time.time()),
            },
            {
                "evento_id": "evt-002",
                "tipo": "clic",
                "version": 1,
                "clic_id": "c-200",
                "impresion_id": "imp-100",
                "campania_id": 8596,
                "sitio_id": 260,
                "dispositivo_id": "d-5d99cc2ff365b3e2",
                "ip": "198.18.58.247",
                "costo": "0.17",
                "ts": int(time.time()),
            },
            {
                "evento_id": "evt-mal-001",
                "tipo": "clic",
                "version": 1,
                "clic_id": "c-mal",
                "costo": "0.50",
                "ts": int(time.time()),
            },
        ]
        metricas = consumidor.procesar_iterador(muestra)
        print(json.dumps(metricas, indent=2))
        sys.exit(0)

    if args.directorio:
        ruta_dir = Path(args.directorio)
        ruta_dir.mkdir(parents=True, exist_ok=True)
        if args.intervalo <= 0:
            metricas = consumidor.procesar_directorio_incremental(ruta_dir)
            print(json.dumps(metricas, indent=2))
            sys.exit(0)
        try:
            while True:
                metricas = consumidor.procesar_directorio_incremental(ruta_dir)
                if metricas["nuevos_procesados"] > 0:
                    print(json.dumps(metricas), flush=True)
                time.sleep(args.intervalo)
        except KeyboardInterrupt:
            sys.exit(0)

    if args.archivo:
        ruta = Path(args.archivo)
        if not ruta.exists():
            print(f"Error: El archivo '{ruta}' no existe.", file=sys.stderr)
            sys.exit(1)
        metricas = consumidor.procesar_archivo_jsonl(ruta)
        print(json.dumps(metricas, indent=2))
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
