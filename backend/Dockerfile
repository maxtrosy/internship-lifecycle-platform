FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml alembic.ini ./
COPY migrations ./migrations
COPY app ./app

RUN pip install --no-cache-dir .

EXPOSE 8000

# Migrations and the API run against DATABASE_URL provided by docker-compose.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
