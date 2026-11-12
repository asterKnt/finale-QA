"""Clase base para el patron Page Object Model (POM).

Aplica principios SOLID:
- SRP (Single Responsibility Principle): Centraliza la interaccion elemental con Playwright
  (navegacion, esperas explicitas, busqueda de selectores y obtencion de texto).
- DIP (Dependency Inversion Principle): Expone la interfaz abstracta IPage para desacoplar
  las aserciones y consumidores de la implementacion concreta de navegacion.
"""

from typing import Protocol, runtime_checkable

from playwright.sync_api import Locator, Page, Response


@runtime_checkable
class IPage(Protocol):
    """Protocolo abstracto que define el contrato de cualquier pagina en el sistema."""

    def navegar(self, ruta_relativa: str) -> Response | None:
        """Navega a la ruta indicada respecto a la URL base."""
        ...

    def obtener_titulo(self) -> str:
        """Retorna el titulo de la pagina."""
        ...

    def obtener_texto(self, selector: str) -> str:
        """Obtiene el texto de un elemento indicado por su selector CSS."""
        ...


class BasePage:
    """Implementacion base reutilizable para todos los Page Objects del sistema.

    Cumple con SRP al encapsular unicamente el manejo del ciclo de vida del navegador,
    resolucion de rutas y esperas explicitas.
    """

    def __init__(self, page: Page, base_url: str) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def navegar(self, ruta_relativa: str) -> Response | None:
        """Navega a la ruta especificada resolviendo contra la base_url del servidor."""
        url_completa = f"{self.base_url}{ruta_relativa}"
        return self.page.goto(url_completa, wait_until="domcontentloaded")

    def obtener_titulo(self) -> str:
        """Retorna el titulo del documento HTML."""
        return self.page.title()

    def localizar(self, selector: str) -> Locator:
        """Retorna el localizador de Playwright para un selector especifico."""
        return self.page.locator(selector)

    def obtener_texto(self, selector: str) -> str:
        """Espera a que el elemento sea visible y extrae su texto limpio."""
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=5000)
        return (locator.text_content() or "").strip()

    def hacer_clic(self, selector: str) -> None:
        """Espera a que un elemento sea interactivo y ejecuta el clic."""
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=5000)
        locator.click()

    def escribir(self, selector: str, valor: str) -> None:
        """Limpia el campo y escribe el valor indicado."""
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=5000)
        locator.fill(valor)

    def seleccionar_opcion(self, selector: str, valor: str) -> None:
        """Selecciona una opcion en un elemento <select>."""
        locator = self.page.locator(selector)
        locator.wait_for(state="visible", timeout=5000)
        locator.select_option(value=valor)

    def esperar_selector(self, selector: str, estado: str = "visible") -> None:
        """Espera explicitamente a que un selector alcance el estado deseado."""
        self.page.locator(selector).wait_for(state=estado, timeout=5000)  # type: ignore[arg-type]
