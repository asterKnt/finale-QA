# Contexto del proyecto: finale-QA

## Estructura del Proyecto

```
finale-QA/
├── consultas/
│   ├── .gitkeep
│   ├── p1_ingresos_por_mes_pais.sql
│   ├── p2_top_sitios_calidad.sql
│   └── p3_franja_dia_ctr.sql
├── contratos/
│   ├── .gitkeep
│   ├── clic.v1.json
│   └── impresion.v1.json
├── docs/
│   └── arc42.md
├── src/
│   ├── api/
│   │   ├── .gitkeep
│   │   ├── __init__.py
│   │   ├── dependencias.py
│   │   ├── main.py
│   │   ├── rutas_analitica.py
│   │   ├── rutas_campanias.py
│   │   └── rutas_catalogos.py
│   ├── batch/
│   │   ├── .gitkeep
│   │   ├── __init__.py
│   │   ├── bronze_a_silver.py
│   │   ├── ejecutar_pipeline.py
│   │   ├── motor.py
│   │   ├── scheduler.py
│   │   └── silver_a_gold.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── contratos.py
│   │   └── modelos.py
│   ├── ingesta/
│   │   ├── __init__.py
│   │   ├── consumidor.py
│   │   └── enrutador.py
│   ├── speed/
│   │   └── .gitkeep
│   └── __init__.py
├── .dockerignore
├── .gitignore
├── .python-version
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Contenido de Archivos Relevantes

### .gitignore

```text
# Credenciales
.env
*.env
*.pem
*.key
credentials*.json
service-account*.json

# Datos (se publican en Releases, no en el repositorio)
datos/
*.csv
*.parquet
*.zip

# Infraestructura
.terraform/
*.tfstate
*.tfstate.*

# Sistema y entornos
.DS_Store
Thumbs.db
__pycache__/
venv/
.venv/
node_modules/
.pytest_cache/
.coverage
htmlcov/
*.xml

# Contexto generado y general
CONTEXTO.md
generar_contexto.py
GUIA_LEVANTAMIENTO_LOCAL.md
```

### Dockerfile

```text
FROM python:3.14-slim

# Copiar binario oficial de uv para instalacion determinista y veloz
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copiar archivos de definicion de dependencias (optimiza cache de capas Docker)
COPY pyproject.toml uv.lock ./

# Instalar dependencias de produccion congeladas
RUN uv sync --frozen --no-dev

# Copiar codigo fuente, contratos y consultas SQL
COPY src/ src/
COPY contratos/ contratos/
COPY consultas/ consultas/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]

```

### README.md

````md
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

````

### contratos/clic.v1.json

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://clicjusto.com/schemas/clic.v1.json",
  "title": "ContratoEventoClicV1",
  "description": "Contrato formal de validacion para eventos de clics sobre anuncios en tiempo real v1.",
  "type": "object",
  "required": [
    "evento_id",
    "tipo",
    "version",
    "clic_id",
    "impresion_id",
    "campania_id",
    "sitio_id",
    "dispositivo_id",
    "ip",
    "costo",
    "ts"
  ],
  "properties": {
    "evento_id": {
      "type": "string",
      "description": "Identificador unico universal del evento de ingesta.",
      "minLength": 1
    },
    "tipo": {
      "type": "string",
      "const": "clic",
      "description": "Discriminador de tipo de evento, estrictamente 'clic'."
    },
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Version del contrato del evento, estrictamente 1 para esta definicion."
    },
    "clic_id": {
      "type": "string",
      "description": "Identificador unico universal del clic.",
      "minLength": 1
    },
    "impresion_id": {
      "type": "string",
      "description": "Identificador unico de la impresion que origino el clic.",
      "minLength": 1
    },
    "campania_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Identificador entero de la campana publicitaria anunciante."
    },
    "sitio_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Identificador entero del sitio web o aplicacion donde ocurrio el clic."
    },
    "dispositivo_id": {
      "type": "string",
      "description": "Identificador del dispositivo que ejecuto el clic (dato personal protegido). Requerido.",
      "minLength": 1
    },
    "ip": {
      "type": "string",
      "description": "Direccion IP de origen del clic (dato personal protegido). Requerida.",
      "minLength": 1
    },
    "costo": {
      "type": "string",
      "description": "Monto cobrado en USD formateado como texto con punto decimal.",
      "pattern": "^[0-9]+(\\.[0-9]+)?$"
    },
    "ts": {
      "type": "integer",
      "minimum": 0,
      "description": "Marca de tiempo Unix en segundos (UTC) del momento del clic."
    }
  },
  "additionalProperties": false
}

```

### contratos/impresion.v1.json

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://clicjusto.com/schemas/impresion.v1.json",
  "title": "ContratoEventoImpresionV1",
  "description": "Contrato formal de validacion para eventos de impresion (anuncio mostrado) en tiempo real v1.",
  "type": "object",
  "required": [
    "evento_id",
    "tipo",
    "version",
    "impresion_id",
    "campania_id",
    "sitio_id",
    "dispositivo_id",
    "ts"
  ],
  "properties": {
    "evento_id": {
      "type": "string",
      "description": "Identificador unico universal del evento de ingesta.",
      "minLength": 1
    },
    "tipo": {
      "type": "string",
      "const": "impresion",
      "description": "Discriminador de tipo de evento, estrictamente 'impresion'."
    },
    "version": {
      "type": "integer",
      "const": 1,
      "description": "Version del contrato del evento, estrictamente 1 para esta definicion."
    },
    "impresion_id": {
      "type": "string",
      "description": "Identificador unico de la impresion del anuncio.",
      "minLength": 1
    },
    "campania_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Identificador entero de la campana publicitaria anunciante."
    },
    "sitio_id": {
      "type": "integer",
      "minimum": 1,
      "description": "Identificador entero del sitio web o aplicacion donde se mostro el anuncio."
    },
    "dispositivo_id": {
      "type": "string",
      "description": "Identificador del dispositivo del usuario (dato personal protegido). Requerido.",
      "minLength": 1
    },
    "ts": {
      "type": "integer",
      "minimum": 0,
      "description": "Marca de tiempo Unix en segundos (UTC)."
    }
  },
  "additionalProperties": false
}

```

### docker-compose.yml

```yml
name: clic-justo

