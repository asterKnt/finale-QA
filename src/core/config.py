"""Configuracion centralizada de rutas y constantes de negocio de Clic Justo."""

import os
from pathlib import Path

# Rutas base del proyecto
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
CONTRATOS_DIR: Path = BASE_DIR / "contratos"
DATOS_DIR: Path = Path(os.environ.get("CLIC_JUSTO_DATOS_DIR", str(BASE_DIR / "datos")))

# Zonas de almacenamiento Medallion
DIR_HISTORICO: Path = DATOS_DIR / "clic-justo-historico-v1"
DIR_CRUDO: Path = DATOS_DIR / "crudo"
DIR_CUARENTENA: Path = DATOS_DIR / "cuarentena"
DIR_LIMPIO: Path = DATOS_DIR / "limpio"
DIR_MODELADO: Path = DATOS_DIR / "modelado"
DIR_EVENTOS_VIVO: Path = DATOS_DIR / "eventos_vivo"
DIR_ESTADO_PRODUCTOR: Path = DATOS_DIR / "estado"

# Constantes del Negocio y Temporales
INICIO_HISTORICO_TS: int = 1761026400  # 21-oct-2025 00:00:00 UTC-6
CORTE_HISTORICO_TS: int = 1792562399  # 20-oct-2026 23:59:59 UTC-6
MAX_TS_RAZONABLE_SEGUNDOS: int = 10_000_000_000  # Umbral para detectar timestamps corruptos en milisegundos
TIMEZONE_OFFSET_HOURS: int = -6  # UTC-6 (Centroamerica)
FRANJAS_HORARIAS_COUNT: int = 12  # 12 bloques de 2 horas (00:00-02:00 ... 22:00-24:00)

# Constantes de ventanas moviles (Seccion 07 de la Guia)
SEGUNDOS_DIA: int = 86_400
SEGUNDOS_SEMANA: int = 7 * SEGUNDOS_DIA  # 604,800 s
VENTANA_4_SEMANAS_S: int = 4 * SEGUNDOS_SEMANA  # 2,419,200 s
VENTANA_8_SEMANAS_S: int = 8 * SEGUNDOS_SEMANA  # 4,838,400 s

# Configuracion de DuckDB
DUCKDB_MEMORY_LIMIT: str = "2GB"
DUCKDB_THREADS: int = 4


def convertir_weekday_a_duckdb_dow(weekday_iso: int) -> int:
    """Convierte datetime.weekday() de Python (0=Lunes..6=Domingo) a EXTRACT(DOW) de DuckDB (0=Domingo..6=Sabado)."""
    return (weekday_iso + 1) % 7
