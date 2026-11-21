# Índice de pruebas

Las pruebas ejecutables viven en `../src/backend/tests` y `../src/frontend`. Esta carpeta contiene copias de las pruebas específicas de CR-05 para facilitar la revisión.

| Archivo | Alcance |
|---|---|
| `test_cr05_segments.py` | 12 pruebas: los 18 escenarios obligatorios, concurrencia, privacidad y endpoints HTTP |
| `check_isolated_migrations.py` | Migraciones 0001→0016 y 0010→0016 con backfill de segmento |
| `test_lifecycle.py`, `test_http_authorization.py` | Regresión E3 ajustada a BR-04/BR-06 |
| `../src/frontend/src/segments.test.ts`, `api.segments.test.ts` | Helpers de la UI y contratos de la API CR-05 |
| `../src/frontend/e2e/lifecycle.spec.ts` | E2E del ciclo completo, incluida la revisión de horas |

Las pruebas usan PostgreSQL temporal (pgserver) y nunca una base persistente.
