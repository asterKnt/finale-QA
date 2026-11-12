# Informe de Decisiones de Arquitectura, Estrategia de Calidad y Principios de Diseno

**Asignatura:** Calidad y Automatizacion de Software  
**Proyecto:** Plataforma de Datos Clic Justo (Serving API & Lambda Architecture)  
**Integrantes:**  
- Jonatan Aguilar (20240565) - <josue.aguilar@ufm.edu>  
- Hugo Galina (20240566)  
**Version:** 1.0.0  
**Fecha:** Noviembre 2026  

---

## 1. Matriz Resumen de Decisiones (Formato Oficial de la Rubrica)

A continuacion se presenta la matriz formal que sintetiza cada decision critica de aseguramiento de calidad, contrastada contra sus alternativas, conceptos teoricos del curso, evidencia verificable en el repositorio y fuentes de estandares de ingenieria de software:

| Decision | Alternativa | Concepto del Curso | Evidencia en el Repositorio | Fuente / Referencia |
| :--- | :--- | :--- | :--- | :--- |
| **Umbral de cobertura global fijado en 60%** como compuerta de calidad estricta en el pipeline CI. | Exigir 80-90% forzando cobertura de scripts de carga masiva CLI o no fijar compuerta automatizada. | **Quality Gate / Shift-Left Testing** | `.github/workflows/ci.yml` (linea 127) y reporte de cobertura `pytest --cov=src` (**61.58%**). | Fowler, M. (*Test Coverage*); ISO/IEC 25010 (*Mantenibilidad y Calidad de Producto*). |
| **Distribucion piramidal de pruebas (3 capas de Cohn):** 35 unitarias/DDT en la base, 10 de integracion HTTP/BVA en el centro y 3 E2E con Playwright en la cuspide. | Antipatron de Cono de Helado (Ice-Cream Cone) con predominio de pruebas visuales fragiles, o solo pruebas unitarias aisladas sin navegador real. | **Piramide de Pruebas (Mike Cohn)** | Carpetas `tests/core/`, `tests/batch/`, `tests/api/` y `tests/e2e/` (Total: 48 pruebas pasando). | Cohn, M. (*Succeeding with Agile*); IEEE 829 (*Standard for Software Test Documentation*). |
| **Orden secuencial y estricto de etapas en el pipeline:** Lint/Tipos -> Unitarias/Cobertura -> Build -> Despliegue/Integracion -> E2E. | Ejecucion en paralelo sin bloqueos o ejecucion de E2E antes del build/despliegue. | **Fail-Fast / Shift-Left** | `.github/workflows/ci.yml` (directivas `needs: [...]` encadenadas entre las 5 etapas). | Humble, J. & Farley, D. (*Continuous Delivery: Reliable Software Releases*). |
| **Parametrizacion flexible via `workflow_dispatch`** para ambiente (`staging`/`produccion`), suite (`smoke`/`completa`), navegador (`chromium`/`firefox`) y destinatario; fijando version de Python (3.14) y lockfile determinista. | Todo cableado en duro (hardcoded) o parametrizacion descontrolada de dependencias en tiempo de ejecucion. | **Config as Code / Pipeline as Code** | Bloque `on.workflow_dispatch.inputs` y variables `env` en `.github/workflows/ci.yml`. | ISO/IEC/IEEE 29119-2 (*Test Processes*); 12-Factor App (*Config*). |
| **Page Object Model (POM) desacoplado aplicando principios SOLID:** Protocolo abstracto `IPage` (DIP), `BasePage` con esperas explicitas de ciclo de vida (SRP), y paginas concretas de dominio (SRP/OCP). | Selectores y esperas dispersos dentro de las funciones de prueba o herencia acoplada fuertemente a Playwright. | **SRP (Single Responsibility) y DIP (Dependency Inversion)** | `tests/e2e/pages/base_page.py`, `dashboard_page.py`, `campaign_page.py`, `analytics_page.py`. | Martin, R. C. (*Clean Architecture / SOLID Design Principles*); Documentacion oficial de Playwright. |
| **Diseno formal de pruebas de caja negra en integracion HTTP:** Particion de equivalencia (validas, 422 malformadas y 404/503) y Analisis de Valores Limite (BVA en -1, 0, 1). | Pruebas exploratorias ad-hoc no documentadas o pruebas de camino feliz exclusivamente. | **Particion de Equivalencia y Analisis de Valores Limite (BVA)** | `tests/api/integration/test_endpoints_http.py` y `tests/api/ddt/test_privacidad_pii_y_reglas_accion.py`. | ISO/IEC/IEEE 29119-4 (*Test Techniques*); Myers, G. (*The Art of Software Testing*). |

