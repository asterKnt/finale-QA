"""Configuracion de fixtures para pruebas End-to-End con Playwright."""

import os
import subprocess
import time
import urllib.request
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session")
def live_server_url() -> Generator[str]:
    """Provee la URL base de la Serving API para pruebas End-to-End.

    Si detecta un servidor activo en el puerto 8000 (como en GitHub Actions), lo reutiliza.
    De lo contrario, inicia dinamicamente una instancia ligera en el puerto 8888.
    """
    puerto_ci = 8000
    url_ci = f"http://127.0.0.1:{puerto_ci}"
    try:
        with urllib.request.urlopen(f"{url_ci}/health", timeout=1) as resp:
            if resp.status == 200:
                yield url_ci
                return
    except Exception:
        pass

    puerto_local = 8888
    url_local = f"http://127.0.0.1:{puerto_local}"
    env = os.environ.copy()
    env["APP_ENV"] = "staging"
    env["COMMIT_SHA"] = "test-e2e-local"

    proceso = subprocess.Popen(
        ["uv", "run", "uvicorn", "src.api.main:app", "--host", "127.0.0.1", "--port", str(puerto_local)],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    servidor_listo = False
    for _ in range(30):
        try:
            with urllib.request.urlopen(f"{url_local}/health", timeout=1) as resp:
                if resp.status == 200:
                    servidor_listo = True
                    break
        except Exception:
            time.sleep(0.2)

    if not servidor_listo:
        proceso.terminate()
        raise RuntimeError("No fue posible inicializar el servidor FastAPI local para pruebas E2E.")

    yield url_local

    proceso.terminate()
    try:
        proceso.wait(timeout=5)
    except Exception:
        proceso.kill()
