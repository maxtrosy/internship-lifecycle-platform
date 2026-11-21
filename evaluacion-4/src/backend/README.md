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

## Autoridades institucionales configurables

No se infieren responsables de aprobación a partir del nombre de un rol. Estas variables aceptan los roles internos admitidos y, si se omiten, no conceden la mutación correspondiente:

```text
OPPORTUNITY_REVIEWER_ROLES=
OPPORTUNITY_PUBLISHER_ROLES=
PLACEMENT_FACULTY_ASSIGNER_ROLES=
```

Las dos primeras controlan, respectivamente, la aprobación para publicar y la publicación de oportunidades (`OPEN-05`). La tercera habilita asignación/reasignación docente dentro del programa o ámbito autorizado. El harness E2E asigna valores temporales exclusivamente en su instancia PostgreSQL desechable. Debe existir una decisión institucional y configuración de despliegue antes de habilitarlas en producción.

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

La imagen Compose también es aislada y no monta volúmenes. Si se usa, conserva el nombre de proyecto `dh05-tests` para no mezclar recursos con desarrollo; no hace falta eliminar volúmenes. En esta validación Docker Engine no estaba disponible y se usó `pgserver` temporal.

Python 3.12 es requerido por las dependencias de `pgserver`. La ejecución del 2026-11-02 usó Python 3.12.14 y una base temporal local `pgserver`; Docker Engine no estaba disponible, por lo que no se recurrió a la imagen Compose. El detalle, tiempo y warning de la suite están en
[`docs/evaluation-2/final-readiness-audit.md`](../docs/evaluation-2/final-readiness-audit.md).
