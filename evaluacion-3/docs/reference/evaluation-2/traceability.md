# Trazabilidad

Permite responder **"¿dónde se satisface este requisito?"** y **"¿por qué existe este componente?"**. Solo se incluyen los requisitos arquitectónicamente significativos (ver `architecture-and-design.md` §3).

## D.0 Matriz principal

| Requisito | Escenario de calidad | Driver | ADR | Componente | Vista | Regla | Validación |
|---|---|---|---|---|---|---|---|
| RF-05 | QS-03 | AD-02 | ADR-001 | C-04, C-05 | V-COMP, SEQ-01 | BR-08, BR-12 | **T-06, T-25, T-30, T-53/T-54/T-55/T-56**: política versionada con motivo y autor, revisión restringida al coordinador y datos ausentes en revisión manual. T-55/T-56 agregan opt-ins para fixture demo de elegibilidad; sus umbrales quedan auditados, son reemplazables y no institucionales. |
| RF-06 / RF-07 | QS-01 (precondición) | AD-01 | ADR-003 | C-06 | V-STATE-PLC T1–T3, SEQ-01 | BR-10, BR-11 | **T-26/T-27** (selección y aprobación); T-03 autorización (EXECUTED) |
| RF-08 | QS-01, QS-03 | AD-01, AD-02 | ADR-001, ADR-003 | C-05, C-07 | V-DOM | BR-14 | T-02/T-16e (PoC); T-28 (entrega, revisión y activación), T-29 (revisiones, motivos y descarga) |
| RF-09 | QS-01 | AD-01 | ADR-003 | C-06, C-07 | V-STATE-PLC T4, SEQ-02 | BR-01, BR-02, BR-18 | **T-01, T-02, T-02b, T-08** (EXECUTED); T-16a/b/d (PoC); T-28/T-30 (política y compuerta) |
| RF-10 / RF-12 | QS-02 | AD-03 | ADR-004, ADR-005 | C-02, C-06, C-08, C-11 | dashboard relacional, expediente, V-DOM | BR-03, BR-07, BR-22 | T-47 valida plan por relación y API/UI configurable de asignación docente con historial append-only (`0012`); el E2E comprueba mensaje académico persistido, accesos cruzados denegados, retiro/reasignación y bloqueo tras cierre; suite 84/84. Las listas de autoridad docente permanecen vacías por defecto; evaluaciones siguen narrativas sin instrumento/puntuación institucional. |
| RF-11 | QS-02 | AD-03 | ADR-004, ADR-005 | C-02, C-08, C-11 | dossier, registro de horas | BR-02, BR-03, BR-07 | backend HTTP + E2E: avance/horas persistidos, recarga y lectura histórica después de cierre; no se aprueban horas ni se fija obligatoriedad universal. |
| RF-13 | QS-04 | AD-04 | ADR-005 | C-06, C-11 | V-DOM, SEQ-03 | BR-04 | **T-05** (servicio); no hay endpoint/UI de versión formal porque aprobador y efecto siguen en OPEN-03. El reporte CHANGE no crea una versión. |
| RF-14 | QS-04 | AD-04 | ADR-005 | C-08, C-11 | dossier, historial | BR-03, BR-07 | backend HTTP + E2E: registro persistente y autorización de incidentes/cambios; migración T-46 backfills `REPORTED` como único estado factual e inmutable; sin escalamiento ni decisión automática. |
| RF-15 | QS-07 | AD-05 | ADR-006 | C-10, C-13 | bandeja, V-CONT | — | T-47 valida eventos persistidos, destinatarios por relación, bandeja, lectura y aislamiento por usuario; no hay recordatorios ni worker programado. QS-07/adaptadores no ejecutado. |
| RF-17 | QS-06 | AD-01 | ADR-003 | C-06, C-08 | V-STATE-PLC T7, T8 | BR-05, BR-17, BR-18 | Backend/E2E actuales: informe PDF persistido, evaluación FINAL narrativa del WPS, horas desde política persistida, cierre y eventos `placement.completed`/`placement.closed`; T-56 verifica metadato DH-05 de origen para horas/evidencia de demo y que el opt-in no crea umbrales. T-04 horas-vs-confirmación **PASÓ 1/1** el 2026-10-26 y está en la suite backend actual. T-46 verifica rechazo de escrituras de seguimiento tras CLOSED. Retiro concurrente de evidencia no probado; reglas/actores institucionales OPEN-02/11/14. |
| RF-18 | (QS-05) | AD-07 | ADR-002 | C-12 | reportes, V-COMP | BR-03 | T-47 prueba agregaciones y filtros respaldados por el modelo, alcance PC/EC, acceso denegado a empleador y ausencia de PII/evaluaciones individuales. QS-05/carga no ejecutado. |
| RF-19 | QS-04 | AD-04 | ADR-005 | C-11 | V-DOM | BR-06, BR-07 | **T-05, T-07** (EXECUTED); backend + E2E en esta continuación cubren eventos mínimos desde postulación hasta cierre, incluidas entregas, decisiones, actividad y evaluación; publicación completa sigue pendiente. T-46 también comprueba el estado `REPORTED` y la inmutabilidad del plan de trabajo tras cierre. |
| RF-20 | QS-02 | AD-03 | ADR-004 | C-02 | SEQ-04, [security](design/security.md) | BR-03, BR-13 | **T-03 + T-34** (domain + HTTP role/resource checks; see results) |
| RNF-01 / RNF-02 | QS-05 | AD-07 | ADR-002 | CT-2, CT-4 | V-CONT, V-DEP | — | T-09 NOT EXECUTED |
| RNF-03 | QS-03 | AD-02 | ADR-001 | C-05 | V-COMP | BR-12 | **T-06** |
| RNF-04 | QS-02 | AD-03 | ADR-004 | C-02 | security | BR-03, BR-13 | **T-03 + T-34** |
| RNF-05 | QS-04 | AD-04 | ADR-005 | C-11 | V-DOM | BR-06, BR-07 | T-47 prueba persistencia transaccional de notificaciones/mensajes y log inmutable de asignación docente; retención/alcance completo siguen pendientes. |
| RNF-07 | — | AD-05 | ADR-007 | C-01 | V-CTX | — | **T-31** (autenticación local); SSO institucional OPEN-21 |
| RNF-08 | QS-07 | AD-05 | ADR-006 | C-13 | V-COMP | — | T-10 NOT EXECUTED |
| RNF-09 | — (filtro) | AD-06 | ADR-001, ADR-002 | todos | V-CONT | — | T-15 NOT EXECUTED |
| RNF-11 | QS-08 | AD-03 | ADR-003 (estado derivado) | dashboard, CT-1, C-06 | V-STATE-PLC | — | T-43 implementó orientación derivada de estado de postulación/práctica y requisitos persistidos; T-44 repitió frontend 32/32, build 57 módulos y Chromium 3/3. QS-08/T-13 con participantes y comprensión de todos los estados sigue NOT EXECUTED. |
| RNF-12 | QS-05 | AD-07 | ADR-002 | CT-4 | V-DEP | — | T-09 NOT EXECUTED |

