"""Pruebas de integracion End-to-End (E2E) para el pipeline de arquitectura Medallion."""

from pathlib import Path
from src.batch.bronze_a_silver import TransformadorBronzeSilver
from src.batch.motor import MotorDuckDB
from src.batch.silver_a_gold import AgregadorSilverGold


def test_pipeline_medallion_flujo_completo(tmp_datos_dir: Path) -> None:
    """Verifica que las capas Bronze, Silver y Gold se transformen integradamente sin errores."""
    dir_historico = tmp_datos_dir / "historico"
    dir_limpio = tmp_datos_dir / "limpio"
    dir_modelado = tmp_datos_dir / "modelado"
    dir_cuarentena = tmp_datos_dir / "cuarentena"
    dir_crudo = tmp_datos_dir / "crudo"
    dir_estado = tmp_datos_dir / "estado"

    dir_historico.mkdir(parents=True, exist_ok=True)
    (dir_historico / "catalogos").mkdir(parents=True, exist_ok=True)

    # Crear archivos CSV sinteticos minimos
    with open(dir_historico / "sitios_raw.csv", "w", encoding="utf-8") as f:
        f.write("sitio_id,nombre,tipo_code,pais_code,reparto_pct\n")
        f.write("1,Sitio Test,1,1,50.00\n")

    with open(dir_historico / "campanias_raw.csv", "w", encoding="utf-8") as f:
        f.write("campania_id,anunciante_id,presupuesto_diario,costo_por_clic,estado_code,inicio_ts,fin_ts\n")
        f.write("10,1,100.00,0.50,1,1761026400,\n")

    with open(dir_historico / "anunciantes_raw.csv", "w", encoding="utf-8") as f:
        f.write("anunciante_id,nombre,categoria_code,pais_code,alta_ts\n")
        f.write("1,Anunciante Test,1,1,1761026400\n")

    with open(dir_historico / "clics_raw.csv", "w", encoding="utf-8") as f:
        f.write("clic_id,campania_id,sitio_id,dispositivo_id,ip,costo,ts,valido_code\n")
        f.write("c-1,10,1,dev-1,1.1.1.1,0.50,1761026400,1\n")

    with open(dir_historico / "impresiones_hora_raw.csv", "w", encoding="utf-8") as f:
        f.write("impresion_id,campania_id,sitio_id,dispositivo_id,ts,hora_ts,impresiones\n")
        f.write("imp-1,10,1,dev-1,1761026400,1761026400,10\n")

    motor = MotorDuckDB(base_datos=":memory:")

    # 1. Ejecutar Bronze a Silver
    transformador = TransformadorBronzeSilver(
        dir_historico=dir_historico,
        dir_limpio=dir_limpio,
        dir_cuarentena=dir_cuarentena,
        dir_crudo=dir_crudo,
        dir_estado_productor=dir_estado,
        motor=motor,
    )
    res_dim = transformador.procesar_dimensiones()
    assert res_dim["dimensiones_procesadas"] is True

    res_clics = transformador.procesar_clics()
    assert res_clics["clics_procesados"] is True

    # 2. Ejecutar Silver a Gold
    agregador = AgregadorSilverGold(
        dir_limpio=dir_limpio,
        dir_modelado=dir_modelado,
        motor=motor,
    )
    res_p1 = agregador.generar_p1_ingresos_mensuales()
    assert res_p1["p1_generado"] is True

    res_p2 = agregador.generar_p2_top_sitios()
    assert res_p2["p2_generado"] is True

    # Verificar existencia de archivos en capa Gold
    assert (dir_modelado / "p1_ingresos_mensuales.parquet").exists()
    assert (dir_modelado / "p2_top_sitios.parquet").exists()

    motor.cerrar()