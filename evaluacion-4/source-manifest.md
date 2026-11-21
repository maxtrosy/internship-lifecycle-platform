# Manifiesto de fuentes

`src/` es una copia generada por `scripts/build_eval4_package.py` desde el repositorio en la fecha del paquete. Excluye dependencias (`node_modules`, `.deps`, `.venv`), salidas de build (`dist`, `test-results`), cachés, `.env` reales y datos locales. Solo incluye `.env.example`. La copia parcial anterior de Codex (7 archivos del incremento 0015) quedó reemplazada por esta copia completa; su contenido está contenido en ella.

## Archivos nuevos de CR-05

- `src/backend/app/modules/lifecycle/segments.py`: segmentos, condiciones, transferencias, terminación, revisión de horas y revisión combinada.
- `src/backend/migrations/versions/0016_rotational_segments_and_transfers.py` y `UPGRADE_0016_SQL` en `src/backend/migrations/schema_sql.py`.
- `src/backend/tests/test_cr05_segments.py`.
- `src/frontend/src/segments.ts`, `segments.test.ts`, `api.segments.test.ts`.
- `src/frontend/src/components/PlacementSegments.tsx`, `HoursReviewList.tsx`.
- `src/scripts/build_eval4_package.py`.

## Archivos modificados por CR-05

- Backend: `app/config.py` (autoridades configurables), `app/modules/authz/service.py` (relación por segmento), `app/modules/lifecycle/service.py` (horas, registros, gates, expediente), `app/modules/lifecycle/router.py` (endpoints), `app/modules/notifications/service.py` (supervisor operativo), `app/synthetic_dataset.py` (aceptación de horas en la demo), `.env.example`.
- Pruebas E3 ajustadas a BR-04/BR-06: `tests/conftest.py`, `tests/test_lifecycle.py`, `tests/test_http_authorization.py`.
- Frontend: `src/api.ts`, `src/pages/PracticeDossier.tsx`, `src/pages/Documents.tsx`, `src/progress.ts`, `src/theme.css`, `e2e/lifecycle.spec.ts`.
- Scripts: `check_isolated_migrations.py` (head 0016 y backfill), `run_isolated_e2e.py`, `run_eval3_demo.py`, `persist_synthetic_dataset.py` (configuración de CR-05 solo para bases temporales).

No se modificaron Neon, Docker (`compose*.yaml`, `Dockerfile*`), `render.yaml` ni los paquetes de Evaluación 3.
