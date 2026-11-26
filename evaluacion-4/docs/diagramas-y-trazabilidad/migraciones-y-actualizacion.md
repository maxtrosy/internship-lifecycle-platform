# Migraciones y procedimiento de actualización (0015 → 0016 → 0017 → 0018 → 0019)

## Qué hace `0016_rotational_segments_and_transfers`

1. Crea las tablas de segmentos, condiciones, historial, transferencias, revisiones de horas y revisiones de experiencia, con sus índices, triggers y permisos para `app_user`.
2. Añade `segment_id` (y `work_date` y `description` en `progress_entry`) con FK compuestas.
3. **Backfill:** por cada práctica `ACTIVE`, `COMPLETED` o `CLOSED` crea un segmento `MIGRATED_SINGLE` con la organización, el supervisor, las fechas y las responsabilidades de su versión vigente. Su estado es `ACTIVE` para las prácticas activas, o `COMPLETED` con las horas reconocidas para las demás. Unidad y modalidad quedan `NULL`: no se inventan.
4. Asocia los registros existentes a ese segmento. Para eso deshabilita los triggers de inmutabilidad solo durante la sentencia y los vuelve a habilitar dentro de la misma migración.
5. **No crea revisiones de horas:** las horas existentes quedan pendientes de revisión.
6. Reemplaza `trg_placement_gate`, `trg_active_placement_record` y `trg_work_plan_assignment_guard` para considerar segmentos y horas aceptadas.

`downgrade()` lanza error a propósito: revertir destruiría historia.

## Qué hace `0017_segment_notifications`

Solo reemplaza la restricción `user_notification_category_check` para admitir `SEGMENT_CHANGED` (ADR-013). No reescribe avisos, segmentos ni auditoría. Los eventos de segmento anteriores a 0017 no generan avisos retroactivos. `downgrade()` borra los avisos `SEGMENT_CHANGED` (no contienen datos de origen, solo la categoría y el vínculo) y restaura la lista de 0014.

## Qué hace `0018_segment_schedule_changes`

Crea `placement_segment_schedule_change` (append-only, con permisos `SELECT, INSERT` para `app_user`) y reemplaza `trg_placement_segment_guard`. Las fechas de un segmento abierto solo cambian junto con un registro de la misma transacción. Los demás campos siguen inmutables (ADR-014). No modifica filas existentes. `downgrade()` restaura el trigger de 0016 y elimina la tabla, pero se niega si ya hay cambios registrados, para no borrar historia.

## Qué hace `0019_segment_revisions_and_evidence`

- **Revisiones de datos:** crea `placement_segment_revision` (append-only; `app_user` tiene `SELECT, INSERT`). Reemplaza `trg_placement_segment_guard` para aceptar ajustes de datos solo con una revisión de la misma transacción y según el estado del segmento (ADR-015).
- **Condiciones:** reemplaza `trg_segment_condition_guard` para que una condición vuelva a pendiente solo si su evidencia fue rechazada.
- **Evidencias:** añade `checklist_item.segment_condition_id` con la restricción de no obligatoriedad. Crea los ítems de evidencia de las condiciones pendientes de segmentos planificados existentes. No modifica horas, evaluaciones ni documentos.
- **`downgrade()`:** se niega si existen revisiones o evidencias entregadas. Si no, elimina los ítems de evidencia, la columna y la tabla, y restaura los triggers de 0018.

## Procedimiento recomendado

1. Respaldar la base (`pg_dump`) y verificar el respaldo.
2. Desplegar el código con la migración, sin tráfico de escritura.
3. `alembic upgrade head` y confirmar `SELECT version_num FROM alembic_version` = `0019`.
4. Configurar, si la institución ya decidió, `PLACEMENT_SEGMENT_MANAGER_ROLES` y `PLACEMENT_HOURS_REVIEWER_ROLES`. Si se dejan vacías, nadie puede gestionar segmentos ni aceptar horas, y **las prácticas activas no podrán cerrarse** mientras haya horas pendientes.
5. Revisar las horas migradas antes de confirmar cierres.

Ninguno de estos pasos se ejecutó contra Neon ni contra Docker en este trabajo.

## Verificación ejecutada

`python scripts/check_isolated_migrations.py` crea un PostgreSQL temporal, migra 0001→0007, inserta una práctica activa con un incidente y horas heredadas, migra a 0019 y verifica el segmento `MIGRATED_SINGLE` (secuencia 1, `ACTIVE`, supervisor de la versión, unidad y modalidad `NULL`), los registros asociados y la ausencia de revisiones fabricadas. También comprueba que un `UPDATE` directo de fechas sin registro es rechazado, los permisos de la tabla nueva el rechazo de un `UPDATE` directo de atributos y el ciclo 0019→0017→0019. Después prueba la ruta 0010→0019. El resultado vigente está en `../../evidence/test-results-2026-11-24.md` (la ejecución anterior, hasta 0016, en `test-results-2026-11-20.md`).
