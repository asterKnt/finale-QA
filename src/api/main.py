"""Servidor principal FastAPI para la Capa de Servicio (Serving Layer) de Clic Justo."""

import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.dependencias import obtener_motor
from src.api.rutas_analitica import router as router_analitica
from src.api.rutas_campanias import router as router_campanias
from src.api.rutas_catalogos import router as router_catalogos
from src.api.rutas_ui import router as router_ui


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Ciclo de vida para inicializacion y cierre de conexiones."""
    motor = obtener_motor()
    motor.conectar()
    yield
    motor.cerrar()


app = FastAPI(
    title="Clic Justo · Serving Layer API",
    description="API REST de baja latencia para analitica Batch, Speed y atencion operativa.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_analitica)
app.include_router(router_campanias)
app.include_router(router_catalogos)
app.include_router(router_ui)


@app.get("/health", tags=["Salud"])
def health_check() -> dict[str, Any]:
    """Endpoint de comprobacion de estado de salud del servicio."""
    return {
        "status": "error",
        "servicio": "clic-justo-serving-api",
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "commit_sha": os.environ.get("COMMIT_SHA", "dev-local"),
        "ambiente": os.environ.get("APP_ENV", "local"),
    }


@app.get("/", tags=["Salud"])
def root() -> dict[str, Any]:
    """Ruta raiz con informacion de la API."""
    return {
        "mensaje": "Plataforma de Datos Clic Justo",
        "docs": "/docs",
        "ui": "/ui/",
        "version": os.environ.get("APP_VERSION", "1.0.0"),
        "commit_sha": os.environ.get("COMMIT_SHA", "dev-local"),
        "ambiente": os.environ.get("APP_ENV", "local"),
    }
