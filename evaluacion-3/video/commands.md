# Comandos para la demostración

Ejecutar desde `evaluacion-3/src` con el entorno virtual ya instalado:

```powershell
$env:DATABASE_URL = ''
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'backend')
.\.venv\Scripts\python .\scripts\run_eval3_demo.py --smoke
.\.venv\Scripts\python .\scripts\run_isolated_e2e.py
.\.venv\Scripts\python .\scripts\run_isolated_e2e.py --populated
.\.venv\Scripts\python .\scripts\check_isolated_migrations.py
.\.venv\Scripts\python .\scripts\run_eval3_demo.py --open-browser
```

El primer comando valida la demo; los tres siguientes evidencian pruebas. El último inicia el stack interactivo y permanece abierto hasta Ctrl+C. Para las pruebas de frontend/build:

```powershell
corepack pnpm --dir .\frontend run test
corepack pnpm --dir .\frontend run build
```

No usar `docker compose`, no setear credenciales de Neon y no sustituir la URL temporal. El launcher genera su propio secreto temporal y no imprime la URI de PostgreSQL. La contraseña de demo que imprime solo autentica las cuentas sintéticas del clúster efímero.
