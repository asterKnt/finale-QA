"""Pruebas de integracion para el orquestador/scheduler de la Capa Batch."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.batch.scheduler import OrquestadorBatch


def test_orquestador_batch_ejecucion_exitosa(tmp_datos_dir: Path) -> None:
    """Verifica que el orquestador ejecute un ciclo completo y escriba en la bitacora en datos/modelado."""
    dir_historico = tmp_datos_dir / "historico"
    dir_limpio = tmp_datos_dir / "limpio"
    dir_modelado = tmp_datos_dir / "modelado"
    dir_cuarentena = tmp_datos_dir / "cuarentena"
    dir_crudo = tmp_datos_dir / "crudo"

    dir_historico.mkdir(parents=True, exist_ok=True)

    orquestador = OrquestadorBatch(
        dir_historico=dir_historico,
        dir_limpio=dir_limpio,
        dir_modelado=dir_modelado,
        dir_cuarentena=dir_cuarentena,
        dir_crudo=dir_crudo,
        max_reintentos=1,
    )

    # Mock de los transformadores para probar el flujo del scheduler sin requerir archivos parquet pesados
    with (
        patch("src.batch.scheduler.TransformadorBronzeSilver") as mock_tb,
        patch("src.batch.scheduler.AgregadorSilverGold") as mock_ag,
        patch("src.batch.scheduler.MotorDuckDB") as mock_motor,
    ):
        mock_tb.return_value.ejecutar_todo.return_value = {
            "total_segundos": 0.5,
            "dimensiones": {"segundos": 0.1},
            "clics": {"segundos": 0.2},
            "impresiones": {"segundos": 0.2},
        }
        mock_ag.return_value.ejecutar_todo.return_value = {
            "total_segundos": 0.4,
            "ultimo_corte_batch_ts": 1761026400,
        }

        res = orquestador.ejecutar_ciclo()

        assert res["estado"] == "exitoso"
        assert res["intentos"] == 1
        assert res["ultimo_corte_batch_ts"] == 1761026400

        # Verificar que se creo la bitacora
        ruta_bitacora = dir_modelado / "bitacora_batch.jsonl"
        assert ruta_bitacora.exists()
        with open(ruta_bitacora, encoding="utf-8") as f:
            registro = json.loads(f.readline())
            assert registro["estado"] == "exitoso"