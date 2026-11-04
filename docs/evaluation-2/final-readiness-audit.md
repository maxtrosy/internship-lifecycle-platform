# Auditoría de preparación para versión final

**Fecha de corte:** 2026-11-04
**Alcance:** código del backend y frontend, migraciones, Docker Compose, pruebas y artefactos de `docs/evaluation-2/`.  
**Fuentes:** RFP de ocho páginas, entregado en `C:\Users\maxtr\Downloads\Project 5 Request for Proposal (2).pdf`, leído completo. Los originales de Evaluación 1 no están en el repositorio; permanecen limitados los mapeos RF↔US y las decisiones que solo constan en resúmenes secundarios.

La auditoría requisito por requisito, incluyendo vistas, endpoints, servicios, permisos, pruebas y acción, se mantiene en [functional-completeness-matrix.md](functional-completeness-matrix.md). La implementación nueva no modifica reglas institucionales pendientes ni datos locales.

Los estados describen el comportamiento inspeccionado y la evidencia ejecutada. Compilar por sí solo no cuenta como validación funcional.

## Runtime Neon y preparación de preview — T-49, 2026-11-04

- Se aplicó la migración `0013` a la rama Neon autorizada `long-truth-39527618/main`. `app_user` sigue siendo `NOLOGIN`; la lista ACL revisada contiene 69 pares de privilegios de tabla y 23 grants `USAGE` de secuencia, sin acceso al ledger ni `CREATE` de esquema/base. El permiso PostgreSQL predeterminado `PUBLIC TEMP` permanece sin cambios.
- Se creó `app_runtime` con `LOGIN` y todos los atributos administrativos desactivados. Su única membresía es `app_user` con `SET TRUE`, `INHERIT FALSE`, `ADMIN FALSE`; no tiene grants directos a tablas. La conexión protegida por TLS completó `SET ROLE app_user`. La clave aleatoria se conserva en Windows Credential Manager y no se ha copiado a Render.
- El postcheck registró versión Alembic `0013`, 28 tablas de aplicación y cero filas; no se sembraron cuentas ni se modificaron tablas/datos en `0013`. Un `GET /ready` real mediante TestClient y la conexión runtime contra Neon respondió HTTP 200 con estado `ready`. Este endpoint valida conexión/rol y el marcador de esquema, no lee ni revela la versión del ledger.
- Resultados T-49 completados antes de esta reanudación: backend **88 passed, 1 warning**, frontend **37 passed/14 archivos**, build `tsc -b && vite build` **EXIT 0 (62 módulos)**, migraciones temporales `0001→0013` y `0010→0011→0012→0013` **EXIT 0**, E2E Chromium aislado **7/7**. En aquel corte se inspeccionaron ocho capturas nuevas de desktop y móvil de 390 px. En esta continuación `/ready` volvió a responder HTTP 200 contra Neon y `git diff --check` terminó **EXIT 0**; no se reejecutaron las suites porque no hubo cambios de código.
- Render/Vercel siguen sin recursos públicos ni URLs. No se hizo stage/commit/push y no se ejecutó un E2E público. La revisión del diff y autorización GitHub siguen siendo el bloqueo para publicar la revisión local; el secreto aún requiere introducirse en Render después de crear el servicio.

## Preparación de preview público — T-48 (histórico, 2026-11-03)

- El Blueprint de Render Free, la configuración Vercel Hobby y `GET /ready` quedaron en el árbol local. Los manifiestos parsean; `ready` comprueba PostgreSQL como `app_user` y la existencia del marcador de esquema introducido por la cadena de migraciones, sin exponer errores. No se crearon servicios.
- Antes de migrar, Neon `long-truth-39527618/main` se comprobó en solo lectura: PostgreSQL 18.6, TLS cliente y ningún objeto de aplicación que preservar. Tras autorización explícita se ejecutó Alembic contra la conexión directa; `alembic_version` terminó en `0012`, hay 29 tablas públicas y cero filas de aplicación. No se sembraron cuentas. Un sondeo de lectura posterior mostró que la conexión `neondb_owner` no puede ejecutar `SET ROLE app_user` (`set_option=false`), así que la API no está lista para conectar a Neon. Los resultados de T-48 están en [validation-results.md](validation/validation-results.md), separados de T-47.
- T-48 backend **87 passed, 1 warning**, frontend **37/37**, build **EXIT 0** con 62 módulos, migraciones temporales `0001→0012` y `0010→0011→0012` **EXIT 0**. E2E público no ejecutado: todavía no hay URLs; el 7/7 de Chromium es histórico de T-47.
- En el corte T-48 no se consideró una publicación: Render/Vercel no tenían servicios y no había URLs públicas. El bloqueo de credencial runtime se resolvió en T-49. Siguen pendientes la revisión/aprobación del diff y la autorización GitHub para commit/push; también faltan cuentas institucionales autorizadas y la revisión de privacidad/políticas aplicable antes de usar datos reales. Render Free limita disponibilidad/discos y Vercel Hobby se limita a uso personal/no comercial.

## Notificaciones, mensajería, reportes, revisión/publicación y asignación docente — T-47, 2026-11-03

