# Clic Justo · Plataforma de Datos con Arquitectura Lambda y Marco de QA

Plataforma integral de ingenieria y analitica de datos para publicidad digital local, orientada a la deteccion de fraude y anomalias de trafico sub-minuto y a la consolidacion contable determinista.

Incluye un marco de aseguramiento de calidad (QA) exhaustivo estructurado en tres capas segun la Piramide de Mike Cohn (Unitarias/DDT, Integracion HTTP con BVA/Equivalencia, y End-to-End con Playwright bajo Page Object Model y principios SOLID), integrado en un pipeline CI/CD multiambiente y con notificaciones de alerta SMTP.

---

## 1. Vision General del Sistema

Clic Justo opera conectando anunciantes locales con medios digitales (periodicos, blogs y aplicaciones) bajo un esquema de Costo por Clic (CPC). La plataforma implementa una **Arquitectura Lambda** optimizada para:

1. **Deteccion Temprana y Sub-Minuto:** Identificar y mitigar patrones de clics fraudulentos (ataques botnet, clics repetitivos, anomalias de gasto) antes de consolidar el cobro a los anunciantes.
2. **Consistencia Contable Determinista:** Garantizar la conciliacion mensual exacta de ingresos, deduciendo clics invalidos y calculando transferencias a los medios publicadores mediante procesos batch idempotentes.
3. **Serving Layer de Baja Latencia:** Exponer metricas operativas, baselines moviles y reglas de decision en milisegundos mediante una API REST en FastAPI respaldada por DuckDB y Parquet.
4. **Interfaz Web de Operaciones:** Modulo visual de 3 pantallas para monitoreo del sistema, evaluacion del semaforo de campanias y exploracion analitica de negocio.

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
                                            |
                                            v
            +---------------------------------------------------------------+
            |                       INTERFAZ WEB (UI)                       |
            |   Dashboard (/ui/) · Campanias (/ui/campanias) · Analitica    |
            +---------------------------------------------------------------+
```

---

## 3. Estructura del Repositorio

```
finale-QA/
|-- .github/workflows/
|   `-- ci.yml           Pipeline de CI/CD (5 etapas, multiambiente, parametros, SMTP)
|-- src/
|   |-- api/             Serving Layer: endpoints FastAPI, rutas_ui, plantillas HTML
|   |-- batch/           Batch Layer: transformaciones Medallion y motor DuckDB
|   |-- core/            Nucleo comun: configuracion, contratos JSON y modelos Pydantic
|   `-- ingesta/         Ingesta asincrona de eventos y enrutamiento a cuarentena
|-- tests/
|   |-- api/             Pruebas de integracion HTTP (BVA, Equivalencia) y DDT
|   |-- arquitectura/    SLA y benchmarks de rendimiento
|   |-- batch/           Pruebas unitarias de transformaciones SQL y pipeline Medallion
|   |-- core/            Pruebas unitarias y DDT de contratos JSON multiversion
|   |-- e2e/             Pruebas End-to-End con Playwright y patron Page Object Model
|   `-- ingesta/         Pruebas de cuarentena, consumidor y enrutador
|-- DECISIONES.md        Informe de decisiones de arquitectura y calidad (rubrica)
|-- EVIDENCIA.md         Registro de ejecuciones verdes/rojas, SHAs y cobertura
|-- pyproject.toml       Definicion de dependencias y configuracion de herramientas
`-- uv.lock              Lockfile determinista de paquetes
```

---

## 4. Requisitos Previos y Entorno

- **Python:** 3.14 o superior
- **Gestor de Paquetes y Tiempos de Ejecucion:** [`uv`](https://docs.astral.sh/uv/) (v0.5+)

Para sincronizar todas las dependencias (incluyendo herramientas de prueba y desarrollo):
```bash
uv sync --dev
```

Para instalar los binarios del navegador Playwright (necesario para pruebas E2E):
```bash
uv run playwright install chromium
```

---

## 5. Ejecucion de la Suite de Pruebas

La suite de 48 pruebas automatizadas cubre las tres capas de la piramide de Cohn:

### Ejecucion Completa con Umbral de Cobertura (Gate >= 60%)
```bash
uv run pytest tests/ -v --cov=src --cov-report=term-missing --cov-fail-under=60
```

### Ejecucion por Capas

1. **Capa 1: Unitarias y DDT (Contratos y Logica):**
   ```bash
   uv run pytest tests/core tests/batch/unit tests/ingesta/ddt tests/api/ddt -v
   ```

2. **Capa 2: Integracion HTTP y Caja Negra (BVA / Equivalencia / SLA):**
   ```bash
   uv run pytest tests/api/integration tests/arquitectura/sla -v
   ```

3. **Capa 3: End-to-End con Playwright (Navegador Real):**
   ```bash
   # Suite E2E completa (Chromium)
   uv run pytest tests/e2e/ -v --browser chromium

   # Smoke test rapido de interfaz web
   uv run pytest tests/e2e/ -v -m smoke --browser chromium
   ```

### Analisis Estatico y Formato de Codigo
```bash
# Verificacion de formato y estilo con Ruff
uv run ruff check .
uv run ruff format --check .

