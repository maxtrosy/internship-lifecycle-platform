# Estado del proyecto

**Fecha de corte:** 2026-11-05. **Regla:** nada se marca como completado si solo fue diseñado. Los resultados T-48 y anteriores se conservan como históricos; T-49 verificó el runtime de Neon, T-50 el estado previo de los datos y T-51 la herramienta de carga antes del refactor parcial.

La matriz requisito por requisito vigente está en [functional-completeness-matrix.md](functional-completeness-matrix.md). El RFP fuente de ocho páginas ya se contrastó completo; faltan en el repositorio los originales de Evaluación 1 y documentos institucionales que definan OPEN-xx.

### Cargador persistente — carga parcial segura T-52, revalidación 2026-11-05
- Se agregó `--mode partial`, independiente de `--mode full`: 10 organizaciones, hasta 47 cuentas con relaciones y 16 oportunidades solo `DRAFT`/`IN_REVIEW`. No crea postulaciones, prácticas, políticas ni cierres. Oportunidades y notificaciones siguen los servicios de dominio; catálogos/cuentas usan un bootstrap justificado y limitado. Los nombres/perfiles/relaciones existentes se verifican y no se sobreescriben.
- El `app_bootstrap` de partial no recibe membresía en `app_user`; el preflight compara todos sus permisos efectivos de columnas/tablas/secuencias/esquemas con una allowlist y rechaza cualquier extra. No permite escribir programas, políticas, postulaciones o prácticas, leer hashes, borrar filas ni crear esquema. `app_runtime` no cambia. Contraseñas independientes requieren flag explícito para escribir Credential Manager; el valor nunca aparece en salida.
- El corte anterior de T-52 reportó **94 passed** y queda como histórico. La revalidación del 2026-11-05: backend **97 passed, 1 warning (135.30 s)**; prueba focal **9/9 (39.85 s)**; E2E poblado Chromium **4/4 (25.8 s)** con PostgreSQL temporal; dry-run partial **EXIT 2** (solo lectura) y full **EXIT 2**. Neon confirmó target `long-truth-39527618/main`, TLS, 14 cuentas base, 2 organizaciones, 2 programas, 4 políticas de activación/finalización, 9 eventos de auditoría y cero oportunidades/postulaciones/prácticas. Partial prevé 8 organizaciones, 47 cuentas/relaciones, 16 oportunidades y 24 auditorías; excluye 24 postulaciones, 12 prácticas y 12 publicaciones. Faltan snapshot hijo reciente, credencial `app_bootstrap` y 47 secretos individuales. No se aplicó la carga ni se modificaron Credential Manager, Neon, base local, demo o Docker.
- Full continúa bloqueado por ausencia de elegibilidad persistida, autoridades OPEN-05/asignación docente, snapshot y login `app_dataset_full`. El marcador visible no permite a los roles de runtime/bootstrap certificar el ledger exacto; el corte histórico T-49 comprobó `0013`, pero este preflight no lo volvió a leer. No se hizo stage, commit ni push. Véase [resultados T-52](validation/validation-results.md) y [permisos bootstrap](../synthetic-dataset-bootstrap.md).

### Herramienta de carga persistente SYN-01 — T-51, 2026-11-04
- `scripts/persist_synthetic_dataset.py` ejecuta preflight de solo lectura por defecto y no lee `DATABASE_URL` ni `.env`. El camino `--apply` exige confirmar `long-truth-39527618/main`, un snapshot hijo reciente, la credencial puntual separada y las reglas persistidas/configuradas; aborta sin ellas. No se ejecutó `--apply`.
- La fixture admite un hash provisto por cuenta nueva y conserva los hashes existentes. El cargador genera secretos aleatorios por cuenta para Windows Credential Manager, comparte una transacción PostgreSQL entre los comandos de dominio, verifica idempotencia dentro de ella y restaura los grants/membresía temporal antes del commit. La prueba temporal cubrió el rollback completo; el camino de escritura Neon no se ejecutó.
- Validación nueva: backend **90 passed, 1 warning** (90.36 s); E2E poblado Chromium **4/4** (28.2 s), con base temporal limpiada. Preflight actual Neon **EXIT 2 (bloqueado)**: TLS/rol/runtime/esquema y conteos coinciden; falta elegibilidad para ambos programas, tres variables de autoridad, respaldo snapshot y credencial puntual de escritura. El login `app_runtime` no tiene `INSERT` en `host_org`; no fue elevado. No se escribieron filas ni se creó rama Neon.
- Frontend/build no se repitieron porque no cambiaron. Resultados históricos SYN-01/T-50 no se atribuyen a T-51. Detalles: [validation-results.md](validation/validation-results.md).

### Preflight de carga de datos en Neon — T-50, 2026-11-04
- Se verificaron en solo lectura el proyecto/rama `long-truth-39527618/main`, conexión `app_runtime` con TLS requerido y `SET ROLE app_user`. Las rutas públicas Render `/health` y `/ready` respondieron HTTP 200.
- Neon contiene 14 cuentas base, 2 programas, 2 organizaciones, 4 políticas de activación/finalización y 7 eventos auth; siguen vacías las tablas de oportunidades, postulaciones, prácticas y sus datos de ciclo. No hay política `ELIGIBILITY` para los programas existentes.
- No se creó rama snapshot ni se ejecutaron escrituras. La carga poblada se detuvo porque las reglas institucionales de elegibilidad y las autoridades OPEN-05 no están definidas; además, el generador asigna un único `DEMO_PASSWORD` a las cuentas nuevas. Resultados detallados: [validation-results.md](validation/validation-results.md). No se declara carga o demo pública completada.

