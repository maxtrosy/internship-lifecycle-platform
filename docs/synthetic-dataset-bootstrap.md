# Carga sintética persistente: modalidad parcial y permisos

## Modalidades

`scripts/persist_synthetic_dataset.py --mode partial` es el modo predeterminado de solo lectura. La carga parcial incluye las diez organizaciones sintéticas (dos del seed existente y ocho nuevas), hasta 47 cuentas sintéticas con relaciones, y 16 oportunidades que solo pueden quedar en `DRAFT` o `IN_REVIEW`. No crea programas, políticas, postulaciones, selecciones, prácticas, evaluaciones, evidencias de cierre ni cierres.

La creación de organizaciones, cuentas y asignaciones de rol usa SQL de bootstrap porque el producto todavía no tiene servicios de aprovisionamiento para esas entidades. Se respetan claves foráneas y restricciones únicas; las cuentas existentes se comparan por perfil y por su conjunto completo de relaciones. Si difieren, la carga se aborta y las conserva sin modificarlas. Las oportunidades se crean y se envían a revisión exclusivamente mediante los servicios de dominio, que escriben su auditoría y notificaciones dentro de la misma transacción.

El bloqueo asesorado por `pg_advisory_xact_lock` serializa dos ejecuciones del cargador. Una sola transacción contiene organizaciones, cuentas, relaciones, oportunidades, eventos de auditoría y notificaciones. Un error revierte la carga completa. Una segunda ejecución informa cero inserciones. Una oportunidad que ya avanzó a `APPROVED`, `PUBLISHED` o `CLOSED` causa un bloqueo; el cargador no la rebaja de estado. El modo parcial no necesita autoridad para aprobar o publicar.

`--mode full` sigue siendo un flujo distinto. Requiere políticas persistidas de elegibilidad, activación y finalización para cada programa, autoridades explícitas para revisión/publicación/asignación docente y un rol de escritura dedicado. El código no crea políticas institucionales. `allow_test_only_synthetic_evidence` permanece desactivado en el cargador persistente: sin ese opt-in no se inventan horas, evaluación/evidencia final ni se confirma o cierra una práctica. El fixture `full` todavía modela eventos sintéticos de seguimiento/documentación mediante servicios de dominio, pero no los trata como prueba suficiente para el cierre. El fallback anterior de una hora cuando faltaba `MIN_HOURS` fue eliminado; solo las pruebas aisladas pueden habilitar el opt-in.

## Contraseñas de cuentas nuevas

Cada cuenta nueva recibe una contraseña aleatoria única, almacenada fuera del repositorio en Windows Credential Manager con el destino `InternshipLifecyclePlatform/SyntheticDataset/long-truth-39527618/main/<username>/PASSWORD`. Las cuentas existentes no se vuelven a cifrar. El preflight lee las credenciales solo en memoria, detecta duplicados por huella SHA-256 y no muestra valores. Si debe generar una contraseña, el cargador exige `--allow-credential-store-write`; en un rollback borra únicamente las credenciales que generó en esa ejecución. No se usa una contraseña compartida.

## Rol mínimo para `partial`

El login dedicado se llama `app_bootstrap`. Debe conectarse directamente a Neon `main` con TLS, `NOINHERIT`, sin membresías, sin permisos administrativos y sin acceso de lectura al hash de contraseña. No se concede membresía en `app_user`; `app_runtime` permanece intacto.

Un administrador de base de datos puede provisionar el rol una vez, comprobando primero que no exista. No use el cargador ni `app_runtime` para alterar roles:

```sql
CREATE ROLE app_bootstrap LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE
  NOREPLICATION NOBYPASSRLS;
GRANT CONNECT ON DATABASE neondb TO app_bootstrap;
GRANT USAGE ON SCHEMA public TO app_bootstrap;

GRANT SELECT (id, code, name) ON public.academic_program TO app_bootstrap;
GRANT SELECT (id, name), INSERT (name) ON public.host_org TO app_bootstrap;
GRANT SELECT (id, username, email, display_name, is_active, credits, academic_level, completed_courses),
  INSERT (username, email, password_hash, is_active, display_name, credits, academic_level, completed_courses)
  ON public.user_account TO app_bootstrap;
GRANT SELECT (id, user_id, role, program_id, host_org_id),
  INSERT (user_id, role, program_id, host_org_id)
  ON public.role_assignment TO app_bootstrap;
GRANT SELECT ON public.opportunity TO app_bootstrap;
GRANT INSERT (host_org_id, program_id, title, state), UPDATE (state)
  ON public.opportunity TO app_bootstrap;
GRANT INSERT (actor_id, action, subject_type, subject_id, before_state, after_state, correlation_id),
  SELECT (id, occurred_at) ON public.audit_event TO app_bootstrap;
GRANT SELECT (recipient_id, source_event_id),
  INSERT (recipient_id, source_event_id, category, placement_id, opportunity_id, created_at)
  ON public.user_notification TO app_bootstrap;
GRANT USAGE ON SEQUENCE public.host_org_id_seq, public.user_account_id_seq,
  public.role_assignment_id_seq, public.opportunity_id_seq, public.audit_event_id_seq,
  public.user_notification_id_seq TO app_bootstrap;
```

