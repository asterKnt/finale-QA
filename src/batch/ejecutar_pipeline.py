"""CLI para ejecucion del Pipeline Batch completo (Bronze -> Silver -> Gold)."""

import json
import sys
import time

from src.batch.bronze_a_silver import TransformadorBronzeSilver
from src.batch.motor import MotorDuckDB
from src.batch.silver_a_gold import AgregadorSilverGold
from src.core.config import DIR_CUARENTENA, DIR_HISTORICO, DIR_LIMPIO, DIR_MODELADO


def ejecutar_pipeline_batch() -> None:
    """Ejecuta de extremo a extremo el pipeline Batch de Clic Justo."""
    print("================================================================")
    print("Iniciando Pipeline Batch: Clic Justo (DuckDB + Apache Parquet)")
    print("================================================================")
    print(f"Directorio Historico Bronze : {DIR_HISTORICO}")
    print(f"Directorio Cuarentena Batch : {DIR_CUARENTENA}")
    print(f"Directorio Limpio Silver    : {DIR_LIMPIO}")
    print(f"Directorio Modelado Gold    : {DIR_MODELADO}")
    print("----------------------------------------------------------------")

    if not DIR_HISTORICO.exists():
        print(f"Error: No se encontro el directorio de datos historicos en {DIR_HISTORICO}")
        sys.exit(1)

    t_global = time.perf_counter()
    motor = MotorDuckDB()

    # 1. Transformacion Bronze a Silver y Cuarentena
    print("\n[Paso 1/2] Ejecutando auditoria, cuarentena y transformacion Bronze -> Silver...")
    transformador = TransformadorBronzeSilver(motor=motor)
    res_silver = transformador.ejecutar_todo()
    print(f"  -> Dimensiones procesadas en : {res_silver['dimensiones']['segundos']} s")
    print(f"  -> Clics procesados en        : {res_silver['clics']['segundos']} s")
    print(f"  -> Impresiones procesadas en  : {res_silver['impresiones']['segundos']} s")
    print(f"  Total Silver                  : {res_silver['total_segundos']} s")

    # 2. Agregacion Silver a Gold y Watermark
    print("\n[Paso 2/2] Generando modelos analiticos, baselines Gold y watermark...")
    agregador = AgregadorSilverGold(motor=motor)
    res_gold = agregador.ejecutar_todo()
    print(f"  -> P1 Ingresos Mensuales en   : {res_gold['p1']['segundos']} s")
    print(f"  -> P2 Top 10 Sitios en        : {res_gold['p2']['segundos']} s")
    print(f"  -> P3 Franja y Dia CTR en     : {res_gold['p3']['segundos']} s")
    print(f"  -> Baselines P7-P10 y 15-Sep  : {res_gold['baselines']['segundos']} s")
    print(f"  Total Gold                    : {res_gold['total_segundos']} s")

    # 3. Resumen y Conteos
    delta_total = round(time.perf_counter() - t_global, 2)
    print("\n----------------------------------------------------------------")
    print(f"Pipeline Batch completado exitosamente en {delta_total} segundos.")
    print("----------------------------------------------------------------")

    con = motor.conectar()
    filas_p1 = con.execute(f"SELECT COUNT(*) FROM '{DIR_MODELADO}/p1_ingresos_mensuales.parquet'").fetchone()
    filas_p2 = con.execute(f"SELECT COUNT(*) FROM '{DIR_MODELADO}/p2_top_sitios.parquet'").fetchone()
    filas_p3 = con.execute(f"SELECT COUNT(*) FROM '{DIR_MODELADO}/p3_franja_dia_ctr.parquet'").fetchone()
    cuar_clics = con.execute(f"SELECT COUNT(*) FROM '{DIR_CUARENTENA}/historico_clics_rechazados.parquet'").fetchone()
    cuar_imp = con.execute(
        f"SELECT COUNT(*) FROM '{DIR_CUARENTENA}/historico_impresiones_rechazadas.parquet'"
    ).fetchone()

    resumen = {
        "tiempo_total_segundos": delta_total,
        "ultimo_corte_batch_ts": res_gold["ultimo_corte_batch_ts"],
        "cuarentena_historico": {
            "clics_rechazados": cuar_clics[0] if cuar_clics else 0,
            "impresiones_rechazadas": cuar_imp[0] if cuar_imp else 0,
        },
        "modelos_generados": {
            "p1_ingresos_mensuales_filas": filas_p1[0] if filas_p1 else 0,
            "p2_top_sitios_filas": filas_p2[0] if filas_p2 else 0,
            "p3_franja_dia_ctr_filas": filas_p3[0] if filas_p3 else 0,
        },
    }
    print(json.dumps(resumen, indent=2))


if __name__ == "__main__":
    ejecutar_pipeline_batch()