- Se integró la bandeja persistente de notificaciones y la mensajería por expediente en canales compartido/académico; permisos por destinatario, relación y audiencia se verificaron con pruebas negativas.
- Los reportes operativos usan consultas agregadas persistidas, filtros disponibles en el modelo y autorización PC/EC; no devuelven datos personales ni evaluaciones individuales.
- La revisión/publicación de oportunidades recorre estados protegidos por trigger y endpoints. Las autoridades se configuran mediante `OPPORTUNITY_REVIEWER_ROLES` y `OPPORTUNITY_PUBLISHER_ROLES`, vacías por defecto. La ejecución aislada configuró EC como autoridad de test; OPEN-05 deja pendiente escoger la autoridad institucional real.
- Se habilitó asignación/reasignación docente y un historial append-only con migración `0012`. `PLACEMENT_FACULTY_ASSIGNER_ROLES` no otorga autoridad hasta ser configurado; el harness temporal usa PC. Servicio y trigger deniegan cambios en estados terminales; backend/E2E prueban la denegación tras cierre.
- Validación histórica de T-47: backend **84 passed, 1 warning** (122.13 s), frontend **37/37 en 14 archivos**, `tsc -b && vite build` **EXIT 0** (62 módulos), migraciones `0001→0012` y `0010→0011→0012` **EXIT 0**, E2E Chromium **7/7** (1.2 min). Se inspeccionaron ocho PNG de escritorio/móvil. Docker daemon ausente; se usó `pgserver` temporal y no se tocaron recursos persistentes.
- Los intentos intermedios de E2E y la corrección visual del panel de reportes se documentan en `validation-results.md`; las verificaciones finales de error/reintento y ajuste de tablas pasan.
- Pendiente para preparación final: decisiones institucionales OPEN-xx, alcance de visibilidad y configuración productiva, instrumento de evaluación, integraciones externas/SSO, medición QS-05/QS-07/QS-08 y cobertura completa de todas las vistas. T-47 no declara terminado el producto.

## Reportes factuales y guardas tras cierre — T-46, 2026-11-02

- Se agregó `REPORTED` como estado único e inmutable a incidentes/cambios y una migración que lo asigna a reportes preexistentes. La base temporal recorrió `0001→0009`; una prueba de datos verificó el valor backfilled y la guarda de plan cerrado.
- El E2E incluye una práctica activa realmente asignada a supervisión docente y comprueba navegación a su expediente, lectura por coordinación/Legal y denegación a un actor sin relación. En el ciclo principal, al cerrar, se rechazan escrituras de horas, avances, incidentes, evidencia y actividades del plan.
- Validación T-46: backend **76 passed, 1 warning** (75.00 s), frontend **34 passed en 12 archivos**, `tsc -b && vite build` **EXIT 0** (58 módulos), Chromium aislado **7/7** (55.8 s), migraciones **`0001→0009` EXIT 0**. PostgreSQL se creó mediante `pgserver` sin volúmenes compartidos.
- Inspeccioné las seis capturas nuevas de escritorio y móvil (1280 px y 390 px); no vi overflow horizontal en las vistas móviles. Docker CLI 29.5.3 no encontró el daemon; no se intentó repararlo y no se tocó la base local/demo ni recursos Docker persistentes.
- Siguen abiertas las decisiones institucionales de criterios y actores de cierre/evaluación, versión formal de cambios (OPEN-03), mensajería, notificaciones, publicación de oportunidades, SSO y validación humana QS-08. Los registros de evaluación actuales siguen siendo narrativos y sin escala/ponderación.

## Error y reintento de listas relacionales — T-45, 2026-11-02

- Corregí un defecto observable en los dashboards WPS/coordinación/supervisión docente: un fallo de `GET /placements` mostraba el aviso global, pero la tarjeta de prácticas podía quedarse cargando o sin indicar el fallo. Ahora presenta un estado de error y un botón de reintento que vuelve a cargar con la consulta relacional existente; no se modificaron permisos ni alcance de los datos.
- Validación nueva: backend **75 passed, 1 warning** (66.49 s), frontend **34/34 en 12 archivos**, `pnpm run build` (`tsc -b && vite build`) **EXIT 0** (58 módulos, 1.23 s), Chromium aislado **6/6** (59.7 s). El E2E simula 503, verifica error sin spinner, reintento 200 y contenido cargado/vacío en WPS, coordinación y supervisión docente.
- Se revisaron seis capturas actuales: expediente desktop/móvil **1280×4695 / 390×5746**, estudiante **1280×720 / 390×1137**, WPS **1280×900 / 390×844**. No se observó desbordamiento en móvil y el E2E conserva la aserción `scrollWidth <= 390` para expediente y dashboard de estudiante.
- Dos intentos intermedios del test fallaron por el matcher/conteo de solicitudes (lecturas duplicadas en `StrictMode`); se ajustó el test sin reducir aserciones. Docker CLI 29.5.3 no encontró el daemon. Backend/E2E usaron `pgserver` desechable sin volúmenes; no se tocaron la base local/demo ni recursos Docker.
- T-45 prueba error/reintento en WPS, coordinación y docente; la lista docente usada en el E2E queda vacía, por lo que falta recorrer una práctica efectivamente asignada en esa vista. La comprensión humana QS-08 y los bloqueos institucionales siguen pendientes según la matriz funcional.

