"""Pruebas End-to-End (E2E) con Playwright y patron Page Object Model (POM).

Capa 3 de la piramide de Cohn.
Verifica flujos criticos de usuario a traves de la interfaz web:
- Flujo 1 (Smoke test): Carga del Dashboard, verificacion de salud y navegacion basica.
- Flujo 2: Inspeccion operativa de campanias y evaluacion del semaforo de accion.
- Flujo 3: Ejecucion de consultas analiticas P1 y P2 en el explorador Gold.
"""

import pytest
from playwright.sync_api import Page

from tests.e2e.pages.analytics_page import AnalyticsPage
from tests.e2e.pages.campaign_page import CampaignPage
from tests.e2e.pages.dashboard_page import DashboardPage


@pytest.mark.smoke
def test_flujo_humo_dashboard_y_navegacion(page: Page, live_server_url: str) -> None:
    """Smoke Test: valida la carga del dashboard, estado de salud y enlaces operativos."""
    dashboard = DashboardPage(page, live_server_url)
    dashboard.abrir()

    # Validar titulo del documento y estado de salud
    assert "Clic Justo" in dashboard.obtener_titulo()
    assert dashboard.obtener_estado_salud() == "OPERACIONAL"

    # Validar que los identificadores de despliegue esten presentes
    ambiente = dashboard.obtener_ambiente()
    assert len(ambiente) > 0

    # Validar navegacion hacia el modulo de campanias
    dashboard.navegar_a_campanias()
    assert "/ui/campanias" in page.url


def test_flujo_inspeccion_campania_y_semaforo_accion(page: Page, live_server_url: str) -> None:
    """Valida la consulta operativa de campanias y actualizacion del semaforo de accion."""
    campanias = CampaignPage(page, live_server_url)
    campanias.abrir()

    # 1. Consultar campania estandar 8596 (estado normal)
    campanias.consultar_campania(8596)
    assert campanias.obtener_campania_mostrada() == "8596"
    assert "$50.00" in campanias.obtener_presupuesto()
    assert campanias.obtener_accion_sugerida() == "normal"

    # 2. Consultar campania 1001 con presupuesto agotado (estado pausar)
    campanias.consultar_campania(1001)
    assert campanias.obtener_campania_mostrada() == "1001"
    assert campanias.obtener_accion_sugerida() == "pausar"


def test_flujo_explorador_analitica_gold(page: Page, live_server_url: str) -> None:
    """Valida la ejecucion de consultas analiticas P1 y P2 y renderizado tabular."""
    analitica = AnalyticsPage(page, live_server_url)
    analitica.abrir()

    # 1. Ejecutar consulta P1 (Top dominios)
    analitica.ejecutar_consulta("P1")
    assert "5 filas" in analitica.obtener_resumen_filas()
    assert analitica.contar_filas_tabla() == 5

    # 2. Ejecutar consulta P2 (Horas pico de sospecha)
    analitica.ejecutar_consulta("P2")
    assert "5 filas" in analitica.obtener_resumen_filas()
    assert analitica.contar_filas_tabla() == 5
