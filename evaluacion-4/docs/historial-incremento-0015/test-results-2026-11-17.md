# Resultados de validación — 2026-11-17

- Migraciones aisladas: `0001→0015` y `0010→0011→0012→0013→0014→0015`, exitosas; PostgreSQL temporal limpiado.
- Backend focalizado: `21 passed`.
- Backend completo: `111 passed, 1 warning`.
- Frontend: `41 passed en 14 archivos`.
- Build: `tsc -b && vite build`, `EXIT 0`, 64 módulos.
- E2E poblado: `4 passed`, base temporal limpiada.
- Inspección visual: expediente con contexto de versión revisado en escritorio, móvil 390 px y oscuro; no se observó desbordamiento horizontal.
- `git diff --check`: correcto.

El warning es `StarletteDeprecationWarning` del adaptador TestClient/httpx. No se modificaron Neon, Docker ni bases persistentes.