## D.1 Cruce RF ↔ US (propuesto; verificar contra la hoja FR)

> Mapeo **propuesto por esta auditoría** a partir de los títulos y criterios disponibles. Confirmarlo contra el xlsx antes de adoptarlo como oficial. US-010 está retirado.

| RF | US existentes | US propuestas / enmiendas |
|---|---|---|
| RF-01 | US-001, US-002 | — |
| RF-02 | US-002, US-003 | prioridad de US-003 en conflicto (AUD-14) |
| RF-03 | US-004 | — |
| RF-04 | US-005 | — |
| RF-05 | US-006 | **US-036** (gestión de políticas) |
| RF-06 | US-008 | — |
| RF-07 | US-009 | — |
| RF-08 | US-011, US-012 | **US-033** (entrega de documentos) |
| RF-09 | US-013, US-014 | — |
| RF-10 | US-015, US-016 | — |
| RF-11 | US-017 | prioridad a *Must condicional* (AUD-09) |
| RF-12 | US-020 | **enmienda:** incluir al supervisor docente (AUD-04) |
| RF-13 | US-019 | **US-019A** (cambios/versiones) |
| RF-14 | US-019 | **US-019B** (incidentes + resolución) |
| RF-15 | US-024, US-025, US-026 | — |
| RF-16 | US-018 (parcial) | **US-034** |
| RF-17 | US-021, US-022, US-023 | — |
| RF-18 | US-028, US-029 | quitar "conflictos" (AUD-23) |
| RF-19 | US-027 | mover el habilitador de auditoría a antes de la 1ª aprobación (AUD-24) |
| RF-20 | **ninguna** | **US-032** |
| RNF-07 | US-031 | **T-31** (cuentas locales, sesión segura; SSO sigue OPEN-21) |
| RNF-11 | US-007 | — |
| — | US-030 (calendario) | sin RF; OPEN-10 |
| — | — | **US-035** (interrupción/cancelación, OPEN-08) |