---

## 2. Justificacion de la Piramide de Pruebas (Mike Cohn) y Shift-Left Testing

### 2.1 Distribucion de Pruebas en Tres Capas

La estrategia de aseguramiento de calidad del proyecto Clic Justo adopta de forma estricta el modelo de la Piramide de Pruebas propuesto por Mike Cohn, estructurando 48 pruebas automatizadas en tres capas bien diferenciadas:

```
                  / \
                 /   \
                / Capa\          3 Pruebas End-to-End (Playwright)
               /   3   \         Flujos de usuario, navegador real, POM + SOLID
              /---------\
             /   Capa    \       10 Pruebas de Integracion y API (HTTP / DB)
            /     2       \      Serving API, BVA, Particion de Equivalencia, SLA
           /---------------\
          /      Capa       \    35 Pruebas Unitarias y DDT (Contratos y Logica)
         /        1          \   JSON Schema, deduplicacion Silver, reglas Gold
        /---------------------\
```

1. **Capa 1: Base Unitaria y Pruebas Dirigidas por Datos (DDT) - 35 pruebas:**
   - **Objetivo:** Validacion exhaustiva de la logica algoritmica pura, deduplicacion en capa Silver, calculo de baselines de gasto, transformaciones SQL en DuckDB y evolucion multiversion de contratos JSON Schema.
   - **Justificacion:** Son pruebas aisladas, deterministas y de ejecucion ultra-rapida (< 1.5 segundos para la suite completa). Permiten aislar la causa raiz de fallos en fracciones de segundo sin dependencias de red o de navegador.

2. **Capa 2: Integracion y Servicios HTTP (Serving Layer) - 10 pruebas:**
   - **Objetivo:** Comprobacion del comportamiento de la API REST construida sobre FastAPI, verificando codigos de estado HTTP, acuerdos de nivel de servicio (SLA sub-segundo) y tecnicas de caja negra (Particion de Equivalencia y Analisis de Valores Limite - BVA) sobre parametros de ruta y cabeceras.
   - **Justificacion:** Valida la correcta cooperacion entre el motor DuckDB, la inyeccion de dependencias y el protocolo HTTP, asegurando que los contratos expuestos a clientes se cumplan fielmente.

3. **Capa 3: Pruebas End-to-End en Interfaz Web (Playwright) - 3 pruebas:**
   - **Objetivo:** Validacion holistica de flujos de usuario reales en un navegador web (Chromium/Firefox), abarcando desde el Dashboard de monitoreo hasta la consulta operativa de campanias y exploracion de reportes analiticos.
   - **Justificacion:** Ocupa la cupula de la piramide porque, aunque provee la maxima fidelidad respecto a la experiencia del usuario, su costo de mantenimiento y tiempo de ejecucion es mayor. Se mantiene un numero acotado pero critico de flujos representativos (Smoke test, semaforo de accion y ejecucion de queries analiticas).

### 2.2 Filosofia Shift-Left Testing

El proyecto aplica el principio de *Shift-Left*, trasladando la deteccion de anomalias a las fases mas tempranas del ciclo de vida del software:
- **Analisis Estatico y Tipado Estricto:** Comprobacion con Ruff (estilo y formato) y MyPy estricto sobre 44 archivos fuente antes de ejecutar cualquier suite de pruebas.
- **Validacion de Esquemas en Ingesta:** Cualquier evento con estructura corrupta o tipos no conformes es detectado y desviado a la zona de cuarentena antes de ingresar al pipeline Medallion, previniendo fallos en capas Silver y Gold.
- **Puerta de Cobertura en CI:** Ningun cambio puede integrarse si reduce la cobertura por debajo del 60%, evitando la acumulacion de deuda tecnica.

