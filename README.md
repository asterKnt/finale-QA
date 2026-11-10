# Clic Justo · Plataforma de Datos con Arquitectura Lambda

Plataforma integral de ingenieria y analitica de datos para publicidad digital local, orientada a la deteccion de fraude y anomalias de trafico sub-minuto y a la consolidacion contable determinista.

---

## 1. Vision General del Sistema

Clic Justo opera conectando anunciantes locales con medios digitales (periodicos, blogs y aplicaciones) bajo un esquema de Costo por Clic (CPC). La plataforma implementa una **Arquitectura Lambda** optimizada para:

1. **Deteccion Temprana y Sub-Minuto:** Identificar y mitigar patrones de clics fraudulentos (ataques botnet, clics repetitivos, anomalias de gasto) antes de consolidar el cobro a los anunciantes.
2. **Consistencia Contable Determinista:** Garantizar la conciliacion mensual exacta de ingresos, deduciendo clics invalidos y calculando transferencias a los medios publicadores mediante procesos batch idempotentes.
3. **Serving Layer de Baja Latencia:** Exponer metricas operativas, baselines moviles y reglas de decision en milisegundos mediante una API REST en FastAPI respaldada por DuckDB y Parquet.

---

## 2. Arquitectura de Datos

El diseno combina dos caminos de procesamiento sobre un almacenamiento columnar:

```
+-----------------------------------------------------------------------------------------+
|                                FUENTES DE ENTRADA                                       |
|                  Servidor de Anuncios (Eventos en Vivo) y Archivos Historicos          |
+-----------------------------------------------------------------------------------------+
         |                                                                |
         v (Streaming / Eventos)                                          v (Batch)
+---------------------------------------+               +---------------------------------+
|              SPEED LAYER              |               |           BATCH LAYER           |
|  - Consumo incremental asincrono      |               |  - Motor analitico: DuckDB      |
|  - Validacion JSON Schema (Contratos) |               |  - Arquitectura Medallion:      |
|  - Ventanas deslizantes en memoria    |               |    Bronze: Ingestion cruda      |
|  - Alertas sub-minuto de accion       |               |    Silver: Calidad y tipos      |
|    (normal, revisar, pausar)          |               |    Gold: Modelado y baselines   |
+---------------------------------------+               +---------------------------------+
                    \                                                   /
                     \                                                 /
                      v                                               v
            +---------------------------------------------------------------+
            |                         SERVING LAYER                         |
            |   FastAPI REST API (Consultas analiticas, estado y baselines) |
            +---------------------------------------------------------------+
```

### Arquitectura Medallion (Batch Layer)
- **Bronze (Crudo):** Almacenamiento inmutable de eventos particionados por fecha y tipo de evento.
- **Silver (Limpio):** Tablas Parquet saneadas, deduplicadas, con conversion de tipos y segregacion estricta de informacion sensible (PII).
- **Gold (Modelado):** Vistas analiticas precomputadas, tablas de hechos agregadas por franjas horarias (UTC-6) y baselines moviles de 4 y 8 semanas.

---

## 3. Estructura del Repositorio

```
finale-QA/
|-- src/
|   |-- api/             Serving Layer: endpoints FastAPI, modelos y dependencias
|   |-- batch/           Batch Layer: transformaciones Medallion y motor DuckDB
|   |-- core/            Nucleo comun: configuracion, contratos JSON y modelos Pydantic
|   |-- ingesta/         Ingesta asincrona de eventos y validacion
|   `-- speed/           Componentes de la Speed Layer
|-- contratos/           Esquemas formales JSON Schema draft 2020-12 (clic.v1, impresion.v1)
|-- consultas/           Consultas SQL analiticas de referencia
|-- docs/
|   `-- arc42.md         Especificacion de arquitectura Arc42, decisiones y manual operativo
|-- Dockerfile           Empaquetado de produccion multi-etapa
|-- docker-compose.yml   Orquestacion de servicios locales
|-- pyproject.toml       Definicion de dependencias de produccion
|-- uv.lock              Lockfile determinista de paquetes
`-- .python-version      Version fijada de Python (3.14)
```

---

## 4. Requisitos Previos

- **Python:** 3.14 o superior
- **Gestor de Paquetes:** [`uv`](https://docs.astral.sh/uv/) (v0.13+)
- **Contenedores:** Docker y Docker Compose (v2.20+)

---

## 5. Inicio Rapido

### Opcion A: Despliegue con Docker Compose

1. **Iniciar la Serving API:**
   ```bash
   docker compose up -d serving-api
   ```
2. **Iniciar la ingesta en vivo y el broker:**
   ```bash
   docker compose --profile vivo --profile broker up -d
   ```
3. **Ejecutar el pipeline Batch Medallion:**
   ```bash
   docker compose --profile batch run --rm batch-runner
   ```

Para detalles adicionales de apagado y configuracion operativa, consultar [`docs/arc42.md`](docs/arc42.md#7-vista-de-despliegue-y-manual-operativo-runbook).

### Opcion B: Ejecucion Local con `uv`

1. **Sincronizar el entorno virtual:**
   ```bash
   uv sync --frozen --no-dev
   ```
2. **Iniciar la API REST:**
   ```bash
   uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
   ```
3. **Ejecutar el pipeline Batch:**
   ```bash
   uv run python -m src.batch.scheduler --una-vez
   ```

---

## 6. Endpoints Principales de la API

La documentacion interactiva Swagger / OpenAPI esta disponible en `http://localhost:8000/docs` una vez levantado el servicio.

- **`GET /health`**: Verificacion de salud y disponibilidad del servicio.
- **`GET /v1/campanias/{id}/estado`**: Estado financiero y operativo en tiempo real de una campana (presupuesto diario, gasto consumido hoy, ratio de gasto y accion recomendada: `normal`, `revisar` o `pausar`).
- **`GET /v1/analitica/consultas/{id}`**: Ejecucion y consulta de agregaciones analiticas precomputadas.
- **`GET /v1/catalogos/campanias`**: Listado de campanias registradas y sus configuraciones.

---

## 7. Documentacion Tecnica

- [Documento Maestro de Arquitectura Arc42 y Operaciones](docs/arc42.md)
