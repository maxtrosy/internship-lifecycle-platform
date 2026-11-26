# Resultados ejecutados: versión final de DH-05 (Evaluación 4, séptima sesión)

Formato del registro de evidencia del PDF: **QUÉ / VERSIÓN / ENTORNO / EJECUCIÓN / RESULTADO**. Todos los resultados se obtuvieron ejecutando los comandos indicados; ninguno es un resultado esperado presentado como obtenido. Los registros anteriores (`test-results-2026-11-20.md`, `-11-22.md` y `-11-23.md`) se conservan como historia.

## Entorno común

- **Fecha:** 2026-11-24 (hora local).
- **Sistema:** Windows 10 Home 10.0.19045.
- **Herramientas:** Python 3.12.16 (dependencias en `backend/.deps`); Node v24.18.0; vitest 2.1.9; Playwright 1.64.1 (Chromium).
- **Base de datos:** PostgreSQL temporal (pgserver), creado y eliminado en cada ejecución. **Neon y Docker no se usaron ni se modificaron.**
- **Versión de código:** árbol de trabajo sobre el commit `67f8d56`, con los cambios de esta sesión sin commitear. Esquema Alembic `0019`.
- **Configuración CR-05 solo en bases temporales:** `PLACEMENT_SEGMENT_MANAGER_ROLES=EXPERIENTIAL_COORDINATOR` y `PLACEMENT_HOURS_REVIEWER_ROLES=FACULTY_SUPERVISOR,PROGRAM_COORDINATOR`. Ambas siguen vacías por defecto.
- **ZIP:** `evaluacion-4.zip` **no** se generó, regeneró ni modificó, y no se ejecutó el script de empaquetado. Queda pendiente de autorización expresa.

## Cambios verificados en esta sesión

1. **Ajustes de datos de segmento** (migración `0019`, ADR-015).
   - Endpoint: `PATCH /placements/{pid}/segments/{sid}`, con revisiones append-only.
   - Reglas por estado: la organización nunca se edita; la unidad o el supervisor de un segmento activo exigen una transferencia; las fechas siguen en `/schedule`.
   - Expediente: acción «Ajustar datos» e historial «Ajustes de datos».
2. **Evidencia documental de condiciones de segmento** (`0019`, ADR-015).
   - Un ítem opcional del módulo documental de E3 por cada condición documental.
   - El estudiante lo entrega en «Mis documentos»; aprobarlo en «Revisión documental» cumple la condición, y revocarlo la reabre.
   - Solo se aceptan entregas mientras el segmento está planificado; las descargas son privadas.
3. **Reporte de rotaciones:** filtro `placement_state` con lista cerrada, que también se aplica desde la página de reportes. Nueva prueba de regresión de cada filtro, sus combinaciones y el alcance de cada rol.
4. **Fixture poblada con fechas relativas:** los periodos se calculan desde el día de generación, así que el escenario del navegador ya no caduca el 15 ene 2027.
5. **Seguridad de configuración:** los secretos JWT publicados en el repositorio (el local y el de la demo) se rechazan fuera de `development` y `demo`. Antes solo se rechazaba el local, y solo con `APP_ENV=production`.

## 1. Backend completo

- **EJECUCIÓN:** `cd backend; $env:DATABASE_URL=''; python -m pytest -q -p no:cacheprovider tests`
- **RESULTADO:** `135 passed, 1 warning in 181.58s`. Ejecución final, después de todos los cambios de backend de esta sesión.
- **Comparación:** antes de esta sesión, `126 passed`.
- **Pruebas nuevas:**
  - `test_segment_attribute_changes_are_adjustments_not_transfers`
  - `test_segment_condition_evidence_reuses_the_document_module`
  - `test_rotation_report_filters_and_scope_regression`
  - `test_published_development_secrets_are_refused_outside_development` (6 casos parametrizados)
- **Advertencia:** la única es la deprecación de `httpx` en el TestClient de Starlette.

## 2. Pruebas CR-05

- **EJECUCIÓN:** `python -m pytest -q -p no:cacheprovider tests/test_cr05_segments.py tests/test_synthetic_dataset.py`
- **RESULTADO:** `29 passed`, con 18 pruebas CR-05.
- **Primer intento de la prueba de ajustes:** falló porque suponía que el segmento creado al activar tiene modalidad. Ese segmento se crea sin modalidad (la versión de la práctica no la registra). Se corrigió la prueba, no la regla.
- **Primer intento de la prueba de evidencia:** falló al completar el segmento 1 sin evaluación final (`SEGMENT_FINAL_EVALUATION_MISSING`, regla existente). Se añadió la evaluación a la prueba.