## Revalidación del árbol actual e integridad de migraciones — T-44, 2026-11-02

- En la revisión del diff detecté que el esquema base `SCHEMA` contenía una modificación que pertenece a `0006`. Restauré el trigger `0001` a su comportamiento histórico y dejé el lock exclusivamente en `UPGRADE_0006_SQL`; `CURRENT_SCHEMA` sigue concatenando `0006`, así que el comportamiento del entorno de pruebas actual se conserva.
- En una base nueva de `pgserver`, Alembic `upgrade 0001` confirmó `FOR UPDATE` ausente y `upgrade head` confirmó `alembic_version=0007`, tabla `placement_work_plan_item` y lock presente. La base temporal se limpió.
- Se reejecutó la suite backend: **75 passed, 1 warning** en **111.24 s**; frontend **32/32 en 11 archivos**; `tsc -b && vite build` **EXIT 0**, 57 módulos, 993 ms; runner aislado Chromium **3/3** en **59.5 s**. La prueba relacional también comprueba que un supervisor docente ve solo la práctica asignada.
- Se revisaron seis capturas nuevas de esta E2E: expediente desktop/móvil **1280×4695 / 390×5746**, dashboard estudiante **1280×720 / 390×1137**, dashboard WPS **1280×900 / 390×844**. Docker Engine no estaba disponible; todas las bases fueron temporales sin volúmenes compartidos y la demo/local no se tocaron.
- La evidencia histórica T-42/T-43 se conserva por separado. La validación integral del procedimiento de demo con datos existentes sigue pendiente; no se migró la demo persistente.

## Orientación por estado y dashboard de supervisión — T-43, 2026-11-02

- El inicio estudiantil deriva título, explicación, estado y destino de la última postulación/práctica. En documentación usa el estado persistido de requisitos para diferenciar entrega/corrección de estados en revisión o condiciones vinculadas a otra relación; en ACTIVE conduce al expediente; en estados terminales conduce a la consulta histórica. No crea transiciones ni requisitos.
- Supervisores laborales/docentes y coordinación consultan desde el inicio las prácticas que devuelve `GET /placements`; el backend mantiene el filtrado relacional existente. E2E verifica WPS asignado, selección de la práctica y navegación al expediente; no agrega campos del estudiante.
- Validación nueva T-43: frontend **32/32 en 11 archivos**, `tsc -b && vite build` **EXIT 0** (57 módulos), E2E Chromium **3/3** sobre `pgserver` temporal (1.0 min), incluidos estado `SUBMITTED`, expediente relacionado y viewport 390 px sin overflow. Capturas del expediente (1280×4695 y 390×5746), dashboard de estudiante (1280×720 y 390×1137) y dashboard WPS (1280×900 y 390×844) fueron revisadas.
- La suite backend **75 passed, 1 warning** y Alembic `0006→0007` EXIT 0 pertenecen a T-42, ejecutado antes en esta continuación; T-43 no cambió backend. Docker Engine no estuvo disponible y el runner usó una nueva base efímera local sin volumen. No se accedió a la BD local/demo.
- QS-08/T-13 sigue pendiente: no hay estudio con participantes y la derivación no constituye validación humana de comprensión de todos los estados. Reasignación académica, aprobación formal de cambios, decisión de evidencia y actores de cierre continúan abiertas.

## Plan de trabajo — implementación actual 2026-11-02

- La migración `0007_work_plan_assignments.py`, `GET/POST /placements/{pid}/work-plan` y la sección “Plan de trabajo” del expediente registran actividades narrativas. El supervisor laboral de la versión vigente puede asignarlas; el acceso de lectura se recorta al estudiante titular, supervisión docente asignada, coordinación del programa y EC. Miembro anfitrión y legal no reciben este contenido.
- Las altas quedan append-only, secuenciales y auditadas en la transacción. No hay fechas límite, calificaciones, estado de cumplimiento ni efecto automático sobre activación/cierre. No se implementa edición/retiro de una asignación ni seguimiento estructurado de su cumplimiento.
- Validación nueva 2026-11-02: backend **75 passed, 1 warning** en `pgserver`; Alembic `0006→0007` pasó incrementalmente; frontend **25/25**; `tsc -b && vite build` **EXIT 0** (56 módulos); Chromium **3/3** con `scripts/run_isolated_e2e.py`. Capturas nuevas **1280×4695** y **390×5746** inspeccionadas.
- Docker Engine no estaba disponible; se usaron bases desechables sin volúmenes compartidos. `0007` se aplicó solo en una base temporal; no se accedió a la base local ni a la demo y no se alteraron contenedores/volúmenes. Los resultados 74/74 y 3/3 sobre `0006` del 2026-10-26 siguen identificados como históricos. No se declara terminado el producto.

## Continuación de supervisión y cierre con evidencia — 2026-10-26

### Revalidación y hardening concurrente — continuación más reciente 2026-10-26

