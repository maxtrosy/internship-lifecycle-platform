# Auditoría de preparación para versión final

**Fecha de corte:** 2026-10-25
**Alcance:** código del backend y frontend, migraciones, Docker Compose, pruebas y artefactos de `docs/evaluation-2/`.  
**Fuentes:** RFP de ocho páginas, entregado en `C:\Users\maxtr\Downloads\Project 5 Request for Proposal (2).pdf`, leído completo. Los originales de Evaluación 1 no están en el repositorio; permanecen limitados los mapeos RF↔US y las decisiones que solo constan en resúmenes secundarios.

La auditoría requisito por requisito, incluyendo vistas, endpoints, servicios, permisos, pruebas y acción, se mantiene en [functional-completeness-matrix.md](functional-completeness-matrix.md). Esta actualización no modifica reglas institucionales pendientes ni datos locales.

Los estados describen el comportamiento inspeccionado y la evidencia ejecutada. Compilar por sí solo no cuenta como validación funcional.

## Actualización del incremento de cierre — 2026-10-25

Esta sección reemplaza los estados anteriores de autorización HTTP, concurrencia de compuerta, demo limpia y E2E donde estos difieran; no cambia datos ni reglas institucionales.

| Área | Clasificación actual | Evidencia / brecha restante |
|---|---|---|
| Matriz HTTP por rol y relación | **Implementado y validado** | `validation/http-authorization-matrix.md` enumera rutas y relación requerida; `backend/tests/test_http_authorization.py` y `test_routes_actions.py` ejercitan negativas cruzadas HTTP. Corrigióse una denegación de permisos en colas de revisión, que ahora responde 403 vía `Forbidden`, no 409. Proyección externa de elegibilidad devuelve solo el resultado, no perfil académico/motivos internos. No es auditoría de penetración ni prueba RLS. |
| Compuerta concurrente activación/rechazo | **Implementado y validado** | Migración `0004_serialize_checklist_and_placement_gates.py` bloquea la fila padre en ambos lados de la carrera; T-02 y suite completa pasaron en PostgreSQL. T-04 concurrente (cierre) sigue sin ejecutarse. |
| E2E de navegador | **Implementado y validado (flujos explícitos)** | T-35/T-37 pasó 3/3 en Chromium: acceso rápido a cuentas sintéticas, login inválido/rutas protegidas, postulación, selección, aprobación académica, documentos, activación y registro de horas persistentes. No cubre todas las rutas, roles secundarios, browsers ni todos los tamaños responsive. |
| Registro de horas opcional | **Implementado y validado** | `POST/GET /placements/{pid}/hours`: estudiante titular; solo se escribe en `ACTIVE`; horas finitas y mayores que cero. HTTP y E2E validan denegaciones, escritura, lectura y persistencia. No existe aprobación. La obligatoriedad sigue pendiente en el RFP. |
| Demo aislada | **Implementado y validado** | `docker-compose.demo.yml`, `scripts/Start-Demo.ps1`, guardia de seed y [runbook](validation/demo-runbook.md) separan `dh05_demo` en puerto 5433/volumen `dh05-demo-postgres-data`; arranque limpio migró a 0004, verificó `/health` y sembró 14 cuentas. La base/proyecto local existente no se usó para las pruebas de este incremento. |
| Reglas de duplicados, retiro, alternativas, cupos | **Pendiente de decisión institucional** | No hay requisito inequívoco para la unicidad tras retiro/reapertura, prioridad de alternos ni cupos (`OPEN-13`). No se inventó una transición ni una restricción. |
| Varias colocaciones activas (OPEN-19) | **Pendiente de decisión institucional** | Se mantiene sin cambios el hallazgo de `student1` con dos filas sintéticas `SELECTED` y dos `ACTIVE`. Opciones pendientes: bloquear toda segunda activa, bloquear solo solapamiento de fechas o permitir un máximo configurable por programa; falta definir el momento de evaluación y tratamiento de datos existentes. |
| SSO institucional, email y almacenamiento real de archivos | **Bloqueado por integración externa** | Requiere proveedor/credenciales y configuración TI (IdP/correo) y servicio/repositorio de documentos; las cuentas locales y almacenamiento local siguen siendo la demo. |

