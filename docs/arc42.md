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
  uv run uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
  ```
- **Iniciar Consumidor de Ingesta:**
  ```bash
  uv run python -m src.ingesta.consumidor --directorio datos/eventos_vivo --intervalo 2
  ```
- **Ejecutar Pipeline Batch:**
  ```bash
  uv run python -m src.batch.scheduler --una-vez
  ```

### 7.4 Monitoreo y Diagnostico
- Inspeccionar logs en vivo de la API: `docker compose logs -f serving-api`
- Inspeccionar logs del consumidor: `docker compose logs -f ingesta-worker`
- Verificar particiones Parquet generadas en `datos/limpio` y `datos/modelado`.

### 7.5 Mapeo a Infraestructura en AWS (Estimacion de Costos)
- **Computo:** 2 instancias EC2 `c7g.medium` (Graviton, 1 vCPU, 2 GB RAM) para Speed y API (USD 26.50/mes cada una; `c7g.xlarge` USD 106.00 a 10x volumen). 1 instancia `t4g.small` para orquestador Batch (USD 12.25/mes).
- **Almacenamiento:** Amazon S3 Standard + S3 Standard-IA con politicas de transicion de ciclo de vida para Parquet y retencion diferenciada (USD 32.00/mes actual; USD 145.00/mes a 10x).
- **Red y Balanceo:** Application Load Balancer (USD 22.50) + CloudWatch (USD 20.00).
- **Costo Total Estimado AWS:** **USD 154.75/mes** (consumiendo unicamente el 7% del presupuesto tope de USD 2,200/mes).

---

## 8. Conceptos Transversales

### 8.1 Seguridad y Privacidad de Datos
- Las columnas `ip`, `dispositivo_id` y `email_contacto` son estrictamente segregadas.
- En la Serving Layer, las consultas analiticas operan sobre vistas agregadas que excluyen identifiers personales.
- Unicamente las rutinas de calidad de trafico y deteccion de fraude tienen acceso a `ip` y `dispositivo_id`.

### 8.2 Manejo del Tiempo y Zonas Horarias
- Todos los eventos se registran con `ts` en segundos Unix (UTC).
- Los calculos analiticos convierten explicitamente a hora local de Centroamerica (**UTC-6**).
- Las ventanas deslizantes se evaluan con base en el timestamp del evento (`ts`), asegurando determinismo incluso durante el modo de relleno (*backfill*).

### 8.3 Idempotencia y Recomputacion Batch
- Las ejecuciones batch son estrictamente idempotentes: procesar dos veces el mismo lote o dia sobreescribe deterministicamente la particion correspondiente sin duplicar filas ni conteos.

---

## 9. Decisiones de Arquitectura (ADRs Consolidadas)

### 9.1 ADR-001: Seleccion de Plataforma de Infraestructura
- **Decision:** Uso de arquitectura contenerizada portable basada en Docker Compose para el entorno local de desarrollo y pruebas, con un mapeo formal y reproducible hacia servicios gestionados en AWS (EC2 Graviton para computo y S3 para almacenamiento de objetos).
- **Justificacion:** Cumple con la restriccion presupuestaria (< USD 200/mes vs USD 2,200/mes de tope) y evita el costo de administracion de clusters distribuidos pesados (como Kubernetes o EMR), garantizando operabilidad por un equipo reducido.

### 9.2 ADR-002: Motor para la Capa de Velocidad (Speed Layer)
- **Decision:** Implementacion de un motor de streaming ligero y asincrono en Python nativo (`asyncio`) con estructuras de datos en memoria (`collections.deque`), frente a motores distribuidos basados en JVM (como Apache Flink o Spark Streaming).
- **Justificacion:** Permite evaluar eventos individuales con latencias sub-50ms y consumo inferior a 256 MB de RAM. Ademas, comparte exactamente las mismas clases de validacion de contratos y calculo matematico con la Capa Batch, eliminando el problema de la base de codigo dual (*Dual-Codebase Problem*).

### 9.3 ADR-003: Almacenamiento Columnar y Formato Parquet
- **Decision:** Almacenamiento desacoplado en dos capas fisicas: Zona Cruda inmutable particionada por fecha y tipo de evento, y Zona Silver/Gold en formato columnar Apache Parquet comprimido con Snappy, gestionado directamente por DuckDB.
- **Justificacion:** Reduce el espacio en disco en un 70% comparado con CSVs originales, acelera consultas analiticas al leer unicamente las columnas requeridas (proyeccion push-down) y permite retencion diferenciada segun politicas contables (3 anos para clics, 90 dias para impresiones crudas).

### 9.4 ADR-004: Serving Layer y Teorema CAP
- **Decision:** Posicionamiento de la Serving Layer bajo el modelo **AP (Alta Disponibilidad y Tolerancia a Particiones)** con consistencia eventual durante la operacion continua, y consistencia estricta determinista en los cierres contables mensuales ejecutados por la Capa Batch.
- **Justificacion:** Para la atencion telefonica y deteccion de fraude, responder en < 50ms con datos frescos al segundo es prioritario frente a una consistencia lineal inmediata que bloquearia las lecturas.

### 9.5 Justificacion de DuckDB en Pipelines de Datos
- **Decision:** Utilizacion de DuckDB como motor SQL analitico vectorial embebido para todas las transformaciones Medallion (Bronze a Silver y Silver a Gold).
- **Justificacion:** DuckDB opera en el mismo proceso de Python, evitando la latencia de red y serializacion IPC. Es capaz de procesar millones de registros de clics en pocos segundos con uso de memoria restringido (< 2 GB), superando ampliamente en simplicidad y velocidad a clusters Spark para datasets que caben en memoria de un solo nodo.

---

## 10. Requerimientos de Calidad y Escenarios

1. **Escenario de Latencia en Hora Pico:** Con una tasa sostenida de 600 imp/s y 9 clics/s, el 99% de las consultas a la API de atencion a comercios responde en < 100 ms.
2. **Escenario de Deteccion de Fraude:** Si un dispositivo emite mas de 20 clics en una ventana de 60 minutos, la plataforma clasifica el evento como invalido en < 500 ms.
3. **Escenario de Recomputacion Batch:** Ante una corrupcion de vistas precomputadas, la Capa Batch es capaz de reconstruir la historia completa en < 5 minutos a partir de los datos crudos inmutables.

---

## 11. Riesgos y Deuda Tecnica

| Riesgo Identificado | Impacto | Estrategia de Mitigacion |
|---|---|---|
| **Evolucion del esquema a v2** | Alto | El validador de contratos soporta esquemas versionados y desvia cargas desconocidas a cuarentena sin detener el pipeline. |
| **Inyeccion de incidentes anomalos en vivo** | Critico | Las reglas de fraude se evaluan de forma continua en streaming y emiten telemetria en tiempo real a la API. |
| **Desfase de eventos en modo backfill** | Medio | Las ventanas se indexan por el timestamp propio del evento (`ts`) y no por el reloj del sistema. |

---

## 12. Glosario de Terminos

- **CPC (Costo por Clic):** Modelo publicitario donde el anunciante abona unicamente cuando un usuario interactua con el anuncio.
- **Impresion:** Entrega y visualizacion de un anuncio en un soporte digital.
- **Ventana Deslizante (Sliding Window):** Intervalo temporal dinamico indexado por el timestamp de los eventos que evalua los ultimos N minutos de actividad.
- **Cuarentena:** Directorio aislado donde se almacenan eventos que no superan la validacion del contrato formal JSON Schema.
- **Consistencia Eventual:** Garantia de que, en ausencia de nuevas mutaciones, todos los nodos y vistas convergeran al mismo estado.
