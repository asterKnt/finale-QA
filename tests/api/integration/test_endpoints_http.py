"""Pruebas de integracion HTTP sobre los endpoints de la API Serving Layer en FastAPI.

Capa 2 de la piramide de Cohn (Pruebas de Integracion y API).
Aplica formalmente tecnicas de caja negra (Black-Box Testing):
1. Particion de Equivalencia (Equivalence Partitioning):
   - Clase Valida: rutas operativas existentes (/health, /, /ui/, /ui/campanias, /ui/analitica) -> HTTP 200.
   - Clase Invalida (No Encontrado): IDs de campana inexistentes en el almacenamiento -> HTTP 404/503.
   - Clase Invalida (Tipo de Dato / Malformado): identificadores no enteros -> HTTP 422 Unprocessable Entity.
2. Analisis de Valores Limite (Boundary Value Analysis - BVA):
   - Valores frontera sobre parametros de ruta (campania_id = 0, negativo -1, minimo positivo 1).
"""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


def test_endpoint_health_check() -> None:
    """Verifica que el endpoint /health responda HTTP 200 con el estado del servicio."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "servicio" in data


def test_endpoint_raiz() -> None:
    """Verifica que la ruta raiz / entregue informacion general de la API."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "mensaje" in data
    assert data["version"] == "1.0.0"


def test_endpoint_campania_resumen_no_encontrada() -> None:
    """Particion de Equivalencia - Clase Invalida (ID inexistente):

    Verifica respuesta HTTP 404 o 503 adecuada al consultar una campana no registrada.
    """
    response = client.get("/api/v1/campanias/999999/resumen")
    assert response.status_code in (404, 503)


def test_particion_equivalencia_id_malformado_tipo_dato() -> None:
    """Particion de Equivalencia - Clase Invalida (Tipo no entero):

    Verifica que cadenas alfanumericas en campania_id disparen validacion de esquema HTTP 422.
    """
    response = client.get("/api/v1/campanias/invalido_str/resumen")
    assert response.status_code == 422
    assert "detail" in response.json()


@pytest.mark.parametrize("ruta", ["/ui/", "/ui/campanias", "/ui/analitica"])
def test_particion_equivalencia_rutas_interfaz_web_validas(ruta: str) -> None:
    """Particion de Equivalencia - Clase Valida:

    Verifica que las rutas de la interfaz web HTML entreguen HTTP 200 con cabecera text/html.
    """
    response = client.get(ruta)
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.parametrize("campania_id_frontera", [0, -1, 1])
def test_analisis_valores_limite_campania_id_frontera(campania_id_frontera: int) -> None:
    """Analisis de Valores Limite (BVA):

    Evalua los bordes de campania_id (cero, negativo y primer entero positivo).
    """
    response = client.get(f"/api/v1/campanias/{campania_id_frontera}/resumen")
    # Para 0 y -1 no existen registros validos, retornando 404 o 503 segun estado dimensional
    assert response.status_code in (200, 404, 503)