- Se encontró y corrigió una carrera en la guarda de `progress_entry`: la consulta a estado `ACTIVE` no bloqueaba la práctica frente a `confirm_completion`. `record_hours` y el trigger toman ahora el lock del registro padre; la migración nueva `0006_serialize_hours_and_completion.py` actualiza bases futuras sin alterar datos existentes.
- `test_t04_concurrent_hours_insert_waits_for_completion_commit` pausó la confirmación tras el `UPDATE`; el `INSERT` directo quedó esperando el lock y el trigger lo denegó al persistirse `COMPLETED`. Prueba focal **1/1**; suite backend **74/74**, 1 warning Starlette/httpx, 67.31 s.
- Pruebas frontend **24/24**, build TypeScript/Vite **EXIT 0** (55 módulos), E2E Chromium **3/3** en 46.0 s contra una base nueva `tmpfs`, con Alembic `0006 (head)`. Capturas nuevas de escritorio **1280×4426** y móvil **390×5466** inspeccionadas.
- El primer E2E de esta continuación tuvo 2 pasadas y una falla por no compilar con la bandera documentada de demo; la repetición siguiente no arrancó por agotamiento de subredes automáticas. Se registraron como fallos de configuración/entorno. El run final usó un build temporal con la bandera activa y red explícita `/24`, sin retirar ni alterar recursos anteriores.
- **Cobertura pendiente:** T-04 no probó retiro concurrente de evidencia; no existe una operación de retiro disponible. OPEN-02/11/14, OPEN-03 y el resto de flujos no especificados siguen pendientes; no se declara el producto completo.

### Corte previo de supervisión y cierre con evidencia — 2026-10-26 (histórico)

- Se añadieron APIs/UI y tablas append-only para avances, evaluaciones narrativas, incidentes/cambios y evidencia FINAL_REPORT versionada. El E2E recorrió entregas reales de prueba, evaluación del supervisor asignado, horas desde la política persistida, reload, finalización, cierre e historial terminal.
- La suite backend completa pasó **73/73** (1 warning Starlette/httpx, 115.10 s); frontend **24/24** (10 archivos); `tsc -b && vite build` pasó con 55 módulos; Playwright Chromium final **3/3** (58.1 s). La expectativa errónea sobre la acción del estudiante se corrigió en el test. La revisión visual también encontró y corrigió un texto de activación inexacto para una práctica ACTIVE; r6 comprueba la coordinación autorizada y los eventos de cierre.
- Capturas E2E finales inspeccionadas: escritorio **1280×4521**, móvil **390×5601**. El test móvil confirma que `scrollWidth` no supera 390 px.
- La salida de cierre se deriva de evidencia persistida: informe en `completion_evidence`, evaluación FINAL, suma de horas y requisitos materializados. El ensayo de 100 h y requisitos de informe/evaluación pertenecen a una política sintética en PostgreSQL `tmpfs`; no se convierten en regla institucional.
- En ese corte, T-04 concurrente aún no se había ejecutado. Las evaluaciones no usan escala, los reportes CHANGE no alteran versiones y los incidentes no resuelven/escalan automáticamente. La mensajería, paneles y revisión/publicación aún no están implementados. Ver comandos y límites en [validation-results.md](validation/validation-results.md).

## Expediente integral y controles de cierre — ejecución anterior 2026-10-26 (histórica)

- El expediente consulta la versión de elegibilidad guardada en `application.policy_version_id`, y las versiones de activación/finalización fijadas a la colocación. El checklist, las decisiones/versiones documentales y las condiciones de cierre se proyectan desde registros persistidos.
- La vista permite confirmar finalización a coordinación del programa y cerrar a EC solo cuando el backend declara la capacidad/estado correspondientes. La interfaz bloquea el botón mientras quede una regla obligatoria pendiente o una condición de activación incumplida; el backend conserva la comprobación autoritativa en cada POST.
- La bitácora de horas del titular permanece visible en el expediente después de completar/cerrar, condicionada por `read_hours`. Backend verificó lecturas en COMPLETED/CLOSED y que un nuevo POST en CLOSED devuelve `409 PLACEMENT_NOT_ACTIVE` sin alterar el historial.
- En esa corrida histórica: suite backend **71 passed**, frontend **22/22**, build **54 módulos** y Chromium **3/3**. El primer E2E falló porque el `<label>` de créditos no estaba asociado; se corrigió el HTML manteniendo `getByLabel`. Un test backend sin `Origin` fue correctamente denegado por CSRF; se corrigió el test.
- En ese corte histórico se inspeccionaron capturas de 1280×2620 y 390×3574. En móvil las tarjetas se apilaban y no había overflow; Playwright comprobaba el ancho del documento. Se verificaron el historial, las relaciones, las versiones/decisiones documentales y las horas persistidas.
- Esa corrida no inventó políticas: el E2E usó seed temporal y no cargó evidencia final real; el backend usó filas sintéticas para probar completar/cerrar. Esos límites aplican a la ejecución histórica y se actualizaron arriba.

## Actualización del incremento de cierre — 2026-10-25

Esta sección reemplaza los estados anteriores de autorización HTTP, concurrencia de compuerta, demo limpia y E2E donde estos difieran; no cambia datos ni reglas institucionales.

