# Migraciones y procedimiento de actualización (0015 → 0016)

## Qué hace `0016_rotational_segments_and_transfers`

1. Crea las tablas de segmentos, condiciones, historial, transferencias, revisiones de horas y revisiones de experiencia, con sus índices, triggers y permisos para `app_user`.
2. Añade `segment_id` (y `work_date` y `description` en `progress_entry`) con FK compuestas.
3. **Backfill:** por cada práctica `ACTIVE`, `COMPLETED` o `CLOSED` crea un segmento `MIGRATED_SINGLE` con la organización, el supervisor, las fechas y las responsabilidades de su versión vigente. Su estado es `ACTIVE` para las prácticas activas, o `COMPLETED` con las horas reconocidas para las demás. Unidad y modalidad quedan `NULL`: no se inventan.
4. Asocia los registros existentes a ese segmento. Para eso deshabilita los triggers de inmutabilidad solo durante la sentencia y los vuelve a habilitar dentro de la misma migración.
5. **No crea revisiones de horas:** las horas existentes quedan pendientes de revisión.
6. Reemplaza `trg_placement_gate`, `trg_active_placement_record` y `trg_work_plan_assignment_guard` para considerar segmentos y horas aceptadas.

`downgrade()` lanza error a propósito: revertir destruiría historia.

## Procedimiento recomendado

1. Respaldar la base (`pg_dump`) y verificar el respaldo.
2. Desplegar el código con la migración, sin tráfico de escritura.
3. `alembic upgrade head` y confirmar `SELECT version_num FROM alembic_version` = `0016`.
4. Configurar, si la institución ya decidió, `PLACEMENT_SEGMENT_MANAGER_ROLES` y `PLACEMENT_HOURS_REVIEWER_ROLES`. Si se dejan vacías, nadie puede gestionar segmentos ni aceptar horas, y **las prácticas activas no podrán cerrarse** mientras haya horas pendientes.
5. Revisar las horas migradas antes de confirmar cierres.

Ninguno de estos pasos se ejecutó contra Neon ni contra Docker en este trabajo.

## Verificación ejecutada

`python scripts/check_isolated_migrations.py` crea un PostgreSQL temporal, migra 0001→0007, inserta una práctica activa con un incidente y horas heredadas, migra a 0016 y verifica el segmento `MIGRATED_SINGLE` (secuencia 1, `ACTIVE`, supervisor de la versión, unidad y modalidad `NULL`), los registros asociados y la ausencia de revisiones fabricadas. Después prueba la ruta 0010→0016. El resultado está en `../../evidence/test-results-2026-11-20.md`.