---

## 3. Puerta de Calidad (Quality Gate) y Umbral de Cobertura de Codigo

### 3.1 Justificacion del Umbral del 60%

Se establecio un umbral estricto del **60% de cobertura de sentencias** (`--cov-fail-under=60`) en la etapa de integracion continua. La cobertura actual alcanzada es de **61.58% (484/786 sentencias cubiertas)**.

La seleccion de este umbral responde a un analisis de criticidad de componentes bajo una arquitectura Lambda:
1. **Modulos con Cobertura Alta (80% - 100%):**
   - `src/core/config.py` (100%): Constantes globales y calculo de desfase de tiempo.
   - `src/core/modelos.py` (100%): Modelos de datos Pydantic para Serving API.
   - `src/ingesta/enrutador.py` (100%): Clasificacion y enrutamiento hacia crudo o cuarentena.
   - `src/api/rutas_ui.py` (100%): Entrega de pantallas web HTML y resolucion de variables.
   - `src/api/dependencias.py` (100%): Gestion de conexiones de base de datos.
   - `src/batch/motor.py` (96%): Inicializacion y gestion del pool DuckDB.
   - `src/api/main.py` (86%): Ciclo de vida y endpoints de salud.
   - `src/core/contratos.py` (82%): Validacion determinista de JSON Schema.
2. **Modulos Excluidos o con Cobertura Parcial Justificada:**
   - `src/batch/ejecutar_pipeline.py` (0%): Script wrapper para invocacion manual por CLI que coordina la carga masiva de archivos raw desde disco fisico. En pruebas automatizadas se prueban directamente los orquestadores y transformaciones modulares (`bronze_a_silver.py` y `silver_a_gold.py`) para evitar dependencia de gigabytes de archivos de entrada en el runner de CI.
   - `src/api/rutas_analitica.py` (31%): Rutas analiticas que dependen de tablas preagregadas de gran volumen en almacenamiento columnar persistente.

El umbral del 60% garantiza que el 100% de la logica contractual, de enrutamiento y de atencion operativa este validada, descartando codigo de infraestructura externa.

---

## 4. Diseno del Page Object Model (POM) y Principios SOLID

La suite de pruebas End-to-End implementada en `tests/e2e/` utiliza el patron **Page Object Model (POM)** estructurado conforme a buenas practicas de ingenieria de software:

```
tests/e2e/
|-- conftest.py             Fixture live_server_url con inicio automatico de FastAPI
|-- test_flujos_usuario.py  Pruebas de flujos de usuario (Smoke, Campanias, Analitica)
|-- pages/
    |-- base_page.py        SRP: Primitivas de interaccion | DIP: Protocolo IPage
    |-- dashboard_page.py   SRP: Selectores y acciones de Pantalla 1 (Dashboard)
    |-- campaign_page.py    SRP: Selectores y acciones de Pantalla 2 (Campanias)
    |-- analytics_page.py   SRP: Selectores y acciones de Pantalla 3 (Analitica)
```

### 4.1 Principio de Responsabilidad Unica (Single Responsibility Principle - SRP)

- **`BasePage`:** Tiene la responsabilidad unica de gestionar el ciclo de vida elemental del navegador Playwright: resolucion de rutas con la URL base del servidor, esperas explicitas de visibilidad (`wait_for`), clics sincronizados y extraccion limpia de texto. No contiene ningun selector ni logica de negocio.
- **Page Objects Concretos (`DashboardPage`, `CampaignPage`, `AnalyticsPage`):** Cada clase tiene como unica responsabilidad modelar los selectores y las acciones semanticas de una pantalla especifica. Si la interfaz de campanias cambia, unicamente se modifica `campaign_page.py`, sin afectar al resto de componentes.

### 4.2 Principio de Inversion de Dependencias (Dependency Inversion Principle - DIP)

En `tests/e2e/pages/base_page.py` se definio el protocolo abstracto:

