# Comandos para la demostración

## Opción recomendada para la Mac de la persona que graba

Desde la carpeta `evaluacion-3` extraída, con Docker Desktop iniciado:

```sh
docker compose -p dh05-eval3-share -f compose.macos.yaml up --build -d
docker compose -p dh05-eval3-share -f compose.macos.yaml ps -a
docker compose -p dh05-eval3-share -f compose.macos.yaml logs bootstrap
```

Abrir `http://localhost:8080`. Si se usó el override de red por agotamiento de subredes, añadir `-f compose.macos.subnet.yaml` a cada comando. Al terminar:

```sh
docker compose -p dh05-eval3-share -f compose.macos.yaml down
```

La guía completa está en `README-macos-demo.md`.

## Opción nativa sin Docker

Ejecutar desde `evaluacion-3/src` con Python 3.12, dependencias instaladas y Chromium listo:

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

No configurar credenciales de Neon ni sustituir la URL temporal. El launcher nativo genera su propio secreto temporal y no imprime la URI de PostgreSQL. La contraseña de demo autentica únicamente cuentas sintéticas. Para la opción Docker, la base está en tmpfs y no tiene volumen persistente.
