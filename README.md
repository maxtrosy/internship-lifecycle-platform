# DH-05 — Internship and Practicum Management System
## Evaluación 2 — Architecture and Design Review

| | |
|---|---|
| **Proyecto** | DH-05, Horizon University, Digital Horizon Initiative |
| **Evaluación** | Evaluation 2 — Architecture and Design |
| **Versión revisada** | `E2-draft-1` · 2026-10-08 |
| **Estado del repositorio** | Paquete de documentación + PoC independiente. **No contiene el producto.** El equipo no tenía modelo de dominio ni código previo: solo los artefactos de la Evaluación 1 |
| **Pregunta central** | ¿Puede el equipo justificar cómo debe estructurarse el sistema propuesto? |


## Por dónde empezar
1. **[Documento principal](docs/evaluation-2/architecture-and-design.md)**: alcance, requisitos significativos, escenarios, drivers, decisiones, estado y registro `OPEN`.
2. [Auditoría de la Evaluación 1](docs/evaluation-2/evaluation-1-audit.md): 34 inconsistencias y cómo se reconciliaron.
3. [Trazabilidad](docs/evaluation-2/traceability.md): requisito → escenario → driver → ADR → componente → vista → regla → prueba.

## Contenido
| Área | Archivos |
|---|---|
| **ADRs** | [001 políticas](docs/evaluation-2/adr/ADR-001-configurable-policies.md) · [002 monolito modular](docs/evaluation-2/adr/ADR-002-modular-monolith.md) · [003 compuertas](docs/evaluation-2/adr/ADR-003-activation-closure-gates.md) · [004 autorización](docs/evaluation-2/adr/ADR-004-relationship-authorization.md) · [005 versionado y auditoría](docs/evaluation-2/adr/ADR-005-versioning-audit.md) · [006 adaptadores](docs/evaluation-2/adr/ADR-006-integration-adapters.md) |
| **Vistas** | [Contexto](docs/evaluation-2/views/V-CTX-context.md) · [Contenedores](docs/evaluation-2/views/V-CONT-container.md) · [Componentes](docs/evaluation-2/views/V-COMP-components.md) · [Despliegue](docs/evaluation-2/views/V-DEP-deployment.md) · [Dominio y datos](docs/evaluation-2/views/domain-model.md) · [Estados de la colocación](docs/evaluation-2/views/placement-state-machine.md) · [Secuencias](docs/evaluation-2/views/sequences.md) |
| **Diseño** | [Reglas de negocio](docs/evaluation-2/design/business-rules.md) · [Interfaces](docs/evaluation-2/design/interfaces.md) · [Seguridad](docs/evaluation-2/design/security.md) |
| **Validación** | [Plan](docs/evaluation-2/validation/validation-plan.md) · [Resultados](docs/evaluation-2/validation/validation-results.md) · [PoC](docs/evaluation-2/validation/poc.md) |
| **Estado** | [Estado del proyecto](docs/evaluation-2/project-status.md) |
| **PoC** | [`prototype/`](prototype/) |


## Estado en una tabla
| Estado | Qué incluye |
|---|---|
| **Diseñado** | Contexto, contenedores, componentes, dominio, estados, secuencias, reglas, interfaces, seguridad, despliegue |
| **Ejecutado (Windows 10)** | T-01..T-08 + T-16a..e contra PostgreSQL 16.2: **14 PASS, 0 FAIL** en la corrida 2026-10-22. T-02 variante A: 55 activación primero / 45 rechazo primero, 0 prohibidos; **los conteos de orden varían entre corridas** (la primera corrida tuvo 1 FAIL por un defecto del harness, conservado como evidencia) |
| **NOT EXECUTED** | Pico (QS-05), adaptadores (QS-07), usabilidad (QS-08), T-09..T-15, variante concurrente de T-04, despliegue, API, UI |
| **Abierto** | 21 elementos `OPEN` (ver el documento principal §11) |

## Limitaciones conocidas
- No existía `domain-model.md` ni código previo (ASM-003B cita un documento inexistente): el modelo de este paquete es la **primera versión** y la tecnología concreta aún no está elegida (OPEN-17). El equipo debe revisarlo y adoptarlo como propio.
- Ninguna decisión está validada con el cliente ni con Servicios de TI.
- La evidencia ejecutada **no la ha reproducido el equipo**; debe reejecutarla y registrar su commit.
- El PoC usa un esquema simplificado, sin HTTP ni interfaz, y no mide rendimiento.
- Las correcciones a la Evaluación 1 están **registradas**, no aplicadas a los archivos fuente.

## Reproducir el PoC
```bash
cd prototype
pip install pgserver "psycopg[binary]"
python tests/run_poc.py
```