## D.2 ADR → Requisitos

| ADR | Requisitos | Escenarios | Drivers |
|---|---|---|---|
| ADR-001 | RF-05, RF-08, RF-17, RNF-03, RNF-09 | QS-03 | AD-02, AD-06 |
| ADR-002 | RNF-01, RNF-02, RNF-09, RNF-12 | QS-05 | AD-01, AD-06, AD-07 |
| ADR-003 | RF-09, RF-17 | QS-01, QS-06 | AD-01 |
| ADR-004 | RF-20, RNF-04, RNF-07 | QS-02 | AD-03 |
| ADR-005 | RF-13, RF-14, RF-19, RNF-05 | QS-04 | AD-04 |
| ADR-006 | RNF-08, RF-15 | QS-07 | AD-05 |

## D.3 Escenario de calidad → Validación

| QS | Pruebas | Estado |
|---|---|---|
| QS-01 | T-01, T-02, T-02b, T-08, T-26..T-28, T-30 | EXECUTED; T-16a/e PoC (2026-10-22) |
| QS-02 | T-03, T-29 | EXECUTED at domain/service level; T-14 NOT EXECUTED |
| QS-03 | T-06, T-25, T-30 | EXECUTED partial (no latency measurement) |
| QS-04 | T-05, T-07 | EXECUTED; latencia de historial NOT EXECUTED |
| QS-05 | T-09 | **NOT EXECUTED** |
| QS-06 | T-04 | EXECUTED; carrera concurrente de inserción de horas vs confirmación PASÓ 1/1 el 2026-10-26; retiro concurrente de evidencia sigue NOT EXECUTED; T-16b/c/d EXECUTED (2026-10-22) |
| QS-07 | T-10 | **NOT EXECUTED** |
| QS-08 | T-13 | **NOT EXECUTED** |

**Backend (ADR-007):** T-31 cubre autenticación, sesión y recuperación local; T-20..T-30 cubren rutas y flujos de negocio; T-34 cruza acciones HTTP con roles y relaciones. La migración 0004 serializa rechazo documental/activación; 0005 agrega registros protegidos de seguimiento/evidencia y compuerta desde fuentes; 0006 serializa inserciones de horas con transiciones a finalización. T-44 aplicó con Alembic la cadena completa desde `0001` hasta `0007` en PostgreSQL temporal y comprobó que el lock se incorpora en `0006`; T-35/T-41..T-44 recorren flujo de navegador. Evidencia, alcance y límites en [validation-results.md](validation/validation-results.md).

## D.5 Evidencia añadida en el incremento de preparación final