| Área | Clasificación actual | Evidencia / brecha restante |
|---|---|---|
| Matriz HTTP por rol y relación | **Implementado y validado** | `validation/http-authorization-matrix.md` enumera rutas y relación requerida; `backend/tests/test_http_authorization.py` y `test_routes_actions.py` ejercitan negativas cruzadas HTTP. Corrigióse una denegación de permisos en colas de revisión, que ahora responde 403 vía `Forbidden`, no 409. Proyección externa de elegibilidad devuelve solo el resultado, no perfil académico/motivos internos. No es auditoría de penetración ni prueba RLS. |
| Compuerta concurrente activación/rechazo | **Implementado y validado** | Migración `0004_serialize_checklist_and_placement_gates.py` bloquea la fila padre en ambos lados de la carrera; T-02 y suite completa pasaron en PostgreSQL. T-04 concurrente (cierre) sigue sin ejecutarse. |
| Seguimiento y evidencia final | **Implementado y validado para el alcance documentado** | `placement_progress_report`, `placement_evaluation`, `placement_incident`, `completion_evidence`; APIs y `PlacementFollowUp`. Pruebas HTTP y E2E verifican las relaciones, campos filtrados, versiones, reload, FINAL_REPORT, evaluación narrativa, cierre e historial. No cubre mensajería, resolución/escalamiento ni versionado formal de cambios (OPEN-03). |
| E2E de navegador | **Implementado y validado (flujos explícitos)** | T-35/T-37 son históricos; la corrida actual pasó 3/3 en Chromium: oportunidad, selección, aprobación, documentos/versiones, activación, seguimiento, evaluación, evidencia final, horas, cierre e historial. Capturas 1280×4521 y 390×5601 revisadas; E2E confirma 390 px sin overflow. No cubre todos los browsers/tamaños ni roles fuera de la matriz actual. |
| Registro de horas opcional | **Implementado y validado** | `POST/GET /placements/{pid}/hours`: estudiante titular; solo se escribe en `ACTIVE`; horas finitas y mayores que cero. HTTP y E2E validan denegaciones, escritura, lectura y persistencia. No existe aprobación. La obligatoriedad sigue pendiente en el RFP. |
| Entorno de validación aislado | **Implementado y validado** | La suite backend usó el Compose sin puertos/volúmenes. E2E usó proyectos distintos, PostgreSQL `tmpfs`, sin volúmenes compartidos, API interna y frontend en loopback. La migración `0005` se aplicó al iniciar API contra bases nuevas. No se usó la base local ni la demo persistente. El runbook demo previamente verificado sigue en `0004`; la demo no se migró en esta validación. |
| Reglas de duplicados, retiro, alternativas, cupos | **Pendiente de decisión institucional** | No hay requisito inequívoco para la unicidad tras retiro/reapertura, prioridad de alternos ni cupos (`OPEN-13`). No se inventó una transición ni una restricción. |
| Varias colocaciones activas (OPEN-19) | **Pendiente de decisión institucional** | Se mantiene sin cambios el hallazgo de `student1` con dos filas sintéticas `SELECTED` y dos `ACTIVE`. Opciones pendientes: bloquear toda segunda activa, bloquear solo solapamiento de fechas o permitir un máximo configurable por programa; falta definir el momento de evaluación y tratamiento de datos existentes. |
| SSO institucional, email y almacenamiento real de archivos | **Bloqueado por integración externa** | Requiere proveedor/credenciales y configuración TI (IdP/correo) y servicio/repositorio de documentos; las cuentas locales y almacenamiento local siguen siendo la demo. |

## Actualización de catálogos de oportunidad — 2026-10-25

Se cierra la brecha técnica de selección de catálogos descrita en el corte anterior, sin alterar el flujo institucional aún abierto:

- `GET /opportunities/catalogs` entrega opciones utilizables por quienes ya pueden crear oportunidades. Un miembro anfitrión recibe su organización y programas válidos por la regla existente; un coordinador de programa recibe sus programas y organizaciones válidas por esa misma regla OR.
- `GET /opportunities/{oid}/workplace-supervisors` exige una relación de miembro anfitrión con la organización de la oportunidad y solo devuelve supervisores laborales activos de esa organización.
- `Opportunities.tsx` ahora presenta selects con nombres y no solicita IDs numéricos; el E2E confirma los nombres y una selección nominativa. Pruebas HTTP cubren accesos ajenos/roles denegados y pruebas de servicio confirman que no aparece una cuenta inactiva.
- Validación de este incremento: suite backend 70/70; foco catálogos 6/6 y regresión de supervisor inactivo 1/1; frontend 10/10; `tsc -b && vite build` exitoso (48 módulos); Playwright Chromium 3/3; OpenAPI 37 operaciones. Comandos y límites están en [validation-results.md](validation/validation-results.md).
- Esto no implementa revisión, publicación, edición ni cierre. La creación continúa publicando directamente como `PUBLISHED` por el comportamiento actual; actor, pasos y permisos de revisión siguen bloqueados por OPEN-05. El corte anterior que indicaba “sin API de catálogos” queda superado por este incremento.

## Matriz priorizada

