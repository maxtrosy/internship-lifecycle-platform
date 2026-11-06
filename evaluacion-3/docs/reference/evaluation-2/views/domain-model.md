# Modelo de dominio y de datos

> **Aviso (OPEN-17):** el equipo **no tenía** un modelo de dominio previo (`ASM-003B` cita un `domain-model.md` que no existe, AUD-34). Este modelo, construido desde el RFP y la Evaluación 1, es la **primera versión** y es una propuesta que el equipo debe revisar y adoptar.
> El esquema inicial del PoC era simplificado. La migración `0005` agregó al producto registros separados de avances, evaluaciones narrativas, incidentes/cambios y evidencia final; `0007` agrega asignaciones narrativas del plan de trabajo; `0008` agrega el estado factual `REPORTED` para informes de incidente/cambio y `0009` impide nuevas asignaciones del plan tras el cierre. `ApprovalDecision` genérica, mensajes y notificaciones siguen siendo parte del modelo propuesto, no tablas actuales.

| Campo | Valor |
|---|---|
| **ID** | V-DOM |
| **Propósito** | Mostrar entidades, relaciones, propiedad, ciclo de vida e invariantes |
| **Requisitos** | RF-01..RF-20, RNF-03, RNF-05 |
| **ADRs** | ADR-001, ADR-003, ADR-004, ADR-005 |

```mermaid
erDiagram
  ACADEMIC_PROGRAM ||--o{ USER_ACCOUNT : "pertenece"
  HOST_ORGANIZATION ||--o{ USER_ACCOUNT : "tiene miembros"
  USER_ACCOUNT ||--o{ ROLE_ASSIGNMENT : "tiene"
  HOST_ORGANIZATION ||--o{ OPPORTUNITY : "ofrece"
  ACADEMIC_PROGRAM ||--o{ OPPORTUNITY : "dirigida a"
  POLICY ||--o{ POLICY_VERSION : "versiona"
  ACADEMIC_PROGRAM ||--o{ POLICY : "define"
  OPPORTUNITY ||--o{ APPLICATION : "recibe"
  USER_ACCOUNT ||--o{ APPLICATION : "presenta"
  POLICY_VERSION ||--o{ APPLICATION : "evaluó con"
  APPLICATION ||--o| PLACEMENT : "origina"
  PLACEMENT ||--|{ PLACEMENT_VERSION : "versiona"
  PLACEMENT ||--o{ SUPERVISOR_ASSIGNMENT : "supervisa"
  PLACEMENT ||--o{ CHECKLIST_ITEM : "exige"
  CHECKLIST_ITEM ||--o{ DOCUMENT_SUBMISSION : "recibe"
  PLACEMENT ||--o{ COMPLETION_REQUIREMENT : "exige"
  PLACEMENT ||--o{ APPROVAL_DECISION : "decide"
  PLACEMENT ||--o{ PROGRESS_ENTRY : "registra horas"
  PLACEMENT ||--o{ PLACEMENT_WORK_PLAN_ITEM : "asigna actividades"
  PLACEMENT ||--o{ PLACEMENT_PROGRESS_REPORT : "registra avances"
  PLACEMENT ||--o{ PLACEMENT_EVALUATION : "evalúa narrativamente"
  PLACEMENT ||--o{ PLACEMENT_INCIDENT : "reporta situación/cambio"
  PLACEMENT ||--o{ COMPLETION_EVIDENCE : "entrega evidencia"
  PLACEMENT ||--o{ MESSAGE : "comunica"
  USER_ACCOUNT ||--o{ NOTIFICATION : "recibe"
  PLACEMENT ||--o{ AUDIT_EVENT : "traza"

  PLACEMENT {
    int id PK
    string state
    int current_version_id FK
    int application_id FK
  }
  PLACEMENT_VERSION {
    int id PK
    int version_no
    int workplace_supervisor_id FK
    date start_date
    date end_date
    string location
    string responsibilities
    string status
  }
  CHECKLIST_ITEM {
    int id PK
    string kind
    boolean mandatory
    string status
  }
  COMPLETION_REQUIREMENT {
    int id PK
    string kind
    boolean mandatory
    boolean satisfied
  }
  PLACEMENT_PROGRESS_REPORT {
    int placement_id FK
    int revision
    string content
    datetime created_at
  }
  PLACEMENT_WORK_PLAN_ITEM {
    int placement_id FK
    int revision
    int assigned_by FK
    string title
    string description
    datetime assigned_at
  }
  PLACEMENT_EVALUATION {
    int placement_id FK
    string kind
    int revision
    string narrative
    datetime created_at
  }
  PLACEMENT_INCIDENT {
    int placement_id FK
    string kind
    int revision
    string summary
    string description
    datetime created_at
  }
  COMPLETION_EVIDENCE {
    int placement_id FK
    string kind
    int revision
    string original_filename
    string sha256
    bytes content
  }
  AUDIT_EVENT {
    bigint id PK
    int actor_id
    string action
    string subject_type
    json before_state
    json after_state
    string correlation_id
  }
```

## Decisiones de agrupación (qué NO es una entidad separada)