### Runtime de Neon y preparación de despliegue público — T-49, 2026-11-04
- Neon `long-truth-39527618/main` se verificó nuevamente. La migración `0013` está aplicada; `app_user` permanece `NOLOGIN`, con permisos mínimos explícitos. Se creó `app_runtime` como `LOGIN`, sin atributos administrativos y con membresía `SET TRUE`, `INHERIT FALSE`, `ADMIN FALSE` en `app_user`. La conexión runtime con TLS ejecutó `SET ROLE app_user` correctamente; no se concedieron privilegios directos de tabla a `app_runtime`.
- La auditoría verificó exactamente 69 pares de privilegios de tabla para `app_user` y 23 grants `USAGE` de secuencia. El marcador de readiness respondió HTTP 200 (`{"status":"ready"}`) con la credencial runtime recuperada en memoria desde Windows Credential Manager. La contraseña/URI no se imprimió. El secreto está guardado localmente, pero aún no se configuró en Render.
- Postcheck T-49, antes del preflight T-50: Neon terminó con revisión `0013`, 28 tablas de aplicación y cero filas de aplicación; no se sembraron usuarios ni datos en ese corte. La migración 0013 solo revoca/reconcede ACL, sin alterar filas ni tablas. T-50 luego encontró las 14 cuentas base y los catálogos sintéticos indicados arriba.
- Resultados T-49 completados antes de esta reanudación: backend **88 passed, 1 warning** (94.07 s), frontend **37/37 en 14 archivos**, build **EXIT 0** (62 módulos), migraciones aisladas `0001→0013` y `0010→0011→0012→0013` **EXIT 0**, E2E Chromium aislado **7/7** (1.2 min); se inspeccionaron ocho capturas desktop/390 px. En esta continuación se repitieron `/ready` (HTTP 200) y `git diff --check` (EXIT 0); las suites no se reejecutaron porque el código no cambió.
- Render/Vercel siguen sin servicios ni URLs públicas. La autorización de configurar el rol Neon está completada, pero la revisión/aprobación del diff y la autorización GitHub para stage/commit/push siguen pendientes; no se publica una revisión local no aprobada. No hay E2E público.

### Preparación de despliegue público gratuito — T-48 (histórico, 2026-11-03)
- Se agregaron `render.yaml`, `frontend/vercel.json`, el readiness check `GET /ready` y el runbook [`deployment-free-preview.md`](../deployment-free-preview.md). Se validaron YAML/JSON, el proxy de 17 rutas API, `no-store` y fallback SPA. Esto es configuración, no publicación.
- Preflight de solo lectura antes de migrar Neon `long-truth-39527618/main`: `.env` `DATABASE_URL` (pooler) y `DATABASE_URL_UNPOOLED` (directa) coincidieron con la rama autorizada; PostgreSQL 18.6, TLS activo, cero tablas no internas y sin `alembic_version`. Tras autorización expresa, `alembic upgrade head` sobre la URI directa terminó con `0012 (head)`. Postcheck de solo lectura: 29 tablas públicas, cero filas de aplicación y ninguna cuenta sembrada. Las cadenas aisladas `0001→0012` y `0010→0011→0012` también pasaron en `pgserver` temporal.
- El readiness backend estaba **bloqueado para Neon en T-48**: la conexión comprobada era `neondb_owner`, con TLS cliente activo; el rol de esquema `app_user` era `NOLOGIN`, y su membresía tenía `SET FALSE`. La prueba read-only de `SET ROLE app_user` fue denegada. T-49 corrigió el bloqueo con el rol separado `app_runtime`; esta descripción y las cifras de validación que siguen pertenecen únicamente a T-48.
- Validación T-48: backend **87 passed, 1 warning** (95.43 s), frontend **37/37 en 14 archivos**, build **EXIT 0** (62 módulos); no se ejecutó E2E público porque aún no existen URLs/servicios. El **7/7 de Chromium corresponde a T-47**, no a T-48.
- Docker Engine no está disponible. No se accedió a la base local/demo ni a recursos Docker; no hubo creación de cuentas, seed, stage, commit o push. La migración remota autorizada está completa; Render/Vercel no se crearon y la publicación espera la revisión del diff, autorización GitHub y definición del login DB de ejecución.

