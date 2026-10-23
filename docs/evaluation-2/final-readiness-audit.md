# Auditoría de preparación para versión final

**Fecha de corte:** 2026-10-23  
**Alcance:** código del backend y frontend, migraciones, Docker Compose, pruebas y artefactos de `docs/evaluation-2/`.  
**Límite de evidencia:** el repositorio no contiene el RFP fuente ni los archivos originales de la Evaluación 1; `evaluation-1-audit.md` y los documentos de evaluación-2 los citan, pero no permiten volver a contrastarlos directamente.

Los estados describen el comportamiento inspeccionado y la evidencia ejecutada. Compilar por sí solo no cuenta como validación funcional.

## Actualización del incremento de cierre — 2026-10-23

Esta sección reemplaza los estados anteriores de autorización HTTP, concurrencia de compuerta, demo limpia y E2E donde estos difieran; no cambia datos ni reglas institucionales.

| Área | Clasificación actual | Evidencia / brecha restante |
|---|---|---|
| Matriz HTTP por rol y relación | **Implementado y validado** | `validation/http-authorization-matrix.md` enumera rutas y relación requerida; `backend/tests/test_http_authorization.py` y `test_routes_actions.py` ejercitan negativas cruzadas HTTP. Corrigióse una denegación de permisos en colas de revisión, que ahora responde 403 vía `Forbidden`, no 409. Proyección externa de elegibilidad devuelve solo el resultado, no perfil académico/motivos internos. No es auditoría de penetración ni prueba RLS. |
| Compuerta concurrente activación/rechazo | **Implementado y validado** | Migración `0004_serialize_checklist_and_placement_gates.py` bloquea la fila padre en ambos lados de la carrera; T-02 y suite completa pasaron en PostgreSQL. T-04 concurrente (cierre) sigue sin ejecutarse. |
| E2E de navegador | **Implementado sin E2E** hasta confirmar el resultado final de T-35 en `validation-results.md` | Playwright Chromium prueba error de login, ruta protegida y flujo UI por estudiante, empleador, coordinador académico, legal y EC hasta activar; incluye viewport 390 px. No cubre todas las rutas, roles secundarios, browsers ni todos los tamaños responsive. |
| Demo aislada | **Implementado y validado** | `docker-compose.demo.yml`, `scripts/Start-Demo.ps1`, guardia de seed y [runbook](validation/demo-runbook.md) separan `dh05_demo` en puerto 5433/volumen `dh05-demo-postgres-data`; arranque limpio migró a 0004, verificó `/health` y sembró 14 cuentas. La base/proyecto local existente no se usó para las pruebas de este incremento. |
| Reglas de duplicados, retiro, alternativas, cupos | **Pendiente de decisión institucional** | No hay requisito inequívoco para la unicidad tras retiro/reapertura, prioridad de alternos ni cupos (`OPEN-13`). No se inventó una transición ni una restricción. |
| Varias colocaciones activas (OPEN-19) | **Pendiente de decisión institucional** | Se mantiene sin cambios el hallazgo de `student1` con dos filas sintéticas `SELECTED` y dos `ACTIVE`. Opciones pendientes: bloquear toda segunda activa, bloquear solo solapamiento de fechas o permitir un máximo configurable por programa; falta definir el momento de evaluación y tratamiento de datos existentes. |
| SSO institucional, email y almacenamiento real de archivos | **Bloqueado por integración externa** | Requiere proveedor/credenciales y configuración TI (IdP/correo) y servicio/repositorio de documentos; las cuentas locales y almacenamiento local siguen siendo la demo. |

## Matriz priorizada

