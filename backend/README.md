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
Las pruebas usan `pgserver` (Python 3.12) si no hay `DATABASE_URL`. Si se configura una URL,
el nombre de la base debe identificarla como base de pruebas (`*_test`, `*_tests`, `test_*` o
equivalente); la suite limpia sus tablas con `TRUNCATE` antes de cada prueba y rechaza nombres
ambiguos como `postgres` o `dh05_demo` para evitar borrar datos compartidos.

```powershell
$env:PYTHONPATH=(Resolve-Path .deps).Path
python -m pytest -q
```

Python 3.12 es requerido. En el equipo auditado, el Python local es 3.14 y las extensiones de
`.deps` son para CPython 3.12; la suite se ejecutó en un contenedor Python 3.12 con una base
temporal `dh05_release_test`. El resultado final de esta auditoría está en
[`docs/evaluation-2/final-readiness-audit.md`](../docs/evaluation-2/final-readiness-audit.md).