```python
@runtime_checkable
class IPage(Protocol):
    def navegar(self, ruta_relativa: str) -> Response | None: ...
    def obtener_titulo(self) -> str: ...
    def obtener_texto(self, selector: str) -> str: ...
```

Las suites de prueba y las funciones utilitarias dependen de esta abstraccion contractual `IPage` y no de implementaciones acopladas a frameworks especificos, permitiendo sustituir el motor de navegacion sin modificar la estructura de las aserciones.

### 4.3 Principio Abierto/Cerrado (Open/Closed Principle - OCP)

`BasePage` esta cerrada a modificaciones pero abierta a extension. Para anadir una nueva pantalla operativa al sistema, basta con heredar de `BasePage` implementando sus metodos especializados, sin requerir alterar una sola linea del codigo de interaccion base existente.

---

## 5. Parametros Configurables vs Valores Fijos en el Pipeline CI/CD

El pipeline en `.github/workflows/ci.yml` implementa el evento `workflow_dispatch` con una distincion clara entre entradas configurables y politicas fijas:

### 5.1 Parametros Configurables (Flexibilidad de Despliegue y Pruebas)

1. **`ambiente` (`staging` / `produccion`):**
   - *Justificacion:* Permite ejecutar despliegues de validacion en staging (puerto 8000) o simular despliegues controlados hacia produccion (puerto 8001), validando la correlacion de `APP_ENV` y `COMMIT_SHA` via HTTP antes de habilitar el servicio.
2. **`test_suite` (`smoke` / `completa`):**
   - *Justificacion:* Brinda agilidad operativa. En cambios frecuentes de configuracion, la suite `smoke` valida la disponibilidad basica en < 2 segundos, mientras que la suite `completa` ejecuta las 48 pruebas de las 3 capas antes de un merge a main.
3. **`browser` (`chromium` / `firefox`):**
   - *Justificacion:* Facilita la verificacion de compatibilidad cross-browser en la interfaz web de monitoreo segun los estandares de soporte institucional.
4. **`destinatario_correo` (Texto, por defecto: `josue.aguilar@ufm.edu`):**
   - *Justificacion:* Permite redirigir alertas criticas de compilacion o fallo de pruebas a la persona de guardia o al evaluador academico.

### 5.2 Valores Fijos (Determinismo y Reproducibilidad)

1. **Version de Python (`3.14`):** Fija para asegurar paridad estricta entre el entorno local de desarrollo y los ejecutores de GitHub Actions.
2. **Gestor de Entorno (`uv` con `--frozen`):** Impide discrepancias en las versiones transitivas de dependencias mediante la validacion obligatoria de `uv.lock`.
3. **Limite de Tiempo de Ejecucion (`timeout-minutes: 5` por etapa):** Protege contra bloqueos o procesos zombi consumiendo recursos en la nube.
4. **Puerta de Cobertura (`--cov-fail-under=60`):** Criterio inmutable de aprobacion de calidad que no puede relajarse manualmente.

---

## 6. Referencias a Estandares Internacionales y Modelos de Calidad

El diseno e implementacion del marco de pruebas de Clic Justo se fundamenta en estandares reconocidos por la industria y la academia:

1. **IEEE 829 (Standard for Software Test Documentation):**
   - La organizacion modular de pruebas unitarias, de integracion y de sistema sigue la jerarquia formal de documentacion de casos de prueba y reportes de ejecucion definida por este estandar.
2. **ISO/IEC/IEEE 29119 (Software Testing):**
   - Se adoptaron formalmente las tecnicas de diseno de pruebas de caja negra descritas en la parte 4 del estandar:
     - **Particion de Equivalencia:** Evaluacion de clases validas (rutas HTTP existentes) y clases invalidas (IDs inexistentes HTTP 404/503 y cadenas no numericas HTTP 422).
     - **Analisis de Valores Limite (BVA):** Evaluacion en frontera de identificadores numericos (-1, 0, 1) y umbrales de presupuesto ($50.00, $49.99, $50.01).
     - **Tabla de Decision:** Matriz de condiciones operacionales (presupuesto agotado, clics de dispositivos invalidos > 30%, pico de gasto >= 3x) mapeadas a las acciones sugeridas (`normal`, `revisar`, `pausar`).
