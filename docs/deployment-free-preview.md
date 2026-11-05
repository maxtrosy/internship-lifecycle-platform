# Despliegue público gratuito de DH-05

**Estado actualizado por T-51 (2026-11-04):** Neon `long-truth-39527618/main` conserva el esquema `0013` y 28 tablas de aplicación. El preflight read-only encontró 14 cuentas base, 2 programas, 2 organizaciones sintéticas, 4 políticas de activación/finalización y 7 eventos de login/logout. No hay oportunidades, postulaciones ni prácticas, y falta política de elegibilidad; no se cargó el dataset poblado. El servicio público Render respondió HTTP 200 en `/health` y `/ready` en T-50. La URL de frontend Vercel no se verificó. Este runbook describe una demostración con datos sintéticos; no declara el sistema listo para producción institucional.

## Estado comprobado de Neon

El preflight T-48 del 2026-11-03 es histórico: antes de migrar confirmó el proyecto/branch autorizados, PostgreSQL 18.6, TLS, cero objetos de aplicación y permisos para el bootstrap. Tras autorización explícita, Neon se migró a `0012`; luego el T-49 del 2026-11-04 aplicó `0013` por la conexión administrativa separada. T-50 verificó el endpoint runtime con `app_runtime`, TLS requerido y `SET ROLE app_user`, además de los conteos actuales de tablas y registros descritos arriba. El login de runtime no tiene permiso de lectura del ledger Alembic; `/ready` responde HTTP 200 y no consulta ese ledger. No se imprimió ninguna URI.

En T-49 se auditó el rol `app_user` y se revocaron concesiones históricas amplias. `app_user` permanece `NOLOGIN`, sin flags administrativos, sin `CREATE` de esquema/base, y cuenta con una lista específica de 69 pares de privilegios de tabla y 23 grants `USAGE` de secuencia. Se creó `app_runtime` como `LOGIN` sin flags administrativos, sin grants directos de tabla y con membresía `app_user` configurada `SET TRUE`, `INHERIT FALSE`, `ADMIN FALSE`. La conexión runtime con TLS ejecutó `SET ROLE app_user`; `GET /ready` respondió HTTP 200. El rol `neondb_owner` no se usa en el servicio. El secreto aleatorio reside en Windows Credential Manager, destino `InternshipLifecyclePlatform/Neon/main/app_runtime/DATABASE_URL`; Render todavía no lo tiene. El permiso predeterminado `PUBLIC TEMP` se conserva y queda documentado como residual.

La migración remota de `main` ya se ejecutó tras autorización explícita y preflight vacío. No repitas el bloque de migración que sigue ni ejecutes `app.seed` en Neon. Ese procedimiento queda como referencia para una base o rama nueva solo después de verificar destino y ausencia de objetos/datos que preservar, con autorización expresa para ese destino. No copies la base local.

## Render Free — API

La definición está en [`render.yaml`](../render.yaml). El servicio `internship-lifecycle-api-62997789` responde ahora HTTP 200 en `/health` y `/ready`. Valores de configuración resueltos desde el repositorio:

| Campo | Configuración |
|---|---|
| Tipo y plan | Web Service · Free |
| Región | Virginia, cercana a Neon `aws-us-east-1` |
| Root Directory | `backend` |
| Python | `3.12.14` (`pyproject.toml` requiere Python `>=3.12`) |
| Build | `python -m pip install --upgrade pip && python -m pip install .` |
| Start | `python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Health check | `/ready` (requiere conexión mediante `app_user` y la tabla marcador `placement_faculty_assignment_history`, añadida en 0012; responde de forma genérica y no consulta el ledger Alembic) |
| Auto deploy | Desactivado en el Blueprint |

El Blueprint no automatiza migraciones: Render reserva el comando pre-deploy para servicios de pago, y no se incluyó una migración en el arranque del servicio Free. Primero se revisa y migra Neon con el procedimiento explícito de abajo; solo después se inicia la API.

Configura estas variables desde Render, nunca en un archivo versionado:

| Variable | Valor/fuente |
|---|---|
| `DATABASE_URL` | URI agrupada/pooler de la rama `main` de Neon, del login `app_runtime` con `SET ROLE app_user`, y `sslmode=require`; el secreto ya está en Windows Credential Manager y debe copiarse a Render solo como variable secreta al crear el servicio. No se incluye en este archivo. |
| `JWT_SECRET` | Se genera como secreto aleatorio de 256 bits desde el Blueprint de Render |
| `APP_ENV` | `production` |
| `APP_ALLOWED_ORIGINS` | Orígenes exactos de las URL de producción de Vercel, por ejemplo `https://<dominio-vercel>`; varios separados por coma, sin comodines |
| `JWT_TTL_MINUTES` | `15` |
| `PASSWORD_RESET_DELIVERY` | `disabled` hasta configurar un canal de correo institucional |