| Prioridad | Requisito o flujo | Clasificación | Evidencia concreta y brecha restante |
|---|---|---|---|
| **P0** | Proteger la base de datos usada por las pruebas | **Implementado y validado** | `backend/tests/conftest.py` limpia tablas con `TRUNCATE`; ahora rechaza una `DATABASE_URL` cuyo nombre no identifique una base de pruebas. `backend/tests/test_database_safety.py` comprueba nombres de test y nombres compartidos. Ejecutar la suite sobre la base de demo queda bloqueado por la guarda. |
| **P0** | Límite de tamaño de archivos en HTTP | **Implementado y validado** | `backend/app/modules/lifecycle/router.py` verifica `Content-Length` y limita también cuerpos en streaming antes de almacenar. `test_http_upload_rejects_oversized_declared_and_streamed_bodies` comprueba ambos caminos y que no quede una entrega. La comprobación del formato sigue basada en extensión, MIME y firma inicial; no es un análisis antivirus ni una validación completa del contenido. |
| **P1** | Autenticación y cuentas locales | **Implementado y validado** | `backend/app/modules/identity/`, `provision_user.py`, migración `0003`; `test_authentication.py` y `test_invitations.py`. Login por usuario/correo, hashes Argon2id, sesiones revocables, estado de cuenta, roles desde BD, invitaciones y recuperación local. No hay registro público. |
| **P1** | SSO institucional y entrega de recuperación | **Bloqueado por decisión institucional o integración externa** | `OPEN-21`, `README.md` y `ADR-007`: no hay IdP, protocolo, discovery URL, credenciales ni cuenta de prueba. No hay proveedor de correo; en desarrollo el token se devuelve al operador, en otros entornos la entrega está deshabilitada. Se requiere decisión/configuración de TI. |
| **P1** | Crear, revisar, publicar, editar y cerrar oportunidades | **Parcial** | `backend/app/modules/opportunities/service.py:create_opportunity` crea directamente en `PUBLISHED`; no hay endpoints de edición, cierre ni transición de revisión. `BR-09` requiere revisión, pero el actor y proceso son `OPEN-05`. Implementar revisión requiere esa decisión; la UI actual describe la creación como publicación inmediata. |
| **P1** | Postulación y selección | **Parcial** | `applications/service.py` evalúa la política al postular. La selección valida ahora que la oportunidad siga publicada y que el resultado persistido sea `ELIGIBLE`; `test_selection.py` cubre ambas guardas y la selección repetida. No hay retiro del estudiante, lista/flujo de alternativa, cupo ni transición de renuncia. El tope de cupos es `OPEN-13`. |
| **P1** | Postulaciones duplicadas | **Parcial** | No hay unicidad `(opportunity_id, student_id)` ni detección en `submit_application`; las pruebas no ejercitan duplicados. Antes de imponerla, producto debe confirmar si se permite volver a postular tras retiro/reapertura y qué historial debe conservarse. |
| **P1** | Rechazo académico y selección alternativa | **Parcial** | Hay rechazo académico con motivo y transición terminal (`lifecycle.academic_reject`, `test_t27_academic_reject`). No hay transición de un candidato alternativo, renuncia del seleccionado ni reapertura de candidatos tras rechazo. El comportamiento deseado no está especificado en los artefactos disponibles. |
| **P1** | Estados de colocación, concurrencia y auditoría | **Implementado, pero sin validación suficiente** | Gates de activación/cierre, bloqueo de fila, auditoría transaccional y eventos append-only: `lifecycle/service.py`, `schema_sql.py`, `test_lifecycle.py`, `test_audit.py`. T-01/T-02 están cubiertas; la variante concurrente de T-04 no. No existe restricción contra solapamiento o varias colocaciones `ACTIVE` por estudiante; la política está sin definir (`OPEN-19`). |
| **P1** | Documentos: checklist, revisión, rechazo y reentrega | **Implementado y validado** | `lifecycle/service.py`, `test_documents.py`: revisión exige motivo, reentrega tras rechazo crea revisión numerada, descarga se limita al estudiante o revisor legal y el backend valida estado del ítem. Los bytes se almacenan en PostgreSQL para la demo local, no en un repositorio externo. |
| **P1** | Requisitos documentales institucionales, privacidad y repositorio externo | **Bloqueado por decisión institucional o integración externa** | Tipos y actores exactos permanecen `OPEN-01/02/20`. `ADR-006` y README describen PostgreSQL como almacenamiento temporal de demo; falta decidir qué metadatos/referencias conservar y configurar el servicio real. El control de formato actual solo valida firma inicial y no sustituye análisis de contenido. |
| **P1** | Compuerta de activación y cierre | **Implementado y validado** | Validación en servicio y triggers, políticas fijadas al aprobar y rechazo de acciones repetidas/ilegales; `test_lifecycle.py` y `test_documents.py`. Los requisitos exactos y actores siguen abiertos. La política posterior a activación `BR-18` es propuesta sin aprobación del cliente (`OPEN-14`). |
| **P1** | Políticas versionadas | **Implementado y validado** | `policies/service.py` valida vocabulario cerrado y rol/programa; trigger append-only en `schema_sql.py`; T-06 y `test_documents.py` comprueban versiones fijadas en aplicaciones/colocaciones. No se ha validado creación concurrente de versiones ni vigencia programada; crear una versión la hace efectiva de inmediato. |
| **P1** | Autorización por rol y recurso, aislamiento organizacional | **Implementado, pero sin validación suficiente** | `authz/service.py` filtra por relaciones y reduce campos externos; pruebas `test_authz.py`, `test_selection.py`, `test_documents.py`. La matriz T-03 es de servicio/dominio, no una verificación completa por HTTP. RLS/T-14 no está implementada/probada; el conjunto exacto de campos externos es `OPEN-06`. |
| **P1** | Colocaciones activas múltiples encontradas en datos | **Bloqueado por decisión institucional o integración externa** | Consulta de solo lectura a la BD local: `student1` tiene postulaciones 1 y 3 `SELECTED` y colocaciones 1 y 2 `ACTIVE`, “Pasantia Demo” y “HTTP smoke — Synthetic Internship”. Son cuentas `@demo.local` y el segundo registro está rotulado como smoke sintético. El backend permite ambas; no se cambió ningún registro. `business-rules.md` y `OPEN-19` no definen un límite global ni por solapamiento de fechas. |
| **P2** | Presentación y acciones del frontend | **Parcial** | `frontend/src/App.tsx` limita las secciones por rol; `api.ts` usa la API same-origin y traduce errores conocidos. `formatDomainLabel` presenta enums; `EligibilitySummary` transforma el JSON y ofrece criterios/motivos en detalles; `eligibility.test.ts` cubre elegible, no elegible, motivos, incompletos y forma inesperada. El formulario de oportunidad y selección de supervisor expone IDs internos; no hay API de opciones con nombres. No hay E2E para todas las rutas/roles ni responsive validado en todos los viewports. |
| **P2** | Docker Compose, migraciones y procedimiento de demo | **Implementado, pero sin validación suficiente** | Compose inicia API, PostgreSQL y frontend; `/health` respondió OK y Alembic indicó `0003 (head)`. La base no tiene volumen nombrado, por lo que retirarla elimina datos. El seed solo es para desarrollo y debe ejecutarse una vez en DB limpia; no se volvió a ejecutar sobre la base activa. Falta un smoke repetible desde DB limpia y recorrido E2E de todos los roles. |
| **P2** | Rendimiento, adaptadores, notificaciones, usabilidad y límites de módulos | **No implementado** | `traceability.md`, `validation-plan.md` y `project-status.md`: QS-05, QS-07, QS-08; T-09..T-15, worker/notificaciones, adaptadores con fallos, carga y estudio de usabilidad continúan pendientes. Las pruebas de frontera de módulos existen, pero no prueban todos los escenarios de arquitectura. |

