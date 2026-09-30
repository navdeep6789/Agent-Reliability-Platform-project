FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY packages/schemas /app/packages/schemas
COPY packages/sdk-python /app/packages/sdk-python
COPY apps/api /app/apps/api
COPY evaluations /app/evaluations
COPY demo /app/demo

RUN pip install --no-cache-dir \
    fastapi \
    uvicorn \
    pydantic \
    pydantic-settings \
    SQLAlchemy \
    psycopg2-binary \
    duckdb \
    opentelemetry-api \
    opentelemetry-sdk \
    opentelemetry-proto \
    requests \
    httpx

RUN pip install --no-cache-dir -e /app/packages/schemas -e /app/packages/sdk-python

ENV PYTHONPATH="/app/apps/api:/app"
WORKDIR /app/apps/api

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
