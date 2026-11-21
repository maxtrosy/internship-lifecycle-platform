# ADR-011: Horas reportadas frente a horas aceptadas y consolidación

**Estado:** aceptada como decisión técnica. Quién acepta las horas es configurable y sigue siendo una decisión institucional abierta (OPEN-CR05-02).
**Reglas:** CR-05-BR-04, BR-07.
**Fecha:** 2026-11-20.

## Contexto

En E3, `MIN_HOURS` sumaba todas las horas registradas por la persona estudiante; no existía aprobación. CR-05 exige distinguir las horas reportadas de las horas aceptadas, consolidar entre segmentos y no contar duplicados (BR-04). El documento oficial deja abierto quién acepta las horas y cómo se resuelven disputas y solapamientos.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Columna `status` mutable en `progress_entry` | Pierde quién decidió, cuándo y por qué. Una corrección borraría la decisión anterior. |
| Detección automática de duplicados por fecha y cantidad | Inventaría una política institucional: dos jornadas iguales pueden ser legítimas. |
| **Tabla append-only `progress_entry_review`; la última revisión rige** | **Elegida.** |

## Decisión

- Cada entrada de horas se crea `SUBMITTED` (sin revisión) en el segmento activo, con fecha de jornada y descripción opcionales.
- Una persona revisora autorizada inserta una revisión `ACCEPTED` (total o parcial: `accepted_hours ≤ hours`), `REJECTED` o `DISPUTED`, con un código (`DUPLICATE`, `OUTSIDE_SEGMENT`, `NOT_VERIFIABLE`, `OTHER`) y una justificación, obligatoria si no es aceptación. Las revisiones no se modifican ni se borran; la más reciente define el estado.
- Total consolidado = `placement_accepted_hours(pid)`: suma de las horas aceptadas en la última revisión de cada entrada, **excluyendo** los segmentos con `work_recognition = NOT_RECOGNIZED`. Una entrada nunca cuenta dos veces, aunque se revise varias veces (`test_s10`, `test_s17b`).
- `MIN_HOURS` (servicio y trigger `trg_placement_gate`) usa horas aceptadas. Las entradas pendientes bloquean la confirmación y el cierre.
- Validaciones automáticas mínimas, que no son política institucional: una fecha de jornada debe estar dentro del segmento y no ser futura, y el total de entradas fechadas de un día no puede superar 24 h.
- Revisores configurables con `PLACEMENT_HOURS_REVIEWER_ROLES` (vacío por defecto). Un `WORKPLACE_SUPERVISOR` configurado solo revisa entradas del segmento que supervisa actualmente. La supervisión docente y la coordinación revisan cualquier segmento de su relación. La persona estudiante nunca revisa sus propias horas.

## Consecuencias

- **Cambio de comportamiento respecto a E3:** una práctica con horas reportadas suficientes ya no se puede confirmar sin aceptación. Las pruebas de E3 que dependían de ello se actualizaron explícitamente con `accept_pending_hours`.
- Las horas de E3 migradas quedan pendientes de revisión: no se fabrican aceptaciones (verificado en `check_isolated_migrations.py`).
- **Pendiente:** flujo de resolución de disputas, regla institucional sobre solapamientos y si un supervisor puede revisar horas de un segmento ya cerrado.