### Notificaciones, mensajería, reportes, publicación y asignación docente — T-47, 2026-11-03
- La migración `0010` añade notificaciones y conversaciones con canales `JOINT`/`ACADEMIC`; los eventos reales crean notificaciones en la transacción de origen, y la bandeja/read state está limitada al usuario. Los mensajes y la lectura del historial requieren rol, relación y canal autorizados.
- La migración `0011` protege las transiciones de oportunidad; `OPPORTUNITY_REVIEWER_ROLES` y `OPPORTUNITY_PUBLISHER_ROLES` están vacías por defecto. Las listas se configuraron solo en E2E; OPEN-05 no está resuelto para producción.
- Los reportes agregan datos persistidos y filtran por programa, organización y estados disponibles; se limita el alcance a coordinación/EC y la respuesta excluye PII y evaluaciones individuales. La UI incluye filtros, carga, error y vacío.
- La migración `0012` mantiene historial append-only de asignación/retiro de supervisión docente. API/UI soportan consulta de opciones y reasignación solo si `PLACEMENT_FACULTY_ASSIGNER_ROLES` está configurado y el actor tiene ámbito de programa/EC. Por defecto no concede autoridad. Servicio y trigger rechazan cambios cuando la colocación está `COMPLETED`, `CLOSED`, `REJECTED` o `CANCELLED`.
- Validación histórica de T-47: backend **84 passed, 1 warning** (122.13 s), frontend **37 passed en 14 archivos**, `npm run build` **EXIT 0** (62 módulos), migraciones `0001→0012` y `0010→0011→0012` **EXIT 0**, Playwright Chromium **7/7** (1.2 min). Se inspeccionaron ocho capturas (1280 px/390 px), incluidas las vistas de reportes. Docker daemon ausente; todas las bases fueron PostgreSQL temporales `pgserver`, limpiadas al final. Los resultados de T-48 se listan arriba y no incluyen E2E público.
- En reportes, Playwright verifica la recuperación tras 503, autorización denegada a empleador y ajuste de las cuatro tablas para mostrar todas las columnas sin overflow en escritorio y 390 px. Las capturas confirmaron el ajuste visual.
- Se corrigió en UI una carrera real: al guardar una versión de política, la recarga podía descartar cambios locales pendientes de otra regla. También se corrigieron expectativas/selectores E2E sin retirar comprobaciones. El producto no se declara completo: faltan decisiones OPEN-xx, integración institucional, instrumentos de evaluación, SSO y validación de carga/usabilidad.

### Estado factual de incidentes y escrituras tras cierre — T-46, 2026-11-02
- Los reportes de incidente/cambio reciben el estado factual único `REPORTED`; una migración aislada `0001→0009` verifica el backfill de reportes existentes. No se añadieron revisión, resolución, escalamiento, sanciones ni aprobación de versiones.
- La práctica docente `ACTIVE` asignada se recorrió desde dashboard hasta expediente; la suite E2E comprueba titular, WPS, docente asignado, coordinación y Legal, además de un acceso cruzado denegado. Tras `CLOSED`, se rechazan nuevas horas, avances, incidentes, evidencia y asignaciones al plan. El plan histórico continúa consultable.
- Validación nueva: backend **76 passed, 1 warning** (75.00 s), frontend **34 passed en 12 archivos**, `tsc -b && vite build` **EXIT 0** (58 módulos), migraciones **`0001→0009` EXIT 0**, Playwright Chromium aislado **7/7** (55.8 s). Las pruebas usan PostgreSQL temporal; no se modificó la base local/demo.
- Las capturas T-46 de seis imágenes se conservan como evidencia histórica. En T-47 se generaron e inspeccionaron ocho nuevas: expediente **1280×5152 / 390×6398**, dashboard estudiante **1280×720 / 390×1137**, supervisor **1280×900 / 390×844**, reportes **1280×1271 / 390×2381**. Las tablas de reporte y el expediente no presentan desbordamiento horizontal en móvil.
- Docker CLI 29.5.3 no encontró el daemon `dockerDesktopLinuxEngine`; no se intentó reparar Docker. La suite usó `pgserver` temporal sin volúmenes compartidos. No se hizo stage, commit ni push.

### Recuperación ante fallos en dashboards relacionales — T-45, 2026-11-02
- Los dashboards de WPS, coordinación y supervisión docente reemplazan el estado de carga indefinido por un mensaje de error y reintento cuando falla `GET /placements`; vuelven a consultar con el endpoint y filtro de relación existentes, sin ampliar permisos.
- Validación ejecutada: backend **75 passed, 1 warning** (66.49 s), frontend **34/34 en 12 archivos**, `pnpm run build` (`tsc -b && vite build`) **EXIT 0** (58 módulos, 1.23 s), E2E Chromium aislado **6/6** (59.7 s). PostgreSQL temporal `pgserver`; procesos y base limpiados.
- Revisé seis capturas nuevas de expediente, dashboard estudiante y WPS en escritorio y móvil (1280 px/390 px); no se aprecia desbordamiento en móvil. T-45 recorre error/reintento en WPS, coordinación y docente; la lista docente queda vacía en ese E2E y no valida una práctica docente asignada ni la usabilidad QS-08.
- Docker Engine no estuvo disponible. No se accedió a la base local/demo ni se alteraron credenciales, colocaciones sintéticas, contenedores o volúmenes. No hay cambios en backend en este bloque y no se efectuó stage/commit/push.

