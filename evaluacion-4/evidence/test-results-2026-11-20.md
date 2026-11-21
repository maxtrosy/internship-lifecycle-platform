# Resultados ejecutados: CR-05 (Evaluación 4)

Formato del registro de evidencia del PDF: **QUÉ / VERSIÓN / ENTORNO / EJECUCIÓN / RESULTADO**. Todos los resultados se obtuvieron ejecutando los comandos indicados; ninguno es un resultado esperado presentado como obtenido.

## Entorno común

- **Fecha:** 2026-11-20 y 2026-11-21 (la sesión cruzó medianoche, hora local).
- **Sistema:** Windows 10 Home 10.0.19045.
- **Python:** 3.12.16 (intérprete gestionado por uv en `~/.local/bin`, con dependencias en `backend/.deps`; el Python global no se modificó).
- **Node:** v24.18.0 · vitest 2.1.9 · Playwright Chromium (dependencias de `frontend/node_modules`).
- **Base de datos:** PostgreSQL temporal (pgserver) creado y eliminado en cada ejecución. **Neon y Docker no se usaron ni se modificaron.**
- **Versión de código:** árbol de trabajo sobre el commit `00940e3` con los cambios de CR-05 sin commitear. Esquema Alembic `0016`.

## 1. Backend completo

- **QUÉ:** todas las pruebas backend (E1–E3 + CR-05).
- **EJECUCIÓN:** `cd backend; $env:DATABASE_URL=''; python -m pytest -q -p no:cacheprovider tests`
- **RESULTADO:** `123 passed, 1 warning in 239.57s`. La advertencia es la deprecación de `httpx` en el TestClient de Starlette y no está relacionada con CR-05. Línea base antes de CR-05: `111 passed`.

## 2. Pruebas CR-05

- **QUÉ:** `tests/test_cr05_segments.py`, que cubre los 18 escenarios (ver la matriz de trazabilidad).
- **EJECUCIÓN:** `python -m pytest -q -p no:cacheprovider tests/test_cr05_segments.py -v`
- **RESULTADO:** `12 passed, 1 warning in 28.76s`. Pruebas: `test_s01`, `test_s02`, `test_s13`, `test_s05`, `test_s10`, `test_s11`, `test_s12`, `test_s16`, `test_s16b`, `test_s17`, `test_s17b` y `test_http_segment_endpoints_enforce_permissions_and_privacy`.

## 3. Migraciones aisladas

- **QUÉ:** cadena 0001→0016 con datos heredados y actualización 0010→0016.
- **EJECUCIÓN:** `python scripts/check_isolated_migrations.py`
- **RESULTADO:**
  ```text
  MIGRATION_CHAIN=0001->0016; initial_status_absent=true; cr05_migrated_single_segment=true; legacy_records_attached_to_segment=true; legacy_hours_left_pending_review=true; legacy_incident_status=REPORTED; closed_work_plan_guard=true; notifications_and_audience_scoped_messages=true; opportunity_state_guard=true; manual_eligibility_review_notification=true; faculty_assignment_history=true; app_user_minimal_grants=true
  MIGRATION_UPGRADE=0010->0011->0012->0013->0014->0015->0016; opportunity_state_guard=true; faculty_assignment_history=true; manual_eligibility_review_notification=true; app_user_minimal_grants=true
  TEMPORARY_POSTGRES_CLEANED=true
  ```

## 4. Frontend

- **QUÉ:** pruebas unitarias (incluye `segments.test.ts` y `api.segments.test.ts`), verificación de tipos y build.
- **EJECUCIÓN:** `npx vitest run --exclude "e2e/**"`; `npx tsc -b`; `npx vite build`
- **RESULTADO:** `Test Files 16 passed (16) · Tests 49 passed (49)`; `tsc -b` sin errores; `✓ built`.

## 5. E2E aislado (Chromium)

- **QUÉ:** flujos completos de E3 con la configuración de CR-05, incluida la aceptación de horas en la UI por `pc_sys` y la pérdida de acceso del supervisor anterior tras el cierre (BR-06).
- **EJECUCIÓN:** `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated`
- **RESULTADO:** estándar `18 passed, 4 skipped` (las 4 omitidas son las `@populated`); poblado `4 passed`.
- **Historial honesto:** las dos primeras ejecuciones fallaron por cambios de comportamiento esperados de CR-05: confirmación con horas no aceptadas (BR-04) y supervisor anterior con acceso al expediente cerrado (BR-06). Se adaptó el spec para verificar el nuevo comportamiento. En una ejecución intermedia hubo dos fallos de tiempo en el login mientras la suite backend corría en paralelo; no se repitieron en la ejecución final, sin carga concurrente.
- **Capturas:** `screenshots/dossier-desktop.png`, `screenshots/dossier-mobile.png` y `screenshots/route-documents-mobile.png`, generadas por esa ejecución. El E2E verifica que no haya desplazamiento horizontal a 390 px.

## 6. Demo aislada

- **EJECUCIÓN:** `python scripts/run_eval3_demo.py --smoke`
- **RESULTADO:** `MIGRATION_HEAD=0016`, `HEALTH=/health PASS; READINESS=/ready PASS; SYNTHETIC_LOGIN PASS`, `TEMPORARY_DATABASE_CLEANED=true`. Se corrigió la revisión esperada del lanzador (0014 → 0016), que ya fallaba desde la migración 0015.

## 7. ZIP autocontenido

- **QUÉ:** extraer `evaluacion-4.zip` en una carpeta temporal y ejecutar desde la copia `src/`, usando solo las dependencias Python instaladas.
- **EJECUCIÓN:** `python -m pytest -q tests/test_cr05_segments.py` (en `DH05_E4/src/backend`) y `python scripts/check_isolated_migrations.py` (en `DH05_E4/src`).
- **RESULTADO:** `12 passed, 1 warning in 21.28s`; migraciones completadas con `TEMPORARY_POSTGRES_CLEANED=true`.
- **Auditoría del ZIP:** sin `node_modules`, `.deps`, `__pycache__`, `dist` ni `.env` reales. El único patrón de URL con credenciales es el ejemplo ficticio de `test_database_safety.py`. El hostname de Neon del cargador se sustituyó por un placeholder en la copia empaquetada.

## No ejecutado

- Ningún despliegue, ni carga en Neon, Render o Docker.
- Ningún spec de Playwright dedicado a una rotación o transferencia completa en la UI: esos flujos se cubren con pruebas de servicio, de HTTP y unitarias del frontend.
- No se grabó video.