Deja sin configurar `OPPORTUNITY_REVIEWER_ROLES`, `OPPORTUNITY_PUBLISHER_ROLES` y `PLACEMENT_FACULTY_ASSIGNER_ROLES` hasta que exista una decisión institucional. No habilites autoridades por inferencia.

No hay archivos de documentos en el disco efímero de Render: los documentos y la evidencia final se guardan en PostgreSQL. No hay registro público. El preflight T-50 encontró 14 cuentas sintéticas base activas, pero no probó inicio de sesión ni roles en el navegador; no publiques credenciales sintéticas de prueba. La aplicación aún no tiene oportunidades ni prácticas para una demostración poblada.

## Neon Free — PostgreSQL

Render debe recibir `DATABASE_URL` como secreto usando la URI pooler de `app_runtime`, con `sslmode=require`. El backend ejecuta `SET ROLE app_user` dentro de cada transacción, compatible con la conexión pooler validada. `app_user` es `NOLOGIN`; `neondb_owner` conserva sus flags y membresía preexistentes y **no** es la credencial del servicio. No pongas la URI en `render.yaml`, GitHub, Vercel, documentación ni logs. Para una rama/base nueva, usa la conexión administrativa directa/unpooled separada del runtime y **solo después de confirmar explícitamente el destino autorizado y que está vacío**, ejecuta desde `backend/`:

```powershell
neon status
$env:DATABASE_URL = (& neon connection-string main --ssl require 2>$null | Out-String).Trim()
if (-not $env:DATABASE_URL.StartsWith('postgresql://')) { throw 'No se obtuvo una URI PostgreSQL de Neon.' }
if (([uri]$env:DATABASE_URL).Host -notlike '*.neon.tech') { throw 'El destino no es Neon; se cancela la migración.' }
python -m alembic upgrade head
python -m alembic current
Remove-Item Env:DATABASE_URL
```

La asignación captura la URI sin imprimirla. `neon status` debe mostrar el proyecto esperado y la rama autorizada para esa ejecución. La salida final debe indicar `0013 (head)` en el código actual. Si hay tablas, datos o una revisión existente inesperada en un destino aún no autorizado, detente y no ejecutes `upgrade`. No uses `alembic downgrade`: las migraciones actuales son intencionalmente irreversibles.

## Dataset sintético persistente — preflight T-51

El cargador está en [`scripts/persist_synthetic_dataset.py`](../scripts/persist_synthetic_dataset.py). Su comando por defecto es de solo lectura y usa la credencial runtime desde Windows Credential Manager:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
python scripts/persist_synthetic_dataset.py
```

La aplicación del lote no está autorizada por el estado actual del preflight. No se puede habilitar mientras falte una política de elegibilidad persistida para cada programa, estén sin decidir las autoridades institucionales de revisión/publicación/supervisión docente, no exista un snapshot hijo de `main` creado en las últimas 24 horas y no esté provisionada una credencial puntual de escritura separada. El login `app_runtime` no recibe grants adicionales. El ejecutable tampoco lee la política temporal de `100 créditos/nivel 6` ni establece roles de autoridad por cuenta propia.

Una vez resueltos y comprobados esos requisitos, la herramienta valida de nuevo el destino y pide confirmación interactiva antes de escribir:

```powershell
python scripts/persist_synthetic_dataset.py --apply `
  --confirm-target long-truth-39527618/main `
  --backup-branch-id <id-de-la-rama-snapshot-reciente>