| Prioridad | Requisito o flujo | Clasificación | Evidencia concreta y brecha restante |
|---|---|---|---|
| **P0** | Proteger la base de datos usada por las pruebas | **Implementado y validado** | `backend/tests/conftest.py` limpia tablas con `TRUNCATE`; si recibe `DATABASE_URL`, solo acepta `host=db`, puerto 5432 y `dbname=dh05_http_test`. `test_database_safety.py` comprueba que incluso un host externo con nombre `*_test` y la base demo se rechazan. El Compose de pruebas no monta volumen y se desmonta tras cada corrida. |
| **P0** | Límite de tamaño de archivos en HTTP | **Implementado y validado** | `backend/app/modules/lifecycle/router.py` verifica `Content-Length` y limita también cuerpos en streaming antes de almacenar. `test_http_upload_rejects_oversized_declared_and_streamed_bodies` comprueba ambos caminos y que no quede una entrega. La comprobación del formato sigue basada en extensión, MIME y firma inicial; no es un análisis antivirus ni una validación completa del contenido. |
| **P1** | Autenticación y cuentas locales | **Implementado y validado** | `backend/app/modules/identity/`, `provision_user.py`, migración `0003`; `test_authentication.py` y `test_invitations.py`. Login por usuario/correo, hashes Argon2id, sesiones revocables, estado de cuenta, roles desde BD, invitaciones y recuperación local. No hay registro público. |
| **P1** | SSO institucional y entrega de recuperación | **Bloqueado por decisión institucional o integración externa** | `OPEN-21`, `README.md` y `ADR-007`: no hay IdP, protocolo, discovery URL, credenciales ni cuenta de prueba. No hay proveedor de correo; en desarrollo el token se devuelve al operador, en otros entornos la entrega está deshabilitada. Se requiere decisión/configuración de TI. |
| **P1** | Crear, revisar, publicar, editar y cerrar oportunidades | **Parcial; flujo técnico validado T-47** | `0011` y API/UI habilitan borrador, envío, aprobación, publicación y cierre con triggers de transición. `OPPORTUNITY_REVIEWER_ROLES` y `OPPORTUNITY_PUBLISHER_ROLES` no tienen valores por defecto; el harness aislado configura EC para verificar el recorrido. OPEN-05 aún debe decidir autoridades de producción; edición/criterios no definidos. |
| **P1** | Postulación y selección | **Parcial** | `applications/service.py` evalúa la política al postular. La selección valida ahora que la oportunidad siga publicada y que el resultado persistido sea `ELIGIBLE`; `test_selection.py` cubre ambas guardas y la selección repetida. No hay retiro del estudiante, lista/flujo de alternativa, cupo ni transición de renuncia. El tope de cupos es `OPEN-13`. |
| **P1** | Postulaciones duplicadas | **Parcial** | No hay unicidad `(opportunity_id, student_id)` ni detección en `submit_application`; las pruebas no ejercitan duplicados. Antes de imponerla, producto debe confirmar si se permite volver a postular tras retiro/reapertura y qué historial debe conservarse. |
| **P1** | Rechazo académico y selección alternativa | **Parcial** | Hay rechazo académico con motivo y transición terminal (`lifecycle.academic_reject`, `test_t27_academic_reject`). No hay transición de un candidato alternativo, renuncia del seleccionado ni reapertura de candidatos tras rechazo. El comportamiento deseado no está especificado en los artefactos disponibles. |
| **P1** | Estados de colocación, concurrencia y auditoría | **Implementado y validado para activación/rechazo y carrera horas-vs-confirmación; retiro concurrente de evidencia sin validar** | Migración `0004_serialize_checklist_and_placement_gates.py` y T-02 serializan activación y cambio de checklist mediante bloqueo de la misma fila padre. T-04 horas-vs-confirmación pasó 1/1 el 2026-10-26 y está incluida en la suite backend actual de 75. No existe regla contra solapamiento o varias colocaciones `ACTIVE`; la política está sin definir (`OPEN-19`). |
| **P1** | Documentos: checklist, revisión, rechazo y reentrega | **Implementado y validado** | `lifecycle/service.py`, `test_documents.py`: revisión exige motivo, reentrega tras rechazo crea revisión numerada, descarga se limita al estudiante o revisor legal y el backend valida estado del ítem. Los bytes se almacenan en PostgreSQL para la demo local, no en un repositorio externo. |
| **P1** | Requisitos documentales institucionales, privacidad y repositorio externo | **Bloqueado por decisión institucional o integración externa** | Tipos y actores exactos permanecen `OPEN-01/02/20`. `ADR-006` y README describen PostgreSQL como almacenamiento temporal de demo; falta decidir qué metadatos/referencias conservar y configurar el servicio real. El control de formato actual solo valida firma inicial y no sustituye análisis de contenido. |
| **P1** | Compuerta de activación y cierre | **Implementado y validado con reglas persistidas; carrera horas-vs-confirmación probada** | Servicio y triggers, política fijada y requisitos recalculados desde tablas fuente; migración 0006 y `test_t04_concurrent_hours_insert_waits_for_completion_commit` serializan la inserción de horas. OPEN-02/11 y la propuesta BR-18/OPEN-14 siguen pendientes. Retiro concurrente de evidencia no probado. |
| **P1** | Políticas versionadas | **Implementado y validado** | `policies/service.py` valida vocabulario cerrado y rol/programa; trigger append-only en `schema_sql.py`; T-06 y `test_documents.py` comprueban versiones fijadas en aplicaciones/colocaciones. No se ha validado creación concurrente de versiones ni vigencia programada; crear una versión la hace efectiva de inmediato. |
| **P1** | Autorización por rol y recurso, aislamiento organizacional | **Implementado y validado por HTTP para las relaciones cubiertas** | `authz/service.py`, suite backend T-47 **84/84**, E2E **7/7**. Incluye titular, anfitrión, WPS, docente asignado/no asignado, PC/EC y Legal; mensajes, notificaciones, reportes y asignación docente con negativas cruzadas. No es pentest/RLS; OPEN-06 sigue pendiente. |
| **P1** | Colocaciones activas múltiples encontradas en datos | **Bloqueado por decisión institucional o integración externa** | Consulta de solo lectura a la BD local: `student1` tiene postulaciones 1 y 3 `SELECTED` y colocaciones 1 y 2 `ACTIVE`, “Pasantia Demo” y “HTTP smoke — Synthetic Internship”. Son cuentas `@demo.local` y el segundo registro está rotulado como smoke sintético. El backend permite ambas; no se cambió ningún registro. `business-rules.md` y `OPEN-19` no definen un límite global ni por solapamiento de fechas. |
| **P2** | Presentación y acciones del frontend | **Parcial; expediente e interacciones validadas** | `App.tsx`, `PracticeDossier`, bandeja, mensajería, reportes y asignación docente; T-47 **37/37**, build **62 módulos**, E2E **7/7**; capturas desktop/móvil revisadas. QS-08 con participantes y pantallas/acciones de cada rol aún no se han validado completamente. |
| **P2** | Migraciones y procedimiento de demo | **Cadena `0001→0013` e incremento `0010→0011→0012→0013` validados en PostgreSQL temporal; demo persistente no tocada** | T-49: `scripts/check_isolated_migrations.py` comprobó esquema, triggers y ACL mínimos hasta `0013`, `TEMPORARY_POSTGRES_CLEANED=true`. No se ejecutó el runbook sobre la demo persistente; probarlo en una instalación desechable sigue pendiente. |
| **P2** | Rendimiento, adaptadores, usabilidad y límites de módulos | **No validado/completo** | QS-05, QS-07, QS-08; T-09..T-15, carga, fallos de adaptadores y estudio de usabilidad siguen pendientes. Las notificaciones de eventos reales, mensajería y reportes agregados están implementados, pero no sustituyen esos escenarios ni incorporan recordatorios programados. |

