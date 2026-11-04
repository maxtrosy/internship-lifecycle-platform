# Matriz de autorización HTTP

**Corte:** 2026-11-02. `requires(action)` autentica la sesión y declara la intención de la ruta; la decisión efectiva de rol y relación se aplica en el servicio consultado por cada endpoint. T-42 se ejecutó en backend y Chromium el 2026-11-02; la evidencia y sus límites están en [validation-results.md](validation-results.md).

## Convenciones

- **Estudiante propio:** es la persona titular de la postulación/colocación.
- **Organización propia:** el `host_org_id` de la oportunidad coincide con la asignación del usuario.
- **Supervisor asignado:** además de la organización correspondiente, figura en la versión vigente/histórica o en la asignación docente requerida por ADR-004.
- **Programa propio:** coincide con el `program_id` del estudiante de la colocación o con el ámbito de política.
- **Global institucional:** `EXPERIENTIAL_COORDINATOR` y `LEGAL_REVIEWER` conservan el alcance que describe ADR-004/OPEN-09.
- Rutas no autenticadas se listan explícitamente. Para externos sin relación, las lecturas de recursos responden 404 para ocultar existencia; para actores internos sin relación, 403. Las acciones mutables sin permiso responden 403.

## Endpoint × rol × relación

| Método y endpoint | Quién puede acceder | Relación / proyección aplicada |
|---|---|---|
| `GET /health` | Público | Estado del proceso, sin datos de usuario. |
| `POST /auth/login` | Público | Credencial local válida y cuenta activa; `Origin` permitido. No declara SSO. |
| `GET /auth/me` | Cualquier sesión activa | Solo la cuenta asociada a la sesión actual. |
| `POST /auth/logout` | Cualquier sesión activa | Revoca solo su propio identificador de sesión; `Origin` permitido. |
| `POST /auth/password-reset/request` | Público | Respuesta genérica; `Origin` permitido; el correo no confirma existencia de cuenta. |
| `POST /auth/password-reset/complete` | Público con token válido | Token de un uso ligado a una cuenta activa; sin sesión de otra cuenta. |
| `POST /auth/accept-invitation` | Público con invitación válida | El rol y la organización vienen de la invitación, no del cuerpo; `Origin` permitido. |
| `POST /invitations` | Coordinador de aprendizaje experiencial | Solo roles `HOST_ORG_MEMBER`/`WORKPLACE_SUPERVISOR`; la organización se fija en la invitación. |
| `GET /opportunities` | Toda sesión activa | Estudiante: publicadas; anfitrión/supervisor: organización propia; coordinador de programa: programa propio; EC/legal: alcance global. |
| `GET /opportunities/catalogs` | Miembro anfitrión o coordinador de programa | Requiere `opportunity:create`; el servicio devuelve organizaciones propias para miembros anfitriones y programas propios para coordinadores; el otro catálogo contiene opciones compatibles con la regla OR que ya valida `create_opportunity`. Otros roles: 403. |
| `GET /opportunities/{oid}/workplace-supervisors` | Miembro de la organización anfitriona de la oportunidad | Requiere `application:select`; la organización debe coincidir con una relación anfitriona del usuario. Devuelve solo usuarios activos con rol `WORKPLACE_SUPERVISOR` en esa organización; otros roles/organizaciones: 403; oportunidad inexistente: 404. |
| `POST /opportunities` | Miembro anfitrión o coordinador de programa | Anfitrión debe coincidir con la organización indicada **o** coordinador con el programa indicado. Revisión/publicación sigue OPEN-05. |
| `GET /applications` | Toda sesión activa | La consulta solo devuelve solicitudes cuyo `student_id` es la cuenta actual; para roles sin solicitudes propias devuelve lista vacía. |
| `POST /opportunities/{oid}/apply` | Estudiante | Solicita una oportunidad publicada; evalúa política vigente; no hay regla aprobada de unicidad/reintento. |
| `GET /opportunities/{oid}/applications` | Miembro de la organización anfitriona | La organización debe ser la propietaria de la oportunidad; vista de estudiante limitada a nombre, programa y decisión de elegibilidad (sin entradas ni razones que revelen perfil). |
| `POST /applications/{aid}/select` | Miembro de la organización anfitriona | La organización de la oportunidad debe coincidir; solicitud publicada, `SUBMITTED` y `ELIGIBLE`. |
| `GET /placements/pending-academic` | Coordinadores de programa | La cola contiene solo estudiantes de los programas asignados; otros roles reciben lista vacía. |
| `GET /placements/documents-pending` | Revisor legal | Cola institucional de documentos que cumplen la consulta del backend. Otros roles: 403. |
| `GET /placements/pending-activation` | Coordinador de aprendizaje experiencial | Cola institucional de colocaciones `DOCUMENTATION_PENDING`. Otros roles: 403. |
| `GET /placements` | Cualquier sesión activa | Lista de colocaciones filtrada por las relaciones del rol: titularidad, organización, supervisor asignado, programa o alcance interno. Relaciones externas sin resultados devuelven lista vacía. T-44 comprueba que el supervisor docente solo recibe la práctica asignada. |
| `GET /placements/{pid}` | Roles con lectura de colocación | Rol y relación por titularidad, organización, asignación, programa o alcance institucional según ADR-004. |
| `GET /placements/{pid}/dossier` | Roles con lectura de colocación | Mismo alcance relacional. Proyecta información persistida; arrays de documentos/horas/plan/avances/evaluaciones/incidentes/evidencia se filtran por capacidad y son `null` cuando no se autorizan. La respuesta omite IDs de actores/filas y JSON de auditoría sin filtrar. La suite backend 75/75 y E2E 3/3 verificaron titular, anfitrión, WPS, coordinación, legal y EC. |
| `GET /placements/{pid}/work-plan` | Titular, WPS relacionado, docente asignado, coordinación del programa y EC | Consulta actividades narrativas persistidas por relación. Miembro anfitrión y legal reciben 403; WPS ajeno recibe 404. No contiene fechas límite, calificaciones ni estado de cumplimiento. |
| `POST /placements/{pid}/work-plan` | Supervisor laboral asignado a la versión vigente | Valida título/descripción, relación/organización y secuencia; la fila es append-only y queda auditada. Titular, miembro anfitrión sin asignación y supervisor ajeno no pueden escribir. La E2E verifica persistencia tras recarga. |
| `GET /placements/{pid}/history` | Roles con lectura de colocación | Eventos de la práctica, postulación, checklist y versiones. Solo fecha/acción; sin actor/sujeto internos, correlación, payload antes/después ni IDs. El E2E de esta continuación comprueba historial desde postulación hasta `placement.completed` y `placement.closed`. |
| `GET/POST /placements/{pid}/progress-reports` | Lectores de avances / estudiante titular para crear | El estudiante titular registra avances solo en ACTIVE; titular, WPS asignado, docente asignado, coordinación del programa y EC leen por relación. El anfitrión sin asignación no recibe el contenido. |
| `GET/POST /placements/{pid}/evaluations` | Roles relacionados para lectura / WPS vigente para crear | Evaluación narrativa MIDTERM/FINAL, sin calificación numérica; se limita por relación y estado ACTIVE. El titular puede revisar su propia evaluación; miembro anfitrión sin asignación no. |
| `GET/POST /placements/{pid}/incidents` | Participantes autorizados | Titular y participantes relacionados registran/leen durante ACTIVE; el tipo CHANGE es informativo y no actualiza la versión ni decide escalamiento. |
| `GET /placements/{pid}/completion-evidence`; `POST /placements/{pid}/completion-evidence/{kind}` | Titular para cargar; roles autorizados para leer | Carga de `FINAL_REPORT` por titular en ACTIVE, bytea en PostgreSQL con nombre, tipo, tamaño, hash y revisión; descarga protegida por relación. No se expone PK interno. |
| `GET /placements/{pid}/completion-evidence/{kind}/{revision}/download` | Titular / docente asignado / coordinación del programa / EC | Requiere capacidad de lectura de evidencia final; organización anfitriona y WPS no reciben el archivo por esta ruta. |
| `GET /placements/{pid}/checklist` | Roles con lectura de colocación | Mismo rol y relación que lectura de colocación. |
| `GET /placements/{pid}/activation-status` | Roles con lectura de colocación | Mismo rol y relación que lectura de colocación. |
| `POST /placements/{pid}/approve-academic` | Coordinador del programa del estudiante | Solo transición desde aprobación académica pendiente. |
| `POST /placements/{pid}/reject-academic` | Coordinador del programa del estudiante | Solo transición desde aprobación académica pendiente; registra motivo. |
| `POST /placements/{pid}/activate` | Coordinador de aprendizaje experiencial | Rol global vigente; servicio y trigger vuelven a validar estado y compuerta. |
| `POST /placements/{pid}/confirm-completion` | Coordinador del programa del estudiante | Requiere colocación activa y evidencia/política de cierre. |
| `POST /placements/{pid}/close` | Coordinador de aprendizaje experiencial | Requiere estado completado y compuertas vigentes. |
| `POST /placements/{pid}/items/{item_id}/submit` | Estudiante titular | El ítem debe pertenecer a la colocación y admitir archivo; valida tipo/tamaño/estado. |
| `GET /placements/{pid}/items/{item_id}/submissions` | Estudiante titular o revisor legal | Relación con colocación y pertenencia del ítem; host/supervisor no descarga ni lee archivos. |
| `GET /placements/{pid}/items/{item_id}/submissions/{submission_id}/download` | Estudiante titular o revisor legal | Igual que lectura de entregas; la entrega debe coincidir con ítem y colocación. |
| `POST /placements/{pid}/items/{item_id}/review` | Revisor legal | La entrega/ítem debe pertenecer a la colocación; requiere decisión válida y motivo. |
| `POST /placements/{pid}/hours` | Estudiante titular | Solo su propia colocación; el servicio y la BD rechazan horas antes de `ACTIVE`. |
| `GET /placements/{pid}/hours` | Estudiante titular | Solo consulta horas de su propia colocación; el backend deniega con 403 el acceso cruzado de otro estudiante y de un empleador. |
| `GET /policies` | Coordinador de programa | Solo versiones vigentes de sus programas; otros roles reciben 403. |
| `POST /policies` | Coordinador del programa indicado | Programa coincidente; tipo y condiciones validados por vocabulario cerrado; versiones inmutables. |

