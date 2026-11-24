# Instalación, ejecución y reproducción

Todo se ejecuta contra **PostgreSQL temporal** (pgserver), que se crea y se borra automáticamente. No se usa Neon, Docker ni ninguna base persistente.

## Requisitos

- Python 3.12 con las dependencias de `src/backend/pyproject.toml`, incluidas las de desarrollo (pgserver, pytest, alembic, psycopg). Recomendación: un entorno virtual o `uv`, sin tocar el Python global.
- Node.js 20+ y las dependencias de `src/frontend` (`pnpm install` o `npm install`).
- Para el E2E, Chromium de Playwright: `npx playwright install chromium`.

## 1. Identificar

La raíz del paquete contiene `src/backend`, `src/frontend` y `src/scripts`. La configuración de ejemplo está en `config/.env.example`, sin secretos.

## 2. Preparar

```powershell
cd src/backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
cd ../frontend
npm install
```

## 3. Adaptar datos

No hace falta preparar datos: las pruebas, el E2E y la demo siembran **usuarios sintéticos** (`docs/operacion/usuarios-y-datos-demo.md`). Las autoridades de CR-05 se configuran solo para esas bases temporales.

## 4. Ejecutar

```powershell
# Backend (desde src/backend; usa pgserver si DATABASE_URL está vacío)
$env:DATABASE_URL = ''
python -m pytest -q tests
# Solo CR-05
python -m pytest -q tests/test_cr05_segments.py
# Migraciones 0001→0018 y 0010→0018 (desde src/)
python scripts/check_isolated_migrations.py
# Frontend (desde src/frontend)
npx vitest run --exclude "e2e/**"
npx tsc -b; npx vite build
# E2E aislado con Chromium (desde src/)
python scripts/run_isolated_e2e.py
# E2E con la fixture sintética poblada, incluido el recorrido CR-05 (rotation.spec.ts)
python scripts/run_isolated_e2e.py --populated
# Demo interactiva aislada (desde src/); imprime la URL y la contraseña sintética
python scripts/run_eval3_demo.py --open-browser
```

`run_eval3_demo.py` conserva su nombre de E3, pero ejecuta el código vigente (esquema 0018) y configura `PLACEMENT_SEGMENT_MANAGER_ROLES=EXPERIENTIAL_COORDINATOR` y `PLACEMENT_HOURS_REVIEWER_ROLES=FACULTY_SUPERVISOR,PROGRAM_COORDINATOR` solo para la base temporal.

## 5. Verificar

Compara tus salidas con `evidence/test-results-2026-11-23.md`. Para el recorrido manual de CR-05, usa `docs/operacion/guion-de-demostracion.md`.