## Hallazgos de datos y reglas que no se deben inventar

- La inspección de colocaciones activas fue de solo lectura. No se borró ni cambió ninguna fila.
- Varias colocaciones `ACTIVE` del mismo estudiante son posibles por el esquema y el servicio actuales. No hay una regla aprobada para impedir simultaneidad; producto debe definir si el límite sería global o por fechas solapadas antes de añadir una restricción.
- `OPEN-05`, `OPEN-13`, `OPEN-19`, `OPEN-21` y `OPEN-01/02/06/14/20` requieren decisiones institucionales o integración externa. La ausencia de decisión no se trata como autorización para inventar reglas.

## Correcciones aplicadas en esta auditoría

1. La selección vuelve a comprobar, dentro de la transacción, que la oportunidad esté `PUBLISHED` y que la postulación conserve un resultado `ELIGIBLE`; un estado inconsistente ya no puede crear una colocación.
2. La ruta de entrega de documentos aplica el máximo de 10 MB mientras lee el cuerpo, incluso si no viene `Content-Length`, antes de insertar bytes en PostgreSQL.
3. El listado de postulaciones para empleadores conserva solo el resultado de elegibilidad; no devuelve entradas ni razones que revelen créditos, nivel o cursos aprobados.
4. Las colas de revisión devuelven 403 ante un rol incorrecto mediante `Forbidden`, en vez de exponer una respuesta de conflicto 409.
5. El trigger de la migración 0004 y la actualización de checklist bloquean primero la misma colocación, serializando la decisión documental con la activación.
6. El harness de pytest solo acepta la DB efímera Compose `db/dh05_http_test`; no confía únicamente en el nombre de una base externa.
7. El reset de demo valida el destino, etiqueta de propiedad del volumen y puertos loopback; el seed comprueba estado de entorno, DB y ausencia de cuentas. La imagen API de producción no copia `tests/`.

## Validación del corte anterior (histórica)

| Comando / verificación | Resultado real |
|---|---|
| suite previa, frontend y Compose local | 63 pruebas backend; 5 frontend; build; Alembic 0003 | Histórico del corte 2026-10-22; los resultados vigentes aparecen en [validation-results.md](validation/validation-results.md). |

El Python del host es 3.14 y las extensiones locales de `.deps` corresponden a CPython 3.12; por eso el backend se probó en contenedor Python 3.12. La ejecución usó bases de pruebas separadas. No se volvió a sembrar ni se alteró la base local de demo.

## Siguiente incremento recomendado

