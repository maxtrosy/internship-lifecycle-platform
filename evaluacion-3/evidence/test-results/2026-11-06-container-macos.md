# Validación del paquete Docker para grabación en macOS

Fecha de ejecución: 2026-11-06. Entorno de prueba: Windows con Docker Desktop, Engine 29.5.3, Compose 5.1.4 y contenedores Linux `x86_64` en WSL2. No es una ejecución sobre Mac físico; la receptora debe construir las imágenes en su propio Docker Desktop para usar la arquitectura nativa.

## Resultados

| Comprobación | Resultado |
|---|---|
| `docker compose ... config --quiet` | **PASS** para `compose.macos.yaml` y el override de subred. |
| `docker compose ... build` | **EXIT 0** para backend/bootstrap y frontend/nginx. El build de frontend compiló TypeScript y Vite: 64 módulos. En pnpm 11 se autorizó únicamente el script de instalación de `esbuild`, que Vite necesita; el ajuste vive en el Dockerfile de demo. La política `allowBuilds` es la opción documentada por pnpm para este control. |
| Alembic | `MIGRATION_HEAD=0014`. |
| Rol de runtime | `app_runtime` conectó y `SET ROLE app_user` fue exitoso. API recibió únicamente la URL local de runtime; el bootstrap temporal usó el rol administrador interno de PostgreSQL para migrar y sembrar. |
| Fixture | 61 cuentas, 10 organizaciones, 16 oportunidades, 24 postulaciones y 12 prácticas, todas sintéticas. |
| API / UI | `/health=ok`, `/ready=ready`, HTML de SPA HTTP 200. Login HTTP 200 como `demo_student_07`; `GET /auth/me`, `/placements` y el expediente cerrado respondieron correctamente. |
| Aislamiento Docker | Puerto web publicado solo en `127.0.0.1:18080`; API y PostgreSQL no publican puertos al host. PostgreSQL usa tmpfs de 512 MB; `docker inspect` informó `Mounts=[]`. |
| Limpieza de ejecución | `docker compose down` dejó 0 contenedores y 0 redes del proyecto de validación. No se tocaron contenedores o volúmenes preexistentes, Neon ni PostgreSQL local. |

Comandos principales ejecutados en Windows PowerShell:

```powershell
$env:DH05_DEMO_PORT = '18080'
$env:DH05_DEMO_SUBNET = '10.255.255.0/24'
docker compose -p dh05-eval3-validation -f evaluacion-3/compose.macos.yaml -f evaluacion-3/compose.macos.subnet.yaml config --quiet
docker compose -p dh05-eval3-validation -f evaluacion-3/compose.macos.yaml -f evaluacion-3/compose.macos.subnet.yaml build
docker compose -p dh05-eval3-validation -f evaluacion-3/compose.macos.yaml -f evaluacion-3/compose.macos.subnet.yaml up -d
# Se comprobaron HTTP, login, expediente, conteos, el montaje tmpfs y el bind loopback.
docker compose -p dh05-eval3-validation -f evaluacion-3/compose.macos.yaml -f evaluacion-3/compose.macos.subnet.yaml down
```

El rango Docker automático del host de prueba estaba agotado, así que se usó `compose.macos.subnet.yaml` con una subred libre. La configuración principal no fija una subred; en una Mac normal Compose selecciona una automáticamente. Si la Mac receptora tiene el mismo problema, debe seguir la nota de red en `README-macos-demo.md` y seleccionar un bloque libre.

En la primera iteración de validación, la imagen oficial de PostgreSQL creó su volumen anónimo por defecto. Se inspeccionó y eliminó únicamente ese recurso temporal generado por esa prueba. El Compose final sustituye el directorio de datos por tmpfs; la inspección de la ejecución final confirmó que no se creó ningún volumen.

La primera instalación pnpm de la imagen falló por la política nueva de scripts ignorados; se corrigió aprobando el build de `esbuild` de forma específica, no habilitando scripts arbitrarios. [Documentación oficial de pnpm sobre aprobaciones de builds](https://pnpm.io/cli/approve-builds).

El ZIP transporta la configuración y el código, no imágenes OCI preconstruidas. La amiga debe tener Docker Desktop y conexión a Internet la primera vez para descargar imágenes base y dependencias. Esto permite que Docker construya para la arquitectura de su Mac. La presentación no debe describir la fixture como dato real ni como decisión universitaria.