## Evidencia y límites

- `backend/tests/test_routes_actions.py` comprueba que cada ruta autenticada declara acción.
- `backend/tests/test_authz.py` cubre relaciones en el servicio y proyección mínima del estudiante.
- `backend/tests/test_http_authorization.py` cubre accesos HTTP cruzados por estudiante, organización, asignación de supervisor y programa; lista/selección de postulaciones; lectura/entrega/descarga de documentos; colas institucionales y sesión ausente.
- Las pruebas HTTP de catálogos verifican 200 para creadores relacionados, 403 para estudiantes/supervisores y cruces de organización; la prueba de servicio verifica que el catálogo de supervisores solo proyecta ID/nombre de cuentas activas de la organización anfitriona.
- `backend/tests/test_http_authorization.py` contiene casos para dossier, versiones, documentos, horas, historial, plan y permisos de seguimiento/evaluación/incidentes/evidencia final por relación; T-44 reejecutó la suite completa (**75/75**, 1 warning, 111.24 s) e incluyó la lista docente limitada a su práctica. E2E Chromium pasó **3/3**, incluidas denegaciones de contenido, plan tras recarga, cierre e historial.
- **PASÓ en corte 2026-10-25:** suite backend completa 70/70; foco de oportunidades/autorización 6/6 y regresión de supervisor inactivo 1/1. La matriz HTTP cruza titularidad, organización, supervisor, programa, roles institucionales y sesión ausente. Esta evidencia no equivale a pentest ni RLS.
- Las lecturas legales son institucionales conforme a ADR-004/OPEN-09; no se ha inventado un alcance por programa.
- Hay servicios internos sin endpoint HTTP, por ejemplo `approve_version`; la matriz no los presenta como rutas disponibles.
- La verificación no es una prueba de penetración, una revisión de RLS ni una certificación de producción.
