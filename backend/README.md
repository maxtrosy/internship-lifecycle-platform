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
Las pruebas locales usan `pgserver` (Python 3.12) cuando no hay `DATABASE_URL`. Para la corrida
reproducible en contenedor, usa el Compose separado de pruebas: solo acepta `host=db`, puerto
`5432` y base `dh05_http_test`, sin volumen persistente. La suite limpia esa base con `TRUNCATE`
antes de cada prueba; rechaza URLs locales, externas, de demo o con otro nombre aunque incluyan
la palabra `test`.

```powershell
$env:PYTHONPATH=(Resolve-Path .deps).Path
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python -m pytest -q
```

En Docker: `docker compose -p dh05-tests -f docker-compose.test.yml run --build --rm tests`;
después, retira el contenedor/base efímera con `docker compose -p dh05-tests -f docker-compose.test.yml down --volumes --remove-orphans`.

Python 3.12 es requerido. En el equipo auditado, el Python local es 3.14 y las extensiones de
`.deps` son para CPython 3.12; la suite se ejecutó en un contenedor Python 3.12 con una base
temporal `dh05_release_test`. El resultado final de esta auditoría está en
[`docs/evaluation-2/final-readiness-audit.md`](../docs/evaluation-2/final-readiness-audit.md).