# Analisis estatico estricto de tipos con MyPy
uv run mypy src/ tests/ --strict
```

---

## 6. Interfaz Web de Operaciones y Serving API

La aplicacion incluye 3 pantallas interactivas construidas con HTML5 semantico, CSS embebido de alta velocidad y vanilla JavaScript (sin dependencias externas de Node.js):

- **`/ui/` (Dashboard Principal):** Indicador de salud del servicio (`#badge-health`), estado de ingesta y metadatos del ambiente desplegado (`#env-badge`) y SHA del commit (`#commit-badge`).
- **`/ui/campanias` (Inspeccion y Semaforo):** Consulta operativa de campanias publicitarias con actualizacion dinamica del presupuesto (`#val-presupuesto`), gasto del dia y semaforo de accion (`#badge-accion`: `normal`, `revisar`, `pausar`).
- **`/ui/analitica` (Explorador Analitico):** Selector interactivo (`#select-query`) para ejecutar las consultas analiticas P1 (Top 5 dominios), P2 (Horas pico de sospecha) y P3 (Tasa de fraude por dispositivo) con renderizado tabular (`#tabla-resultados`).

Para levantar el servidor localmente:
```bash
uv run uvicorn src.api.main:app --host 127.0.0.1 --port 8000 --reload
```
Acceder a la interfaz web en: `http://localhost:8000/ui/`.  
Documentacion Swagger OpenAPI en: `http://localhost:8000/docs`.

---

## 7. Pipeline de Integracion Continua (CI/CD)

El flujo de trabajo en `.github/workflows/ci.yml` cuenta con 5 etapas secuenciales protegidas por compuertas de calidad:

```
[1. Lint & Tipos] -> [2. Unitarias & Cobertura] -> [3. Build] -> [4. Despliegue & Integracion] -> [5. End-to-End]
```

### Ambientes de Despliegue Soportados
- **`staging`:** Instancia en puerto `8000` con verificacion activa de salud.
- **`produccion`:** Instancia en puerto `8001` con validacion estricta de `APP_ENV` y `COMMIT_SHA`.

### Parametros de Ejecucion Manual (`workflow_dispatch`)
- `ambiente`: Seleccion entre `staging` (default) o `produccion`.
- `test_suite`: Seleccion entre `smoke` (ejecucion rapida) o `completa`.
- `browser`: Seleccion entre `chromium` (default) o `firefox`.
- `destinatario_correo`: Correo para alertas de fallo (default: `josue.aguilar@ufm.edu`).

### Notificaciones de Alerta por Correo (SMTP)
Ante cualquier fallo en cualquiera de las 5 etapas, GitHub Actions despacha un correo electronico mediante la accion `dawidd6/action-send-mail` utilizando las credenciales configuradas en los GitHub Secrets (`SMTP_SERVER`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`).

---

## 8. Entregables Academicos Formales

- **[`DECISIONES.md`](DECISIONES.md):** Justificacion de la piramide de pruebas de Cohn, shift-left testing, puerta de calidad (umbral 60%), principios SOLID en el Page Object Model, referencias a estandares IEEE (829, 29119, 25010) y evaluacion critica de 3 sugerencias de asistentes de IA.
- **[`EVIDENCIA.md`](EVIDENCIA.md):** Registro formal de auditoria del pipeline en ciclos verde/rojo/verde, metricas de ejecucion (< 35s), desglose de las 48 pruebas automatizadas y bitacora de alertas SMTP.
- **[`docs/arc42.md`](docs/arc42.md):** Especificacion completa de arquitectura de software bajo la plantilla Arc42 y manual operativo.