### Revalidación del árbol y migraciones — T-44, 2026-11-02
- Tras revisar el diff, se restituyó `SCHEMA` al estado inicial de la migración `0001`; el lock de horas permanece en `UPGRADE_0006_SQL` y en el esquema compuesto `CURRENT_SCHEMA`.
- En PostgreSQL temporal, Alembic recorrió `0001→0007`: lock ausente en `0001`, presente al final; head `0007` y tabla `placement_work_plan_item` comprobados. La base temporal se limpió.
- Se reejecutaron backend **75 passed, 1 warning** (111.24 s), frontend **32/32 en 11 archivos**, `tsc -b && vite build` **EXIT 0** (57 módulos, 993 ms) y Chromium **3/3** (59.5 s) con el runner aislado. Se revisaron seis capturas nuevas desktop/móvil; una aserción comprueba que la lista docente incluya solo la práctica asignada.
- Docker cliente 29.5.3 no encontró el daemon `dockerDesktopLinuxEngine`. La validación usó solo `pgserver` temporal, sin volúmenes compartidos; no se accedió a la base local/demo ni se modificaron recursos Docker.

### Orientación del estudiante y acceso de supervisión — T-43, 2026-11-02
- El panel del estudiante presenta estado y destino derivados de la última postulación/práctica y, en documentación pendiente, de los requisitos persistidos. No convierte una condición asignada a otro rol en una instrucción para el estudiante. Prácticas activas y terminales llevan al expediente/historial.
- Supervisores laborales/docentes y coordinadores ven las prácticas devueltas por `GET /placements`, con el filtrado relacional del backend, y pueden abrir Expedientes desde Inicio. La ejecución E2E verificó una práctica asignada a WPS; la lista docente está cubierta por el endpoint relacional, pero su vista con asignación no se recorrió en esta E2E.
- Validación de este incremento: frontend **32/32 en 11 archivos**; `pnpm run build` (`tsc -b && vite build`) **EXIT 0**, 57 módulos; runner Chromium aislado **3/3** (1.0 min). Se probaron estado SUBMITTED, supervisor asignado, navegación y 390 px sin overflow. Se revisaron capturas nuevas: expediente desktop/móvil **1280×4695 / 390×5746**; dashboard estudiante **1280×720 / 390×1137**; dashboard WPS **1280×900 / 390×844**.
- La suite backend **75 passed, 1 warning** y Alembic `0006→0007` EXIT 0 son la validación T-42 anterior del mismo corte; T-43 no modificó backend. Docker Engine siguió sin estar disponible; Playwright utilizó PostgreSQL temporal `pgserver`, sin volúmenes compartidos.
- RNF-11 tiene implementación y pruebas automáticas parciales; QS-08/T-13 con participantes sigue pendiente. La reasignación académica, decisiones de cierre/evidencia y aprobación formal de cambios no se inventaron.

### Plan de trabajo — código actual 2026-11-02
- Se añadió la migración `0007` y la API `GET/POST /placements/{pid}/work-plan`. El WPS vinculado a la versión vigente puede asignar narrativas; titulares, supervisores docentes, coordinadores del programa y EC pueden leer según relación. Miembros anfitriones y legal no reciben el contenido del plan.
- El plan se integra al expediente y al historial. Las filas son append-only y tienen revisión secuencial; no añaden vencimientos, calificaciones, estado de cumplimiento ni compuertas de elegibilidad/cierre.
- Validación nueva: backend **75 passed, 1 warning** en PostgreSQL temporal `pgserver`; Alembic `0006→0007` **EXIT 0**; frontend **25/25** en 10 archivos; `tsc -b && vite build` **EXIT 0**, 56 módulos; Playwright Chromium **3/3** con `scripts/run_isolated_e2e.py`. Capturas nuevas de **1280×4695** y **390×5746** inspeccionadas.
- Docker Engine no estaba disponible; se usaron bases temporales sin volúmenes compartidos. `0007` se aplicó únicamente a PostgreSQL desechable en la prueba incremental. No se accedió a la BD local/demo, no se alteraron credenciales/colocaciones allí ni recursos Docker. OPEN-02/11/14/03, mensajería, revisión/publicación y otros flujos aún no definidos siguen pendientes.

### Revalidación y carrera de horas/cierre — validación anterior 2026-10-26 (histórica)
- Revalidación nueva: backend **74 passed, 1 warning** en 67.31 s; foco T-04 **1 passed**; frontend **24/24**; `tsc -b && vite build` **EXIT 0**, 55 módulos; Chromium **3/3** en 46.0 s. Detalles y comandos en [validation-results.md](validation/validation-results.md).
- La E2E final aplicó la migración `0006 (head)` en PostgreSQL temporal `tmpfs`, sin mounts ni volúmenes compartidos; sus capturas nuevas **1280×4426** y **390×5466** fueron inspeccionadas. El build temporal habilitó la ruta de acceso sintético que usa el test existente.
- T-04 ahora valida concurrentemente una inserción directa de horas mientras `confirm_completion` tiene sin confirmar el `UPDATE`: la escritura espera el lock de la práctica y PostgreSQL la rechaza al quedar `COMPLETED`. Se añadió el mismo lock en `record_hours`; no se probó retiro concurrente de evidencia.
- Docker agotó la asignación automática de subredes tras las corridas previas; se usaron redes explícitas `/24` solo para nuevos proyectos. No se retiraron contenedores, redes ni volúmenes existentes, ni se accedió a la BD local/demo persistente.

