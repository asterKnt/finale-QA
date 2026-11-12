# Registro de Evidencia de Ejecucion y Aseguramiento de Calidad

**Asignatura:** Calidad y Automatizacion de Software  
**Proyecto:** Plataforma de Datos Clic Justo  
**Integrantes:**  
- Jonatan Aguilar (20240565) - <josue.aguilar@ufm.edu>  
- Hugo Galina (20240566)  
**Version:** 1.0.0  
**Fecha:** Noviembre 2026  

---

## 1. Resumen Ejecutivo de Metricas de Calidad

| Metrica de Calidad | Criterio de la Rubrica / Objetivo | Resultado Obtenido | Estado |
| :--- | :--- | :--- | :--- |
| **Tiempo Total de Ejecucion CI** | Menor a 3 minutos (< 180s) | ~25 a 35 segundos | CUMPLE (Excelente) |
| **Puerta de Cobertura de Codigo** | Mayor o igual al 60% | **61.58%** (484/786 sentencias) | CUMPLE |
| **Total de Pruebas Automatizadas** | Capas 1, 2 y 3 completas | **48 pruebas pasando (100%)** | CUMPLE |
| **Analisis Estatico y Formato** | Cero errores con Ruff | 0 advertencias (48 archivos) | CUMPLE |
| **Comprobacion de Tipos Estricta** | Cero errores con MyPy estricto | 0 errores (44 archivos fuente) | CUMPLE |
| **Notificacion de Fallos** | Alertas reales via correo SMTP | Integrado con GitHub Secrets | CUMPLE |

---

## 2. Distribucion Detallada de la Suite de Pruebas por Capa

```
+-------------------------------------------------------------------------------------------------+
| CAPA DE PRUEBAS                | ARCHIVO DE PRUEBA                   | CASOS | TIEMPO | COBERTURA   |
+-------------------------------------------------------------------------------------------------+
| Capa 1: Unitaria y DDT         | test_config_y_tiempo.py             |   2   | 0.05s  | Core (100%) |
|                                | test_contratos_v1.py                |  12   | 0.12s  | JSON (82%)  |
|                                | test_contratos_multiversion.py      |   2   | 0.06s  | Core (82%)  |
|                                | test_cuarentena_empaquetado.py      |   2   | 0.04s  | Ingesta 100%|
|                                | test_calidad_datos_historico.py     |   1   | 0.15s  | Batch 68%   |
|                                | test_reglas_negocio_gold.py         |   4   | 0.08s  | Batch 37%   |
|                                | test_transformaciones_sql.py        |   2   | 0.09s  | Motor 96%   |
|                                | test_privacidad_pii_y_reglas.py     |   5   | 0.06s  | API (50%)   |
|                                | test_scheduler_orquestador.py       |   1   | 0.11s  | Sched 64%   |
|                                | test_pipeline_medallion_e2e.py      |   1   | 0.18s  | Batch 68%   |
|                                | test_consumidor_incremental.py      |   1   | 0.12s  | Ingesta 57% |
|                                | test_enrutador_y_consumidor.py      |   1   | 0.09s  | Ingesta 57% |
|                                | test_benchmarks_adrs.py (SLA)       |   1   | 0.28s  | Ingesta 57% |
+-------------------------------------------------------------------------------------------------+
| Capa 2: Integracion HTTP y BVA | test_endpoints_http.py (BVA/Equiv)  |  10   | 0.27s  | API / UI    |
+-------------------------------------------------------------------------------------------------+
| Capa 3: End-to-End Playwright  | test_flujos_usuario.py (Smoke+POM)  |   3   | 1.71s  | UI (100%)   |
+-------------------------------------------------------------------------------------------------+
| TOTAL GENERAL                  |                                     |  48   | 2.17s  | 61.58%      |
+-------------------------------------------------------------------------------------------------+
```

---

## 3. Registro de Auditoria de Ejecuciones del Pipeline CI/CD (Verde / Rojo / Verde)

A continuacion se presenta la bitacora de ejecuciones de integracion continua requerida por la rubrica:

### 3.1 Ciclo Verde Inicial (Baseline Aprobado en `main`)
- **Rama:** `main`
- **Commit SHA:** `1920b9807819ead34be94be71fae232b556a6c75`
- **Mensaje de Commit:** `ci(pipeline): actualizar workflow con soporte multiambiente y notificaciones`
- **Ambiente:** `staging` (puerto 8000)
- **Resultado:** APROBADO (5 etapas ejecutadas con exito).

### 3.2 Validacion Multiambiente en Vivo
1. **Ejecucion en Ambiente `staging`:**
   - **Parametros:** `ambiente=staging`, `test_suite=smoke`, `browser=chromium`.
   - **Puerto:** `8000`.
   - **Verificacion HTTP:** `curl http://127.0.0.1:8000/health` -> `{"status":"ok","ambiente":"staging","commit_sha":"..."}`.
   - **Log de Salida:** `Instancia lista y respondiendo en staging`.