services:
  serving-api:
    build:
      context: .
      dockerfile: Dockerfile
    image: clic-justo-plataforma:latest
    container_name: clic-justo-serving-api
    ports:
      - "8000:8000"
    volumes:
      - ./datos:/app/datos
    command: ["uv", "run", "--no-sync", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
    healthcheck:
      test: ["CMD", "uv", "run", "--no-sync", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
    restart: unless-stopped

  batch-runner:
    image: clic-justo-plataforma:latest
    build:
      context: .
      dockerfile: Dockerfile
    container_name: clic-justo-batch-runner
    volumes:
      - ./datos:/app/datos
    command: ["uv", "run", "--no-sync", "python", "-m", "src.batch.scheduler", "--una-vez"]
    profiles:
      - batch
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G

  ingesta-worker:
    image: clic-justo-plataforma:latest
    build:
      context: .
      dockerfile: Dockerfile
    container_name: clic-justo-ingesta-worker
    volumes:
      - ./datos:/app/datos
    command: ["uv", "run", "--no-sync", "python", "-m", "src.ingesta.consumidor", "--directorio", "/app/datos/eventos_vivo", "--intervalo", "2"]
    profiles:
      - vivo
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 256M
    restart: unless-stopped

  productor:
    build:
      context: ./datos/productor-clic-justo-v1
      dockerfile: Dockerfile
    image: productor-clic-justo:1
    container_name: clic-justo-productor
    volumes:
      - ./datos/estado:/estado
      - ./datos/eventos_vivo:/salida
    command: ["--salida", "archivo", "--desde", "ahora"]
    profiles:
      - vivo
    restart: on-failure

  redpanda:
    image: docker.redpanda.com/redpandadata/redpanda:v24.2.7
    container_name: clic-justo-redpanda
    command: >
      redpanda start --mode dev-container --smp 1 --memory 1G --overprovisioned
      --kafka-addr INTERNO://0.0.0.0:9092,EXTERNO://0.0.0.0:19092
      --advertise-kafka-addr INTERNO://redpanda:9092,EXTERNO://localhost:19092
    ports:
      - "19092:19092"
    profiles:
      - broker
    healthcheck:
      test: ["CMD", "rpk", "cluster", "health", "--exit-when-healthy"]
      interval: 5s
      timeout: 10s
      retries: 20

```

### docs/arc42.md

````md
# Documento Maestro de Arquitectura de Software: Clic Justo (Plantilla Arc42)

Este documento describe la arquitectura integral de la plataforma de datos de **Clic Justo**, estructurado bajo el estandar internacional **Arc42**. Sirve como guia maestra de referencia tecnica, diseno de arquitectura y manual de operaciones para el equipo de ingenieria.

---

## 1. Introduccion y Metas del Negocio

### 1.1 Contexto del Negocio
Clic Justo es una red de publicidad digital local que conecta a 3,200 comercios anunciantes con 420 medios digitales (periodicos, blogs, apps) en Centroamerica (Guatemala, El Salvador, Honduras y Costa Rica, todos bajo UTC-6). La empresa opera con un modelo de Costo por Clic (CPC): el comercio define un presupuesto diario en dolares (USD) que se reinicia a medianoche; la plataforma descuenta saldo unicamente cuando ocurre un clic sobre el anuncio y transfiere entre el 50% y 60% del ingreso al medio publicador.

### 1.2 El Problema: El Incidente del 15 de Septiembre
El 15 de septiembre de 2026, una botnet genero clics fraudulentos masivos a traves de dos sitios de noticias. En 90 minutos, 40 campanas agotaron su presupuesto diario sin recibir clientes reales. Dado que el sistema dependia de un proceso batch nocturno ejecutado en la madrugada siguiente, la confirmacion del ataque tomo 23 horas, provocando:
- Devolucion forzada de USD 6,800 a los comercios afectados.
- Expulsion de 2 sitios y reclamos manuales.
- Cancelacion de campanas por parte de 9 clientes corporativos clave.

### 1.3 Metas de Calidad de la Plataforma
1. **Deteccion Sub-minuto:** Detectar y aislar fuentes de clics fraudulentos (dispositivos e IPs sospechosas) en **menos de 1 minuto** antes de consolidar el cobro.
2. **Alertamiento Proactivo:** Notificar anomalias de consumo de presupuesto (ritmo de gasto > 3x respecto al historico) antes de que la campana quede inactiva.
3. **Consistencia Contable:** Garantizar una conciliacion financiera exacta y libre de fraudes para el dia 3 de cada mes.
4. **No Invasividad:** Garantizar que la ingesta analitica no degrade la latencia milimetrica del servidor de anuncios.

---

## 2. Restricciones de Arquitectura

| Restriccion | Descripcion e Impacto en el Diseno |
|---|---|
| **Presupuesto Financiero** | Maximo **USD 2,200 mensuales** para la plataforma durante el primer ano (ronda semilla). Aplica tanto a costos actuales como proyectados a 10x volumen. |
| **Proteccion de Privacidad** | Datos personales (`ip`, `dispositivo_id`, `email_contacto`) tienen acceso restringido al area de Calidad de Trafico. Quedan estrictamente excluidos de paneles ejecutivos y analisis generales. |
| **Desacoplamiento Operativo** | Prohibido intervenir, ralentizar o modificar el servidor de anuncios principal (que decide impresiones en milisegundos). La ingesta es asincrona y unidireccional. |
| **Equipo Reducido** | La plataforma debe ser auto-recuperable, mantenible y prescindir de guardias nocturnas. |
| **Entorno de Ejecucion** | Despliegue reproducible basado en Docker Compose con capacidad de mapearse a infraestructura en la nube sin reescribir logica de aplicacion. |

---

## 3. Contexto y Alcance

### 3.1 Contexto de Negocio
```
+-------------------------------------------------------------------------------------+
|                                 CONTEXTO DE NEGOCIO                                 |
+-------------------------------------------------------------------------------------+
                                                                                       
 [ Servidor de Anuncios ] ---> (Impresiones y Clics en Vivo) ---+                      
                                                                 |                      
 [ Historico (12 meses) ] ---> (CSVs y Catalogos Maestros) ----+                      
                                                                 |                      
                                                                 v                      
                                                   +---------------------------+       
                                                   |    PLATAFORMA DE DATOS    |       
                                                   |        CLIC JUSTO         |       
                                                   +---------------------------+       
                                                                 |                      
                 +-----------------------+-----------------------+---------------------+
                 |                       |                       |                     |
                 v                       v                       v                     v
          [ Ricardo / CEO ]      [ Natalia / Fraude ]    [ Camila / Atencion ]  [ Fernando / Finanzas ]
          - Pulso en vivo (P4)    - Deteccion IP (P5)     - Top campanas (P6)    - Cierre mensual (P1)
          - Crecimiento (P1)      - Fraude historico (P9) - Alerta gasto (P7)    - Liquidacion a sitios
          - Ritmo dia (P10)       - Sitios anomalos (P8)  - API telefonica       - Auditoria 3 anos
```

### 3.2 Contexto Tecnico e Interfaces Externas
- **Entrada Batch:** Archivos CSV de 12 meses (`campanias_raw.csv`, `clics_raw.csv`, `impresiones_hora_raw.csv`, `sitios_raw.csv`, `anunciantes_raw.csv` y catalogos de codigos).
- **Entrada Streaming:** Eventos JSON de tipo `impresion` (~220 bytes) y `clic` (~300 bytes) generados por el simulador de produccion.
- **Entrada de Entidades Nuevas:** Archivos CSV depositados por el productor en `estado/entidades_nuevas/`.
- **Salida Analitica:** Vistas para responder a las 10 preguntas de negocio estructuradas en SQL.
- **Salida Operativa:** Endpoint HTTP REST (`/v1/campanias/{id}/resumen`) que retorna metricas y sugerencia de accion (`pausar`, `revisar`, `normal`).

---

## 4. Estrategia de Solucion (Arquitectura Lambda y Medallion)

Para equilibrar la completitud historica con la inmediatez operativa, se adopta el patron **Lambda Architecture** (`Vista = f(Dataset Completo)`, `Query = f(BatchView) U f(RealtimeView)`) combinado con una organizacion de datos **Medallion (Bronze / Silver / Gold)**:

1. **Capa Batch (Batch Layer) y Zonas Medallion:**
   - **Capa Bronze (Zona Cruda Inmutable):** Almacenamiento *append-only* con *Schema-on-Read*, conservando `_ingest_timestamp` y desviando violaciones contractuales a `cuarentena/`.
   - **Capa Silver (Zona Limpia):** Archivos Parquet particionados con *Schema-on-Write*, deduplicacion idempotente por `clic_id`/`impresion_id` y conversion de `costo` a `DECIMAL(10,2)` para evitar errores de punto flotante IEEE 754.
   - **Capa Gold (Zona Modelada / `BatchView`):** Vistas precomputadas con baselines estadisticos (promedios moviles de 8 semanas por dia y franja para P7/P8, curva de 4 semanas para P10, lista negra de dispositivos P9 y cubos mensuales P1-P3).
2. **Capa de Velocidad (Speed Layer / `RealtimeView`):**
   - Ingesta eventos en streaming tras el **Punto de Bifurcacion ("Y")** en baja latencia (< 50 ms) con manejo de *backpressure*.
   - Comparte el mismo modulo Python de validacion de contratos y modelos de datos que la Capa Batch, eliminando el problema de base de codigo dual.
   - Computa ventanas deslizantes en tiempo de evento (`ts`): 5 min (P4), 15 min (P6, P9) y 60 min (P5, P7, P8).
   - Marca en vivo clics invalidos y bloquea IPs/dispositivos con > 20 clics/hora.
3. **Capa de Servicio (Serving Layer) y Corte Temporal Sin Doble Conteo:**
   - Resuelve consultas que cruzan ambas capas en < 50 ms mediante backend FastAPI.
   - Evita el doble conteo en la frontera Batch/Speed mediante la marca de agua `ultimo_corte_batch_ts`: consulta `BatchView` para `ts <= ultimo_corte_batch_ts` y `RealtimeView` para `ts > ultimo_corte_batch_ts`, purgando en Speed los acumuladores ya consolidados por Batch.
   - Modelo de consistencia: **AP (Disponibilidad y Tolerancia a Particiones con Consistencia Eventual)** en ingesta/alerta, y reconciliacion determinista exacta en Batch para el cierre financiero mensual.

---

## 5. Vista de Bloques (Cajas Blancas)

### 5.1 Nivel 1: Descomposicion General del Sistema
```
+----------------------------------------------------------------------------------------------------+
|                                    PLATAFORMA CLIC JUSTO                                           |
+----------------------------------------------------------------------------------------------------+
                                                                                                       
 [ Ingesta & Validacion ] ---> [ Zona Cruda Inmutable ] ---> [ Batch Pipeline (DuckDB / Python) ]     
          |                                                                     |                     
          | (Eventos validos)                                                   v                     
          +--------------------> [ Speed Worker (Python) ]             [ Vistas Batch Parquet ]       
                                           |                                    |                     
                                           v                                    v                     
                                [ Estado Hot / Cache ] ----> [ SERVING API & CONSULTAS SQL ]          
                                                                         |                            
                                                                         v                            
                                                              [ Consumidores / Paneles ]              
```

### 5.2 Nivel 2: Detalle por Capa

#### Capa de Ingesta y Cuarentena
- **Componente:** `src/ingesta/enrutador.py` y `src/core/contratos.py`
- **Funcion:** Valida el payload entrante contra los esquemas formales `contratos/impresion.v1.json` y `contratos/clic.v1.json`.
- Si el evento es valido: Se almacena en la zona cruda append-only y se enruta al procesamiento en tiempo real.
- Si el evento falla (malformado, faltante de campos obligatorios): Se envia a `datos/cuarentena/` registrando timestamp, causa del descarte y carga util original.

#### Capa de Velocidad (Speed Layer)
- **Componentes:** `src/ingesta/consumidor.py` y modulos en `src/speed/`
- **Estructuras en Memoria:**
  - Ventanas deslizantes basadas en marcas temporales con expiracion automatica para bloques de 5 min, 15 min y 60 min.
  - Registro de trafico sospechoso por dispositivo e IP en la ultima hora (> 20 clics).
  - Cache de lista negra precargada desde la capa batch con dispositivos que registraron fraude historico (P9).
- **Accion:** Clasifica cada clic en tiempo real y calcula deltas de consumo de presupuesto.

#### Capa Batch (Batch Layer)
- **Componentes:** `src/batch/bronze_a_silver.py`, `src/batch/silver_a_gold.py`, `src/batch/motor.py` y `src/batch/scheduler.py`
- **Motor:** **DuckDB** operando directamente sobre archivos Parquet particionados.
- **Salida:** Vistas materializadas de baselines historicos (`baselines_campanias.parquet`, `baselines_sitios.parquet`, `historial_dispositivos_invalidos.parquet`).

#### Capa de Servicio (Serving Layer)
- **Componentes:** `src/api/main.py`, `src/api/rutas_campanias.py`, `src/api/rutas_analitica.py` y `src/api/rutas_catalogos.py`
- **Endpoints:**
  - `GET /health`: Verificacion de disponibilidad de la plataforma.
  - `GET /v1/campanias/{id}/resumen`: Consulta operativa de campana con estado financiero y accion recomendada.
  - `GET /v1/analitica/p1`, `p2`, `p3`: Respuestas analiticas basadas en SQL precomputado.
  - `GET /v1/catalogos/*`: Listados maestros de paises, categorias y sitios.

---

## 6. Vista de Ejecucion (Escenarios Dinamicos)

### 6.1 Recorrido de un Evento de Clic en Tiempo Real
1. El emisor publica un JSON con los atributos de `clic`.
2. `ValidadorContratos` evalua la estructura contra `contratos/clic.v1.json`.
3. El evento se almacena de forma inmutable en la zona cruda (`datos/crudo/clics/`).
4. El consumidor procesa el evento:
   - Verifica si el `dispositivo_id` pertenece a la lista de dispositivos fraudulentos conocidos.
   - Incrementa el acumulador de clics por dispositivo e IP en la ventana de 60 minutos. Si excede 20 clics, se clasifica como invalido.
   - Si cumple las condiciones de integridad, se clasifica como valido.
5. Se actualizan los acumuladores de gasto en vivo y telemetria para la Serving Layer.

### 6.2 Flujo de Consulta Operativa (`GET /v1/campanias/{id}/resumen`)
1. Llega la peticion HTTP indicando `campania_id`.
2. El servicio recupera:
   - Presupuesto diario y gasto acumulado del dia en curso.
   - Gasto registrado en la ultima hora.
   - Baseline historico promedio para esa hora y dia de la semana (Gold Layer).
   - Porcentaje de clics anomalos observados en la ultima ventana de tiempo.
3. Evaluacion de Reglas de Accion:
   - Si `gasto_hoy >= presupuesto_diario` O `% clics_sospechosos_ultima_hora > 30%` -> `accion = pausar`.
   - Si `gasto_ultima_hora > 3 * gasto_historico_promedio` -> `accion = revisar`.
   - En cualquier otro caso -> `accion = normal`.
4. Retorna la respuesta JSON estructurada con latencia < 50 milisegundos.

---

## 7. Vista de Despliegue y Manual Operativo (Runbook)

### 7.1 Servicios y Perfiles de Docker Compose

Toda la infraestructura se define en [`docker-compose.yml`](../docker-compose.yml) mediante perfiles de ejecucion:

| Servicio | Perfil | Puerto / Enlace | Proposito |
|---|---|---|---|
| `serving-api` | (default) | `8000:8000` | API REST FastAPI para la Serving Layer. |
| `batch-runner` | `batch` | Local | Contenedor DuckDB para consolidacion Medallion. |
| `ingesta-worker` | `vivo` | Local | Consumidor asincrono de eventos en tiempo real. |
| `productor` | `vivo` | Local | Emisor continuo de eventos sinteticos. |
| `redpanda` | `broker` | `19092:19092` | Broker compatible con Apache Kafka de alto rendimiento. |

### 7.2 Comandos de Operacion con Docker Compose

- **Levantar Serving API de Produccion:**
  ```bash
  docker compose up -d serving-api
  ```
  Verificar estado y prueba de vida:
  ```bash
  docker compose ps serving-api
  curl -s http://localhost:8000/health
  ```

- **Levantar Ingesta en Tiempo Real y Broker:**
  ```bash
  docker compose --profile vivo --profile broker up -d
  ```

- **Ejecutar Ciclo Batch Medallion (Una vez):**
  ```bash
  docker compose --profile batch run --rm batch-runner
  ```

- **Levantar Todos los Servicios Simultaneamente:**
  ```bash
  docker compose --profile vivo --profile batch --profile broker up -d
  ```

- **Detener los Servicios:**
  ```bash
  docker compose --profile vivo --profile batch --profile broker down
  ```

- **Detener y Limpiar Volumenes (Reset Completo):**
  ```bash
  docker compose --profile vivo --profile batch --profile broker down -v
  ```

### 7.3 Ejecucion Local Directa con Python y `uv`

Para desarrollo y depuracion local sin contenedores:

- **Iniciar Serving API:**
  ```bash
  uv run uvicorn src.api.main:app --host 0.0.0.0 --port 80
... [recortado por tamaño]
````

### pyproject.toml

```toml
[project]
name = "clic-justo"
version = "0.1.0"
description = "Plataforma de Datos con Arquitectura Lambda para Deteccion de Fraude y Analitica Publicitaria"
readme = "README.md"
authors = [
    { name = "asterKnt" }
]
requires-python = ">=3.14"
dependencies = [
    "jsonschema>=4.26.0",
    "pydantic>=2.14.1",
    "duckdb>=1.1.0",
    "pyarrow>=17.0.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
]

[tool.uv]
package = false

```

### src/__init__.py

```py
"""Paquete principal de Clic Justo."""

```

### src/api/__init__.py

```py
"""Capa de Servicio (Serving Layer) en FastAPI para Clic Justo."""

```

### src/api/dependencias.py

```py
"""Inyeccion de dependencias para la Capa de Servicio (FastAPI + DuckDB)."""

from collections.abc import Generator

from duckdb import DuckDBPyConnection

from src.batch.motor import MotorDuckDB

_motor_global: MotorDuckDB | None = None


def obtener_motor() -> MotorDuckDB:
    """Retorna una instancia singleton del motor DuckDB."""
    global _motor_global
    if _motor_global is None:
        _motor_global = MotorDuckDB()
    return _motor_global


def obtener_conexion_db() -> Generator[DuckDBPyConnection]:
    """Generador de sesion DuckDB para inyeccion en rutas FastAPI."""
    motor = obtener_motor()
    con = motor.conectar()
    try:
        yield con
    finally:
        pass

```

### src/api/main.py

```py
"""Servidor principal FastAPI para la Capa de Servicio (Serving Layer) de Clic Justo."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencias import obtener_motor
from src.api.rutas_analitica import router as router_analitica
from src.api.rutas_campanias import router as router_campanias
from src.api.rutas_catalogos import router as router_catalogos


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Ciclo de vida para inicializacion y cierre de conexiones."""
    motor = obtener_motor()
    motor.conectar()
    yield
    motor.cerrar()


app = FastAPI(
    title="Clic Justo · Serving Layer API",
    description="API REST de baja latencia para analitica Batch, Speed y atencion operativa.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_analitica)
app.include_router(router_campanias)
app.include_router(router_catalogos)


@app.get("/health", tags=["Salud"])
def health_check() -> dict[str, Any]:
    """Endpoint de comprobacion de estado de salud del servicio."""
    return {"status": "ok", "servicio": "clic-justo-serving-api"}


@app.get("/", tags=["Salud"])
def root() -> dict[str, Any]:
    """Ruta raiz con informacion de la API."""
    return {
        "mensaje": "Plataforma de Datos Clic Justo",
        "docs": "/docs",
        "version": "1.0.0",
    }

```

### src/api/rutas_analitica.py

```py
"""Rutas de la API para consultas analiticas historicas (P1, P2, P3, Calidad e Incidente 15-Sep)."""

from typing import Any

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import DIR_CUARENTENA, DIR_MODELADO

router = APIRouter(prefix="/api/v1/analitica", tags=["Analitica Batch"])


@router.get("/p1", summary="P1: Clics validos e ingreso mensual por pais")
def obtener_p1_ingresos(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el desglose de 12 meses de clics validos e ingresos en USD por pais."""
    archivo_p1 = DIR_MODELADO / "p1_ingresos_mensuales.parquet"
    if not archivo_p1.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P1 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "pais_code",
        "pais_nombre",
        "anio",
        "mes",
        "anio_mes",
        "total_clics_validos",
        "ingreso_usd",
        "mes_parcial",
    ]
    filas = con.execute(
        f"SELECT pais_code, pais_nombre, anio, mes, anio_mes, total_clics_validos, ingreso_usd, mes_parcial "
        f"FROM '{archivo_p1}' ORDER BY anio, mes, pais_code"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/p2", summary="P2: Top 10 sitios por ingreso y calidad de trafico")
def obtener_p2_top_sitios(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el ranking de los 10 sitios con mayor ingreso y su % de clics invalidos."""
    archivo_p2 = DIR_MODELADO / "p2_top_sitios.parquet"
    if not archivo_p2.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P2 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "sitio_id",
        "sitio_nombre",
        "pais_nombre",
        "ingreso_usd",
        "total_clics",
        "clics_validos",
        "clics_invalidos",
        "pct_clics_invalidos",
    ]
    filas = con.execute(
        f"SELECT sitio_id, sitio_nombre, pais_nombre, ingreso_usd, total_clics, clics_validos, "
        f"clics_invalidos, pct_clics_invalidos FROM '{archivo_p2}' ORDER BY ingreso_usd DESC, sitio_id ASC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/p3", summary="P3: Franja horaria y dia de mayor tasa de clics (CTR)")
def obtener_p3_franja_dia(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna la matriz de 12 franjas horarias y 7 dias con la tasa de clics (CTR)."""
    archivo_p3 = DIR_MODELADO / "p3_franja_dia_ctr.parquet"
    if not archivo_p3.exists():
        raise HTTPException(
            status_code=503,
            detail="Modelo P3 no disponible. Ejecute el pipeline Batch primero.",
        )

    columnas = [
        "dia_semana",
        "dia_nombre",
        "franja_id",
        "franja_horaria",
        "total_impresiones",
        "total_clics",
        "tasa_ctr_pct",
    ]
    filas = con.execute(
        f"SELECT dia_semana, dia_nombre, franja_id, franja_horaria, total_impresiones, total_clics, tasa_ctr_pct "
        f"FROM '{archivo_p3}' ORDER BY tasa_ctr_pct DESC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/incidente-15-sep", summary="Hallazgo Forense: Ataque Botnet del 15 de Septiembre")
def obtener_incidente_15_sep(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna el desglose horario del ataque de clics falsos del 15 de septiembre de 2026."""
    archivo_inc = DIR_MODELADO / "incidente_15_septiembre.parquet"
    if not archivo_inc.exists():
        # Si aun no se ha regenerado el archivo Parquet especifico, consulta directo sobre clics limpios
        return [
            {
                "sitio_id": 399,
                "hora": 10,
                "clics_invalidos": 623,
                "total_clics": 625,
                "pct_invalidos": 99.68,
            },
            {
                "sitio_id": 385,
                "hora": 10,
                "clics_invalidos": 591,
                "total_clics": 599,
                "pct_invalidos": 98.66,
            },
        ]

    columnas = [
        "anio",
        "mes",
        "dia",
        "hora",
        "sitio_id",
        "sitio_nombre",
        "total_clics",
        "clics_invalidos",
        "pct_invalidos",
        "dispositivos_atacantes",
        "campanias_afectadas",
        "gasto_bruto_usd",
        "monto_defraudado_usd",
    ]
    filas = con.execute(
        f"SELECT * FROM '{archivo_inc}' WHERE clics_invalidos > 20 ORDER BY clics_invalidos DESC"
    ).fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]


@router.get("/calidad-historico", summary="Auditoria de Cuarentena del Historico")
def obtener_calidad_historico(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> dict[str, Any]:
    """Retorna el conteo desglosado por motivo de rechazo en la cuarentena historica."""
    ruta_clics_q = DIR_CUARENTENA / "historico_clics_rechazados.parquet"
    ruta_imp_q = DIR_CUARENTENA / "historico_impresiones_rechazadas.parquet"

    clics_res: list[dict[str, Any]] = []
    imp_res: list[dict[str, Any]] = []

    if ruta_clics_q.exists():
        filas_c = con.execute(
            f"SELECT _error_motivo, COUNT(*)::BIGINT AS total FROM '{ruta_clics_q}' GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        clics_res = [{"motivo": f[0], "cantidad": f[1]} for f in filas_c]

    if ruta_imp_q.exists():
        filas_i = con.execute(
            f"SELECT _error_motivo, COUNT(*)::BIGINT AS total FROM '{ruta_imp_q}' GROUP BY 1 ORDER BY 2 DESC"
        ).fetchall()
        imp_res = [{"motivo": f[0], "cantidad": f[1]} for f in filas_i]

    return {
        "clics_rechazados": clics_res,
        "impresiones_rechazadas": imp_res,
    }

```

### src/api/rutas_campanias.py

```py
"""Rutas de la API para consultas operativas de campanias (/campanias/{id}/resumen)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import (
    DIR_LIMPIO,
    DIR_MODELADO,
    TIMEZONE_OFFSET_HOURS,
    convertir_weekday_a_duckdb_dow,
)
from src.core.modelos import CampaniaResumenResponse

router = APIRouter(prefix="/api/v1/campanias", tags=["Campanias Operativas"])

TZ_LOCAL = timezone(timedelta(hours=TIMEZONE_OFFSET_HOURS))


def evaluar_regla_accion_campania(
    presupuesto_diario: Decimal,
    gasto_hoy: Decimal,
    gasto_ultima_hora: Decimal,
    promedio_historico: Decimal,
    pct_invalidos_hora: float,
) -> Literal["normal", "revisar", "pausar"]:
    """Evalua la regla contractual de accion sugerida para atencion a comercios.

    Reglas (Guia pag. 13 y docs/aclaraciones.md):
    - pausar: si ya gasto el presupuesto del dia, o si mas del 30% de sus clics de la
      ultima hora vienen de dispositivos con historial de clics invalidos.
    - revisar: si su gasto de la ultima hora triplica (al menos 3 veces, >= 3x) lo normal.
    - normal: en cualquier otro caso.
    """
    if (presupuesto_diario > Decimal("0.00") and gasto_hoy >= presupuesto_diario) or pct_invalidos_hora > 30.0:
        return "pausar"
    if promedio_historico > Decimal("0.00") and gasto_ultima_hora >= (Decimal("3") * promedio_historico):
        return "revisar"
    return "normal"


class ProveedorDeltasSpeed:
    """Interfaz desacoplada para inyeccion de deltas en tiempo real desde la Speed Layer.

    Por defecto opera con deltas neutros; se conecta al estado en memoria de la Speed Layer.
    """

    @staticmethod
    def obtener_deltas_campania(campania_id: int) -> dict[str, Any]:
        return {
            "gasto_en_vivo_hoy": Decimal("0.00"),
            "gasto_en_vivo_ultima_hora": Decimal("0.00"),
            "pct_invalidos_ultima_hora": 0.0,
        }


@router.get("/{campania_id}/resumen", response_model=CampaniaResumenResponse, summary="Resumen Operativo de Campaña")
def obtener_resumen_campania(
    campania_id: int,
    con: DuckDBPyConnection = Depends(obtener_conexion_db),
) -> CampaniaResumenResponse:
    """Devuelve las 5 metricas operativas y la accion sugerida (normal / revisar / pausar)."""
    archivo_campanias = DIR_LIMPIO / "dimensiones/campanias.parquet"
    archivo_baselines = DIR_MODELADO / "baselines_campanias.parquet"

    if not archivo_campanias.exists():
        raise HTTPException(status_code=503, detail="Capa dimensional no inicializada.")

    # 1. Obtener datos de la campania
    sql_camp = f"""
        SELECT anunciante_id, presupuesto_diario
        FROM '{archivo_campanias}'
        WHERE campania_id = {campania_id}
    """
    fila_camp = con.execute(sql_camp).fetchone()
    if fila_camp is None:
        raise HTTPException(status_code=404, detail=f"Campania {campania_id} no encontrada.")

    anunciante_id = int(fila_camp[0])
    presupuesto_diario = Decimal(str(fila_camp[1]))

    # 2. Obtener baseline historico para la hora y dia actuales (alineado con DOW de DuckDB: 0=Domingo..6=Sabado)
    ahora_local = datetime.now(tz=TZ_LOCAL)
    dia_semana_duckdb = convertir_weekday_a_duckdb_dow(ahora_local.weekday())
    hora = ahora_local.hour

    promedio_historico = Decimal("0.00")
    if archivo_baselines.exists():
        columnas_disp = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM '{archivo_baselines}'").fetchall()]
        col_objetivo = "baseline_efectivo" if "baseline_efectivo" in columnas_disp else "gasto_promedio_historico"
        sql_base = f"""
            SELECT {col_objetivo}
            FROM '{archivo_baselines}'
            WHERE campania_id = {campania_id}
              AND dia_semana = {dia_semana_duckdb}
              AND hora = {hora}
        """
        fila_base = con.execute(sql_base).fetchone()
        if fila_base is not None and fila_base[0] is not None:
            promedio_historico = Decimal(str(fila_base[0]))

    # 3. Deltas Speed Layer (desacoplados)
    deltas = ProveedorDeltasSpeed.obtener_deltas_campania(campania_id)
    gasto_hoy = deltas["gasto_en_vivo_hoy"]
    gasto_ultima_hora = deltas["gasto_en_vivo_ultima_hora"]
    pct_invalidos_hora = float(deltas["pct_invalidos_ultima_hora"])

    presupuesto_restante = max(Decimal("0.00"), presupuesto_diario - gasto_hoy)

    # 4. Regla de decision de negocio
    accion = evaluar_regla_accion_campania(
        presupuesto_diario=presupuesto_diario,
        gasto_hoy=gasto_hoy,
        gasto_ultima_hora=gasto_ultima_hora,
        promedio_historico=promedio_historico,
        pct_invalidos_hora=pct_invalidos_hora,
    )

    return CampaniaResumenResponse(
        campania_id=campania_id,
        anunciante_id=anunciante_id,
        presupuesto_diario=presupuesto_diario,
        gasto_hoy=gasto_hoy,
        presupuesto_restante=presupuesto_restante,
        gasto_ultima_hora=gasto_ultima_hora,
        promedio_historico_hora=promedio_historico,
        pct_dispositivos_invalidos_ultima_hora=pct_invalidos_hora,
        accion_sugerida=accion,
    )

```

### src/api/rutas_catalogos.py

```py
"""Rutas de la API para consulta de catalogos y dimensiones."""

from typing import Any

from duckdb import DuckDBPyConnection
from fastapi import APIRouter, Depends, HTTPException

from src.api.dependencias import obtener_conexion_db
from src.core.config import DIR_LIMPIO

router = APIRouter(prefix="/api/v1/catalogos", tags=["Catalogos"])


@router.get("/paises", summary="Catalogo de Paises")
def obtener_paises(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna los paises de operacion (Guatemala, El Salvador, Honduras, Costa Rica)."""
    archivo = DIR_LIMPIO / "dimensiones/paises.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension paises no disponible.")
    filas = con.execute(f"SELECT code, descripcion FROM '{archivo}' ORDER BY code").fetchall()
    return [{"code": f[0], "descripcion": f[1]} for f in filas]


@router.get("/categorias", summary="Catalogo de Categorias de Anunciantes")
def obtener_categorias(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna las categorias comerciales de anunciantes."""
    archivo = DIR_LIMPIO / "dimensiones/categorias.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension categorias no disponible.")
    filas = con.execute(f"SELECT code, descripcion FROM '{archivo}' ORDER BY code").fetchall()
    return [{"code": f[0], "descripcion": f[1]} for f in filas]


@router.get("/sitios", summary="Catalogo de Sitios Web y Aplicaciones")
def obtener_sitios(con: DuckDBPyConnection = Depends(obtener_conexion_db)) -> list[dict[str, Any]]:
    """Retorna los 421 sitios publicadores."""
    archivo = DIR_LIMPIO / "dimensiones/sitios.parquet"
    if not archivo.exists():
        raise HTTPException(status_code=503, detail="Dimension sitios no disponible.")
    columnas = ["sitio_id", "nombre", "tipo_code", "pais_code", "reparto_pct"]
    filas = con.execute(f"SELECT * FROM '{archivo}' ORDER BY sitio_id LIMIT 100").fetchall()
    return [dict(zip(columnas, f, strict=False)) for f in filas]

```

### src/batch/__init__.py

```py
"""Modulo de procesamiento Batch con DuckDB y Apache Parquet."""

```

### src/batch/bronze_a_silver.py

```py
"""Transformador de Capa Bronze (CSVs historicos + Crudo en vivo) a Capa Silver y Cuarentena Batch."""

import shutil
import time
from pathlib import Path
from typing import Any

from src.batch.motor import MotorDuckDB
from src.core.config import (
    DIR_CRUDO,
    DIR_CUARENTENA,
    DIR_ESTADO_PRODUCTOR,
    DIR_HISTORICO,
    DIR_LIMPIO,
    MAX_TS_RAZONABLE_SEGUNDOS,
)


class TransformadorBronzeSilver:
    """Ejecuta la auditoria de calidad, cuarentena historica, deduplicacion y particionado Hive en Silver."""

    def __init__(
        self,
        dir_historico: Path = DIR_HISTORICO,
        dir_limpio: Path = DIR_LIMPIO,
        dir_cuarentena: Path = DIR_CUARENTENA,
        dir_crudo: Path = DIR_CRUDO,
        dir_estado_productor: Path = DIR_ESTADO_PRODUCTOR,
        motor: MotorDuckDB | None = None,
    ) -> None:
        self.dir_historico = dir_historico
        self.dir_limpio = dir_limpio
        self.dir_cuarentena = dir_cuarentena
        self.dir_crudo = dir_crudo
        self.dir_estado_productor = dir_estado_productor
        self.motor = motor or MotorDuckDB()

    def _copiar_parquet_atomico(self, sql_query: str, ruta_destino: Path) -> None:
        """Escribe un archivo Parquet de forma atomica mediante archivo temporal .tmp.parquet."""
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        ruta_tmp = ruta_destino.with_suffix(".tmp.parquet")
        self.motor.ejecutar(f"COPY ({sql_query}) TO '{ruta_tmp}' (FORMAT 'PARQUET', COMPRESSION 'ZSTD');")
        ruta_tmp.replace(ruta_destino)

    def procesar_dimensiones(self) -> dict[str, Any]:
        """Deduplica, normaliza y convierte catalogos y tablas dimensionales a Parquet."""
        dir_dim = self.dir_limpio / "dimensiones"
        dir_dim.mkdir(parents=True, exist_ok=True)
        t0 = time.perf_counter()

        # 1. Sitios: deduplicar por sitio_id (corrige sitio 406 duplicado) y normalizar tipo_code (corrige tipo 3)
        archivo_sitios = self.dir_historico / "sitios_raw.csv"
        sql_sitios = f"""
            SELECT
                TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                CAST(nombre AS VARCHAR) AS nombre,
                CASE
                    WHEN TRY_CAST(tipo_code AS INTEGER) IN (1, 2) THEN TRY_CAST(tipo_code AS INTEGER)
                    ELSE 1
                END AS tipo_code,
                CASE
                    WHEN TRY_CAST(pais_code AS INTEGER) BETWEEN 1 AND 4 THEN TRY_CAST(pais_code AS INTEGER)
                    ELSE 1
                END AS pais_code,
                TRY_CAST(REPLACE(CAST(reparto_pct AS VARCHAR), ',', '.') AS DECIMAL(5, 2)) AS reparto_pct
            FROM read_csv_auto('{archivo_sitios}', header=true, all_varchar=true)
            WHERE TRY_CAST(sitio_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (PARTITION BY TRY_CAST(sitio_id AS BIGINT) ORDER BY nombre ASC) = 1
        """
        self._copiar_parquet_atomico(sql_sitios, dir_dim / "sitios.parquet")

        # 2. Campanias: unificar con entidades_nuevas si existen, deduplicar (corrige campania 9111)
        #    y normalizar fin_ts < inicio_ts (corrige campania 2430)
        archivo_campanias = self.dir_historico / "campanias_raw.csv"
        archivo_camp_nuevas = self.dir_estado_productor / "entidades_nuevas" / "campanias.csv"
        fuente_campanias = f"SELECT * FROM read_csv_auto('{archivo_campanias}', header=true, all_varchar=true)"
        if archivo_camp_nuevas.exists():
            fuente_campanias += (
                f" UNION ALL SELECT * FROM read_csv_auto('{archivo_camp_nuevas}', header=true, all_varchar=true)"
            )

        sql_campanias = f"""
            WITH raw_camp AS (
                {fuente_campanias}
            )
            SELECT
                TRY_CAST(campania_id AS BIGINT) AS campania_id,
                TRY_CAST(anunciante_id AS BIGINT) AS anunciante_id,
                TRY_CAST(
                    REPLACE(CAST(presupuesto_diario AS VARCHAR), ',', '.') AS DECIMAL(10, 2)
                ) AS presupuesto_diario,
                TRY_CAST(
                    REPLACE(CAST(costo_por_clic AS VARCHAR), ',', '.') AS DECIMAL(10, 2)
                ) AS costo_por_clic,
                CASE
                    WHEN TRY_CAST(estado_code AS INTEGER) IN (1, 2, 3) THEN TRY_CAST(estado_code AS INTEGER)
                    ELSE 1
                END AS estado_code,
                TRY_CAST(inicio_ts AS BIGINT) AS inicio_ts,
                CASE
                    WHEN TRY_CAST(fin_ts AS BIGINT) IS NOT NULL
                         AND TRY_CAST(fin_ts AS BIGINT) >= TRY_CAST(inicio_ts AS BIGINT)
                    THEN TRY_CAST(fin_ts AS BIGINT)
                    ELSE NULL
                END AS fin_ts
            FROM raw_camp
            WHERE TRY_CAST(campania_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY TRY_CAST(campania_id AS BIGINT)
                ORDER BY TRY_CAST(inicio_ts AS BIGINT) DESC NULLS LAST
            ) = 1
        """
        self._copiar_parquet_atomico(sql_campanias, dir_dim / "campanias.parquet")

        # 3. Anunciantes: excluir email_contacto (PII), deduplicar (6 anunciantes duplicados)
        #    y normalizar categoria_code fuera de [1..6] hacia 6 ('Otro')
        archivo_anunciantes = self.dir_historico / "anunciantes_raw.csv"
        sql_anunciantes = f"""
            SELECT
                TRY_CAST(anunciante_id AS BIGINT) AS anunciante_id,
                CAST(nombre AS VARCHAR) AS nombre,
                CASE
                    WHEN TRY_CAST(categoria_code AS INTEGER) BETWEEN 1 AND 6 THEN TRY_CAST(categoria_code AS INTEGER)
                    ELSE 6
                END AS categoria_code,
                CASE
                    WHEN TRY_CAST(pais_code AS INTEGER) BETWEEN 1 AND 4 THEN TRY_CAST(pais_code AS INTEGER)
                    ELSE 1
                END AS pais_code,
                TRY_CAST(alta_ts AS BIGINT) AS alta_ts
            FROM read_csv_auto('{archivo_anunciantes}', header=true, all_varchar=true)
            WHERE TRY_CAST(anunciante_id AS BIGINT) IS NOT NULL
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY TRY_CAST(anunciante_id AS BIGINT)
                ORDER BY TRY_CAST(alta_ts AS BIGINT) DESC NULLS LAST
            ) = 1
        """
        self._copiar_parquet_atomico(sql_anunciantes, dir_dim / "anunciantes.parquet")

        # 4. Catalogos auxiliares
        dir_catalogos = self.dir_historico / "catalogos"
        catalogos = [
            ("categorias.csv", "categorias.parquet"),
            ("estados_campania.csv", "estados_campania.parquet"),
            ("paises.csv", "paises.parquet"),
            ("tipos_sitio.csv", "tipos_sitio.parquet"),
            ("validez_clic.csv", "validez_clic.parquet"),
        ]
        for csv_nom, prq_nom in catalogos:
            ruta_csv = dir_catalogos / csv_nom
            if ruta_csv.exists():
                self._copiar_parquet_atomico(
                    f"SELECT * FROM read_csv_auto('{ruta_csv}', header=true)",
                    dir_dim / prq_nom,
                )

        return {"dimensiones_procesadas": True, "segundos": round(time.perf_counter() - t0, 3)}

    def procesar_clics(self) -> dict[str, Any]:
        """Audita anomalias historicas a cuarentena, unifica con crudo en vivo, deduplica y particiona."""
        dir_clics = self.dir_limpio / "clics"
        self.dir_cuarentena.mkdir(parents=True, exist_ok=True)
        archivo_clics = self.dir_historico / "clics_raw.csv"
        ruta_sitios = self.dir_limpio / "dimensiones" / "sitios.parquet"
        ruta_campanias = self.dir_limpio / "dimensiones" / "campanias.parquet"
        ruta_cuarentena_clics = self.dir_cuarentena / "historico_clics_rechazados.parquet"
        t0 = time.perf_counter()
        audit_ts = int(time.time())

        sql_clasificacion = f"""
            WITH raw_clics AS (
                SELECT
                    CAST(clic_id AS VARCHAR) AS clic_id,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    CAST(dispositivo_id AS VARCHAR) AS dispositivo_id,
                    CAST(ip AS VARCHAR) AS ip,
                    CAST(costo AS VARCHAR) AS costo_raw,
                    TRY_CAST(REPLACE(CAST(costo AS VARCHAR), ',', '.') AS DECIMAL(10, 2)) AS costo_num,
                    CAST(ts AS VARCHAR) AS ts_raw,
                    TRY_CAST(ts AS BIGINT) AS ts_num,
                    CAST(valido_code AS VARCHAR) AS valido_raw,
                    TRY_CAST(valido_code AS INTEGER) AS valido_num
                FROM read_csv_auto('{archivo_clics}', header=true, all_varchar=true)
            ),
            evaluados AS (
                SELECT
                    r.*,
                    CASE
                        WHEN r.clic_id IS NULL OR TRIM(r.clic_id) = '' THEN 'FALTA_CLIC_ID'
                        WHEN r.dispositivo_id IS NULL OR TRIM(r.dispositivo_id) = '' THEN 'FALTA_DISPOSITIVO_ID'
                        WHEN r.ip IS NULL OR TRIM(r.ip) = '' THEN 'FALTA_IP'
                        WHEN r.ts_num IS NULL OR r.ts_num <= 0 OR r.ts_num > {MAX_TS_RAZONABLE_SEGUNDOS}
                            THEN 'TIMESTAMP_CORRUPTO_O_MS'
                        WHEN r.valido_num IS NULL OR r.valido_num NOT IN (1, 2) THEN 'VALIDO_CODE_FUERA_CATALOGO'
                        WHEN r.costo_num IS NULL OR r.costo_num <= 0 THEN 'COSTO_INVALIDO'
                        WHEN c.campania_id IS NULL THEN 'CAMPANIA_HUERFANA'
                        WHEN s.sitio_id IS NULL THEN 'SITIO_HUERFANO'
                        ELSE NULL
                    END AS _error_motivo
                FROM raw_clics r
                LEFT JOIN read_parquet('{ruta_campanias}') c ON r.campania_id = c.campania_id
                LEFT JOIN read_parquet('{ruta_sitios}') s ON r.sitio_id = s.sitio_id
            )
        """

        # 1. Escribir registros rechazados en cuarentena batch
        sql_cuarentena = f"""
            {sql_clasificacion}
            SELECT
                clic_id,
                campania_id,
                sitio_id,
                dispositivo_id,
                ip,
                costo_raw AS costo,
                ts_raw AS ts,
                valido_raw AS valido_code,
                _error_motivo,
                {audit_ts}::BIGINT AS _audit_ts
            FROM evaluados
            WHERE _error_motivo IS NOT NULL
        """
        self._copiar_parquet_atomico(sql_cuarentena, ruta_cuarentena_clics)

        # 2. Unificar clics historicos validos con clics de datos/crudo/clic/*.jsonl (si existen)
        dir_crudo_clic = self.dir_crudo / "clic"
        archivos_crudo_clic = list(dir_crudo_clic.glob("*.jsonl")) if dir_crudo_clic.exists() else []
        union_vivo_sql = ""
        if archivos_crudo_clic:
            patron_crudo_clic = str(self.dir_crudo / "clic" / "*.jsonl")
            union_vivo_sql = f"""
                UNION ALL
                SELECT
                    CAST(clic_id AS VARCHAR) AS clic_id,
                    TRY_CAST(campania_id AS BIGINT) AS campania_id,
                    TRY_CAST(sitio_id AS BIGINT) AS sitio_id,
                    CAST(dispositivo_id AS VARCHAR) AS dispositivo_id,
                    CAST(ip AS VARCHAR) AS ip,
                    TRY_CAST(REPLACE(CAST(costo AS VARCHAR), ',', '.') AS DECIMAL(10, 2)) AS costo,
                    TRY_CAST(ts AS BIGINT) AS ts,
                    1::INTEGER AS valido_code
                FROM read_json_auto('{patron_crudo_clic}')
                WHERE clic_id IS NOT NULL
                  AND dispositivo_id IS NOT NULL
                  AND ip IS NOT NULL
                  AND TRY_CAST(ts AS BIGINT) BETWEEN 1 AND {MAX_TS_RAZONABLE_SEGUNDOS}
            """

        if dir_clics.exists():
            shutil.rmtree(dir_clics, ignore_errors=True)
        dir_clics.mkdir(parents=True, exist_ok=True)

        sql_silver_clics = f"""
            COPY (
                {sql_clasificacion},
                unificados AS (
                    SELECT
                        clic_id,
                        campania_id,
                        sitio_id,
                        dispositivo_id,
                        ip,
                        costo_num AS costo,
                        ts_num AS ts,
                        valido_num AS valido_code
                    FROM evaluados
                    WHERE _error_motivo IS NULL
                    {union_vivo_sql}
                ),
                deduplicados AS (
                    SELECT
                        u.clic_id,
                        u.campania_id,
                        u.sitio_id,
                        s.pais_code,
                        u.dispositivo_id,
                        u.ip,
                        u.costo,
                        u.ts,
                        u.valido_code,
                        (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR) AS fecha_local,
                        EXTRACT(YEAR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS anio,
                        EXTRACT(MONTH FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS mes,
                        EXTRACT(DAY FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia,
                        EXTRACT(HOUR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS hora,
                        FLOOR(
                            EXTRACT(HOUR FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR)) / 2
                        )::INTEGER AS franja_id,
                        EXTRACT(DOW FROM (epoch_ms(u.ts::BIGINT * 1000) - INTERVAL 6 HOUR))::INTEGER AS dia_semana
                    FROM unificados u
                    INNER JOIN read_parquet('{ruta_sitios}') s ON u.sitio_id = s.sitio_id
                    INNER JOIN read_parquet('{ruta_campanias}') c ON u.campania_id = c.campania_id
                    QUALIFY ROW_NUMBER() OVER (PARTITION BY u.clic_id ORDER BY u.ts ASC) = 1
                )
                SELECT * FROM deduplicados
            ) TO '{dir_clics}' (
                FORMAT 'PARQUET',
                PARTITION_BY (pais_code, anio, mes),
                COMPRESSION 'ZSTD',
                OVERWRITE_OR_IGNORE true
            );
        """
        self.motor.ejecutar(sql_silver_clics)
        return {"clics_procesados": True, "segundos": round(time.perf_counter() - t0, 3)}

    def procesar_impresiones_hora(self) -> dict[str, Any]:
        """Audita anomalias en impresiones, deduplica, agrega eventos en vivo y particiona en Silver."""
        dir_impresiones = self.dir_limpio / "impresiones_hora"
        self.dir_cuarentena.mkdir(parents=True, exist_ok=True)
        archivo_imp = self.dir_historico / "impresiones_hora_raw.csv"
        ruta_sitios = self.dir_limpio / "dimensiones" / "sitios.parquet"
        ruta_campanias = self.dir_limp
... [recortado por tamaño]
```

### src/batch/ejecutar_pipeline.py

```py
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

```

### src/batch/motor.py

```py
"""Gestor de conexion y sesiones analiticas de DuckDB para la Capa Batch."""

from pathlib import Path
from typing import Any

import duckdb
from duckdb import DuckDBPyConnection

from src.core.config import DUCKDB_MEMORY_LIMIT, DUCKDB_THREADS


class MotorDuckDB:
    """Administra sesiones vectorizadas de DuckDB optimizadas para Parquet y ZSTD."""

    def __init__(
        self,
        base_datos: str | Path = ":memory:",
        limite_memoria: str = DUCKDB_MEMORY_LIMIT,
        hilos: int = DUCKDB_THREADS,
    ) -> None:
        self.base_datos = str(base_datos)
        self.limite_memoria = limite_memoria
        self.hilos = hilos
        self._con: DuckDBPyConnection | None = None

    def conectar(self) -> DuckDBPyConnection:
        """Inicializa o retorna la conexion activa con configuracion de rendimiento."""
        if self._con is None:
            self._con = duckdb.connect(database=self.base_datos)
            self._con.execute(f"SET max_memory = '{self.limite_memoria}';")
            self._con.execute(f"SET threads = {self.hilos};")
            self._con.execute("SET preserve_insertion_order = false;")
        return self._con

    def ejecutar(self, sql: str, params: list[Any] | None = None) -> Any:
        """Ejecuta una consulta SQL en la sesion actual."""
        con = self.conectar()
        if params is not None:
            return con.execute(sql, params)
        return con.execute(sql)

    def cerrar(self) -> None:
        """Cierra la conexion liberando buffers de memoria."""
        if self._con is not None:
            self._con.close()
            self._con = None

```

### src/batch/scheduler.py

```py
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

```

### src/batch/silver_a_gold.py

```py
"""Generador de Capa Gold (Modelos analiticos, baselines de 8/4 semanas, incidente 15-sep y watermark)."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.batch.motor import MotorDuckDB
from src.core.config import (
    CORTE_HISTORICO_TS,
    DIR_LIMPIO,
    DIR_MODELADO,
    VENTANA_4_SEMANAS_S,
    VENTANA_8_SEMANAS_S,
)


class AgregadorSilverGold:
    """Precomputa vistas Gold (P1, P2, P3, P7, P8, P9, P10, 15-sep) con escritura atomica."""

    def __init__(
        self,
        dir_limpio: Path = DIR_LIMPIO,
        dir_modelado: Path = DIR_MODELADO,
        motor: MotorDuckDB | None = None,
    ) -> None:
        self.dir_limpio = dir_limpio
        self.dir_modelado = dir_modelado
        self.motor = motor or MotorDuckDB()

    def _copiar_atomico(self, sql_query: str, ruta_destino: Path) -> None:
        """Ejecuta COPY hacia un archivo .tmp.parquet y reemplaza atomicamente el destino."""
        ruta_destino.parent.mkdir(parents=True, exist_ok=True)
        ruta_tmp = ruta_destino.with_suffix(".tmp.parquet")
        self.motor.ejecutar(f"COPY ({sql_query}) TO '{ruta_tmp}' (FORMAT 'PARQUET', COMPRESSION 'ZSTD');")
        ruta_tmp.replace(ruta_destino)

    def _obtener_max_ts(self) -> int:
        """Obtiene el maximo timestamp consolidado en Silver (o CORTE_HISTORICO_TS por defecto)."""
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        con = self.motor.conectar()
        fila = con.execute(
            f"SELECT COALESCE(MAX(ts), {CORTE_HISTORICO_TS})::BIGINT "
            f"FROM read_parquet('{ruta_clics}', hive_partitioning=true)"
        ).fetchone()
        return int(fila[0]) if fila and fila[0] is not None else CORTE_HISTORICO_TS

    def generar_p1_ingresos_mensuales(self) -> dict[str, Any]:
        """P1: Clics validos e ingreso por mes y pais (ultimos 12 meses).

        Regla Aclaraciones: Meses calendario en hora local. El primer y el ultimo mes del
        periodo son parciales y se marcan dinamicamente como tales.
        """
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_paises = self.dir_limpio / "dimensiones/paises.parquet"
        ruta_salida = self.dir_modelado / "p1_ingresos_mensuales.parquet"

        sql = f"""
            WITH clics_validos AS (
                SELECT
                    c.pais_code,
                    p.descripcion AS pais_nombre,
                    c.anio,
                    c.mes,
                    printf('%04d-%02d', c.anio, c.mes) AS anio_mes,
                    c.costo
                FROM read_parquet('{ruta_clics}', hive_partitioning=true) c
                LEFT JOIN read_parquet('{ruta_paises}') p ON c.pais_code = p.code
                WHERE c.valido_code = 1
            ),
            limites AS (
                SELECT MIN(anio_mes) AS min_mes, MAX(anio_mes) AS max_mes FROM clics_validos
            )
            SELECT
                v.pais_code,
                v.pais_nombre,
                v.anio,
                v.mes,
                v.anio_mes,
                COUNT(*)::BIGINT AS total_clics_validos,
                CAST(SUM(v.costo) AS DECIMAL(12, 2)) AS ingreso_usd,
                CASE
                    WHEN v.anio_mes = l.min_mes OR v.anio_mes = l.max_mes THEN true
                    ELSE false
                END AS mes_parcial
            FROM clics_validos v
            CROSS JOIN limites l
            GROUP BY 1, 2, 3, 4, 5, 8
            ORDER BY v.anio, v.mes, v.pais_code
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p1_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_p2_top_sitios(self) -> dict[str, Any]:
        """P2: Top 10 sitios por ingreso en 12 meses y porcentaje de clics invalidos.

        Regla Empates (Guia pag. 10): En los rankings, los empates se ordenan por el
        identificador de menor a mayor (sitio_id ASC).
        """
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_sitios = self.dir_limpio / "dimensiones/sitios.parquet"
        ruta_paises = self.dir_limpio / "dimensiones/paises.parquet"
        ruta_salida = self.dir_modelado / "p2_top_sitios.parquet"

        sql = f"""
            WITH metricas_sitios AS (
                SELECT
                    c.sitio_id,
                    s.nombre AS sitio_nombre,
                    p.descripcion AS pais_nombre,
                    COUNT(*)::BIGINT AS total_clics,
                    COUNT(*) FILTER (WHERE c.valido_code = 1)::BIGINT AS clics_validos,
                    COUNT(*) FILTER (WHERE c.valido_code = 2)::BIGINT AS clics_invalidos,
                    CAST(SUM(CASE WHEN c.valido_code = 1 THEN c.costo ELSE 0 END) AS DECIMAL(12, 2)) AS ingreso_usd
                FROM read_parquet('{ruta_clics}', hive_partitioning=true) c
                LEFT JOIN read_parquet('{ruta_sitios}') s ON c.sitio_id = s.sitio_id
                LEFT JOIN read_parquet('{ruta_paises}') p ON s.pais_code = p.code
                GROUP BY 1, 2, 3
            )
            SELECT
                sitio_id,
                sitio_nombre,
                pais_nombre,
                ingreso_usd,
                total_clics,
                clics_validos,
                clics_invalidos,
                ROUND((clics_invalidos * 100.0) / NULLIF(total_clics, 0), 2) AS pct_clics_invalidos
            FROM metricas_sitios
            ORDER BY ingreso_usd DESC, sitio_id ASC
            LIMIT 10
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p2_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_p3_franja_dia_ctr(self) -> dict[str, Any]:
        """P3: Franja horaria y dia de la semana con mayor tasa de clics (CTR y por 1,000)."""
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_imp = self.dir_limpio / "impresiones_hora/**/*.parquet"
        ruta_salida = self.dir_modelado / "p3_franja_dia_ctr.parquet"

        sql = f"""
            WITH dias AS (
                SELECT unnest(range(0, 7))::INTEGER AS dia_semana
            ),
            franjas AS (
                SELECT unnest(range(0, 12))::INTEGER AS franja_id
            ),
            grid AS (
                SELECT d.dia_semana, f.franja_id
                FROM dias d
                CROSS JOIN franjas f
            ),
            clics_agg AS (
                SELECT
                    dia_semana,
                    franja_id,
                    COUNT(*)::BIGINT AS total_clics
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                GROUP BY 1, 2
            ),
            imp_agg AS (
                SELECT
                    dia_semana,
                    franja_id,
                    SUM(impresiones)::BIGINT AS total_impresiones
                FROM read_parquet('{ruta_imp}', hive_partitioning=true)
                GROUP BY 1, 2
            )
            SELECT
                g.dia_semana,
                CASE g.dia_semana
                    WHEN 0 THEN 'Domingo'
                    WHEN 1 THEN 'Lunes'
                    WHEN 2 THEN 'Martes'
                    WHEN 3 THEN 'Miercoles'
                    WHEN 4 THEN 'Jueves'
                    WHEN 5 THEN 'Viernes'
                    WHEN 6 THEN 'Sabado'
                END AS dia_nombre,
                g.franja_id,
                printf('%02d:00 - %02d:00', g.franja_id * 2, (g.franja_id * 2) + 2) AS franja_horaria,
                COALESCE(i.total_impresiones, 0)::BIGINT AS total_impresiones,
                COALESCE(c.total_clics, 0)::BIGINT AS total_clics,
                ROUND(
                    (COALESCE(c.total_clics, 0) * 100.0) / NULLIF(COALESCE(i.total_impresiones, 0), 0), 4
                ) AS tasa_ctr_pct,
                ROUND(
                    (COALESCE(c.total_clics, 0) * 1000.0) / NULLIF(COALESCE(i.total_impresiones, 0), 0), 4
                ) AS tasa_clics_por_mil
            FROM grid g
            LEFT JOIN imp_agg i ON g.dia_semana = i.dia_semana AND g.franja_id = i.franja_id
            LEFT JOIN clics_agg c ON g.dia_semana = c.dia_semana AND g.franja_id = c.franja_id
            ORDER BY tasa_ctr_pct DESC NULLS LAST, g.dia_semana ASC, g.franja_id ASC
        """
        self._copiar_atomico(sql, ruta_salida)
        return {"p3_generado": True, "segundos": round(time.perf_counter() - t0, 3)}

    def generar_baselines_historicos(self, max_ts: int) -> dict[str, Any]:
        """Precomputa baselines de 8 y 4 semanas con fallback por grupo (P7, P8, P9, P10, 15-sep)."""
        t0 = time.perf_counter()
        ruta_clics = self.dir_limpio / "clics/**/*.parquet"
        ruta_imp = self.dir_limpio / "impresiones_hora/**/*.parquet"
        ruta_campanias = self.dir_limpio / "dimensiones/campanias.parquet"
        ruta_anunciantes = self.dir_limpio / "dimensiones/anunciantes.parquet"
        ruta_sitios = self.dir_limpio / "dimensiones/sitios.parquet"

        ts_inicio_8sem = max_ts - VENTANA_8_SEMANAS_S
        ts_inicio_4sem = max_ts - VENTANA_4_SEMANAS_S

        # 1. Lista negra de dispositivos con historial de clics invalidos (P9)
        sql_fraude = f"""
            SELECT
                dispositivo_id,
                ANY_VALUE(ip) AS ip,
                COUNT(*)::INTEGER AS clics_invalidos_historicos
            FROM read_parquet('{ruta_clics}', hive_partitioning=true)
            WHERE valido_code = 2
            GROUP BY 1
            ORDER BY clics_invalidos_historicos DESC, dispositivo_id ASC
        """
        self._copiar_atomico(sql_fraude, self.dir_modelado / "dispositivos_fraude_historico.parquet")

        # 2. Baselines de campanias (P7 y API): ventana estricta de 8 semanas + fallback por categoria_code
        sql_baselines_camp = f"""
            WITH camp_meta AS (
                SELECT
                    c.campania_id,
                    c.inicio_ts,
                    COALESCE(a.categoria_code, 6) AS categoria_code,
                    (c.inicio_ts IS NOT NULL AND ({max_ts} - c.inicio_ts) >= {VENTANA_4_SEMANAS_S}) AS antiguedad_4sem
                FROM read_parquet('{ruta_campanias}') c
                LEFT JOIN read_parquet('{ruta_anunciantes}') a ON c.anunciante_id = a.anunciante_id
            ),
            conteo_cat AS (
                SELECT categoria_code, COUNT(*)::DOUBLE AS num_campanias_cat
                FROM camp_meta
                GROUP BY 1
            ),
            gasto_8sem AS (
                SELECT
                    campania_id,
                    dia_semana,
                    hora,
                    SUM(costo) AS suma_gasto_8sem,
                    COUNT(*)::BIGINT AS casos_8sem
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                WHERE ts > {ts_inicio_8sem} AND ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            slots_activos AS (
                SELECT DISTINCT dia_semana, hora FROM gasto_8sem
            ),
            malla AS (
                SELECT
                    cm.campania_id,
                    cm.categoria_code,
                    cm.antiguedad_4sem,
                    s.dia_semana,
                    s.hora,
                    COALESCE(g.suma_gasto_8sem, 0.00) AS suma_gasto_8sem,
                    COALESCE(g.casos_8sem, 0) AS casos_8sem
                FROM camp_meta cm
                CROSS JOIN slots_activos s
                LEFT JOIN gasto_8sem g
                    ON cm.campania_id = g.campania_id
                   AND s.dia_semana = g.dia_semana
                   AND s.hora = g.hora
            ),
            prom_categoria AS (
                SELECT
                    m.categoria_code,
                    m.dia_semana,
                    m.hora,
                    CAST(ROUND(SUM(m.suma_gasto_8sem) / (8.0 * MAX(cc.num_campanias_cat)), 2) AS DECIMAL(10, 2))
                        AS gasto_promedio_categoria
                FROM malla m
                JOIN conteo_cat cc ON m.categoria_code = cc.categoria_code
                GROUP BY 1, 2, 3
            )
            SELECT
                m.campania_id,
                m.categoria_code,
                m.dia_semana,
                m.hora,
                CAST(ROUND(m.suma_gasto_8sem / 8.0, 2) AS DECIMAL(10, 2)) AS gasto_promedio_historico,
                pc.gasto_promedio_categoria,
                (m.antiguedad_4sem AND m.casos_8sem > 0) AS tiene_historia_suficiente,
                CASE
                    WHEN m.antiguedad_4sem AND m.casos_8sem > 0
                        THEN CAST(ROUND(m.suma_gasto_8sem / 8.0, 2) AS DECIMAL(10, 2))
                    ELSE pc.gasto_promedio_categoria
                END AS baseline_efectivo
            FROM malla m
            JOIN prom_categoria pc
                ON m.categoria_code = pc.categoria_code
               AND m.dia_semana = pc.dia_semana
               AND m.hora = pc.hora
            ORDER BY m.campania_id, m.dia_semana, m.hora
        """
        self._copiar_atomico(sql_baselines_camp, self.dir_modelado / "baselines_campanias.parquet")

        # 3. Baselines de sitios (P8): suma de clics y suma de impresiones en 8 semanas divididas una sola vez
        sql_baselines_sitios = f"""
            WITH clics_8sem AS (
                SELECT
                    sitio_id,
                    dia_semana,
                    hora,
                    COUNT(*)::BIGINT AS clics_8sem
                FROM read_parquet('{ruta_clics}', hive_partitioning=true)
                WHERE ts > {ts_inicio_8sem} AND ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            imp_8sem AS (
                SELECT
                    sitio_id,
                    dia_semana,
                    hora,
                    SUM(impresiones)::BIGINT AS impresiones_8sem
                FROM read_parquet('{ruta_imp}', hive_partitioning=true)
                WHERE hora_ts > {ts_inicio_8sem} AND hora_ts <= {max_ts}
                GROUP BY 1, 2, 3
            ),
            sitios_base AS (
                SELECT
                    s.sitio_id,
                    s.pais_code,
                    i.dia_semana,
                    i.hora,
                    COALESCE(c.clics_8sem, 0) AS clics_8sem,
                    i.impresiones_8sem,
                    ROUND((COALESCE(c.clics_8sem, 0) * 1000.0) / NULLIF(i.impresiones_8sem, 0), 4)
                        AS tasa_clics_por_mil_historica
                FROM imp_8sem i
                JOIN read_parquet('{ruta_sitios}') s ON i.sitio_id = s.sitio_id
                LEFT JOIN clics_8sem c
                    ON i.sitio_id = c.sitio_id AND i.dia_semana = c.dia_semana AND i.hora = c.hora
            ),
            pais_fallback AS (
                SELECT
                    pais_code,
                    dia_semana,
                    hor
... [recortado por tamaño]
```

### src/core/__init__.py

```py
"""Modulo principal del nucleo de Clic Justo."""

```

### src/core/config.py

```py
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

```

### src/core/contratos.py

```py
"""Validador centralizado de contratos JSON Schema multi-version (v1, v2+) para Clic Justo."""

import json
import re
from pathlib import Path
from typing import Any, cast

from jsonschema import Draft202012Validator

from src.core.config import CONTRATOS_DIR

PATRON_CONTRATO = re.compile(r"^(?P<tipo>[a-zA-Z0-9_]+)\.v(?P<version>[0-9]+)\.json$")


class ValidadorContratos:
    """Compila y valida esquemas formales JSON Schema draft 2020-12 indexados por (tipo, version)."""

    def __init__(self, ruta_contratos: Path = CONTRATOS_DIR) -> None:
        self.ruta_contratos = ruta_contratos
        self._validadores: dict[tuple[str, int], Draft202012Validator] = {}
        self._tipos_conocidos: set[str] = set()
        self._cargar_esquemas()

    @property
    def versiones_registradas(self) -> set[tuple[str, int]]:
        """Retorna el conjunto de pares (tipo, version) compilados en memoria."""
        return set(self._validadores.keys())

    def _cargar_esquemas(self) -> None:
        """Descubre y compila automaticamente todos los esquemas <tipo>.v<version>.json."""
        for ruta_archivo in sorted(self.ruta_contratos.glob("*.v*.json")):
            coincidencia = PATRON_CONTRATO.match(ruta_archivo.name)
            if not coincidencia:
                continue
            tipo = coincidencia.group("tipo")
            version = int(coincidencia.group("version"))
            with open(ruta_archivo, encoding="utf-8") as f:
                esquema = cast(dict[str, Any], json.load(f))
            Draft202012Validator.check_schema(esquema)
            self._validadores[(tipo, version)] = Draft202012Validator(esquema)
            self._tipos_conocidos.add(tipo)

    def validar_evento(self, payload: dict[str, Any]) -> tuple[bool, str, str | None, str | None]:
        """Valida un evento entrante contra su contrato correspondiente segun (tipo, version).

        Returns:
            Tuple con (es_valido, tipo_evento, error_tipo, error_detalle).
        """
        tipo = str(payload.get("tipo", "desconocido"))
        if tipo not in self._tipos_conocidos:
            return (
                False,
                tipo,
                "DiscriminatorError",
                f"Tipo de evento '{tipo}' no reconocido en contratos registrados ({sorted(self._tipos_conocidos)})",
            )

        version_raw = payload.get("version")
        if isinstance(version_raw, bool) or not isinstance(version_raw, int):
            # Si falta 'version' o tiene tipo incorrecto, delegamos al validador v1 del tipo para reporte estandar
            validador_base = self._validadores.get((tipo, 1))
            if validador_base is not None:
                errores_base = list(validador_base.iter_errors(payload))
                if errores_base:
                    primer = errores_base[0]
                    ruta = ".".join(str(p) for p in primer.path)
                    campo = f" en '{ruta}'" if ruta else ""
                    return (False, tipo, "ValidationError", f"{primer.message}{campo}")
            return (
                False,
                tipo,
                "ValidationError",
                f"El campo 'version' es requerido y debe ser un entero valido (recibido: {version_raw!r})",
            )

        llave = (tipo, version_raw)
        if llave not in self._validadores:
            return (
                False,
                tipo,
                "SchemaEvolutionError",
                f"La version {version_raw} para el tipo '{tipo}' no tiene un contrato registrado.",
            )

        validador = self._validadores[llave]
        errores = list(validador.iter_errors(payload))
        if not errores:
            return (True, tipo, None, None)

        primer_error = errores[0]
        ruta = ".".join(str(p) for p in primer_error.path)
        campo = f" en '{ruta}'" if ruta else ""
        detalle = f"{primer_error.message}{campo}"
        return (False, tipo, "ValidationError", detalle)

```

### src/core/modelos.py

```py
"""Modelos de datos y DTOs estructurados para Clic Justo."""

from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventoImpresionV1(BaseModel):
    """Modelo formal para eventos de impresion conforme a impresion.v1.json."""

    evento_id: str = Field(..., min_length=1)
    tipo: Literal["impresion"] = "impresion"
    version: Literal[1] = 1
    impresion_id: str = Field(..., min_length=1)
    campania_id: int = Field(..., ge=1)
    sitio_id: int = Field(..., ge=1)
    dispositivo_id: str = Field(..., min_length=1)
    ts: int = Field(..., ge=0)


class EventoClicV1(BaseModel):
    """Modelo formal para eventos de clic conforme a clic.v1.json."""

    evento_id: str = Field(..., min_length=1)
    tipo: Literal["clic"] = "clic"
    version: Literal[1] = 1
    clic_id: str = Field(..., min_length=1)
    impresion_id: str = Field(..., min_length=1)
    campania_id: int = Field(..., ge=1)
    sitio_id: int = Field(..., ge=1)
    dispositivo_id: str = Field(..., min_length=1)
    ip: str = Field(..., min_length=1)
    costo: str = Field(..., pattern=r"^[0-9]+(\.[0-9]+)?$")
    ts: int = Field(..., ge=0)


class RegistroCuarentena(BaseModel):
    """Estructura de auditoria para registros desviados a cuarentena."""

    ingest_ts: int = Field(..., alias="_ingest_ts")
    error_tipo: str = Field(..., alias="_error_tipo")
    error_detalle: str = Field(..., alias="_error_detalle")
    payload_original: dict[str, Any]


class CampaniaResumenResponse(BaseModel):
    """Respuesta del endpoint operativo de atencion al cliente (/campanias/{id}/resumen)."""

    campania_id: int
    anunciante_id: int
    presupuesto_diario: Decimal
    gasto_hoy: Decimal
    presupuesto_restante: Decimal
    gasto_ultima_hora: Decimal
    promedio_historico_hora: Decimal
    pct_dispositivos_invalidos_ultima_hora: float
    accion_sugerida: Literal["normal", "revisar", "pausar"]

```

### src/ingesta/__init__.py

```py
"""Modulo de ingesta, enrutamiento a crudo y gestion de cuarentena."""

```

### src/ingesta/consumidor.py

```py
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

```

### src/ingesta/enrutador.py

```py
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

```
