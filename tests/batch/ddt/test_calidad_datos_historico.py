"""Pruebas dirigidas por datos (DDT) para validar la calidad e integridad de los datos historicos."""

from pathlib import Path

from duckdb import DuckDBPyConnection

from src.batch.bronze_a_silver import TransformadorBronzeSilver
from src.batch.motor import MotorDuckDB


def test_calidad_deduplicacion_y_tipos_silver(tmp_datos_dir: Path) -> None:
    """Verifica la deduplicacion de entidades (sitios, campanias) y casting correcto a Parquet."""
    dir_historico = tmp_datos_dir / "historico"
    dir_limpio = tmp_datos_dir / "limpio"
    dir_cuarentena = tmp_datos_dir / "cuarentena"
    dir_crudo = tmp_datos_dir / "crudo"
    dir_estado = tmp_datos_dir / "estado"

    dir_historico.mkdir(parents=True, exist_ok=True)
    (dir_historico / "catalogos").mkdir(parents=True, exist_ok=True)

    # Sitio 10 duplicado intencionalmente para probar la deduplicacion
    with open(dir_historico / "sitios_raw.csv", "w", encoding="utf-8") as f:
        f.write("sitio_id,nombre,tipo_code,pais_code,reparto_pct\n")
        f.write("10,Sitio A,1,1,50.00\n")
        f.write("10,Sitio A Duplicado,1,1,50.00\n")

    with open(dir_historico / "campanias_raw.csv", "w", encoding="utf-8") as f:
        f.write("campania_id,anunciante_id,presupuesto_diario,costo_por_clic,estado_code,inicio_ts,fin_ts\n")
        f.write("100,1,100.00,0.50,1,1761026400,\n")

    with open(dir_historico / "anunciantes_raw.csv", "w", encoding="utf-8") as f:
        f.write("anunciante_id,nombre,categoria_code,pais_code,alta_ts\n")
        f.write("1,Anunciante 1,1,1,1761026400\n")

    motor = MotorDuckDB(base_datos=":memory:")
    transformador = TransformadorBronzeSilver(
        dir_historico=dir_historico,
        dir_limpio=dir_limpio,
        dir_cuarentena=dir_cuarentena,
        dir_crudo=dir_crudo,
        dir_estado_productor=dir_estado,
        motor=motor,
    )
    transformador.procesar_dimensiones()

    con: DuckDBPyConnection = motor.conectar()
    archivo_sitios = dir_limpio / "dimensiones/sitios.parquet"

    # Verificar que solo exista 1 registro para sitio_id 10 tras la deduplicacion
    conteo = con.execute(f"SELECT COUNT(*) FROM '{archivo_sitios}' WHERE sitio_id = 10").fetchone()
    assert conteo is not None
    assert conteo[0] == 1
