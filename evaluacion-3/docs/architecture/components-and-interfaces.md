# Componentes, responsabilidades e interfaces

El proceso FastAPI incluye routers en `backend/app/modules/*/router.py` y servicios con lógica SQL/negocio en `service.py`. No hay despliegue separado por módulo. `backend/app/main.py` registra routers y middleware CORS.

| Módulo / componente | Responsabilidad as-built | Contratos API relevantes |
|---|---|---|
| identity / authz | Sesiones locales, identidad actual y predicados de rol + relación | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout` |
| opportunities | Consulta, creación, solicitud de revisión, aprobación, publicación y cierre configurables | `/opportunities`, `/{id}/submit-review`, `/approve`, `/publish`, `/close` |
| applications + policies | Evaluación contra política versionada, postulación, cola/decisión manual, selección | `POST /opportunities/{id}/apply`, `/applications/pending-eligibility-review`, `/applications/{id}/eligibility-review`, `/applications/{id}/select`, `/policies` |
| lifecycle | Proyección expediente, relaciones, documentos/checklist, asignaciones, seguimiento, horas, evaluación, incidentes, evidencia, gates y cierre | `/placements`, `/{id}/dossier`, `/history`, `/hours`, `/work-plan`, `/progress-reports`, `/evaluations`, `/incidents`, `/completion-evidence`, `/activate`, `/confirm-completion`, `/close` |
| notifications | Bandeja transaccional y conversaciones de expediente con audiencias JOINT/ACADEMIC | `/notifications`, `/notifications/{id}/read`, `/placements/{id}/messages` |
| reports | Consultas agregadas por alcance | `GET /reports/operations` |
| audit | Eventos atómicos y append-only para operaciones de negocio | Escribe en la transacción del servicio; no se ofrece el JSON crudo al dossier |
| migrations | Revisión de esquema por SQL | Alembic `0001`–`0014`; launcher de demo migra una base temporal |

**No implementado como componente independiente:** aunque el diseño anterior dibujaba `checklist`, `supervision`, `messaging` y adaptadores, algunos paquetes son marcadores vacíos y esas responsabilidades las ejecutan `lifecycle`/`notifications` o no tienen adaptador externo. No se debe atribuir a un paquete vacío una función inexistente.

## Contrato de permisos (resumen)

El router exige capacidades (`requires(...)`) y los servicios filtran la relación concreta. La lectura de expedientes, horas y artefactos vuelve a comprobar relación. Estudiante: titular. Miembro anfitrión: organización de la oportunidad. Supervisor laboral: organización + asignación a una versión. Supervisor docente: asignación efectiva. Coordinador de programa: programa del estudiante. Los roles institucionales conservan alcance definido por código/configuración y decisiones pendientes. Para externos sin relación se oculta existencia como 404 donde corresponde; las pruebas de autorización comprueban denegaciones cruzadas. No hay RLS en PostgreSQL.

La matriz exacta por endpoint sigue en `docs/reference/evaluation-2/validation/http-authorization-matrix.md` y las pruebas de esta entrega están enumeradas en `evidence/test-results/2026-11-05.md`.