1. Resolver con producto la revisión/publicación de oportunidades (`OPEN-05`), cupos (`OPEN-13`), retiro/repostulación y candidatos alternativos.
2. Resolver con producto/TI la simultaneidad (`OPEN-19`), reglas/actores de documentos y cierre (`OPEN-01/02/11/14/20`), alcance de privacidad (`OPEN-06/09`) e IdP, correo y repositorio externo.
3. Tras esas decisiones, exponer los flujos formales aprobados (incluida asignación académica y cambios versionados); ejecutar la variante concurrente de cierre T-04 y ampliar E2E al resto de vistas/roles que queden en alcance.

## Actualización de auditoría funcional — 2026-10-24

- Confirmado en el código que el backend aún crea oportunidades directamente `PUBLISHED`; no hay edición, cierre, review/publish endpoints ni API de catálogos. El review de publicación queda bloqueado por OPEN-05; no se añadieron transiciones supuestas.
- **Nota de actualización 2026-10-25:** los dos endpoints de catálogos ya se añadieron y validaron (ver actualización anterior); la afirmación de ausencia de catálogos en este registro fechado corresponde al corte del 24-10. El flujo de publicación/revisión, edición y cierre sigue sin implementarse por OPEN-05.
- Los siete roles están presentes en asignaciones; los roles de supervisor laboral/docente tienen autorización de lectura relacional, pero no dashboards/vistas propias ni endpoints de evaluación/incidentes. Se corrigió que al seleccionar solo pueda asignarse como supervisor laboral un usuario `WORKPLACE_SUPERVISOR` de la misma organización anfitriona. También se rechazan fechas inicio posteriores a fin.
- Los servicios `propose_change`/`approve_version` están probados a nivel de servicio, pero no se exponen por HTTP; no se agregaron endpoints mientras OPEN-03 no resuelve quién aprueba y el efecto de una versión pendiente.
- La matriz completa de requisitos, incluyendo RNF y limitaciones de fuente, está en el documento enlazado arriba. El diseño sigue no listo para entrega final: falta cerrar flujos UI/API, requisitos documentales reales e integraciones externas, y completar las validaciones indicadas.

## Contraste con el RFP fuente y trabajo posterior a activación

El RFP §5 declara incompleto el proceso inicial y §9 llama a las capacidades una lista de posibles necesidades que no prescribe el alcance. El RFP §3 sí asigna al supervisor laboral la tarea de asignar actividades; se implementó una primera sección narrativa de plan, sin estados, plazos o aprobación añadidos. Mensajería, recordatorios y reportes agregados aún requieren priorización y definición. Las restricciones expresas siguen vigentes: datos sintéticos; autorización por rol/relación; protección de evaluaciones/datos de empleadores; trazabilidad; no nómina/finanzas, LMS, vigilancia ni selección automática con IA.

La brecha resoluble previa fue el registro opcional de horas para prácticas activas; el servicio y la interfaz muestran acumulado e historial. La interfaz avisa que es opcional y no lo transforma en obligación general. El plan de trabajo actual tampoco añade aprobación automática de actividades; los flujos de comunicación y revisión estructurada permanecen fuera hasta definir roles, campos, estados, evidencia y permisos.

## Verificación final del registro opcional de horas — 2026-10-25

La bitácora se expone en `GET/POST /placements/{pid}/hours`. El backend limita ambas operaciones al estudiante titular; el POST además requiere `ACTIVE` y valida que `hours` sea finito y mayor que cero. El E2E confirmó la fila de 4.5 horas y su total en la vista; tras recargar, volvió a comprobar el total, que se reconstruye desde `GET /hours`. La primera corrida reveló que la API serializa el decimal de PostgreSQL como texto; se corrigió la conversión validada en frontend. La ruta antigua de historial dejó de responder 500 tras corregir la importación del servicio de auditoría. La expectativa anterior de 422 para una colocación no activa era un defecto del test: el contrato de negocio responde 409 `PLACEMENT_NOT_ACTIVE`; el test verifica ese contrato sin reducir la denegación. Resultados y comandos exactos: [validation-results.md](validation/validation-results.md).

La implementación técnica está validada, pero el RFP §5/§9 pide investigar si registrar horas debe ser obligatorio. Esa decisión institucional continúa pendiente; no se añadieron aprobación de horas ni criterios de evaluación.

## Actualización — actividad visible e historial de práctica (2026-10-25)

Se añadió en “Mis documentos” una vista desplegable de acciones ligadas a colocación, checklist y versiones. El endpoint de historial reduce la proyección a fecha/acción y mantiene la autorización por relación; la interfaz traduce acciones conocidas sin mostrar payloads internos. Pruebas actuales: backend focalizado 3/3 y suite completa 70/70; frontend 15/15; `tsc -b && vite build` correcto (50 módulos); Playwright Chromium 3/3 en demo `tmpfs`, incluyendo persistencia tras reload y viewport 390 px sin overflow. La vista cubre el tramo de práctica y no satisface todavía toda la traza oportunidad→postulación→cierre del RFP. OPEN-05, OPEN-02/11/14 y los flujos de supervisión/evaluación/incidentes siguen pendientes conforme a las decisiones institucionales.