```

El escritor de una sola operación se obtiene únicamente de Windows Credential Manager, destino `InternshipLifecyclePlatform/Neon/main/synthetic_loader/DATABASE_URL`; no se configura en Render. Las contraseñas nuevas son independientes y se guardan en Credential Manager, nunca se imprimen. `--apply` aún requiere verificación controlada después de que los prerrequisitos estén completos; no se ejecutó en T-51.

## Vercel Hobby — frontend

La configuración está en [`frontend/vercel.json`](../frontend/vercel.json). En el proyecto de Vercel establece:

| Campo | Configuración |
|---|---|
| Root Directory | `frontend` |
| Framework | Vite |
| Install Command | `pnpm install --frozen-lockfile` |
| Build Command | `pnpm run build` (`tsc -b && vite build`) |
| Output Directory | `dist` |
| API URL variable | No se necesita `VITE_API_URL`: la app solicita rutas relativas y Vercel las reescribe al API |

El destino de proxy preparado es `https://internship-lifecycle-api-62997789.onrender.com`, correspondiente al nombre de servicio del Blueprint. Confirma el dominio que Render asigne; si difiere, actualiza los destinos en `frontend/vercel.json` antes del primer build público. Las rutas de API se reescriben antes del fallback SPA y las respuestas de API indican `Cache-Control: no-store`. El proxy conserva la app en un mismo origen y la cookie de sesión `HttpOnly`, `Secure`, `SameSite=Strict`; el origen de producción debe coincidir exactamente con `APP_ALLOWED_ORIGINS` en Render.

No configures `VITE_DEMO_LOGIN_ENABLED` ni `VITE_DEMO_LOGIN_PASSWORD`. La vista de demo está deshabilitada por defecto en builds de producción.

## Orden de publicación y comprobaciones

El servicio API de Render está público y sus rutas `/health` y `/ready` respondieron HTTP 200 en T-50. No se verificó una URL de frontend Vercel ni flujos funcionales públicos. El código T-51 del cargador está solo en el árbol local; no se hizo `git add`, commit o push. No se debe desplegar ese cambio antes de revisar y aprobar el diff.

1. Revisa el diff actual; cualquier publicación del cargador requiere aprobación y un commit/push autorizados por separado.
2. Cuando la revisión aprobada llegue a la rama Git importable, actualiza el servicio Render existente o confirma su Blueprint, con `DATABASE_URL` runtime desde el almacén protegido, origen Vercel y `JWT_SECRET` generado.
3. Crea o verifica el proyecto Vercel Hobby (`frontend`), configura la reescritura al dominio real de Render y comprueba ambos extremos.
4. T-50 comprobó públicamente `GET /health` y `GET /ready`: HTTP 200 en ambos. Siguen pendientes los flujos públicos de login, permisos, oportunidades, expediente, documentos, horas, plan de trabajo, notificaciones, mensajería, reportes y persistencia tras recargar. Neon conserva las cuentas/políticas base, pero no tiene oportunidades, postulaciones, prácticas ni elegibilidad configurada.

## Rollback y límites del plan gratuito

- Frontend: promover desde Vercel el deployment de producción anterior.
- API: Render Free conserva rollback solo a los dos deploys exitosos anteriores. Comprueba la revisión antes de volver atrás.
- Base: no hay un downgrade seguro para las migraciones actuales. Si ya hubo escrituras, no reviertas el esquema a ciegas; preserva datos y prepara una migración correctiva o una restauración de Neon revisada antes de tocar la rama.
- Render Free duerme el servicio tras 15 minutos sin tráfico (el siguiente inicio puede tardar alrededor de un minuto), puede reiniciarlo, no ofrece discos persistentes ni SSH, y Render desaconseja usar Free para aplicaciones de producción. Neon Free puede suspender cómputo inactivo; el anuncio actual de octubre de 2026 indica 1 GB de almacenamiento, 100 CU-horas por proyecto/mes, hasta 2 CU, 10 ramas y ventana de restauración instantánea de 6 horas. Vercel Hobby se limita por sus términos a uso personal o no comercial y esos términos indican que contenido en Hobby puede usarse para entrenar modelos de IA; confirma que el uso previsto cumple los términos. No se deben alojar datos personales reales de estudiantes en esta demostración gratuita sin autorización institucional y revisión de privacidad aplicables.

Fuentes oficiales: [Render Free](https://render.com/docs/free), [Render Blueprint](https://render.com/docs/blueprint-spec), [comandos de despliegue Render](https://render.com/docs/deploys), [Render Python](https://render.com/docs/python-version), [Vercel rewrites](https://vercel.com/docs/routing/rewrites), [Vercel configuración de builds](https://vercel.com/docs/builds/configure-a-build), [términos de Vercel](https://vercel.com/legal/terms), [pooler y semántica de sesión Neon](https://neon.com/blog/inside-lubots-database-per-tenant-architecture), [límites actuales de Neon Free](https://neon.com/blog/neon-free-plan-1-gb-per-project).
