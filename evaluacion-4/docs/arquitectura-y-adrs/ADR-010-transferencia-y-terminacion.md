# ADR-010: Transferencia atómica y terminación anticipada de segmentos

**Estado:** aceptada como decisión técnica del equipo para CR-05. La autoridad que aprueba una transferencia es configurable y sigue siendo una decisión institucional abierta (OPEN-CR05-01).
**Reglas:** CR-05-BR-05, BR-08, BR-09.
**Fecha:** 2026-11-20.

## Contexto

Una transferencia a mitad de práctica cambia de organización, supervisor o unidad sin borrar ni reescribir lo ocurrido (BR-05). Una terminación anticipada conserva horas, evaluaciones, incidentes y el motivo (BR-08). Los motivos pueden ser sensibles y deben mostrarse solo a quien corresponda (BR-09).

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Editar el segmento activo (cambiar organización/supervisor) | Reescribe historia: los registros previos quedarían atribuidos al nuevo supervisor. Viola BR-05. |
| Dos operaciones separadas (terminar y luego crear) | Deja una ventana sin un vínculo explícito entre origen y destino, permite carreras y pierde la decisión sobre el trabajo previo. |
| **Una operación `transfer` atómica que cierra el origen, crea el destino y escribe `placement_transfer`** | **Elegida.** |

## Decisión

- `transfer` se ejecuta en una sola transacción (`db.command`): bloquea la práctica, marca el origen `TRANSFERRED` con fecha de efecto, crea el destino como segmento `PLANNED` de origen `TRANSFER`, inserta `placement_transfer` (fecha de efecto, motivo compartido, motivo interno, tratamiento del trabajo previo, aprobador y marca de tiempo) y escribe el evento de auditoría `segment.transferred`.
- El destino **no** se activa automáticamente: debe cumplir sus propias condiciones (BR-02).
- `terminate_segment` marca `TERMINATED_EARLY` con fecha de cierre, motivo compartido, motivo interno opcional y la decisión de reconocimiento (`ACCEPTED_HOURS_RECOGNIZED` / `NOT_RECOGNIZED`). Los registros del segmento se conservan. Las horas de un segmento `NOT_RECOGNIZED` no suman al total consolidado.
- Los segmentos y las transferencias son inmutables después de cerrarse (triggers `trg_placement_segment_guard` y `placement_transfer_immutable`). Solo se permiten las transiciones de estado definidas.
- **Privacidad (BR-09):** `end_reason_internal` y `reason_internal` se eliminan de las proyecciones cuando el lector no tiene `segment:read_internal`. Esa capacidad la tienen la coordinación del programa del estudiante, la supervisión docente asignada y la coordinación experiencial. El motivo interno **nunca** se copia al registro de auditoría.
- Quién puede transferir, terminar o activar se configura con `PLACEMENT_SEGMENT_MANAGER_ROLES` (vacío por defecto: nadie puede).

## Consecuencias

- Las transferencias concurrentes sobre el mismo segmento producen exactamente una transferencia (`test_s17_concurrent_activation_and_transfer_stay_consistent`).
- El historial de estados de cada segmento queda en `placement_segment_status_history`.
- **Pendiente:** el flujo de disputa sobre el reconocimiento, la notificación específica de transferencia (se audita, pero no se emite una notificación nueva) y el acceso histórico del supervisor anterior (ADR-012).