3. **ISO/IEC 25010 (Systems and Software Quality Requirements and Evaluation - SQuaRE):**
   - Se priorizaron las caracteristicas de calidad de:
     - **Adecuacion Funcional:** Cumplimiento exacto de los contratos de esquema JSON y reglas de negocio.
     - **Eficiencia de Desempeno:** Verificacion de SLA sub-segundo en ingesta asincrona (validado en `test_benchmarks_adrs.py`).
     - **Mantenibilidad:** Separacion de responsabilidades en Page Objects y bajo acoplamiento arquitectonico.

---

## 7. Analisis Critico de Sugerencias de Asistentes de IA

Durante el desarrollo de la infraestructura de QA y la interfaz web, se evaluaron criticamente tres propuestas generadas por asistentes de inteligencia artificial:

### Sugerencia 1: Incorporar una cadena de herramientas de Node.js (React/Vite y Tailwind CSS) para la interfaz web
- **Propuesta de la IA:** Instalar Node.js, `npm`, React y Tailwind en el repositorio para renderizar una SPA (Single Page Application) moderna.
- **Evaluacion Critica:** Rechazada.
- **Justificacion Tecnica:** Introducir una pila completa de Node.js en un proyecto cuyo backend y herramientas de prueba estan 100% basados en Python (`uv`, FastAPI, Pytest) habria duplicado la complejidad del pipeline de CI/CD, aumentando el tiempo de construccion de 20 segundos a mas de 3 minutos debido a la descarga de paquetes `node_modules`. En su lugar, se implementaron plantillas HTML5 semanticas con CSS moderno embebido y vanilla JavaScript servidas directamente desde FastAPI. Esta solucion elimino dependencias externas de CDN o NPM, opero a velocidad de milisegundos y permitio que Playwright ejecutara las pruebas E2E en menos de 2 segundos.
- **Evidencia / Respaldo:** `src/api/rutas_ui.py` y `src/api/templates/`.

### Sugerencia 2: Simular completamente (Mock total) las peticiones HTTP y el motor DuckDB en las pruebas End-to-End
- **Propuesta de la IA:** Emplear `unittest.mock` para interceptar todas las llamadas de red y el comportamiento del servidor, evitando levantar una instancia real de FastAPI.
- **Evaluacion Critica:** Rechazada.
- **Justificacion Tecnica:** Aplicar mocking total en la Capa 3 desvirtua el principio fundamental de la piramide de Cohn, convirtiendo pruebas que deben ser de sistema en pruebas unitarias disfrazadas. Si el servidor real no se levanta, no se validan fallos de enlace de sockets, problemas de CORS, cabeceras HTTP reales o discrepancias en la resolucion del ciclo de vida de la aplicacion (`lifespan`). Se opto por disenar un fixture en `conftest.py` que inicia un subproceso real de Uvicorn en background solo cuando no detecta una instancia viva, garantizando que Playwright interactue contra un servidor HTTP autentico.
- **Evidencia / Respaldo:** `tests/e2e/conftest.py` y `tests/e2e/test_flujos_usuario.py`.

### Sugerencia 3: Implementar un Protocolo Abstracto `IPage` (DIP) y aislar las primitivas de Playwright en `BasePage`
- **Propuesta de la IA:** Aplicar principios SOLID en el diseno del Page Object Model mediante una interfaz protocolar y una clase base que encapsule las esperas explicitas de Playwright.
- **Evaluacion Critica:** Aceptada.
- **Justificacion Tecnica:** En pruebas E2E con navegadores reales, el mayor causante de pruebas intermitentes (flaky tests) son los tiempos de sincronizacion ciegos (`time.sleep`). Centralizar las esperas explicitas basadas en visibilidad y estado de Playwright dentro de `BasePage` elimino cualquier condicion de carrera en la ejecucion. Ademas, definir el protocolo `IPage` asegura que la arquitectura de pruebas permanezca desacoplada y cumpla con los requerimientos academicos de diseno de software.
- **Evidencia / Respaldo:** `tests/e2e/pages/base_page.py`.
