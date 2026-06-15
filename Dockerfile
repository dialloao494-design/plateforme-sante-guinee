# Backend API — production image
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements-prod.txt ./
RUN pip install --upgrade pip && pip install -r requirements-prod.txt

COPY . .

RUN sed -i 's/\r$//' scripts/docker/entrypoint-backend.sh scripts/docker/start-uvicorn.sh \
    && mkdir -p uploads logs \
    && chmod +x scripts/docker/entrypoint-backend.sh scripts/docker/start-uvicorn.sh

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health/ready || exit 1

ENTRYPOINT ["/app/scripts/docker/entrypoint-backend.sh"]
CMD ["/app/scripts/docker/start-uvicorn.sh"]