### Seguimiento, evaluación y evidencia de cierre — validación anterior 2026-10-26 (histórica)
- El expediente ahora incluye avances, evaluaciones narrativas MIDTERM/FINAL, reportes INCIDENT/CHANGE y evidencia FINAL_REPORT persistida como bytes, hash, nombre, tipo, tamaño y revisión. Los registros son append-only y generan actividad; el reporte CHANGE no crea una versión ni inicia aprobación.
- El cierre recalcula horas y consulta documentos/evaluaciones desde las tablas de origen contra requisitos persistidos. La E2E usó únicamente una política sintética de 100 h y requisitos de informe/evaluación en PostgreSQL `tmpfs`; no se definió una regla institucional nueva.
- La autorización por rol/relación se verificó para titular, miembro anfitrión, supervisor laboral asignado, coordinación de programa, legal y EC. El E2E registró avance/cambio, entregó el informe, recibió la evaluación FINAL, recargó, confirmó/cerró y comprobó horas e historial terminal. El estudiante no recibe capacidad de confirmar finalización.
- Resultados finales de esta continuación: backend **73 passed**, 1 warning Starlette/httpx (115.10 s); frontend **24/24** en 10 archivos (4.88 s); `tsc -b && vite build` **EXIT 0**, 55 módulos; Playwright Chromium **3/3** (58.1 s). Capturas nuevas de **1280×4521** y **390×5601** inspeccionadas; el E2E comprobó 390 px sin overflow.
- La primera E2E falló 2/3 por una expectativa errónea del test sobre el rol estudiante. Se corrigió la aserción para verificar permiso denegado y ausencia del botón. La revisión visual r5 también detectó un mensaje de activación inexacto en una práctica ACTIVE; se corrigió en la UI y el E2E r6 comprueba el nuevo texto, las acciones `placement.completed`/`placement.closed` y los permisos.
- OPEN-02/11/14 y OPEN-03 siguen pendientes. En ese corte T-04 concurrente no se había ejecutado. Las evaluaciones no tienen escala, incidentes/cambios no se escalan ni resuelven automáticamente y la aprobación formal de nuevas versiones sigue sin endpoint por OPEN-03. El producto no se declara terminado.

### Expediente integral y horas históricas — ejecución anterior 2026-10-26 (histórica)
- El expediente mostró versiones de elegibilidad/activación/finalización y horas históricas desde filas persistidas; en ese corte no existía interfaz para evidencia final.
- Resultados anteriores: backend **71/71**, frontend **22/22**, build **54 módulos**, E2E **3/3**. No representan validación del bloque de seguimiento/evidencia descrito arriba.

## Estado actual de preparación final

### Implementado y validado
- Autenticación local y roles; matriz HTTP de rutas y relaciones con pruebas negativas: `backend/tests/test_http_authorization.py` (T-34).
- Compuerta de activación/rechazo serializada en PostgreSQL con migración `0004`; fuentes de cierre y evidencia final en `0005`; lock de horas frente a cierre en `0006`. T-44 pasó backend **75/75** y Alembic `0001→0007` completo en `pgserver`; filtro de supervisores inactivos: 1/1 en su corte histórico.
- El runbook de demo previamente verificado llega a `0004`; las continuaciones aplicaron `0005` y `0006` solo al iniciar APIs contra bases E2E nuevas en `tmpfs`. La base local y la demo persistente no se migraron ni modificaron.
- Pruebas frontend: corte histórico 2026-10-25 **10 aprobadas**; expediente histórico **22/22**; T-44 **32/32 en 11 archivos** y `tsc -b && vite build` EXIT 0 (57 módulos). T-42 (25/25, 56 módulos) y T-43 son cortes previos distintos.
- E2E Chromium históricos del 2026-10-25/26: **3/3**. La ejecución nueva del 2026-11-02 pasó **3/3** con plan de trabajo, seguimiento, evaluación, evidencia final, recarga, cierre e historial, sobre PostgreSQL temporal; capturas **1280×4695** y **390×5746** inspeccionadas. Ver [validation-results.md](validation/validation-results.md).
- Catálogos para crear oportunidades: `GET /opportunities/catalogs` y `GET /opportunities/{oid}/workplace-supervisors`; selects nominativos sin IDs numéricos manuales. T-39 cubre autorización cruzada y filtro de supervisor inactivo. T-47 añade los estados de revisión/publicación protegidos; OPEN-05 mantiene pendientes las autoridades institucionales y no existe edición de oportunidad.
- Rediseño responsive de las vistas existentes: **inspección visual** en escritorio para estudiante, empleador, coordinador, revisor legal y EC; comprobación automatizada de ancho sin desbordamiento en 13 rutas/vistas a 390 px y 320 px. Capturas de comprobación en `frontend/test-results/ui-redesign/` (directorio ignorado por Git); no equivale a E2E de todas las acciones.
- Selección valida ahora que el rango de fechas no esté invertido y que cualquier supervisor laboral indicado pertenezca a la organización anfitriona; pruebas positiva y negativas en `backend/tests/test_selection.py`.
- Estudiante titular puede registrar horas opcionales solo en prácticas `ACTIVE` y consultar su propio total e historial. El backend valida horas finitas y mayores que cero; persistencia tras recarga probada con E2E. No existe aprobación de horas; la obligatoriedad institucional queda pendiente según el RFP.

