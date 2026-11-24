# ADR-014: Cambios de periodo de un segmento con historial append-only

**Estado:** aceptada como decisión técnica. Refina ADR-009 (segmentos inmutables) sin reemplazarla. No decide la superposición de segmentos (OPEN-CR05-03) ni quién gestiona segmentos (OPEN-CR05-01).
**Reglas:** CR-05 §6.3 «Excepciones temporales» (segmentos acortados o extendidos según reglas explícitas), CR-05-BR-03, BR-08.
**Fecha:** 2026-11-23.

## Contexto

Hasta 0017 el contenido de un segmento era inmutable por trigger: para cambiar su fin había que cancelarlo y planificar otro, y un segmento activo no podía extenderse ni acortarse. La solicitud pide gestionar segmentos acortados o extendidos con reglas explícitas, y BR-03 exige que cada segmento conserve su historial.

## Alternativas

- **A. Cancelar y volver a planificar.** Sin cambios técnicos, pero no sirve para un segmento activo: cancelarlo perdería la continuidad de sus horas y evaluaciones.
- **B. Permitir `UPDATE` libre de fechas.** Simple, pero borra el periodo anterior y solo deja rastro en la auditoría.
- **C. Tabla append-only `placement_segment_schedule_change` y trigger que solo acepta el cambio de fechas junto con su registro en la misma transacción.**

## Decisión

Se elige **C** (migración `0018`).

- `POST /placements/{pid}/segments/{sid}/schedule` (`segments.reschedule_segment`) usa la misma autoridad configurable que el resto de los comandos de segmento (`segment:manage`, vacía por defecto).
- **Reglas explícitas:**
  - Solo se cambian segmentos `PLANNED` o `ACTIVE`.
  - Un segmento activo conserva su fecha de inicio y no puede terminar antes de hoy. Terminar antes es una terminación anticipada con decisión de reconocimiento (BR-08).
  - Las horas fechadas ya registradas deben quedar dentro del nuevo periodo.
  - El motivo compartido es obligatorio, y el periodo nuevo debe ser distinto del actual.
- Cada cambio guarda el periodo anterior, el nuevo, el motivo, el autor y la hora. La tabla no admite `UPDATE` ni `DELETE`.
- `trg_placement_segment_guard` rechaza cualquier cambio de fechas sin un registro de la misma transacción (`txid_current()`) que coincida con el periodo anterior y el nuevo. Así ni el SQL directo puede saltarse el historial.
- El evento `segment.rescheduled` queda en la auditoría y genera el aviso `SEGMENT_CHANGED`.
- La superposición no se decide: las fechas pueden solaparse, y sigue habiendo un solo segmento activo.

## Consecuencias

- Organización, unidad, supervisor, modalidad, responsabilidades y horas esperadas siguen siendo inmutables. Cambiarlos sigue exigiendo una transferencia, o cancelar y planificar.
- `downgrade()` se niega a ejecutarse si existen cambios registrados, porque eliminar la tabla borraría el historial de periodos.
- Como las horas no pueden fecharse en el futuro, en un segmento activo la comprobación de horas fuera del periodo es defensiva. Se mantiene en el servicio y en el trigger.

## Comprobación

- `backend/tests/test_cr05_segments.py::test_segment_schedule_changes_follow_explicit_rules_and_keep_history`: autoridad, reglas, historial, inmutabilidad, rechazo de un `UPDATE` directo, auditoría, aviso, segmento planificado, segmento cancelado y HTTP.
- `scripts/check_isolated_migrations.py`: rechazo de un cambio de fechas sin registro, permisos de `app_user` y ciclo 0018→0017→0018.
- `frontend/e2e/rotation.spec.ts`: extensión del segmento activo destino desde el panel lateral y su historial visible.