| Prueba | Requisitos | Alcance | Evidencia |
|---|---|---|---|
| T-02 (producto) | RF-09, BR-01 | Rechazo documental frente a activación bajo concurrencia en PostgreSQL | `backend/tests/test_lifecycle.py`; migración `0004_serialize_checklist_and_placement_gates.py` |
| T-34 | RF-20, RNF-04, BR-03, BR-13 | Negativas por estudiante, organización anfitriona, supervisor asignado, programa y actor legal/EC en el límite HTTP | `backend/tests/test_http_authorization.py`; [matriz endpoint/rol/relación](validation/http-authorization-matrix.md) |
| T-35 | RF-01..RF-09, RF-20 | Login, ruta protegida, oportunidad, postulación, selección, aprobación académica, rechazo/reentrega documental y activación por roles mediante Chromium | **PASÓ históricamente 2026-10-25**; la continuación T-41 también recorrió el ciclo y pasó 3/3 en Chromium el 2026-10-26. |
| T-39 | RF-01, RF-06, RF-20 | Catálogos de organizaciones/programas para creadores; supervisores activos por organización anfitriona; denegaciones HTTP cruzadas y uso de opciones nominativas en el E2E | `backend/tests/test_opportunities.py`, `backend/tests/test_http_authorization.py`, `frontend/src/api.catalogs.test.ts`, `frontend/e2e/lifecycle.spec.ts`; [matriz HTTP](validation/http-authorization-matrix.md) |
| T-40 | RF-19, RNF-04, RNF-05 | API de historial con proyección mínima; vista de actividad de práctica legible; autorización por titularidad y relaciones; persistencia visible tras recarga y responsive a 390 px | **PASÓ históricamente 2026-10-25**. Esa corrida cubrió eventos de colocación/checklist/versiones; no cubrió la historia previa de oportunidad/postulación. |
| T-41 | RF-05, RF-08, RF-10, RF-11, RF-12, RF-14, RF-17, RF-19, RF-20 | Expediente y seguimiento: decisiones/versiones, avances, evaluaciones narrativas, incidentes/cambios, evidencia final, horas e historial por relación; incluye cierre y lecturas después de recarga | **Ejecución histórica 2026-10-26**: suite backend 74 passed (1 warning, 67.31 s), frontend 24/24, build 55 módulos y Playwright Chromium 3/3 (46.0 s) con migración 0006. Capturas desktop 1280×4426 y mobile 390×5466 inspeccionadas. El alcance actual se amplió y se registra en T-42; no se atribuyen estas cifras a la corrida nueva. |
| T-42 | RF-10, RF-12, RF-19, RF-20 | Asignar y consultar actividades narrativas; validar relación del WPS vigente y lectores; impedir saltos de revisión o mutación directa; auditar y confirmar que el plan no cambia requisitos/estado de cierre | `backend/tests/test_http_authorization.py`, `backend/tests/test_lifecycle.py::test_work_plan_database_guard_enforces_assignment_revision_and_immutability`, `frontend/src/api.followup.test.ts`, `frontend/e2e/lifecycle.spec.ts`; **corte original 2026-11-02**: suite backend 75 passed, 1 warning (81.81 s), Alembic `0006→0007` EXIT 0, frontend 25/25, build 56 módulos y runner aislado Chromium 3/3 (46.6 s). Capturas 1280×4695 y 390×5746 revisadas. T-44 es la revalidación posterior del árbol actual. |
| T-43 | RF-10, RF-11, RF-12, RNF-11, RF-20 | Orientación del estado/siguiente paso desde datos de postulación, práctica y requisitos persistidos; lista de prácticas y navegación a expediente para WPS/coordinación según la consulta relacional existente | `frontend/src/studentJourney.test.ts`, `frontend/e2e/lifecycle.spec.ts`, `/placements`; **2026-11-02**: frontend 32/32 en 11 archivos, build 57 módulos, E2E Chromium 3/3 (1.0 min); WPS relacionado comprobado; estudiante comprueba estado SUBMITTED; 390 px sin desbordamiento. Capturas de dashboard student/supervisor y dossier desktop/móvil inspeccionadas. Backend 75/75 corresponde al T-42 anterior; T-43 no cambia backend. QS-08 no ejecutado. |
| T-44 | RF-10, RF-11, RF-12, RF-17, RF-19, RF-20, RNF-04/05 | Revalidación del árbol actual y cadena íntegra de migraciones tras restaurar el esquema inicial `0001` | `pytest -q`, `pnpm run test`, `pnpm run build`, `scripts/run_isolated_e2e.py`, Alembic con `pgserver` temporal; **2026-11-02**: backend 75 passed, 1 warning (111.24 s); frontend 32/32; build EXIT 0 (57 módulos); Chromium 3/3 (59.5 s); `0001→0007` EXIT 0, lock ausente en `0001` y presente en `head`; se verifica que la lista docente solo incluya la práctica asignada; seis capturas desktop/móvil revisadas. |
| T-45 | RF-10, RF-12, RNF-04 | Recuperación de error temporal en listas relacionales de WPS, coordinación y supervisión docente | `relatedPlacements.test.ts`, `lifecycle.spec.ts`, `GET /placements`; 2026-11-02: backend 75 passed/1 warning (66.49 s), frontend 34/34, build 58 módulos, E2E Chromium 6/6 (59.7 s). WPS, `pc_sys` y `f1` simulan 503, confirman error sin spinner indefinido, reintento 200 y lista/estado vacío; seis capturas actuales revisadas. El matcher/conteo inicial del test se corrigió tras dos intentos fallidos de prueba. |
| T-46 | RF-10, RF-11, RF-12, RF-14, RF-17, RF-19, RF-20, RNF-04/05 | Estado factual de incidentes/cambios, restricción de nuevas asignaciones tras cierre y lectura de práctica docente realmente asignada | Backend `pytest -q`, frontend `pnpm run test`, `pnpm run build`, migraciones temporales `0001→0009`, `scripts/run_isolated_e2e.py`; 2026-11-02: backend 76 passed/1 warning (75 s), frontend 34/34 en 12 archivos, build EXIT 0 (58 módulos), migración EXIT 0, E2E Chromium 7/7 (55.8 s). Incluye acceso docente, titular, WPS, coordinación y Legal; negativos cruzados y de escritura tras CLOSED; seis capturas nuevas inspeccionadas. Docker daemon no disponible; PostgreSQL temporal sin volúmenes. |
| T-47 | RF-01/02, RF-10/12, RF-15/16/18/19/20, RNF-04/05 | Notificaciones y mensajes con alcance relacional, reportes operativos agregados y filtros, flujo configurable de revisión/publicación, asignación docente con historial append-only | Backend `python -m pytest tests -q`; frontend `npm test -- --reporter=dot`; `npm run build`; `scripts/check_isolated_migrations.py`; `scripts/run_isolated_e2e.py`; PostgreSQL temporal `pgserver`; 2026-11-03: backend **84 passed, 1 warning** (122.13 s); frontend **37 passed en 14 archivos**; build **EXIT 0, 62 módulos**; migraciones `0001→0012` y `0010→0011→0012` EXIT 0; Chromium **7/7** (1.2 min). Se revisaron ocho capturas actuales 1280 px/390 px, incluidas las de reportes. E2E cubre fallo/reintento, tablas que ajustan todas sus columnas, permisos denegados y asignación tras cierre. Docker Engine no disponible; clúster temporal limpiado. Los intentos intermedios están descritos en resultados. |
| T-48 | RNF-01/02/04/06; QS-05 | Preparar un preview público aislado para el backend FastAPI, PostgreSQL Neon y SPA Vite; comprobar health/readiness sin exponer detalles ni migrar datos locales | `render.yaml`, `frontend/vercel.json`, `GET /ready`, [runbook](../deployment-free-preview.md); backend **87 passed, 1 warning**, frontend **37/37**, build **EXIT 0 (62 módulos)**, migraciones aisladas `0001→0012`/`0010→0011→0012` **EXIT 0**, validación YAML/JSON **EXIT 0**. Neon `long-truth-39527618/main` se verificó vacío antes de migrar; tras autorización expresa, upgrade directo **EXIT 0**, `alembic_version=0012`, 29 tablas públicas, cero filas de aplicación. El sondeo read-only confirmó TLS y `app_user` `NOLOGIN`, pero `neondb_owner` tiene membresía `SET FALSE` y `/ready` fallará hasta configurar un login de ejecución. Servicios no creados, no hay E2E público ni URLs; revisión del diff y autorización GitHub pendientes. |
| T-49 | RNF-01/02/04/05/06; QS-05 | Preparar rol runtime de privilegio mínimo en Neon y comprobar la readiness sin publicar ni usar credenciales administrativas | Migración `0013`, `app_runtime`, ACL audit, [runbook](../deployment-free-preview.md); Neon `main`: Alembic **0013**, 28 tablas de aplicación, 0 filas. `app_user=NOLOGIN`; 69 pares de privilegios de tabla y 23 `USAGE` de secuencia; `app_runtime` `LOGIN` sin flags administrativos, membresía SET-only sin `INHERIT`/`ADMIN`; `SET ROLE app_user` y `/ready` **HTTP 200** con TLS. Suites backend **88/1 warning**, frontend **37/37**, build **EXIT 0 (62 módulos)**, migraciones aisladas y E2E Chromium **7/7** pertenecen al segmento T-49 anterior; ocho capturas se inspeccionaron entonces. En esta continuación se repitieron `/ready` y `git diff --check` (**EXIT 0**). No hay servicios/URLs públicos; secreto solo en Windows Credential Manager, diff y autorización GitHub pendientes. |
| T-51 | RNF-06; RNF-04/05; SYN-01 | Preparar carga persistente idempotente con identidades sintéticas únicas, transacción única, preflight contra Neon y verificación del respaldo/colisiones | `scripts/persist_synthetic_dataset.py`, `app.shared_command_connection`, `test_synthetic_dataset.py`; backend **90 passed/1 warning**, E2E poblado **4/4** en PostgreSQL temporal. El preflight Neon actual devolvió **EXIT 2** sin escritura: target/runtime/TLS correctos, 14 cuentas y sin ciclo, no hay reglas `ELIGIBILITY`, autoridades OPEN-05, snapshot ni credencial puntual de escritura; `app_runtime` no puede insertar `host_org`. No se ejecutó `--apply`; la carga persistente no está completada. |
| T-52 | RNF-04/05/06; SYN-01; OPEN-05 | Separar carga reanudable de catálogos/cuentas/oportunidades pendientes del flujo completo; sin elegibilidad o publicaciones inventadas | `backend/app/synthetic_dataset.py`, `backend/app/modules/authz/service.py`, `scripts/persist_synthetic_dataset.py`, `backend/tests/test_synthetic_dataset.py`, [permisos bootstrap](../synthetic-dataset-bootstrap.md). Revalidación 2026-11-05: suite backend **97 passed, 1 warning** (135.30 s; el corte previo de 94 es histórico); pruebas focales **9/9** (39.85 s); E2E poblado Chromium en PostgreSQL temporal **4/4** (25.8 s); `compileall` **EXIT 0**; dry-runs Neon partial/full **EXIT 2**, ambos `write_performed=false`. Prueba aislada partial: 10 organizaciones/47 cuentas/16 oportunidades (8 `DRAFT`, 8 `IN_REVIEW`), segundo pase sin inserciones, cuenta existente preservada, rollback, ACL con rechazo de grant adicional, cero aplicaciones/prácticas/políticas de elegibilidad, aviso dirigido al EC relacionado y publicación denegada sin autoridad. El modo persistente sin opt-in no crea horas/evidencia de cierre ni cierra prácticas. Neon read-only: destino/TLS, 14 cuentas, 2 organizaciones, 2 programas, 4 políticas activation/completion, 9 eventos de auditoría y cero ciclo. Faltan snapshot reciente, login `app_bootstrap` y 47 contraseñas individuales nuevas; no se ejecutó `--apply`. |
| T-53 | RF-05, RF-06, RF-19/20; RNF-04/05 | Resolver elegibilidad insuficientemente informada mediante revisión manual con relación de programa, fundamento, notificación y auditoría | `policies.evaluate`, `applications.review_eligibility`, `GET/POST /applications/*eligibility-review`, `AcademicReview.tsx`, `backend/tests/test_applications.py`, `test_http_authorization.py`, `frontend/e2e/manual-eligibility.spec.ts`; migración `0014` amplía categoría de notificación | `MANUAL_REVIEW` o un operando académico ausente produce estado pendiente; el anfitrión no recibe la fila hasta la decisión; coordinación del programa correcto puede resolver; intento cruzado denegado; resultado y fundamento persisten tras recarga y no incluyen ID interno del revisor; auditoría conserva actor | **Ejecutado en esta continuación**: suite backend **101 passed, 1 warning (144.38 s)**; frontend **40/40 en 14 archivos**; build **EXIT 0, 64 módulos**; migraciones temporales `0001→0014` y `0013→0014` EXIT 0; E2E base Chromium **18 passed/4 skipped** y poblado **4/4**; las capturas actuales de revisión escritorio/móvil y expediente poblado móvil fueron inspeccionadas. La ejecución de regresión ya incluye la aserción de no exposición y la verificación del número de versión real. Sin escritura Neon. | **PASÓ para revisión de elegibilidad y permisos probados. No determina umbrales institucionales. OPEN-01/04 siguen pendientes; el EC en `render.yaml` es configuración local de demostración, no aprobación de autoridad institucional ni despliegue.** |
| T-54 | RF-05, RNF-05/06 | Trazabilidad de autor/motivo de políticas nuevas y revalidación de estado remoto | `policies.create_policy_version`, proyección `policies_for_subject`, `Policies.tsx`; solo lectura Neon | Motivo requerido; autor/motivo visibles al coordinador; no se filtra ID interno; catálogo parcial y ciclo ausente constatados sin escribir | **2026-11-05**: backend **103 passed/1 warning**, frontend **40/14**, build **EXIT 0**, E2E base **18/4** y poblado **4/4**; capturas desktop/móvil revisadas. El preflight de Neon registró 61 cuentas, 10 organizaciones, 16 oportunidades, 4 políticas de activación/finalización y 0 ciclo. | **PASÓ para auditoría/proyección y lectura. No se escribió Neon.** |
| T-55 | RF-05/RF-06/RF-17; RNF-04/05/06; SYN-01 | Opt-in de políticas sintéticas reemplazables y ACL append-only mínima para el cargador full | `scripts/persist_synthetic_dataset.py`, `backend/app/synthetic_dataset.py`, `test_synthetic_dataset.py`, [permisos de carga](../synthetic-dataset-bootstrap.md) | Dos reglas demo faltantes se agregan solo por opt-in vía servicio y actor coordinador; motivo explícito, inserción exacta por columnas, sin update/delete; segundo pase no duplica | **2026-11-05**: backend **105 passed/1 warning (116.41 s)**, frontend **40/14**, build **EXIT 0**, E2E base **18/4**, poblado **4/4**, ACL focal **2/2**, módulo del cargador **11/11**. El preflight Neon `full --allow-demo-eligibility-policy` salió **2**, `write_performed=false`; confirma objetivo/TLS/snapshot, proyecta dos versiones y deniega por credencial `app_dataset_full` ausente. | **PASÓ en aislado; producción no cargada y rol real no verificado.** |
| T-56 | RF-05/RF-11/RF-17/RF-19; RNF-04/05/06; SYN-01 | Opt-in independiente para horas/evidencia/evaluación/cierre sintéticos con políticas persistidas | `backend/app/synthetic_dataset.py`, `backend/app/modules/lifecycle/service.py`, cargador full, populated E2E | Evidencia y horas quedan marcadas en auditoría como DH-05; nada de esto se escribe sin opt-in; horas siguen umbral persistido y confirmación/cierre validan requisitos existentes; PDF final válido | **2026-11-05**: backend **105/1 warning (118.14 s)**, frontend **40/14**, build **EXIT 0/64**, E2E base **18/4**, poblado **4/4 (20.6 s)**; capturas desktop y móvil claro/oscuro inspeccionadas. Preflight Neon solo lectura **EXIT 2/write=false**. Inspección TLS/READ ONLY por `app_bootstrap`: rol directo `app_dataset_full` ausente; `app_bootstrap` tiene LOGIN/NOINHERIT, sin memberships/admin y sin permisos DELETE, pero no cubre el ACL integral (23 SELECT, alcance INSERT, seis UPDATE, cinco comprobaciones de política pendientes). | **PASÓ temporalmente. Neon no recibió cambios; falta provisionar el login/ACL integral mediante autoridad DBA autorizada.** |
| T-45 | RF-10, RF-12, RNF-04 | Recuperación de error temporal en listas relacionales de WPS, coordinación y supervisión docente | `relatedPlacements.test.ts`, `lifecycle.spec.ts`, `GET /placements`; 2026-11-02: backend 75 passed/1 warning (66.49 s), frontend 34/34, build 58 módulos, E2E Chromium 6/6 (59.7 s). WPS, `pc_sys` y `f1` simulan 503, confirman error sin spinner indefinido, reintento 200 y lista/estado vacío; seis capturas actuales revisadas. El matcher/conteo inicial del test se corrigió tras dos intentos fallidos de prueba. |
| T-04 concurrente | RF-11, RF-17, BR-02, BR-05 | Impedir que una escritura directa de horas pase la guarda ACTIVE durante una confirmación concurrente | `test_t04_concurrent_hours_insert_waits_for_completion_commit`, trigger `trg_progress_gate` y migración `0006`; **PASÓ 1/1** focal el 2026-10-26 y está incluida en la suite backend actual de 75. El insert espera el lock y PostgreSQL lo rechaza al confirmar `COMPLETED`; no añade horas. Cubre horas-vs-confirmación, no retiro concurrente de evidencia ni política institucional. |
| T-12 | RNF-01, RNF-02 | Arranque, migración y seed reproducible en PostgreSQL aislado de demo | [runbook](validation/demo-runbook.md); Compose `dh05-demo`, DB `dh05_demo` |

