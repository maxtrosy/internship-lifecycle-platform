# Resultados ejecutados: versión final de DH-05 (Evaluación 4)

Formato del registro de evidencia del PDF: **QUÉ / VERSIÓN / ENTORNO / EJECUCIÓN / RESULTADO**. Todos los resultados se obtuvieron ejecutando los comandos indicados en esta sesión; ninguno es un resultado esperado presentado como obtenido. El registro anterior (`test-results-2026-11-20.md`) se conserva como historia.

## Entorno común

- **Fecha:** 2026-11-22 y 2026-11-23 (hora local; la sesión cruzó medianoche).
- **Sistema:** Windows 10 Home 10.0.19045.
- **Python:** 3.12.16 (intérprete gestionado por uv en `~/.local/bin`, dependencias en `backend/.deps`; el Python global no se modificó).
- **Node:** v24.18.0 · vitest 2.1.9 · Playwright 1.64.1 con Chromium (dependencias de `frontend/node_modules`).
- **Base de datos:** PostgreSQL temporal (pgserver) creado y eliminado en cada ejecución. **Neon y Docker no se usaron ni se modificaron.**
- **Versión de código:** árbol de trabajo sobre el commit `36c125e`, con los cambios de esta sesión sin commitear. Esquema Alembic `0017`.
- **Configuración CR-05 solo en bases temporales:** `PLACEMENT_SEGMENT_MANAGER_ROLES=EXPERIENTIAL_COORDINATOR` y `PLACEMENT_HOURS_REVIEWER_ROLES=FACULTY_SUPERVISOR,PROGRAM_COORDINATOR`. Ambas variables quedan vacías por defecto: no son política institucional.

## 1. Backend completo

- **QUÉ:** todas las pruebas backend (E1–E3, CR-05, reportes y avisos).
- **EJECUCIÓN:** `cd backend; $env:DATABASE_URL=''; python -m pytest -q -p no:cacheprovider tests`
- **RESULTADO:** `125 passed, 1 warning in 251.84s (0:04:11)`. La advertencia es la deprecación de `httpx` en el TestClient de Starlette y no está relacionada con el cambio. Antes de esta sesión: `123 passed`.

## 2. Pruebas CR-05

- **QUÉ:** `tests/test_cr05_segments.py`, con los escenarios de segmentos, transferencias, horas, cierre combinado y permisos, más dos pruebas nuevas:
  - `test_rotation_reports_aggregate_cr05_state_within_scope`: indicadores, alcance por programa, `403` para empleador y estudiante, sin motivos ni nombres en la respuesta.
  - `test_segment_events_notify_related_people_but_not_the_previous_supervisor`.
- **EJECUCIÓN:** `python -m pytest -q -p no:cacheprovider tests/test_cr05_segments.py`
- **RESULTADO:** `14 passed, 1 warning in 25.78s`.

## 3. Migraciones aisladas

- **QUÉ:** cadena 0001→0017 con datos heredados y actualización 0010→0017. La migración `0017` solo amplía la restricción de categorías de aviso con `SEGMENT_CHANGED`.
- **EJECUCIÓN:** `python scripts/check_isolated_migrations.py`
- **RESULTADO:**
  ```text
  MIGRATION_CHAIN=0001->0017; initial_status_absent=true; cr05_migrated_single_segment=true; legacy_records_attached_to_segment=true; legacy_hours_left_pending_review=true; legacy_incident_status=REPORTED; closed_work_plan_guard=true; notifications_and_audience_scoped_messages=true; opportunity_state_guard=true; manual_eligibility_review_notification=true; faculty_assignment_history=true; app_user_minimal_grants=true
  MIGRATION_UPGRADE=0010->0011->0012->0013->0014->0015->0016->0017; opportunity_state_guard=true; faculty_assignment_history=true; manual_eligibility_review_notification=true; app_user_minimal_grants=true
  TEMPORARY_POSTGRES_CLEANED=true
  ```

## 4. Frontend

