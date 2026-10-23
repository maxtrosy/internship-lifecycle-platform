# ADR-007 — Stack, estructura modular y migraciones (Fase 1)

**Status:** propuesta del equipo, **pendiente de adopción** · **Fecha:** 2026-10-22

## Context
OPEN-17 dejaba sin elegir la tecnología. El PoC (`prototype/`) demostró en PostgreSQL la semántica de compuertas, bloqueo de fila (`SELECT … FOR UPDATE`), triggers y autorización por relación; al portarlo hay que **conservar** esos mecanismos y no debilitarlos. El equipo es pequeño y debe poder mantenerlo en un semestre.

## Decision
1. **Backend:** Python 3.12 · **FastAPI** · **Uvicorn** · **Pydantic v2** · **psycopg 3** con SQL explícito (sin ORM: se conservan `SELECT … FOR UPDATE` y los triggers) · **PostgreSQL 16**.
2. **Migraciones:** **Alembic** con revisiones escritas en SQL (`op.execute`). SQLAlchemy se usa **solo** como motor de Alembic, nunca como ORM.
3. **Pruebas:** **pytest**; las de concurrencia usan conexiones independientes y barrera (como `run_poc.py`).
4. **Frontend:** React + TypeScript + Vite (iniciado en `frontend/` con el flujo de oportunidades y postulaciones; crecerá por fases).
5. **Desarrollo:** **Docker Compose** con servicios `db` (postgres:16) y `api`.
6. **Monolito modular (ADR-002):** `backend/app/modules/<módulo>/` con C-01 identity, C-02 authz, C-03 opportunities, C-04 applications, C-05 policies, C-06 lifecycle, C-07 checklist, C-08 supervision, C-09 messaging, C-10 notifications, C-11 audit, C-12 reports, y `backend/app/adapters/` + `backend/app/ports/` para C-13. Un módulo usa solo la interfaz pública (`service.py`) de otro, nunca sus tablas; el dominio no importa adaptadores (verificado por T-23, chequeo AST).
7. **Autenticación simulada (C-01, OPEN-21):** JWT HS256 de 15 min que **solo** lleva el `sub` (id del sujeto); los roles NO viajan en el token y se evalúan en BD en cada solicitud. Usuarios externos entran por invitación con token cuyo hash se guarda.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| ORM (SQLAlchemy model layer) | Ocultaría `FOR UPDATE` y triggers; riesgo de perder la semántica validada |
| Django | Más magia, menos control del SQL; no justificado para este alcance |
| Node/TypeScript en backend | Segundo lenguaje para el equipo; el PoC ya está en Python |
| Migraciones ad-hoc en SQL | Sin historial ni reversión; Alembic es estándar |

## Consequences
- El equipo mantiene un solo lenguaje en backend y reutiliza la lógica del PoC casi 1:1.
- La autorización se mantiene en SQL (predicados por relación), no en el framework.
- Las integraciones (C-13) quedan detrás de puertos para simularlas (ADR-006).

## What gets worse / trade-offs
- SQL explícito y triggers exigen disciplina para no duplicar la lógica de negocio (mitigación: T-16c/T-20/T-23 y el patrón `command()`).
- `command()` obliga a que toda mutación aceptada escriba auditoría (BR-07); los comandos denegados revierten sin evento.
- Alembic con `op.execute` delega la corrección del SQL en el equipo; hay que revisar cada migración.

## Verification
- **EXECUTED (backend).** `pytest` en `backend/`: **28 PASS** (T-20..T-23, T-24/T-25 y los tests portados T-01/T-02/T-02b/T-04/T-08/T-16a..e) contra PostgreSQL real (pgserver, Python 3.12).
- **EXECUTED.** `alembic upgrade head` + `python -m app.seed` + `GET /health` responden `{"status":"ok"}`.
- **Frontend:** `tsc -b && vite build` genera `frontend/dist/` (bundler OK); pnpm emite una advertencia de build-script de esbuild ignorado. La integración navegador↔API no se probó end-to-end (NOT EXECUTED).

## Reconsider when
El equipo adopte formalmente este stack o decida cambiarlo antes de Fase 2; si se elige ORM; si el volumen de migraciones hace inviable revisarlas a mano.

## Related requirements
RNF-01, RNF-02, RNF-09 · RF-20, RF-08, RF-17

## Related ADRs
ADR-001 (políticas), ADR-002 (monolito), ADR-003 (compuertas), ADR-004 (autorización), ADR-005 (auditoría), ADR-006 (adaptadores)