## D.6 Auditoría funcional requisito por requisito (2026-10-25)

La clasificación completa (incluye responsable, vista, endpoint/servicio, autorización, prueba y brecha) se mantiene en [functional-completeness-matrix.md](functional-completeness-matrix.md). **T-36** añade selección segura de supervisor laboral por organización y validación del rango de fechas; véase `backend/tests/test_selection.py`. **T-37/T-38** cubren registro opcional de horas, titularidad, estado activo para escritura, validación y persistencia tras recargar. No se implementan transiciones de publicación, simultaneidad, alternos ni versionado HTTP mientras dependan de OPEN-05/13/19/03. La obligatoriedad institucional de registrar horas continúa por investigar conforme al RFP.

**T-39** completa catálogos legibles de organizaciones, programas y supervisores laborales sin cambiar la regla de autorización existente para crear oportunidades; incluye autorización HTTP cruzada y cobertura frontend. La revisión/publicación, edición y cierre siguen pendientes según OPEN-05.

**T-40** (ejecutado el 2026-10-25) validó una primera vista legible del historial de la práctica, con proyección de solo fecha/acción y acciones con etiquetas humanas. T-41 (ejecutado el 2026-10-26) integra eventos de postulación y práctica en el expediente y valida su proyección backend/E2E. Ninguno de los dos incrementos cubre publicación de oportunidad, evaluaciones/incidentes ni la trazabilidad completa que describe el RFP.