### Implementado parcialmente o pendiente de contrato
- E2E cubre plan narrativo asignado, avances, evaluación narrativa, reporte de cambio, evidencia y cierre, además de mensajería contextual, notificaciones, reportes, revisión/publicación configurable y asignación docente. No hay escala/instrumento de evaluación, cumplimiento estructurado de actividades, resolución/escalamiento de incidentes, ni políticas institucionales para varios permisos. El RFP §5 deja el proceso incompleto y §9 presenta algunas funciones como capacidades posibles.
- Los actores y tipos obligatorios del cierre siguen sujetos a OPEN-02/11/14; la política utilizada en E2E es sintética y persistida solo en la base temporal.
- El servicio interno para proponer/aprobar versiones sigue sin endpoints HTTP ni vista y depende de OPEN-03. Un reporte CHANGE no sustituye ese proceso.

### Pendiente de decisión institucional
- OPEN-05 (autoridad y proceso institucional de revisión/publicación; flujo técnico ya implementado); OPEN-13 (cupos); OPEN-19 (prácticas simultáneas); OPEN-01/02/06/09/14/20 (reglas, campos y actores documentales/externos); OPEN-03 (cambio versionado); instrumento/visibilidad de evaluación; duplicados tras retiro y selección alternativa.
- Para OPEN-19 siguen abiertas las opciones: bloquear cualquier segunda colocación activa, bloquear solo fechas solapadas o fijar máximo configurable. No se aplica límite automáticamente ni se modificaron registros sintéticos.

### Bloqueado por integración externa
- SSO institucional/IdP, envío real de recuperación por correo y repositorio de documentos externo. No existe configuración de proveedor en el repositorio; no se presentan como integraciones validadas.

## Completado
| Qué | Evidencia |
|---|---|
| Artefactos de la Evaluación 1 (Visión y Alcance; Requisitos/Backlog/Riesgos/Criterios; Interesados/Aclaraciones/Supuestos/AS-IS/TO-BE/Pendientes) | Tres archivos entregados en contexto fueron analizados; sus originales no están incluidos en este repositorio. |
| Auditoría de coherencia de la Evaluación 1 | [`evaluation-1-audit.md`](evaluation-1-audit.md): 34 hallazgos con decisión |
| Documentación de arquitectura y diseño | `docs/evaluation-2/` distingue el diseño acordado, el estado real del demo y los pendientes institucionales |
| PoC de la rebanada crítica ejecutado por el equipo | `prototype/evidence/results.json`: **14 PASS, 0 FAIL** (2026-10-22; incluye T-02 y T-16a..e) |
| Backend Fase 1 (identidad, authz, auditoría, lifecycle) | `backend/`: T-20..T-31; autenticación local con Argon2id, cookie de sesión y recuperación |
| Incremento oportunidades + postulaciones (Sprint 1) | `backend/app/modules/{opportunities,applications,policies}` + frontend React; T-24/T-25 |
| Sprint 2: selección del empleador + aprobación académica | Selección, aprobación/rechazo, relación por programa y auditoría; pruebas T-26/T-27 |
| Frontend UX/UI (shell, dashboard, formularios y vistas por rol) | `frontend/src/{index.css,components,pages,studentJourney.ts}`; T-43 ejecutó 32/32 pruebas en 11 archivos, build de 57 módulos, E2E Chromium 3/3 e inspección de dashboard estudiante/WPS y expediente desktop/móvil; la cobertura de comprensión humana, todas las acciones y browsers adicionales sigue pendiente |
| Sprint 3: documentos + activación | Archivos PDF/PNG/JPG/DOCX en PostgreSQL (≤10 MB), revisiones con motivo, historial y reentrega; permisos de descarga; activación/cierre por políticas versionadas; vistas de estudiante, revisor legal y EC; T-28..T-30 |
| Políticas EB-08 | UI de coordinación para versiones de elegibilidad, activación y cierre; validadores de vocabulario cerrado; las colocaciones fijan las versiones al aprobarse académicamente |

## En progreso
| Qué | Nota |
|---|---|
| Aplicar las correcciones a los artefactos fuente de la Evaluación 1 | Ver EB-01 |
| Decidir el stack y revisar el modelo de dominio de este paquete para adoptarlo como el primero del equipo | OPEN-17; EB-03 |

## No implementado
Instrumento y evaluación institucional formal; autoridad de producción para revisión/publicación (OPEN-05) y asignación docente; IdP/SSO institucional (OPEN-21); proveedor real de correo para recuperación; reglas institucionales exactas de documentos/evidencia y actores (OPEN-01/02/11/14); API/UI de versión formal por OPEN-03; workers de recordatorios y adaptadores con fallos a pedido.