- **QUÉ:** pruebas unitarias (incluida la URL de `getRotationReports` en `api.segments.test.ts`), verificación de tipos y build.
- **EJECUCIÓN:** `cd frontend; npx vitest run --exclude "e2e/**"; npx tsc -b; npx vite build`
- **RESULTADO:** `Test Files 16 passed (16) · Tests 51 passed (51)`; `tsc -b` sin errores; `✓ built in 1.20s`.

## 5. E2E aislado (Chromium)

- **QUÉ:** flujos de E1–E3 con la configuración CR-05, el rediseño institucional y el recorrido en navegador del criterio DH-05 del PDF: «Una transferencia conserva horas aceptadas» / «Supervisor previo: sin acceso automático» (`e2e/rotation.spec.ts`).
- **EJECUCIÓN:** `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated`
- **RESULTADO:** estándar `18 passed, 5 skipped` (las 5 omitidas son las `@populated`, que corren en la segunda ejecución); poblado `5 passed (36.6s)`.
- **Qué comprueba `rotation.spec.ts`:**
  1. La coordinación del programa acepta las horas reportadas.
  2. La coordinación de experiencias transfiere el segmento a otra organización desde el panel lateral.
  3. El destino no se activa antes de su condición documental. Revisión jurídica la confirma y luego se activa.
  4. El supervisor anterior recibe `404` en el expediente. El nuevo ve solo su segmento y recibe el aviso `SEGMENT_CHANGED`.
  5. El estudiante ve las mismas horas aceptadas, el motivo compartido y el aviso, sin el motivo interno.
  6. El reporte «Rotaciones y transferencias» cuenta la transferencia.
- **Historial honesto:**
  - Las primeras ejecuciones de `rotation.spec.ts` revelaron un defecto real de la interfaz: tras una acción, el expediente se recargaba desmontándose y el aviso «Transferencia registrada.» desaparecía. Se corrigió en `PracticeDossier.tsx` (refresco en el sitio) sin tocar la prueba.
  - Otro intento falló porque la coordinación de experiencias no lee horas por diseño de E3. La comprobación de horas pasó a hacerse con la persona revisora y con el estudiante.
  - La primera ejecución estándar falló en `lifecycle.spec.ts:142` y `visual-ui.spec.ts:210`: la nueva sección de reportes reutilizaba las clases `.page-stack` y `.report-tables`. Se dieron clases propias a la sección (`.rotation-*`) en vez de cambiar las pruebas existentes.

## 6. Demo aislada

- **EJECUCIÓN:** `python scripts/run_eval3_demo.py --smoke`
- **RESULTADO:** `MIGRATION_HEAD=0017`, `HEALTH=/health PASS; READINESS=/ready PASS; SYNTHETIC_LOGIN PASS`, `TEMPORARY_DATABASE_CLEANED=true`.

## 7. ZIP autocontenido

- **QUÉ:** regenerar el paquete, extraer `evaluacion-4.zip` en una carpeta temporal y ejecutar desde la copia `src/`, usando solo las dependencias Python instaladas.
- **EJECUCIÓN:** `python scripts/build_eval4_package.py`; luego `python -m pytest -q tests/test_cr05_segments.py` (en `DH05_E4/src/backend`) y `python scripts/check_isolated_migrations.py` (en `DH05_E4/src`).
- **RESULTADO:**
  - `FILES=255`, sin `.env`, `node_modules` ni `.deps` en el ZIP, con la migración 0017, `rotation.spec.ts`, ADR-013 y las copias del MD y el PPTX.
  - `14 passed, 1 warning in 23.53s`.
  - `MIGRATION_CHAIN=0001->0017`, `TEMPORARY_POSTGRES_CLEANED=true`.
  - La carpeta temporal se eliminó.

## 8. Límites de esta evidencia

- No se hizo revisión con lector de pantalla real ni pruebas con usuarios. La auditoría de accesibilidad es automatizada (contraste calculado, nombres accesibles, foco, 390 px).
- Las fechas del fixture poblado son sintéticas y fijas (2026–2027). Si el reloj del equipo supera esas fechas, algunos escenarios dependientes del calendario podrían cambiar de estado.
- Las autoridades CR-05 usadas en pruebas son supuestos reemplazables, no decisiones de Horizon University (OPEN-CR05-01 y 02).
