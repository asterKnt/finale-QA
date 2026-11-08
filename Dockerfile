FROM python:3.14-slim

# Copiar binario oficial de uv para instalacion determinista y veloz
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# Copiar archivos de definicion de dependencias (optimiza cache de capas Docker)
COPY pyproject.toml uv.lock ./

# Instalar dependencias de produccion congeladas
RUN uv sync --frozen --no-dev

# Copiar codigo fuente, contratos y consultas SQL
COPY src/ src/
COPY contratos/ contratos/
COPY consultas/ consultas/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uv", "run", "--no-sync", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
