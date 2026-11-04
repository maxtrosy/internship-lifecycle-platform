# ADR-005 — Versionado de la colocación e historial de auditoría

**Status:** propuesta, **parcialmente verificada** en PoC · **Fecha:** 2026-10-08

## Context
RFP: cambios de supervisor, horario, ubicación o responsabilidades "no se registran consistentemente"; la universidad debe "reconstruir aplicaciones, aprobaciones, acuerdos, evaluaciones, cambios y decisiones de finalización". RF-13 (cambio = nueva versión con aprobación), RF-19, RNF-05. Qué cambios exigen re-aprobación y de quién es **OPEN-03**.

## Decision
Se distinguen **tres cosas** que no deben mezclarse:

| Concepto | Qué es | Dónde vive | Mutabilidad |
|---|---|---|---|
| **Estado vigente** | Dónde está hoy la colocación y qué versión rige | `Placement.state`, `Placement.current_version_id` | Cambia mediante comandos |
| **Datos de negocio versionados** | Supervisor del lugar de trabajo, fechas, ubicación y responsabilidades; políticas, entregas documentales y evidencia/informes versionados | `PlacementVersion`, `PolicyVersion`, `DocumentSubmission`, `completion_evidence`, `placement_progress_report`, `placement_evaluation`, `placement_incident` | **Contenido inmutable**; las entregas/evaluaciones/registros se agregan por revisión. El estado de decisión de una versión cambia una vez (`PROPOSED → APPROVED/REJECTED`) |
| **Historial de auditoría** | Quién hizo qué, cuándo, antes/después | `AuditEvent` | **Append-only** |

Reglas:
1. La versión 1 se aprueba junto con la aprobación académica.
2. Un cambio relevante crea una versión `PROPOSED`; **la vigente no cambia hasta aprobar**. Cuando se aprueba, `current_version_id` se mueve y la anterior se conserva.
3. **Auditoría atómica:** cada mutación aceptada escribe su `AuditEvent` en **la misma transacción** (actor, instante, acción, sujeto, antes/después, correlación). Si falla la auditoría, falla la mutación.
4. **Inmutabilidad:** la aplicación solo puede `INSERT/SELECT` sobre auditoría (permisos) y un trigger rechaza `UPDATE/DELETE` incluso al dueño de la tabla; la versión protege su contenido con trigger.
5. Los registros de seguimiento, evaluaciones, incidentes/cambios y evidencia final son append-only y enlazan por colocación y revisión; cada mutación aprobada escribe auditoría en la misma transacción. Un reporte de cambio no crea versión y los incidentes no tienen resolución/escalamiento implementados.
6. Qué cambios exigen aprobación, quién aprueba y qué ocurre mientras se espera (¿sigue activa?, ¿cambio urgente?) quedan en **OPEN-03**. Propuesta: aprobación del coordinador de programa; versión vigente rige mientras tanto.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| Sobrescribir + tabla de auditoría | Pierde la versión consultable; la auditoría puede divergir |
| Event sourcing completo | Reconstrucción perfecta, pero curva y complejidad desproporcionadas para un semestre |
| Tablas temporales / extensión genérica de auditoría | Útil pero sin semántica de negocio (aprobación, versión) y expone datos de más |
| Cadena de hashes por evento | Detectaría manipulación, pero costo y verificación excesivos hoy |
| **Versiones inmutables + auditoría append-only (elegida)** | Separa responsabilidades con costo contenido |

## Rationale
La versión responde "¿qué rige hoy y qué regía antes?"; la auditoría responde "¿quién decidió qué y cuándo?". Son preguntas distintas con ciclos de vida distintos.

## Consequences
Las lecturas del estado vigente hacen un *join* con la versión actual. La línea de tiempo se arma con eventos de postulación, colocación, checklist, versiones, horas, seguimiento, evaluación, incidentes/cambios y cierre. El endpoint proyecta solo fecha/acción; omite actor/sujeto internos, IDs, correlación y JSON antes/después. La interfaz traduce acciones conocidas y usa una etiqueta genérica para acciones nuevas. La E2E de esta continuación verificó los eventos `placement.completed` y `placement.closed`. La traza de publicación de oportunidad y cobertura de todas las mutaciones siguen incompletas.

## What gets worse / trade-offs
- Más almacenamiento y más complejidad de lectura/reconciliación.
- Si algún código evade el servicio de comandos, estado y auditoría pueden divergir (mitigación: misma transacción + pruebas).
- Un **superusuario de BD** puede deshabilitar el trigger (riesgo residual aceptado; mitigable con auditoría a nivel de motor y permisos).
- La auditoría puede contener datos personales: minimizar contenido y definir retención (pendiente).

## Verification
- **Ejecutado (PoC, equipo):** **T-05** — la propuesta no cambia la versión vigente; un coordinador de otro programa no puede aprobar; un supervisor ajeno no puede proponer (no encontrado); al aprobar, el puntero se mueve y la v1 permanece intacta; el contenido de v1 no se puede modificar (trigger); eventos `change_proposed` y `version_approved` con antes/después. **T-07** — permiso denegado a la aplicación para `UPDATE/DELETE` sobre auditoría; el trigger rechaza al dueño; el evento sigue intacto.
- **NOT EXECUTED:** estado de la colocación mientras hay una versión pendiente; cambio urgente; latencia de reconstrucción del historial (QS-04); retención.

## Reconsider when
Aparecen requisitos regulatorios de evidencia inalterable (entonces hash encadenado o almacenamiento WORM); el volumen de eventos degrada las consultas; se acuerda re-aprobación con circuitos distintos por tipo de cambio.

## Related requirements
RF-13, RF-14, RF-19, RNF-05 · BR-04, BR-06, BR-07

## Related quality scenarios
QS-04

## Related architecture views
V-COMP (C-06, C-11), V-DOM (PlacementVersion, AuditEvent), SEQ-03