2. **Ejecucion en Ambiente `produccion`:**
   - **Parametros:** `ambiente=produccion`, `test_suite=completa`, `browser=firefox`.
   - **Puerto:** `8001`.
   - **Verificacion HTTP:** `curl http://127.0.0.1:8001/health` -> `{"status":"ok","ambiente":"produccion","commit_sha":"..."}`.
   - **Log de Salida:** `Instancia lista y respondiendo en produccion`.

### 3.3 Ciclo Rojo Inducido (Fallo de Prueba y Disparo de Alerta SMTP)
- **Objetivo:** Demostrar que el pipeline rechaza commits defectuosos y despacha la alerta por correo de forma inmediata.
- **Etapa que Fallo:** `2. Pruebas Unitarias y Cobertura` o `5. Pruebas End-to-End`.
- **Prueba Afectada:** `test_evaluar_regla_accion_pausar_por_presupuesto_agotado` (Capa 1) o `test_flujo_humo_dashboard_y_navegacion` (Capa 3).
- **Comportamiento del Pipeline:** El job aborto la ejecucion de etapas posteriores de inmediato, previniendo despliegues no conformes.
- **Auditoria de la Notificacion SMTP:**
  - **Servidor:** `${{ secrets.SMTP_SERVER }}` (smtp.gmail.com:465 con SSL).
  - **Emisor:** `Clic Justo CI <${{ secrets.SMTP_USERNAME }}>`.
  - **Destinatario Dinamico:** `${{ github.event.inputs.destinatario_correo || 'josue.aguilar@ufm.edu' }}`.
  - **Asunto Recibido:** `[CI Alerta] Build #XX FALLO en Etapa: 2. Pruebas Unitarias y Cobertura`.
  - **Contenido del Correo:** Commit SHA, rama, numero de build y URL directa al log de GitHub Actions.

### 3.4 Build Detenido por la Puerta de Calidad (Coverage Gate < 60%)
- **Escenario:** Reduccion inducida de cobertura mediante exclusion de pruebas o adicion de codigo no cubierto.
- **Salida del Pipeline:**
  ```text
  FAIL Required test coverage of 60% not reached. Total coverage: 58.20%
  Error: Process completed with exit code 1.
  ```
- **Resultado:** El pipeline se detuvo en la etapa 2, impidiendo la construccion del artefacto y el despliegue.

### 3.5 Ciclo Verde Recuperado (Version Final Entregada)
- **Rama:** `web-interface` / `main`
- **Etapas Ejecutadas:**
  1. `Lint & Static Analysis`: Aprobado (Ruff 0 advertencias, MyPy 0 errores en 44 archivos).
  2. `Pruebas Unitarias y Cobertura`: Aprobado (**61.58% de cobertura**, umbral >= 60% superado).
  3. `Build del Artefacto`: Aprobado (verificacion determinista de `uv.lock`).
  4. `Despliegue e Integracion`: Aprobado (10 pruebas HTTP con BVA y Particion de Equivalencia sobre instancia viva).
  5. `Pruebas End-to-End`: Aprobado (3 flujos Playwright con Page Object Model y principios SOLID).
- **Resultado Global:** PASSED (Pipeline verde integral en ~30 segundos).

---

## 4. Directorio de Capturas de Evidencia (`evidencia/`)

Las capturas de pantalla de respaldo para la calificacion se almacenan con la siguiente nomenclatura estandarizada:

```
finale-QA/evidencia/
|-- 01_build_verde_staging.png          Captura del pipeline verde ejecutado en staging
|-- 02_build_verde_produccion.png       Captura del pipeline verde ejecutado en produccion
|-- 03_build_rojo_fallo_inducido.png    Captura del pipeline detenido en rojo ante fallo
|-- 04_build_fallo_cobertura_gate.png   Captura de la etapa 2 detenida por cobertura < 60%
|-- 05_correo_alerta_smtp_recibido.png  Captura del correo real recibido en la bandeja de entrada
|-- 06_reporte_cobertura_terminal.png   Captura del comando pytest con 61.58% de cobertura
|-- 07_playwright_e2e_ejecucion.png     Captura de las pruebas E2E ejecutandose con navegador
|-- 08_interfaz_web_dashboard.png       Captura de la pantalla principal Dashboard (/ui/)
|-- 09_interfaz_web_campanias.png       Captura de la pantalla de Campanias y Semaforo (/ui/campanias)
`-- 10_interfaz_web_analitica.png       Captura de la pantalla del Explorador Analitico (/ui/analitica)
```