## Hallazgos de datos y reglas que no se deben inventar

- La inspección de colocaciones activas fue de solo lectura. No se borró ni cambió ninguna fila.
- Varias colocaciones `ACTIVE` del mismo estudiante son posibles por el esquema y el servicio actuales. No hay una regla aprobada para impedir simultaneidad; producto debe definir si el límite sería global o por fechas solapadas antes de añadir una restricción.
- `OPEN-05`, `OPEN-13`, `OPEN-19`, `OPEN-21` y `OPEN-01/02/06/14/20` requieren decisiones institucionales o integración externa. La ausencia de decisión no se trata como autorización para inventar reglas.

## Correcciones aplicadas en esta auditoría

1. La selección vuelve a comprobar, dentro de la transacción, que la oportunidad esté `PUBLISHED` y que la postulación conserve un resultado `ELIGIBLE`; un estado inconsistente ya no puede crear una colocación.
2. La ruta de entrega de documentos aplica el máximo de 10 MB mientras lee el cuerpo, incluso si no viene `Content-Length`, antes de insertar bytes en PostgreSQL.
3. El harness de pytest se niega a ejecutar la limpieza contra bases cuyo nombre no indique que son de pruebas.

## Validación ejecutada

| Comando / verificación | Resultado real |
|---|---|
| `python -m pytest -q /workspace/tests` en contenedor Python 3.12, con DB temporal nueva `dh05_release_test` | **63 passed, 1 warning, 36.00 s**. La advertencia es deprecación de Starlette TestClient con `httpx`; no falló ninguna prueba. |
| `npm run test` en `frontend/` | **5 passed** en `src/eligibility.test.ts`. |
| `npm run build` en `frontend/` | `tsc -b && vite build`: **EXIT 0**, 45 módulos transformados. |
| `GET http://localhost:8000/health` | `200`, `{"status":"ok"}`. |
| `docker compose exec api alembic current` | **0003 (head)**. |
| `docker compose up --build -d api frontend` | Imágenes reconstruidas; API y frontend volvieron a `Up`. El frontend sirve `/assets/index-DTCGYKtr.js`, que coincide con el bundle local y contiene las etiquetas de elegibilidad en español. |
| Lectura de postulaciones/colocaciones `ACTIVE` tras el rebuild | Siguen presentes las dos filas sintéticas previas de `student1`; no se alteraron datos de demo. Las bases temporales usadas por pytest se eliminaron después de las pruebas. |

El Python del host es 3.14 y las extensiones locales de `.deps` corresponden a CPython 3.12; por eso el backend se probó en contenedor Python 3.12. La ejecución usó bases de pruebas separadas. No se volvió a sembrar ni se alteró la base local de demo.

## Siguiente incremento recomendado

1. Resolver con producto quién revisa y publica oportunidades (`OPEN-05`), reglas de cupos (`OPEN-13`), retiro/reselección y política de postulaciones repetidas.
2. Resolver con producto/TI la simultaneidad de colocaciones (`OPEN-19`), reglas y actores documentales (`OPEN-01/02/20`), alcance de privacidad externa (`OPEN-06`) y proveedor SSO/correo (`OPEN-21`).
3. Después de esas decisiones, completar el flujo funcional faltante y añadir matriz HTTP de autorización, E2E por rol/responsive, prueba concurrente de T-04, demo desde base limpia y evidencia de migraciones.
