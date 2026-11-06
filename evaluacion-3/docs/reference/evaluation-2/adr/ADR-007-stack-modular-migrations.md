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
7. **Autenticación local (C-01, RNF-07):** cuentas con nombre de usuario, correo, estado activo y hash Argon2id; JWT HS256 de 15 min en cookie `HttpOnly`, con `sub` y `jti` pero sin roles. Cada solicitud valida sesión y estado en PostgreSQL y vuelve a resolver permisos desde `role_assignment`. No hay signup público. El operador aprovisiona cuentas y las invitaciones solo crean los roles externos permitidos.
8. **SSO institucional (OPEN-21):** no implementado. No se encontró proveedor, protocolo, URL de descubrimiento, credenciales ni cuenta de prueba. La autenticación local sirve como alternativa operativa; la integración OIDC/SAML queda pendiente de decisión e información institucional.
9. **Recuperación:** tokens aleatorios de un solo uso, guardados como hash y válidos 30 minutos; las sesiones existentes se revocan al cambiar la contraseña. Sin correo configurado, solo el entorno local puede devolver el token al operador.
10. **Mitigación de intentos repetidos:** límite en memoria por usuario/IP en la instancia local de un trabajador. Para varios procesos o producción se requiere un almacén compartido o WAF.

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
- **PASÓ (backend, 2026-10-24):** 65/65 pruebas en el Compose efímero `dh05-tests`/`dh05_http_test`, incluidas identidad T-31, autorización HTTP T-34 y concurrencia T-02. Evidencia detallada en [validation-results.md](../validation/validation-results.md).
- **PASÓ (migraciones y Compose demo):** base nueva aislada migró a `0004 (head)`, `/health` devolvió `ok` y se sembraron 14 cuentas. La imagen API comprobada no contiene `tests/`.
- **PASÓ (frontend):** 6 pruebas unitarias, `tsc -b && vite build` (45 módulos) y E2E Chromium T-35 (2/2) para el flujo principal. Otros roles/vistas y browsers no están cubiertos por este recorrido.

## Reconsider when
El equipo adopte formalmente este stack o decida cambiarlo antes de Fase 2; si se elige ORM; si el volumen de migraciones hace inviable revisarlas a mano.

## Related requirements
RNF-01, RNF-02, RNF-09 · RF-20, RF-08, RF-17

## Related ADRs
ADR-001 (políticas), ADR-002 (monolito), ADR-003 (compuertas), ADR-004 (autorización), ADR-005 (auditoría), ADR-006 (adaptadores)