## Matriz priorizada

| Prioridad | Requisito o flujo | Clasificación | Evidencia concreta y brecha restante |
|---|---|---|---|
| **P0** | Proteger la base de datos usada por las pruebas | **Implementado y validado** | `backend/tests/conftest.py` limpia tablas con `TRUNCATE`; si recibe `DATABASE_URL`, solo acepta `host=db`, puerto 5432 y `dbname=dh05_http_test`. `test_database_safety.py` comprueba que incluso un host externo con nombre `*_test` y la base demo se rechazan. El Compose de pruebas no monta volumen y se desmonta tras cada corrida. |
| **P0** | Límite de tamaño de archivos en HTTP | **Implementado y validado** | `backend/app/modules/lifecycle/router.py` verifica `Content-Length` y limita también cuerpos en streaming antes de almacenar. `test_http_upload_rejects_oversized_declared_and_streamed_bodies` comprueba ambos caminos y que no quede una entrega. La comprobación del formato sigue basada en extensión, MIME y firma inicial; no es un análisis antivirus ni una validación completa del contenido. |
| **P1** | Autenticación y cuentas locales | **Implementado y validado** | `backend/app/modules/identity/`, `provision_user.py`, migración `0003`; `test_authentication.py` y `test_invitations.py`. Login por usuario/correo, hashes Argon2id, sesiones revocables, estado de cuenta, roles desde BD, invitaciones y recuperación local. No hay registro público. |
| **P1** | SSO institucional y entrega de recuperación | **Bloqueado por decisión institucional o integración externa** | `OPEN-21`, `README.md` y `ADR-007`: no hay IdP, protocolo, discovery URL, credenciales ni cuenta de prueba. No hay proveedor de correo; en desarrollo el token se devuelve al operador, en otros entornos la entrega está deshabilitada. Se requiere decisión/configuración de TI. |
| **P1** | Crear, revisar, publicar, editar y cerrar oportunidades | **Parcial** | `backend/app/modules/opportunities/service.py:create_opportunity` crea directamente en `PUBLISHED`; no hay endpoints de edición, cierre ni transición de revisión. `BR-09` requiere revisión, pero el actor y proceso son `OPEN-05`. Implementar revisión requiere esa decisión; la UI actual describe la creación como publicación inmediata. |
| **P1** | Postulación y selección | **Parcial** | `applications/service.py` evalúa la política al postular. La selección valida ahora que la oportunidad siga publicada y que el resultado persistido sea `ELIGIBLE`; `test_selection.py` cubre ambas guardas y la selección repetida. No hay retiro del estudiante, lista/flujo de alternativa, cupo ni transición de renuncia. El tope de cupos es `OPEN-13`. |
| **P1** | Postulaciones duplicadas | **Parcial** | No hay unicidad `(opportunity_id, student_id)` ni detección en `submit_application`; las pruebas no ejercitan duplicados. Antes de imponerla, producto debe confirmar si se permite volver a postular tras retiro/reapertura y qué historial debe conservarse. |
| **P1** | Rechazo académico y selección alternativa | **Parcial** | Hay rechazo académico con motivo y transición terminal (`lifecycle.academic_reject`, `test_t27_academic_reject`). No hay transición de un candidato alternativo, renuncia del seleccionado ni reapertura de candidatos tras rechazo. El comportamiento deseado no está especificado en los artefactos disponibles. |
| **P1** | Estados de colocación, concurrencia y auditoría | **Implementado y validado para activación/rechazo; cierre concurrente sin validar** | Migración `0004_serialize_checklist_and_placement_gates.py` y T-02 serializan activación y cambio de checklist mediante bloqueo de la misma fila padre; suite completa y prueba focalizada pasan. T-04 concurrente (cierre) sigue sin ejecutar. No existe regla contra solapamiento o varias colocaciones `ACTIVE`; la política está sin definir (`OPEN-19`). |
| **P1** | Documentos: checklist, revisión, rechazo y reentrega | **Implementado y validado** | `lifecycle/service.py`, `test_documents.py`: revisión exige motivo, reentrega tras rechazo crea revisión numerada, descarga se limita al estudiante o revisor legal y el backend valida estado del ítem. Los bytes se almacenan en PostgreSQL para la demo local, no en un repositorio externo. |
| **P1** | Requisitos documentales institucionales, privacidad y repositorio externo | **Bloqueado por decisión institucional o integración externa** | Tipos y actores exactos permanecen `OPEN-01/02/20`. `ADR-006` y README describen PostgreSQL como almacenamiento temporal de demo; falta decidir qué metadatos/referencias conservar y configurar el servicio real. El control de formato actual solo valida firma inicial y no sustituye análisis de contenido. |
| **P1** | Compuerta de activación y cierre | **Implementado y validado** | Validación en servicio y triggers, políticas fijadas al aprobar y rechazo de acciones repetidas/ilegales; `test_lifecycle.py` y `test_documents.py`. Los requisitos exactos y actores siguen abiertos. La política posterior a activación `BR-18` es propuesta sin aprobación del cliente (`OPEN-14`). |
| **P1** | Políticas versionadas | **Implementado y validado** | `policies/service.py` valida vocabulario cerrado y rol/programa; trigger append-only en `schema_sql.py`; T-06 y `test_documents.py` comprueban versiones fijadas en aplicaciones/colocaciones. No se ha validado creación concurrente de versiones ni vigencia programada; crear una versión la hace efectiva de inmediato. |
| **P1** | Autorización por rol y recurso, aislamiento organizacional | **Implementado y validado por HTTP para las relaciones cubiertas** | `authz/service.py`, [matriz de las 35 operaciones](validation/http-authorization-matrix.md), T-34 y suite backend (68/68 en el corte final). Las pruebas niegan cruces de titularidad, organización, supervisor y programa, cubren colas por rol y verifican proyección mínima del empleador. No es prueba de penetración/RLS; el alcance final de algunos campos externos sigue OPEN-06. |
| **P1** | Colocaciones activas múltiples encontradas en datos | **Bloqueado por decisión institucional o integración externa** | Consulta de solo lectura a la BD local: `student1` tiene postulaciones 1 y 3 `SELECTED` y colocaciones 1 y 2 `ACTIVE`, “Pasantia Demo” y “HTTP smoke — Synthetic Internship”. Son cuentas `@demo.local` y el segundo registro está rotulado como smoke sintético. El backend permite ambas; no se cambió ningún registro. `business-rules.md` y `OPEN-19` no definen un límite global ni por solapamiento de fechas. |
| **P2** | Presentación y acciones del frontend | **Parcial** | `frontend/src/App.tsx` limita las secciones por rol; `api.ts` usa la API same-origin y traduce errores conocidos. `formatDomainLabel` presenta enums; `EligibilitySummary` transforma el JSON y ofrece criterios/motivos en detalles; `eligibility.test.ts` cubre elegible, no elegible, motivos, incompletos y forma inesperada. El rediseño neutral y responsive se inspeccionó por rol y 13 vistas no desbordan a 390/320 px; E2E Chromium 3/3 cubre flujos explícitos, no todas las acciones. Las opciones de organización/programa se derivan de oportunidades visibles; sin oportunidades, el fallback de creación sigue pidiendo valores numéricos porque no hay catálogos API. Tampoco existe catálogo API de supervisores ni vistas específicas para supervisores, por lo que su asignación nominativa y esos flujos siguen pendientes. |
| **P2** | Docker Compose, migraciones y procedimiento de demo | **Implementado y validado en demo aislada** | [Runbook](validation/demo-runbook.md), `docker-compose.demo.yml` y `Start-Demo.ps1` validan proyecto, DB, volumen/etiquetas y puertos loopback; el reset/seed limpio llegó a Alembic `0004 (head)`, `/health` OK y 14 cuentas. La imagen API verificada no contiene `/app/tests`. El E2E dejó una oportunidad y una colocación activa de demo; `-Reset` restaura el conjunto limpio. |
| **P2** | Rendimiento, adaptadores, notificaciones, usabilidad y límites de módulos | **No implementado** | `traceability.md`, `validation-plan.md` y `project-status.md`: QS-05, QS-07, QS-08; T-09..T-15, worker/notificaciones, adaptadores con fallos, carga y estudio de usabilidad continúan pendientes. Las pruebas de frontera de módulos existen, pero no prueban todos los escenarios de arquitectura. |

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
2. Resolver con producto/TI la simultaneidad de colocaciones (`OPEN-19`), reglas/actores documentales (`OPEN-01/02/20`), alcance de privacidad (`OPEN-06`) e IdP, correo y repositorio externo.
3. Tras esas decisiones, implementar solamente las reglas aprobadas; conservar pendiente la prueba concurrente de cierre T-04 y ampliar E2E al resto de vistas/roles que queden en alcance.