| Candidata del enunciado | Decisión | Justificación |
|---|---|---|
| Student | **No** separada: `UserAccount` + perfil académico leído por `StudentRecordsPort` (instantánea guardada con la elegibilidad) | La fuente es externa (simulada); no se replica entera |
| Role | `RoleAssignment` (usuario, rol, alcance: programa u organización) | Un usuario puede tener varios roles/alcances |
| WorkplaceSupervisor / FacultySupervisor | **Roles** de `UserAccount`; el supervisor del lugar de trabajo es un campo de `PlacementVersion`; el docente es `SupervisorAssignment` | El cambio de supervisor del lugar de trabajo es un cambio **versionado** (RFP); el docente no |
| EligibilityRule / Policy | `Policy` + `PolicyVersion` con condiciones del vocabulario cerrado | ADR-001 |
| RequiredDocument | **No** entidad: es una *condición* de política que se materializa en `ChecklistItem` | Una sola mecánica para activación y cierre |
| Approval | `ApprovalDecision` genérica (sujeto, decisión, actor, instante) | Selección, aprobación académica, aprobación de versión, revisión de oportunidad comparten forma |
| Activity / Progress / HoursRecord | `ProgressEntry` conserva horas; `PlacementProgressReport` registra narrativas de avance | Tablas distintas por campos y autorización: estudiante escribe ambas; lecturas según relación |
| Change | `PlacementIncident(kind=CHANGE,status=REPORTED)` conserva el reporte informativo; la modificación formal futura usa **`PlacementVersion`** | Reportar cambio no versiona ni aprueba; RF-13 sigue sujeto a OPEN-03 |
| Incident | `PlacementIncident(kind=INCIDENT,status=REPORTED)` como reporte append-only | `REPORTED` es el único estado implementado; no tiene revisión, resolución ni escalamiento, y no inventa una transición RF-14 |
| Evaluation | `PlacementEvaluation` narrativa MIDTERM/FINAL, sin escala numérica | WPS vigente escribe; lectura se filtra por actor/relación |
| CompletionEvidence | `CompletionEvidence` conserva archivo y revisión/hash para requisito `FINAL_REPORT` | Bytes en PostgreSQL de demo; el almacenamiento institucional externo sigue pendiente |
| Communication | `Message` (usuarios); `Notification` (sistema), separadas | Orígenes, permisos y reintentos distintos |

## Cardinalidades, propiedad y ciclo de vida

| Entidad | Propietario (módulo) | Cardinalidad clave | Ciclo de vida |
|---|---|---|---|
| Opportunity | C-03 | Organización 1—N Oportunidad | `Draft → InReview → Published → Closed`; ver abajo |
| Application | C-04 | Oportunidad 1—N; Estudiante 1—N | `Submitted → …`; ver abajo |
| **Placement** | **C-06** | Postulación 1—0..1 Colocación | V-STATE-PLC |
| PlacementVersion | C-06 | Colocación 1—N (≥1) | `PROPOSED → APPROVED/REJECTED`, contenido inmutable |
| ChecklistItem | C-07 | Colocación 1—N | `REQUIRED → SUBMITTED → APPROVED/REJECTED` |
| DocumentSubmission | C-07 | Ítem 1—N | Cada entrega se conserva |
| CompletionRequirement | C-08 | Colocación 1—N | `satisfied` falso → verdadero (recalculable desde el origen) |
| PlacementProgressReport | C-08 | Colocación 1—N | Revisiones append-only |
| PlacementEvaluation | C-08 | Colocación 1—N, por tipo/revisión | Narrativa MIDTERM/FINAL; sin puntuación |
| PlacementIncident | C-08 | Colocación 1—N, por tipo/revisión | Estado factual append-only `REPORTED`; sin flujo posterior de revisión/resolución |
| CompletionEvidence | C-08 | Colocación 1—N, por requisito/revisión | Archivo append-only; descargable según permiso |
| PolicyVersion | C-05 | Política 1—N | Inmutable |
| AuditEvent | C-11 | Colocación 1—N | **Append-only** |

### Ciclos de vida de apoyo

```mermaid
stateDiagram-v2
  direction LR
  state "Oportunidad" as OPP {
    [*] --> Draft
    Draft --> InReview : enviar a revisión
    InReview --> Published : aprobar
    InReview --> Draft : devolver
    Published --> Closed : cerrar postulaciones
  }
```

```mermaid
stateDiagram-v2
  direction LR
  state "Postulación" as APP {
    [*] --> Submitted : postular
    Submitted --> Ineligible : política no cumplida
    Submitted --> UnderEmployerReview : elegible
    UnderEmployerReview --> Selected : seleccionar
    UnderEmployerReview --> NotSelected : rechazar
    Submitted --> Withdrawn : retirar
    UnderEmployerReview --> Withdrawn : retirar
  }
```

*Un estado `EligibilityReview` (revisión humana de elegibilidad) queda fuera hasta resolver OPEN-04.*

## Invariantes

| ID | Invariante | Aplicación |
|---|---|---|
| INV-01 | Una colocación solo es `ACTIVE` si sus requisitos de activación obligatorios están aprobados | ADR-003, BR-01 |
| INV-02 | Una colocación solo es `COMPLETED`/`CLOSED` con requisitos de cierre obligatorios cumplidos | ADR-003, BR-05 |
| INV-03 | Horas y progreso solo existen para colocaciones `ACTIVE` | Trigger, BR-02 |
| INV-04 | `current_version_id` apunta a una versión `APPROVED` de la misma colocación | C-06 |
| INV-05 | El contenido de una versión y los eventos de auditoría nunca cambian | ADR-005, BR-06 |
| INV-06 | Una postulación conserva la versión de política con la que se evaluó | BR-12 |
| INV-07 | Una colocación en estado terminal no cambia de estado | BR-17 |
| INV-08 | Toda mutación aceptada tiene su evento de auditoría en la misma transacción | BR-07 |

## Restricción de datos
No existen campos de nómina, impuestos ni transacciones financieras (RNF-10). Que una colocación sea remunerada o no es, a lo sumo, un indicador informativo (RFP sec. 8; **OPEN**).
