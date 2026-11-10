"""Page Object para la Pantalla 2: Inspeccion de Campanias y Semaforo de Accion."""

from playwright.sync_api import Page, Response

from tests.e2e.pages.base_page import BasePage


class CampaignPage(BasePage):
    """Encapsula selectores y comportamiento de la pantalla de campanias y semaforo.

    Cumple con SRP al limitarse exclusivamente al dominio de campanias.
    """

    RUTA = "/ui/campanias"

    SELECTOR_INPUT_ID = "#input-campania-id"
    SELECTOR_BTN_CONSULTAR = "#btn-consultar"
    SELECTOR_VAL_ID = "#val-campania-id"
    SELECTOR_VAL_PRESUPUESTO = "#val-presupuesto"
    SELECTOR_VAL_GASTO_HOY = "#val-gasto-hoy"
    SELECTOR_VAL_GASTO_HORA = "#val-gasto-hora"
    SELECTOR_VAL_PCT_INVALIDOS = "#val-pct-invalidos"
    SELECTOR_BADGE_ACCION = "#badge-accion"

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

    def abrir(self) -> Response | None:
        """Navega a la pantalla de campanias."""
        return self.navegar(self.RUTA)

    def consultar_campania(self, campania_id: int) -> None:
        """Ingresa el ID de la campania y presiona el boton de consulta."""
        self.escribir(self.SELECTOR_INPUT_ID, str(campania_id))
        self.hacer_clic(self.SELECTOR_BTN_CONSULTAR)

    def obtener_campania_mostrada(self) -> str:
        """Retorna el ID de campania reflejado en el encabezado del resultado."""
        return self.obtener_texto(self.SELECTOR_VAL_ID)

    def obtener_presupuesto(self) -> str:
        """Retorna el texto del presupuesto diario."""
        return self.obtener_texto(self.SELECTOR_VAL_PRESUPUESTO)

    def obtener_gasto_hoy(self) -> str:
        """Retorna el texto del gasto acumulado de hoy."""
        return self.obtener_texto(self.SELECTOR_VAL_GASTO_HOY)

    def obtener_accion_sugerida(self) -> str:
        """Retorna la accion del semaforo (normal, revisar o pausar)."""
        return self.obtener_texto(self.SELECTOR_BADGE_ACCION)