## No validado
Las decisiones institucionales `OPEN`; QS-05, QS-07, QS-08; T-09..T-11 y T-13..T-15; revisión visual completa y cobertura E2E de todas las vistas/roles/browsers; retiro concurrente de evidencia en T-04. T-12 pasó según su runbook. T-44 reejecutó backend 75/75, frontend 32/32, build de 57 módulos y Chromium 3/3; la cadena Alembic `0001→0007` fue validada en PostgreSQL temporal y las capturas nuevas desktop/móvil fueron revisadas. El runbook no se ejecutó contra demo persistente. Los límites restantes se describen arriba. El repositorio documental externo y SSO real no están integrados.

## Riesgos (priorizados)

> Se conservan R-001..R-010 de la Evaluación 1 (no se reproducen los no revisados). Los marcados *(actualizado)* o *(nuevo)* cambian en esta evaluación. **Responsables:** roles genéricos como en la Evaluación 1; el equipo debe asignar nombres.

| ID | Riesgo | Prob. | Impacto | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|
| R-013 *(nuevo)* | No hay código ni stack elegido: la implementación puede desviarse del diseño, o el modelo (primera versión) tener huecos (OPEN-17) | Media | Media | EB-03: elegir stack, revisar el modelo en equipo y portar el PoC | Líder técnico | Abierto |
| R-017 *(nuevo)* | La evidencia ejecutada no estaba reproducida por el equipo | Alta | Media | EB-04: reejecutar y registrar commit | Líder técnico | Cerrado 2026-10-22: reejecutado por el equipo, 14 PASS, commit `dcda267` |
| R-019 *(nuevo)* | Sprint 4 sobrecargado (55 pts) y habilitadores (auditoría, autorización) demasiado tarde (AUD-24) | Alta | Media | EB-17: re-secuenciar | Gestor de proyecto | Abierto |
| R-009 *(actualizado)* | Exposición de datos a externos; RF-20 sin historia | **Media** (antes Baja) | Alta | US-032, ADR-004; matriz HTTP T-34 y negativas cruzadas | Arquitecto | Mitigación implementada y validada en endpoints cubiertos; revisar al agregar rutas y resolver OPEN-06 |
| R-014 *(nuevo)* | El vocabulario cerrado resulta insuficiente cuando se descubren las reglas reales | Media | Alta | Validar con coordinadores; reconsiderar ADR-001 | Analista de negocio | Abierto |
| R-015 *(actualizado)* | Documento rechazado tras la activación: hay propuesta (BR-18), pero **no está validada** con el cliente (OPEN-14) | Media | Alta | EB-10: validar la propuesta y definir plazo/excepciones | Product Owner | Abierto; propuesta probada en el PoC (2026-10-22) |
| R-018 *(nuevo)* | SSO institucional sin proveedor ni configuración (OPEN-21); cuentas locales implementadas como alternativa | Media | Alta | EB-11 consultar a TI | Arquitecto | Abierto: datos de TI pendientes |
| R-011 *(nuevo)* | Carreras en comandos del ciclo de vida | Media | Alta | ADR-003 | Arquitecto | T-01/T-02 y serialización de activación/rechazo verificadas con PostgreSQL; T-04 horas-vs-confirmación pasó 1/1 con `0006`; retiro concurrente de evidencia no cubierto |
| R-012 *(nuevo)* | Un endpoint nuevo olvida la autorización | Media | Alta | Prueba de rutas con acción declarada | Líder técnico | Matriz HTTP T-34 ejecutada; mantener la cobertura en CI |
| R-016 *(nuevo)* | La lógica del trigger diverge de la política de aplicación o se rompe en migraciones | Baja | Media | Pruebas de contrato app↔BD; revisar cada migración | Líder técnico | Cadena Alembic `0001→0007` y suite backend 75/75 validadas en PostgreSQL temporal; demo persistente se mantiene sin migrar |
| R-001 *(sin cambio de nivel)* | Reglas por programa desconocidas o cambiantes | — | — | ADR-001 | — | Abierto |
| R-002 *(sin cambio de nivel)* | Integración simulada oculta problemas reales | — | — | ADR-006; contratos | — | Abierto |

## Backlog de la evaluación

