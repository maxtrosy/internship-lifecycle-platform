# ADR-008 — Contexto de versión aprobado para registros de seguimiento

## Estado

Aceptado como decisión técnica del incremento. No resuelve OPEN-03.

## Contexto

Una práctica puede tener varias versiones inmutables. Horas, avances, actividades, evaluaciones, incidentes y evidencia final deben conservar la versión aprobada que estaba vigente al registrarse.

## Decisión

Cada nueva fila de esos registros captura `placement_version_id` desde `placement.current_version_id`. Una función y triggers SQL rechazan referencias a otra práctica, versiones propuestas o versiones que dejaron de ser vigentes. Los registros anteriores conservan `NULL` si no existe evidencia de contexto.

## Consecuencias

- El expediente puede explicar qué versión respaldaba cada operación.
- No se reescribe ni se adivina la historia anterior.
- Las mutaciones siguen siendo atómicas y auditadas.
- La autoridad institucional para aprobar nuevas versiones permanece fuera de este ADR.
