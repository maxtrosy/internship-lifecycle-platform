# Comandos ejecutados

El entorno backend se creó temporalmente con Python 3.12.16 mediante `uv`; no se modificó el intérprete global.

```powershell
python scripts/check_isolated_migrations.py
cd backend
python -m pytest -q tests/test_lifecycle.py
python -m pytest -q tests
cd ../frontend
pnpm run test
pnpm run build
cd ..
python scripts/run_isolated_e2e.py --populated
git -c core.autocrlf=false diff --check
```

Las pruebas E2E crean PostgreSQL temporal y lo limpian automáticamente. Neon y Docker no forman parte del entorno de validación.