## Actualización de auditoría funcional — 2026-10-24

- Confirmado en el código que el backend aún crea oportunidades directamente `PUBLISHED`; no hay edición, cierre, review/publish endpoints ni API de catálogos. El review de publicación queda bloqueado por OPEN-05; no se añadieron transiciones supuestas.
- Los siete roles están presentes en asignaciones; los roles de supervisor laboral/docente tienen autorización de lectura relacional, pero no dashboards/vistas propias ni endpoints de evaluación/incidentes. Se corrigió que al seleccionar solo pueda asignarse como supervisor laboral un usuario `WORKPLACE_SUPERVISOR` de la misma organización anfitriona. También se rechazan fechas inicio posteriores a fin.
- Los servicios `propose_change`/`approve_version` están probados a nivel de servicio, pero no se exponen por HTTP; no se agregaron endpoints mientras OPEN-03 no resuelve quién aprueba y el efecto de una versión pendiente.
- La matriz completa de requisitos, incluyendo RNF y limitaciones de fuente, está en el documento enlazado arriba. El diseño sigue no listo para entrega final: falta cerrar flujos UI/API, requisitos documentales reales e integraciones externas, y completar las validaciones indicadas.

## Contraste con el RFP fuente y trabajo posterior a activación

El RFP §5 declara incompleto el proceso inicial y §9 llama a las capacidades una lista de posibles necesidades que no prescribe el alcance. Por ello, supervisión, plan de trabajo, evaluaciones intermedias/finales, incidentes, recordatorios y reportes no se implementan por mera mención: hace falta priorización y definición acordada. Las restricciones sí son expresas: solo datos sintéticos; autorización por rol y relación; proteger evaluaciones/datos de empleadores; trazabilidad; integraciones pueden simularse; no nómina/finanzas, LMS, vigilancia ni selección automática con IA.

