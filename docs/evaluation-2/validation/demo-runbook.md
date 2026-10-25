# Demo reproducible y aislada

**Verificado:** 2026-10-24.

La demostración usa el proyecto Compose `dh05-demo`, el frontend `http://localhost:5174`, la API `http://localhost:8001`, PostgreSQL en `127.0.0.1:5433`, la base `dh05_demo` y el volumen `dh05-demo-postgres-data`. No apunta al proyecto Compose local (`internship-lifecycle-platform`) ni a su base `postgres` en el puerto 5432.

## Arranque conservando el conjunto de demo

Desde la raíz del repositorio, en PowerShell:

```powershell
.\scripts\Start-Demo.ps1
```

El script valida `APP_ENV=demo`, el destino de conexión `db/dh05_demo`, el volumen exacto `dh05-demo-postgres-data`, sus etiquetas de propiedad Compose y que los tres puertos publicados estén ligados a `127.0.0.1`. Si el volumen existente pertenece a otro proyecto, se detiene antes de cambiar datos. Ejecuta el seed solo si no hay cuentas; si encuentra 14, compara los nombres de usuario con el conjunto seed conocido y conserva los datos; otros conteos o usuarios detienen el script. `backend/app/demo_seed.py` vuelve a comprobar `APP_ENV=demo`, host `db`, base `dh05_demo` y que no existan cuentas antes de insertar.

## Base limpia para repetir la demo

El reset elimina **solo** el proyecto Compose y volumen de demo. Requiere escribir la frase de confirmación exacta:

```powershell
.\scripts\Start-Demo.ps1 -Reset
```

Escribe `RESET DH05 DEMO` cuando PowerShell lo solicite. Luego Compose crea un volumen vacío, ejecuta las migraciones Alembic desde el comando de inicio de la API y el script aplica una sola vez los 14 usuarios y políticas sintéticas. Si se cancela o la comprobación de configuración falla, no se hace reset.

Para verificar la configuración sin iniciar ni borrar nada:

```powershell
docker compose -p dh05-demo -f .\docker-compose.demo.yml config
docker compose -p dh05-demo -f .\docker-compose.demo.yml ps
docker compose -p dh05-demo -f .\docker-compose.demo.yml exec db psql -U postgres -d dh05_demo -c "select current_database();"
Invoke-RestMethod http://localhost:8001/health
```

La salida esperada de `current_database()` es `dh05_demo`, y el estado de salud es `ok`. Evita ejecutar `docker compose down --volumes` sin el mismo `-p dh05-demo` y `-f docker-compose.demo.yml`; el script aplica ambos y verifica el destino antes de permitir reset.

## Cuentas sintéticas para recorrer los roles

Todas las cuentas seed usan la contraseña local de demostración `Demo-Only-2026!`:

| Rol | Usuario |
|---|---|
| Estudiante | `s1`, `s2`, `s3` |
| Coordinador de programa | `pc_sys`, `pc_adm` |
| Coordinador de prácticas | `ec1` |
| Revisor legal | `legal1` |
| Miembro anfitrión | `hm_alfa`, `hm_beta` |
| Supervisor de lugar de trabajo | `ws_alfa`, `ws_alfa2`, `ws_beta` |
| Supervisor docente | `f1` |
| Coordinador/supervisor con roles múltiples | `dual1` |

Son cuentas y datos sintéticos exclusivos del entorno local de demo; no reutilizar en un entorno compartido.

## E2E

Con el entorno limpio preparado, ejecutar desde `frontend/`:

```powershell
pnpm install --frozen-lockfile
pnpm exec playwright install chromium
$env:E2E_BASE_URL = "http://localhost:5174"
pnpm run test:e2e
```

El recorrido modifica la base `dh05_demo` al crear una oportunidad, postulación, colocación, revisiones documentales y activación. La corrida verificada dejó una colocación activa E2E en la demo; usa el procedimiento de reset antes de presentar una base limpia o repetirla. La suite no restablece ni se conecta al proyecto Compose usado por el desarrollo local. La suite backend tiene su propio proyecto `dh05-tests` y base `dh05_http_test`, sin volumen persistente.
