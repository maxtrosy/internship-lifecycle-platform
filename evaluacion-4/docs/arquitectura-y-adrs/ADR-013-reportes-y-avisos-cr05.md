# ADR-013: Reportes y avisos de CR-05 derivados de datos persistidos y de la auditoría

**Estado:** aceptada como decisión técnica. Amplía ADR-005 (auditoría) y el reporte operativo de E3 (RF-18) sin reemplazarlos. No cambia ninguna regla académica.
**Reglas:** CR-05 §6 (reportes solicitados), CR-05-BR-04, BR-06, BR-09.
**Fecha:** 2026-11-22.

## Contexto

La solicitud CR-05 pide reportes de prácticas con varios segmentos, rotaciones activas, transferencias, interrupciones, horas aceptadas, evaluaciones faltantes y consolidaciones pendientes. Hasta esta versión, el reporte operativo de E3 no conocía los segmentos, y los cambios de segmento solo quedaban en la auditoría: nadie recibía un aviso cuando un segmento se activaba o se transfería.

Había que decidir dónde calcular esos indicadores y cómo avisar sin abrir datos sensibles: los motivos confidenciales (BR-09) y el acceso del supervisor anterior (BR-06).

## Alternativas

- **A. Tabla de indicadores mantenida por cada comando** (contadores de transferencias, horas, etc.). Lecturas más rápidas, pero duplica el estado: cada comando de segmentos tendría que mantenerla, y una corrección de horas podría dejarla desalineada.
- **B. Consultas agregadas sobre las tablas de 0016 y avisos generados desde la auditoría.** Sin estado nuevo: los números salen de las mismas filas que usan los gates de cierre, y los avisos reutilizan el mecanismo de E3 (`audit.write` → `enqueue_from_audit`).

## Decisión

Se elige **B**.

- `GET /reports/rotations` (`reports/service.py::rotations`) reutiliza `_scope` del reporte operativo: coordinación de programa limitada a sus programas, coordinación de experiencias con alcance institucional y `403` para el resto. Devuelve solo agregados: ningún nombre, motivo, evaluación ni registro individual. Las horas aceptadas siguen la misma regla que `placement_accepted_hours` (la última revisión manda y los segmentos `NOT_RECOGNIZED` no cuentan). Una consolidación está pendiente si la práctica está activa, tiene más de un segmento efectivo, ninguno abierto y no tiene una revisión combinada aprobada posterior al último cierre de segmento; es el mismo criterio que `segment_gate_status`.
- Los eventos `segment.activated`, `segment.completed`, `segment.terminated_early` y `segment.transferred` producen la categoría `SEGMENT_CHANGED` (migración `0017`, que solo amplía la restricción de categorías). Los destinatarios son los de E3 para la práctica: estudiante, supervisión docente asignada, coordinación del programa, coordinación de experiencias y el supervisor laboral del segmento activo **en el momento del evento**. El actor nunca recibe su propio aviso.
- El aviso lleva solo la categoría y el vínculo a la práctica, como en E3. No copia motivos ni datos del segmento.

## Consecuencias

- Una activación avisa al supervisor nuevo. Una transferencia o terminación no avisa al supervisor anterior, porque ya no existe un segmento activo suyo. Así el aviso no le da un enlace a un expediente que respondería `404` (BR-06).
- El supervisor de un segmento destino `PLANNED` recibe el aviso al activarse el segmento, no al planificarlo.
- Las consultas del reporte recorren las tablas de segmentos en cada petición. Es aceptable para el volumen de la demo y del semestre. Si creciera, se podría materializar sin cambiar el contrato.
- El filtro de organización se aplica a la organización de la oportunidad, igual que en `/reports/operations`. Un segmento puede ocurrir en otra organización; esto queda documentado en el contrato.

## Comprobación

- `backend/tests/test_cr05_segments.py::test_rotation_reports_aggregate_cr05_state_within_scope`: indicadores tras transferir, activar, terminar sin reconocimiento y aprobar la revisión combinada. También comprueba el alcance por programa, el `403` HTTP para empleador y estudiante, y que la respuesta no incluye motivos ni nombres.
- `backend/tests/test_cr05_segments.py::test_segment_events_notify_related_people_but_not_the_previous_supervisor`.
- `frontend/e2e/rotation.spec.ts` (fixture `--populated`): recorrido en navegador con avisos y reporte.
- `scripts/check_isolated_migrations.py`: cadenas 0001→0017 y 0010→0017.
