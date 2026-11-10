"""Rutas de la interfaz web para visualizacion y pruebas End-to-End."""

import os
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/ui", tags=["Interfaz Web"])

DIR_TEMPLATES = Path(__file__).parent / "templates"


@router.get("", response_class=HTMLResponse, summary="Panel de Control Principal (Dashboard)")
@router.get("/", response_class=HTMLResponse, summary="Panel de Control Principal (Dashboard)")
def render_dashboard() -> HTMLResponse:
    """Entrega la pantalla principal del Dashboard con metricas de salud del sistema."""
    plantilla = (DIR_TEMPLATES / "dashboard.html").read_text(encoding="utf-8")
    ambiente = os.environ.get("APP_ENV", "local")
    commit_sha = os.environ.get("COMMIT_SHA", "dev-local")

    contenido = plantilla.replace("{{ AMBIENTE }}", ambiente).replace("{{ COMMIT_SHA }}", commit_sha)
    return HTMLResponse(content=contenido, status_code=200)


@router.get("/campanias", response_class=HTMLResponse, summary="Inspeccion de Campañas y Semaforo")
def render_campanias() -> HTMLResponse:
    """Entrega la pantalla de inspeccion de campanias y semaforo de accion."""
    contenido = (DIR_TEMPLATES / "campanias.html").read_text(encoding="utf-8")
    return HTMLResponse(content=contenido, status_code=200)


@router.get("/analitica", response_class=HTMLResponse, summary="Explorador Analitico Gold")
def render_analitica() -> HTMLResponse:
    """Entrega la pantalla del explorador analitico de consultas P1, P2 y P3."""
    contenido = (DIR_TEMPLATES / "analitica.html").read_text(encoding="utf-8")
    return HTMLResponse(content=contenido, status_code=200)