La brecha resoluble seleccionada fue el registro opcional de horas para prácticas activas: el servicio backend existía, el estudiante podía crear registros autorizados, la política ya puede incluir `MIN_HOURS`, pero no había interfaz que completara el recorrido ni lectura persistida visible. Se añadió UI con acumulado e historial de eventos. La interfaz avisa que es opcional; no transforma la posibilidad del RFP en obligación general, ni inventa aprobación de horas, actividades, plan, evaluaciones o escalas. Los otros flujos posteriores permanecen fuera de este incremento hasta que stakeholders definan roles, campos, estados, evidencia y permisos.

## Verificación final del registro opcional de horas — 2026-10-25

La bitácora se expone en `GET/POST /placements/{pid}/hours`. El backend limita ambas operaciones al estudiante titular; el POST además requiere `ACTIVE` y valida que `hours` sea finito y mayor que cero. El E2E confirmó la fila de 4.5 horas y su total en la vista; tras recargar, volvió a comprobar el total, que se reconstruye desde `GET /hours`. La primera corrida reveló que la API serializa el decimal de PostgreSQL como texto; se corrigió la conversión validada en frontend. La ruta antigua de historial dejó de responder 500 tras corregir la importación del servicio de auditoría. La expectativa anterior de 422 para una colocación no activa era un defecto del test: el contrato de negocio responde 409 `PLACEMENT_NOT_ACTIVE`; el test verifica ese contrato sin reducir la denegación. Resultados y comandos exactos: [validation-results.md](validation/validation-results.md).

La implementación técnica está validada, pero el RFP §5/§9 pide investigar si registrar horas debe ser obligatorio. Esa decisión institucional continúa pendiente; no se añadieron aprobación de horas ni criterios de evaluación.