## D.4 Componente → Responsabilidad y razón de existir

| Componente | Responsabilidad | **¿Por qué existe?** (requisito / driver / ADR) |
|---|---|---|
| C-01 Identidad y sesión | Autenticar cuenta local, emitir y revocar sesión | RNF-07 · AD-05 · ADR-007 |
| C-02 Autorización | Rol + relación, filtrado, proyección | RF-20, RNF-04 · AD-03 · ADR-004 |
| C-03 Oportunidades | Registro, revisión, publicación, búsqueda | RF-01..RF-04 (CRUD/flujo estándar) |
| C-04 Postulaciones y elegibilidad | Postular y evaluar con política | RF-05 · AD-02 · ADR-001 |
| C-05 Configuración de políticas | Versiones validadas con vocabulario cerrado | RNF-03 · AD-02 · ADR-001 |
| C-06 Ciclo de vida | Agregado `Placement`, compuertas, versiones | RF-06..RF-09, RF-13, RF-17 · AD-01, AD-04 · ADR-003, ADR-005 |
| C-07 Checklist y documentos | Instancias de requisitos de activación | RF-08, RF-09 · AD-01 · ADR-003 |
| C-08 Supervisión y evaluación | Plan, avance, horas, evaluaciones, incidentes | RF-10..RF-12, RF-14; evidencia de cierre (RF-17) |
| C-09 Comunicación | Mensajes registrados | RF-16 (alcance mínimo; US-034 propuesta) |
| C-10 Notificaciones | Bandeja de salida y plazos | RF-15 · AD-05 · ADR-006 |
| C-11 Auditoría | Eventos append-only | RF-19, RNF-05 · AD-04 · ADR-005 |
| C-12 Reportes y paneles | Modelos de lectura | RF-18 |
| C-13 Adaptadores | Puertos y simuladores | RNF-08 · AD-05 · ADR-006 |

**Prueba de la cadena inversa (ejemplo).** *¿Por qué existe el trigger de la compuerta?* → RF-09 exige bloquear la activación → AD-01 lo vuelve dominante → ADR-003 pide una red de seguridad además de la guarda → SEQ-02 muestra dónde actúa → BR-01 la formula → **T-02b** la ejercitó (2/2 `UPDATE` directos rechazados).
