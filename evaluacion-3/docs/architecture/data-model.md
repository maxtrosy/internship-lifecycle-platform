# Modelo de datos persistido

Esquema PostgreSQL; SQL detallado y constraints están en `src/backend/migrations/schema_sql.py` y revisiones Alembic `src/backend/migrations/versions/0001_initial.py`–`0014_manual_eligibility_review.py`.

```mermaid
erDiagram
  ACADEMIC_PROGRAM ||--o{ OPPORTUNITY : targets
  HOST_ORG ||--o{ OPPORTUNITY : owns
  USER_ACCOUNT ||--o{ ROLE_ASSIGNMENT : has
  APPLICATION }o--|| USER_ACCOUNT : applicant
  APPLICATION }o--|| OPPORTUNITY : applies_to
  APPLICATION ||--o| PLACEMENT : selected_into
  POLICY_VERSION ||--o{ APPLICATION : evaluates
  PLACEMENT ||--o{ PLACEMENT_VERSION : versions
  PLACEMENT ||--o{ CHECKLIST_ITEM : requires
  PLACEMENT ||--o{ DOCUMENT_SUBMISSION : receives
  PLACEMENT ||--o{ SUPERVISOR_ASSIGNMENT : assigns
  PLACEMENT ||--o{ PLACEMENT_FACULTY_ASSIGNMENT_HISTORY : tracks
  PLACEMENT ||--o{ PROGRESS_ENTRY : records
  PLACEMENT ||--o{ PLACEMENT_PROGRESS_REPORT : records
  PLACEMENT ||--o{ PLACEMENT_WORK_PLAN_ITEM : plans
  PLACEMENT ||--o{ PLACEMENT_EVALUATION : evaluates
  PLACEMENT ||--o{ PLACEMENT_INCIDENT : reports
  PLACEMENT ||--o{ COMPLETION_EVIDENCE : closes_with
  PLACEMENT ||--o{ AUDIT_EVENT : audits
  USER_ACCOUNT ||--o{ USER_NOTIFICATION : receives
  PLACEMENT ||--o{ PLACEMENT_CONVERSATION : discusses
  PLACEMENT_CONVERSATION ||--o{ PLACEMENT_MESSAGE : contains
```

Las postulaciones fijan la versión de política y entradas usadas. Los documentos, reportes, evaluaciones, cambios reportados y evidencia se asocian a la práctica y mantienen revisión/historial según el tipo. `placement.state` registra estado de ciclo; `placement.current_version_id` apunta a la versión vigente. `audit_event` es append-only y su proyección web se minimiza. El almacenamiento binario de documentos/evidencia está en PostgreSQL en el demo.

Los registros de demostración pueden establecer explícitamente umbrales o escenarios sintéticos. El esquema no equivale a una política institucional aprobada ni convierte cada número del fixture en requisito universal.