| ID | Tarea | Prioridad | Responsable | Dependencia | Estado |
|---|---|---|---|---|---|
| EB-01 | Aplicar correcciones a la Evaluación 1 (ASM-005, CL-004, ASM-009..011, SC-06, división de US-019, enmienda de US-020, prioridades de US-003/US-017, fuente de ASM-003B) | Alta | Analista de negocio | — | Pendiente |
| EB-02 | Agregar US-032..US-036 y SC-13 al backlog y validarlas | Alta | Product Owner | EB-01 | Pendiente |
| EB-03 | Elegir el stack y revisar en equipo `views/domain-model.md` para adoptarlo (o corregirlo) como el modelo oficial | Alta | Líder técnico | — | Propuesta de stack en ADR-007, pendiente de adopción |
| EB-04 | Reejecutar `run_poc.py` y registrar commit y fecha | Alta | Líder técnico | — | Hecho (2026-10-22, commit `dcda267`) |
| EB-05 | Portar las compuertas (ADR-003) con pruebas T-01/T-02 en la tecnología real | Alta | Desarrollo | EB-03 | Ejecutado y cubierto por suite del backend |
| EB-06 | Autorización C-02 con matriz de pruebas (ADR-004), **antes** de exponer postulantes a externos | Alta | Desarrollo | EB-03 | Matriz HTTP T-34 y negativas cruzadas ejecutadas; RLS y cobertura de penetración no incluidas |
| EB-07 | Escritor de auditoría atómico (ADR-005), **antes** de la primera aprobación | Alta | Desarrollo | EB-03 | Ejecutado; eventos de entrega y revisión registran metadatos/motivos, nunca bytes |
| EB-08 | Políticas C-05: 4 condiciones de elegibilidad + activación + finalización | Alta | Desarrollo | EB-03 | Implementado en API/UI con versiones inmutables y binding al aprobar; probar reglas reales y validar listas institucionales sigue OPEN-01/02/04/11 |
| EB-10 | Validar con el cliente la propuesta para OPEN-14 (BR-18: sigue `Active`, indicador derivado y compuerta de cierre) y definir plazo de corrección y aprobador de excepciones | Alta | Product Owner | — | Propuesta probada en el PoC (2026-10-22) |
| EB-11 | Cerrar OPEN-01, 02, 03, 21 con interesados y TI | Alta | Analista de negocio | — | Pendiente |
| EB-17 | Re-secuenciar sprints con habilitadores primero y reestimar | Alta | Gestor de proyecto | EB-02 | Pendiente |
| EB-09 | Puertos y simuladores con pruebas de contrato (ADR-006) | Media | Desarrollo | EB-03 | Pendiente |
| EB-12 | Variante concurrente de T-04 | Media | Desarrollo | EB-05 | Horas-vs-confirmación pasó 1/1 el 2026-10-26; retiro concurrente de evidencia no tiene operación vigente que probar |
| EB-13 | Verificación de fronteras de módulo (T-15) | Media | Líder técnico | EB-03 | Pendiente |
| EB-15 | Despliegue de demo y prueba de humo (T-12) | Media | Desarrollo | EB-05 | Ejecutado en Compose aislado: migración `0004`, `/health` OK, 14 cuentas seed; runbook reproducible |
| EB-14 | Generador de carga y T-09 | Baja | Desarrollo | EB-05 | Pendiente |
| EB-16 | Prueba de usabilidad (T-13) | Baja | Analista de negocio | UI | Pendiente |

*Fechas: sin asignar; las define el equipo.*

## Propuesta de re-secuenciación (a validar y reestimar)
Plan inicial por sprint (referencia histórica): Sprint 1 proponía identidad, **autorización (US-032)**, auditoría, oportunidades, postulaciones y políticas; DH-05 ahora usa cuentas locales para identidad. Sprint 2 cubría selección, aprobación académica, checklist y documentos; Sprint 3, activación, supervisión, horas y cambios; Sprint 4, evaluaciones, cierre, notificaciones y paneles. **El flujo extremo a extremo debería cerrarse antes del último sprint** y el calendario (US-030) queda opcional.

## Próximos pasos (por prioridad al corte 2026-10-24)
1. Resolver con producto OPEN-05 (revisión/publicación), OPEN-13 (cupos), retiro/repostulación/alternos y OPEN-19 (colocaciones activas simultáneas); no se implementarán reglas hasta su decisión.
2. Resolver con producto/TI OPEN-01/02/06/14/20/21: reglas y actores documentales, campos externos, comportamiento tras activación, proveedor de correo e IdP/SSO.
3. Ampliar la validación de frontend a las demás vistas/roles y tamaños responsive; el E2E actual cubre solo el camino principal Chromium descrito en T-35.
4. Completar la variante pendiente de T-04 (retiro concurrente de evidencia) solo si se define una operación que permita ese retiro; ejecutar QS-05/QS-07/QS-08, T-09..T-15 y validaciones de carga, usabilidad e integración cuando exista el entorno y alcance correspondiente.
5. Mantener EB-01/02/03/09/13/14 como tareas de evaluación/arquitectura aún abiertas; la adopción oficial del stack sigue siendo decisión del equipo.

## Actualización de producto — historial visible de práctica (2026-10-25)

- `GET /placements/{pid}/history` conserva autorización por rol y relación y ahora expone solo instante y acción, en vez de IDs internos, payloads JSON antes/después y correlación.
- “Mis documentos” ofrece una actividad desplegable para la práctica: traduce acciones conocidas, trata las futuras como actualización genérica y carga/reintenta sin bloquear la vista documental.
- T-40 (2026-10-25) validó el endpoint y la vista con eventos de colocación. T-41 (2026-10-26) pasó backend 74/74 y E2E Chromium 3/3; T-42 (2026-11-02) amplió el expediente con el plan de trabajo y pasó backend 75/75 y E2E 3/3. Cada corte y su entorno están diferenciados en [validation-results.md](validation/validation-results.md).
- **Clasificación:** segmento de historial de práctica validado; RF-19 sigue parcial, porque no incluye publicación de oportunidad ni evaluaciones/incidentes y no representa toda la traza del RFP hasta cierre. Retención y acceso operacional amplio permanecen por definir.
- No cambia OPEN-05, OPEN-02/11/14, ni la obligatoriedad institucional de horas. El producto aún no está listo para entrega final.
