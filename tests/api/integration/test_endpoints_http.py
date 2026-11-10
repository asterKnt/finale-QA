"""Pruebas de integracion HTTP sobre los endpoints de la API Serving Layer en FastAPI."""

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
    """Verifica respuesta HTTP 404/503 adecuada al consultar una campana inexistente o sin datos."""
    response = client.get("/api/v1/campanias/999999/resumen")
    # Retorna 503 si las tablas dimensionales no existen o 404 si la campana no esta registrada
    assert response.status_code in (404, 503)
