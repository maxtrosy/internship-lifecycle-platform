# Contenido de `src/`

- `src/backend/`: app FastAPI, módulos y servicios, revisiones SQL/Alembic 0001–0014, pyproject, ejemplos seguros de configuración y suite backend.
- `src/frontend/`: React/TypeScript, Vite, paquete/lockfile, pruebas unitarias y Playwright E2E.
- `src/scripts/`: runner E2E aislado, launcher aislado para la demo interactiva y validador de migraciones aisladas.
- `docs/reference/`: PDF de la evaluación y copias de diseño/ADR/trazabilidad históricos necesarios para entender el incremento.

Se excluyeron deliberadamente: `.env`, `.neon`, gestores de secretos, datos persistentes, archivos `node_modules`, cachés `.pnpm-store`/`.deps`, builds, `dist`, logs y archivos temporales de PostgreSQL. El cargador de producción de dataset no está incluido porque no se necesita para demostrar la evaluación y no debe usarse en el entorno aislado de grabación.

Las versiones de dependencias reproducibles se declaran en `src/backend/pyproject.toml`, `src/frontend/package.json` y `src/frontend/pnpm-lock.yaml`. No se incluyeron las dependencias ya instaladas: se descargan siguiendo README.
