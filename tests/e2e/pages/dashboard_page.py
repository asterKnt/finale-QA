"""Page Object para la Pantalla 1: Dashboard de Monitoreo y Operaciones."""

from playwright.sync_api import Page, Response

from tests.e2e.pages.base_page import BasePage


class DashboardPage(BasePage):
    """Encapsula selectores y acciones de la pantalla principal del Dashboard.

    Cumple con SRP al limitarse al dominio del Dashboard.
    """

    RUTA = "/ui/"

    # Selectores
    SELECTOR_BADGE_HEALTH = "#badge-health"
    SELECTOR_VAL_SALUD = "#val-salud"
    SELECTOR_CARD_INGESTA = "#card-ingesta"
    SELECTOR_CARD_PROCESAMIENTO = "#card-procesamiento"
    SELECTOR_ENV_BADGE = "#env-badge"
    SELECTOR_COMMIT_BADGE = "#commit-badge"
    SELECTOR_NAV_CAMPANIAS = "#nav-campanias"
    SELECTOR_NAV_ANALITICA = "#nav-analitica"
    SELECTOR_BTN_IR_CAMPANIAS = "#btn-ir-campanias"
    SELECTOR_BTN_IR_ANALITICA = "#btn-ir-analitica"

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

    def abrir(self) -> Response | None:
        """Navega a la pantalla del Dashboard."""
        return self.navegar(self.RUTA)

    def obtener_estado_salud(self) -> str:
        """Retorna el texto del badge de salud del sistema."""
        return self.obtener_texto(self.SELECTOR_BADGE_HEALTH)

    def obtener_ambiente(self) -> str:
        """Retorna el ambiente reportado en el pie de pagina."""
        return self.obtener_texto(self.SELECTOR_ENV_BADGE)

    def obtener_commit_sha(self) -> str:
        """Retorna el SHA del commit reportado en el dashboard."""
        return self.obtener_texto(self.SELECTOR_COMMIT_BADGE)

    def navegar_a_campanias(self) -> None:
        """Hace clic en la navegacion hacia la pantalla de campanias."""
        self.hacer_clic(self.SELECTOR_NAV_CAMPANIAS)

    def navegar_a_analitica(self) -> None:
        """Hace clic en la navegacion hacia la pantalla de analitica."""
        self.hacer_clic(self.SELECTOR_NAV_ANALITICA)