The narrow read on `user_notification.recipient_id` and `source_event_id` is required by PostgreSQL for the service's `ON CONFLICT` uniqueness check; it does not grant access to notification content. The application authorization service does not select `password_hash`.

The role must **not** receive any additional grant, including reads outside the listed columns, `DELETE`, `CREATE` on any schema, unexpected grants on other public tables/sequences, writes to `academic_program`, `policy_version`, `application` or `placement`, access to `alembic_version`, `CREATE` or a direct `TEMP` grant on the database, or membership in `app_user`. Before apply, the preflight compares effective permissions for every column/table/sequence in `public`, user schemas, and database privileges against the allowlist. A default `TEMP` privilege inherited from `PUBLIC`, if the database has one, is tolerated as a PostgreSQL default; the loader does not create temporary tables. If unexpected privileges exist, it blocks and does not revoke them automatically.

The runtime database URL is not used as the writer. Store the direct TLS URL for the `app_bootstrap` login in Windows Credential Manager as `InternshipLifecyclePlatform/Neon/main/synthetic_loader/app_bootstrap/DATABASE_URL`. The loader never prints either URL. A secure interactive password operation such as `\password app_bootstrap` avoids putting the password in shell history.

## Rol separado para `full`

No se eleva `app_bootstrap` para habilitar el modo integral. Si en el futuro se resuelven las políticas y autoridades, el rol `app_dataset_full` necesita su propia credencial directa y permisos limitados a la fixture. El cargador verifica el siguiente alcance: lectura de las tablas de aplicación enumeradas abajo; inserción solo en tablas de catálogo, flujo, auditoría y notificaciones que usa la fixture; actualización en oportunidades, postulaciones, prácticas, versiones, checklist y requisitos de finalización; `USAGE` en secuencias de esas inserciones. No necesita `DELETE`, acceso de lectura a `user_account.password_hash`, escritura en `policy_version`, membresía `app_user`, ni permisos administrativos. Tampoco lee el ledger de Alembic.

Tablas con lectura de fixture: `academic_program`, `host_org`, `role_assignment`, `policy_version`, `opportunity`, `application`, `placement`, `placement_version`, `supervisor_assignment`, `placement_faculty_assignment_history`, `checklist_item`, `completion_requirement`, `document_submission`, `document_review`, `progress_entry`, `placement_work_plan_item`, `placement_progress_report`, `placement_evaluation`, `placement_incident`, `completion_evidence`, `user_notification`, `placement_conversation`, `placement_message` y `audit_event`. En `user_account` solo se leen las columnas de perfil necesarias, nunca `password_hash`.

Tablas de inserción del modo integral: las anteriores que el servicio crea, además de `user_account`; `supervisor_assignment` es una tabla compuesta y no usa secuencia. Las únicas actualizaciones son `opportunity`, `application`, `placement`, `placement_version`, `checklist_item` y `completion_requirement`. El preflight de código exige esos grants y rechaza `DELETE`, escritura en políticas y cualquier permiso administrativo. No existe un rol `app_dataset_full` provisionado por este cambio.

## Preflight y aplicación

El preflight de partial comprueba el proyecto `long-truth-39527618`, branch `main` (`br-green-wind-bc6cvzzc`), TLS, el marcador de esquema, las colisiones naturales, estados de oportunidad, relaciones ya existentes, permisos del bootstrap, snapshot hijo de menos de 24 horas y cantidad de contraseñas únicas que faltan. La cuenta runtime solo se utiliza para lectura; el ledger de Alembic no está expuesto a los roles de ejecución. El marcador confirma el esquema mínimo (introducido en 0012), no demuestra por sí solo la versión exacta de Alembic. La escritura no ejecuta migraciones.

Desde PowerShell, desde la raíz del repositorio:

```powershell
$Python = 'C:\ruta\al\python-del-proyecto\python.exe'
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
& $Python scripts/persist_synthetic_dataset.py --mode partial
```

El comando es de solo lectura y termina con código 2 si falta snapshot, credencial o permiso. Solo después de revisar el JSON del dry-run, almacenar la URL de bootstrap, contar con snapshot reciente y dar autorización explícita para guardar contraseñas en Credential Manager, se puede ejecutar:

```powershell
& $Python scripts/persist_synthetic_dataset.py --mode partial `
  --apply `
  --confirm-target long-truth-39527618/main `
  --backup-branch-id '<ID_DE_LA_RAMA_SNAPSHOT>' `
  --allow-credential-store-write
```

La ejecución vuelve a revisar el destino y el snapshot, muestra cantidades sin secretos y solicita escribir `PERSIST SYN-01 PARTIAL TO long-truth-39527618/main`. Sin esa frase, sin el flag de credenciales cuando haga falta o con cualquier bloqueo, no se escribe en Neon. El postflight vuelve a leer el resultado con `app_runtime`; no migra el esquema ni toca bases locales, Docker, demo o datos existentes ajenos a la fixture.
