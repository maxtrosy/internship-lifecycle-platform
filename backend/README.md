# Backend DH-05 — Fase 1 (cimientos transversales)

API en FastAPI + PostgreSQL (psycopg 3, SQL explícito, sin ORM). Monolito modular según ADR-002.

## Requisitos
- Python **3.12** (no hay wheel de `pgserver` para 3.14).
- Docker (para `docker compose up`) **o** una instancia local de PostgreSQL 16.

## Instalar dependencias (Windows, PowerShell)
Las dependencias quedan en `.deps/` (fuera de git):

```powershell
cd backend
python -m pip install --target .deps -e .[dev]
$env:PYTHONPATH=(Resolve-Path .deps).Path
```

## Levantar con Docker Compose

```powershell
docker compose up --build
```

`GET http://localhost:8000/health` responde `{"status":"ok"}`. La migración `0001` corre al iniciar el contenedor `api`.

## Migraciones y datos sintéticos (sin Docker)
Con `DATABASE_URL` apuntando a tu PostgreSQL:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/postgres"
$env:PYTHONPATH=(Resolve-Path .deps).Path
python -m alembic upgrade head
python -m app.seed
```

## API local

```powershell
$env:PYTHONPATH=(Resolve-Path .deps).Path
python -m uvicorn app.main:app --reload
```

## Pruebas
Las pruebas usan `pgserver` (Python 3.12) si no hay `DATABASE_URL`, o el PostgreSQL indicado:

```powershell
$env:PYTHONPATH=(Resolve-Path .deps).Path
python -m pytest
```

Los resultados funcionales están **NOT EXECUTED** en esta entrega (el sandbox no levanta PostgreSQL); el equipo debe correr `pytest`.
