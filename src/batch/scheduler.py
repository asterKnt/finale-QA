"""Orquestador ligero nativo en Python para la Capa Batch (reemplazo KISS de Prefect/Airflow)."""

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.batch.bronze_a_silver import TransformadorBronzeSilver
from src.batch.motor import MotorDuckDB
from src.batch.silver_a_gold import AgregadorSilverGold
from src.core.config import DIR_CRUDO, DIR_CUARENTENA, DIR_HISTORICO, DIR_LIMPIO, DIR_MODELADO


class OrquestadorBatch:
    """Coordina el ciclo lineal Bronze -> Silver -> Gold -> Watermark con reintentos y bitacora."""

    def __init__(
        self,
        dir_historico: Path = DIR_HISTORICO,
        dir_limpio: Path = DIR_LIMPIO,
        dir_modelado: Path = DIR_MODELADO,
        dir_cuarentena: Path = DIR_CUARENTENA,
        dir_crudo: Path = DIR_CRUDO,
        max_reintentos: int = 3,
        espera_inicial_s: float = 1.0,
    ) -> None:
        self.dir_historico = dir_historico
        self.dir_limpio = dir_limpio
        self.dir_modelado = dir_modelado
        self.dir_cuarentena = dir_cuarentena
        self.dir_crudo = dir_crudo
        self.max_reintentos = max_reintentos
        self.espera_inicial_s = espera_inicial_s

    def _registrar_bitacora(self, entrada: dict[str, Any]) -> None:
        """Escribe una linea JSON estructurada en datos/modelado/bitacora_batch.jsonl."""
        self.dir_modelado.mkdir(parents=True, exist_ok=True)
        ruta_bitacora = self.dir_modelado / "bitacora_batch.jsonl"
        with open(ruta_bitacora, "a", encoding="utf-8") as f:
            f.write(json.dumps(entrada, ensure_ascii=False) + "\n")

    def ejecutar_ciclo(self) -> dict[str, Any]:
        """Ejecuta una corrida completa del pipeline Batch con reintentos exponential backoff."""
        intento = 0
        espera = self.espera_inicial_s
        ultimo_error = ""

        while intento < self.max_reintentos:
            intento += 1
            t0 = time.perf_counter()
            try:
                motor = MotorDuckDB()
                transformador = TransformadorBronzeSilver(
                    dir_historico=self.dir_historico,
                    dir_limpio=self.dir_limpio,
                    dir_cuarentena=self.dir_cuarentena,
                    dir_crudo=self.dir_crudo,
                    motor=motor,
                )
                res_silver = transformador.ejecutar_todo()

                agregador = AgregadorSilverGold(
                    dir_limpio=self.dir_limpio,
                    dir_modelado=self.dir_modelado,
                    motor=motor,
                )
                res_gold = agregador.ejecutar_todo()
                motor.cerrar()

                duracion = round(time.perf_counter() - t0, 3)
                registro: dict[str, Any] = {
                    "ts_ejecucion_utc": datetime.now(tz=UTC).isoformat(),
                    "estado": "exitoso",
                    "intentos": intento,
                    "duracion_segundos": duracion,
                    "silver_segundos": res_silver["total_segundos"],
                    "gold_segundos": res_gold["total_segundos"],
                    "ultimo_corte_batch_ts": res_gold["ultimo_corte_batch_ts"],
                }
                self._registrar_bitacora(registro)
                return registro
            except Exception as exc:
                ultimo_error = f"{type(exc).__name__}: {exc}"
                if intento < self.max_reintentos:
                    time.sleep(espera)
                    espera *= 2.0

        fallo: dict[str, Any] = {
            "ts_ejecucion_utc": datetime.now(tz=UTC).isoformat(),
            "estado": "fallido",
            "intentos": intento,
            "error": ultimo_error,
        }
        self._registrar_bitacora(fallo)
        return fallo


def main() -> None:
    """CLI del orquestador Batch."""
    parser = argparse.ArgumentParser(description="Orquestador ligero nativo de la Capa Batch Clic Justo")
    parser.add_argument("--una-vez", action="store_true", help="Ejecuta un unico ciclo batch y termina")
    parser.add_argument(
        "--intervalo-segundos",
        type=int,
        default=3600,
        help="Intervalo en segundos entre corridas periodicas (por defecto 3600s = 1h)",
    )
    args = parser.parse_args()

    orquestador = OrquestadorBatch()
    if args.una_vez:
        resultado = orquestador.ejecutar_ciclo()
        print(json.dumps(resultado, indent=2))
        sys.exit(0 if resultado["estado"] == "exitoso" else 1)

    try:
        while True:
            resultado = orquestador.ejecutar_ciclo()
            print(json.dumps(resultado), flush=True)
            time.sleep(max(1, args.intervalo_segundos))
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
