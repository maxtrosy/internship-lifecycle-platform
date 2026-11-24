# Resultados ejecutados: auditoría final de DH-05 (Evaluación 4)

Formato del registro de evidencia del PDF: **QUÉ / VERSIÓN / ENTORNO / EJECUCIÓN / RESULTADO**. Todos los resultados se obtuvieron ejecutando los comandos indicados; ninguno es un resultado esperado presentado como obtenido. Los registros anteriores (`test-results-2026-11-20.md` y `test-results-2026-11-22.md`) se conservan como historia.

## Entorno común

- **Fecha:** 2026-11-23 y 2026-11-24 (hora local).
- **Sistema:** Windows 10 Home 10.0.19045.
- **Python:** 3.12.16 (`~/.local/bin`, dependencias en `backend/.deps`).
- **Node:** v24.18.0 · vitest 2.1.9 · Playwright 1.64.1 (Chromium).
- **Base de datos:** PostgreSQL temporal (pgserver), creado y eliminado en cada ejecución. **Neon y Docker no se usaron ni se modificaron.**
- **Versión de código:** árbol de trabajo sobre el commit `e7bf234`, con los cambios de esta auditoría sin commitear. Esquema Alembic `0018`.
- **Configuración CR-05 solo en bases temporales:** `PLACEMENT_SEGMENT_MANAGER_ROLES=EXPERIENTIAL_COORDINATOR` y `PLACEMENT_HOURS_REVIEWER_ROLES=FACULTY_SUPERVISOR,PROGRAM_COORDINATOR`. Ambas siguen vacías por defecto.
- **ZIP:** `evaluacion-4.zip` **no** se regeneró en esta auditoría. Corresponde al estado del 2026-11-22 (esquema 0017) y deberá regenerarse cuando se autorice.

## Cambios verificados en esta auditoría

1. **Excepciones temporales (§6.3):** acortar o extender un segmento abierto, o mover uno planificado.
   - Migración `0018` y ADR-014.
   - `POST /placements/{pid}/segments/{sid}/schedule` con historial append-only, aviso `SEGMENT_CHANGED` y la acción «Cambiar fechas» o «Cambiar fecha de fin» en el expediente.
2. **Reporte de rotaciones:** el filtro `organization_id` ahora incluye la organización de cada segmento. Antes solo usaba la de la oportunidad, así que una transferencia a otra organización no aparecía al filtrar por ella.
3. **Presentación:**
   - La diapositiva 16 (guía) tenía texto desbordado fuera de sus tarjetas.
   - Las diapositivas 13 y 14 tenían un espaciado de letras distinto al del resto.
   - La diapositiva 13 presentaba como «Diseñado» un acceso histórico configurable que ADR-012 no diseña. Se movió a «Pendiente» (OPEN-CR05-05).

## 1. Backend completo

- **EJECUCIÓN:** `cd backend; $env:DATABASE_URL=''; python -m pytest -q -p no:cacheprovider tests`
- **RESULTADO:** `126 passed, 1 warning in 165.70s`. La advertencia es la deprecación de `httpx` en el TestClient de Starlette. Antes de esta auditoría: `125 passed`.

## 2. Pruebas CR-05

- **EJECUCIÓN:** `python -m pytest -q -p no:cacheprovider tests/test_cr05_segments.py`
- **RESULTADO:** `15 passed, 1 warning in 22.34s`.
- **Nuevo:** `test_segment_schedule_changes_follow_explicit_rules_and_keep_history`.
  - Rechazos: personas sin la autoridad configurada (supervisor laboral, estudiante, supervisión docente); inicio de un segmento activo; fin antes de hoy; periodo sin cambio; motivo vacío; fechas invertidas; segmento cancelado.
  - Historial append-only visible solo con el motivo compartido.
  - Un `UPDATE` directo de fechas y un `UPDATE` del historial son rechazados por triggers.
  - Auditoría y aviso, y respuesta HTTP 200 y 403/404.
- **Ampliado:** `test_rotation_reports_aggregate_cr05_state_within_scope` comprueba el filtro por la organización del segmento destino.
- **Primer intento:** falló porque la prueba registraba horas con fecha futura, que la regla existente `HOURS_WORK_DATE_INVALID` rechaza. Se corrigió la prueba, no la regla. Por eso la comprobación de horas fuera del nuevo periodo es defensiva en un segmento activo (ADR-014).

## 3. Migraciones aisladas

- **EJECUCIÓN:** `python scripts/check_isolated_migrations.py`
- **RESULTADO:** `MIGRATION_CHAIN=0001->0018; ...; app_user_minimal_grants=true; segment_dates_require_schedule_change=true; downgrade_0018_roundtrip=true`, `MIGRATION_UPGRADE=0010->...->0017->0018; ...` y `TEMPORARY_POSTGRES_CLEANED=true`.

## 4. Frontend

- **EJECUCIÓN:** `cd frontend; npx vitest run --exclude "e2e/**"; npx tsc -b; npx vite build`
- **RESULTADO:** `Test Files 16 passed (16) · Tests 52 passed (52)`; `tsc -b` sin errores; `✓ built in 1.21s`.

## 5. E2E aislado (Chromium)

- **EJECUCIÓN:** `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated`
- **RESULTADO:** estándar `18 passed, 5 skipped (2.1m)`; poblado `5 passed (1.6m)`.
- **Omitidas:** las 5 omitidas del modo estándar son las pruebas `@populated`. Requieren la fixture poblada y se ejecutan, y pasan, en la segunda ejecución. Ninguna prueba queda sin ejecutar.
- **`rotation.spec.ts`:** ahora también extiende desde el panel lateral el segmento activo destino. Comprueba que el inicio está bloqueado, el aviso de éxito, el historial «Cambios de periodo» y, por API, la nueva fecha de fin y el registro del cambio.
- **Historial honesto:** la primera ejecución en segundo plano se interrumpió al cerrarse la sesión anterior, después de la suite estándar. La ejecución poblada se repitió completa.

## 6. Demo aislada

- **EJECUCIÓN:** `python scripts/run_eval3_demo.py --smoke`
- **RESULTADO:** `MIGRATION_HEAD=0018`, `HEALTH=/health PASS; READINESS=/ready PASS; SYNTHETIC_LOGIN PASS`, `TEMPORARY_DATABASE_CLEANED=true`.

## 7. Presentación y Markdown

- **PPTX:** se renderizaron las 16 diapositivas con PowerPoint (exportación COM) y se revisaron visualmente. Después de las correcciones se renderizaron otra vez las diapositivas 13, 14 y 16. `validate.py` del paquete pptx: `All validations PASSED!`
- **MD:** las líneas 1–709 (secciones 1 a 6.8) son idénticas al original entregado por el curso. La única diferencia es la sección 6.9 insertada antes de §7.

## 8. Límites de esta evidencia

- No hubo revisión con lector de pantalla real ni pruebas con usuarios.
- La fixture poblada usa fechas fijas (1 sep 2026 – 15 ene 2027). `rotation.spec.ts` debe ejecutarse antes del 15 ene 2027 o con la fixture actualizada.
- Las autoridades CR-05 usadas en pruebas son supuestos reemplazables, no decisiones de Horizon University (OPEN-CR05-01 y 02).