## 3. Migraciones aisladas

- **EJECUCIÓN:** `python scripts/check_isolated_migrations.py`
- **RESULTADO:**
  - `MIGRATION_CHAIN=0001->0019; ...; segment_dates_require_schedule_change=true; segment_attributes_require_revision=true; downgrade_0019_0018_roundtrip=true`
  - `MIGRATION_UPGRADE=0010->...->0018->0019; ...`
  - `TEMPORARY_POSTGRES_CLEANED=true`
- **Qué incluye:** el rechazo de un `UPDATE` directo de responsabilidades sin revisión, y el downgrade a 0017 seguido de `upgrade head`.

## 4. Frontend

- **EJECUCIÓN:** `cd frontend; npx vitest run --exclude "e2e/**"; npx tsc -b; npx vite build`
- **RESULTADO:**
  - Vitest: `Test Files 17 passed (17) · Tests 56 passed (56)`. El archivo nuevo es `segments.update.test.ts`.
  - `tsc -b`: sin errores.
  - Build: `✓ built in 1.26s`.

## 5. E2E aislado (Chromium)

- **EJECUCIÓN:** `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated`
- **RESULTADO:** estándar `18 passed, 5 skipped (1.9m)`; poblado `5 passed (37.9s)`.
- **Omitidas:** las 5 del modo estándar son las pruebas `@populated`, que se ejecutan y pasan en la segunda ejecución.
- **`rotation.spec.ts`, pasos nuevos:**
  - El estudiante sube un PDF sintético para la condición del segmento 2.
  - `legal1` lo aprueba en «Revisión documental». La API muestra la condición `SATISFIED` con evidencia `APPROVED` y la referencia del archivo.
  - `ec1` activa el segmento y lo ajusta: modalidad remota y 120 horas esperadas. El panel muestra la unidad y el supervisor como fijos, y aparece el historial «Ajustes de datos».
- **Primer intento poblado:** falló porque la prueba esperaba que la fila aprobada desapareciera de la cola. En una práctica activa, la regla de E3 la mantiene visible para poder revocarla. Se corrigió la prueba para comprobar el botón «Revocar aprobación».

## 6. Demo aislada

- **EJECUCIÓN:** `python scripts/run_eval3_demo.py --smoke`
- **RESULTADO:** `MIGRATION_HEAD=0019`, `HEALTH=/health PASS; READINESS=/ready PASS; SYNTHETIC_LOGIN PASS`, `TEMPORARY_DATABASE_CLEANED=true`.

## 7. Presentación y Markdown

- **PPTX:**
  - Se reconstruyó desde el original del curso con `build_deck.py`. Diapositiva 13: fecha 2026-11-24, esquema 0019, «Periodo, datos y evidencia con historial». Diapositiva 14: filas «Periodo y ajustes» y «Evidencia de condición», más la línea de resultados de esta sesión.
  - `validate.py` del paquete pptx: `All validations PASSED!`
  - Se renderizaron las 16 diapositivas con PowerPoint (exportación COM) y se revisaron visualmente en mosaico y una por una (13 y 14). En la primera versión de la 14, dos celdas ocupaban dos líneas; se acortaron y se volvió a renderizar.
  - Las capturas de las diapositivas 13 y 14 están en `evidence/screenshots/deck-dh05-*.png`.
- **MD:**
  - Las líneas 1–709 (§1–6.8) son idénticas al original (comparación con `diff`).
  - §6.9 se actualizó con el esquema 0019, «Datos por segmento», «Preparación», los filtros del reporte, los avisos y los resultados.

## 5b. E2E poblado repetido

Tras un último ajuste de texto en «Mis documentos» (segmento que ya no está planificado), se repitió `python scripts/run_isolated_e2e.py --populated`: `5 passed (41.5s)`. Vitest 56/56, `tsc -b` y build se repitieron después del mismo cambio, sin errores.

## 8. No ejecutado

- **Lector de pantalla real y pruebas con usuarios:** guiones preparados en `docs/operacion/verificaciones-externas-pendientes.md`.
- **Auditoría de dependencias contra bases de vulnerabilidades** (`npm audit`, `pip-audit`): requiere consultar servicios externos. No se ejecutó.
- **Revisión visual manual del nuevo panel «Ajustar datos» a 390 px y en modo oscuro:** solo hay comprobación funcional en escritorio mediante E2E. Reutiliza las clases existentes del panel lateral.
