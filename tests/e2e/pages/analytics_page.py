"""Page Object para la Pantalla 3: Explorador Analitico Gold."""

from playwright.sync_api import Page, Response

from tests.e2e.pages.base_page import BasePage


class AnalyticsPage(BasePage):
    """Encapsula selectores y acciones para el explorador de consultas analiticas.

    Cumple con SRP al modularizar las interacciones analiticas.
    """

    RUTA = "/ui/analitica"

    SELECTOR_SELECT_QUERY = "#select-query"
    SELECTOR_BTN_EJECUTAR = "#btn-ejecutar"
    SELECTOR_TOTAL_FILAS = "#val-total-filas"
    SELECTOR_TABLA = "#tabla-resultados"
    SELECTOR_FILAS_CUERPO = "#tabla-cuerpo tr"

    def __init__(self, page: Page, base_url: str) -> None:
        super().__init__(page, base_url)

    def abrir(self) -> Response | None:
        """Navega a la pantalla de analitica."""
        return self.navegar(self.RUTA)

    def ejecutar_consulta(self, tipo_query: str) -> None:
        """Selecciona el tipo de consulta analitica (P1, P2 o P3) y presiona ejecutar."""
        self.seleccionar_opcion(self.SELECTOR_SELECT_QUERY, tipo_query)
        self.hacer_clic(self.SELECTOR_BTN_EJECUTAR)

    def obtener_resumen_filas(self) -> str:
        """Retorna el contador textual de filas devueltas."""
        return self.obtener_texto(self.SELECTOR_TOTAL_FILAS)

    def contar_filas_tabla(self) -> int:
        """Retorna el numero de elementos <tr> renderizados en el cuerpo de la tabla."""
        return self.localizar(self.SELECTOR_FILAS_CUERPO).count()
