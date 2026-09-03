# Modelo de Dominio — Internship & Practicum Management System
### RFP DH-05 · Horizon University · Fase 1: Discovery & Domain Modeling

> **Leyenda de confianza**  
> 🟢 <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> · 🟠 <span style="color:#d97706"><strong>TEAM ASSUMPTION</strong></span> · 🔴 <span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> · 🟣 <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> · 🔵 <span style="color:#0d6efd"><strong>RFP EVIDENCE</strong></span>

---

## 1. Bounded Contexts

| Context | Responsabilidad |
|---|---|
| **Opportunity Management** | Registro, revisión institucional y publicación de oportunidades de práctica. |
| **Application & Eligibility** | Postulación de estudiantes, validación de elegibilidad académica, decisión del empleador. |
| **Agreement & Document Management** | Checklist de documentos obligatorios (convenios, seguros, confidencialidad) previos a activación. |
| **Placement Lifecycle** *(core domain)* | El agregado central: activación, cambios, incidentes y cierre de la colocación. |
| **Supervision & Evaluation** | Plan de trabajo, reportes de progreso, horas, evaluaciones midterm/final. |
| **Notifications & Deadlines** | Recordatorios, detección de placements en riesgo (at-risk). |
| **Reporting & Analytics** | Consultas, paneles e informes operativos para seguimiento institucional. |
| **Identity & Access** *(soporte, compartido)* | Autenticación simulada, roles y autorización condicionada por rol y relación con el recurso. |

**Nota de arquitectura:** la separación entre contexts y sus dependencias representa la organización conceptual del dominio. La elección de event bus, interfaces/ports, CQRS u otros mecanismos técnicos **no se considera una decisión de arquitectura confirmada en esta fase**; cualquier arquitectura concreta debe documentarse por separado como hipótesis del equipo.

---

## 2. Entidades, Value Objects e Invariantes por Context

### 2.1 Opportunity Management
- **HostOrganization** (entidad): id, nombre, tipo, estado de verificación institucional.
- **InternshipOpportunity** (entidad): id, hostOrgId, título, modalidad (remote/hybrid/onsite), tipo de compensación, cupo, programas elegibles, estado (Draft → UnderReview → Published → Closed/Cancelled).
- VO: `EligibilityCriteria`, `Modality`, `CompensationType`.

**Invariantes:**
- <span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> La publicación requiere una revisión institucional aprobada. **Propuesta del equipo, pendiente de validación** (relacionada con CL-002: quién puede publicar y bajo qué condiciones).
- <span style="color:#d97706"><strong>TEAM ASSUMPTION</strong></span> El cierre automático al llenar cupo o vencer fecha límite es una **hipótesis del equipo** y no está respaldado explícitamente por el RFP. Debe validarse antes de tratarlo como invariante; también puede considerarse cierre manual.

### 2.2 Application & Eligibility
- **Application** (entidad): id, studentId, opportunityId, estado, submittedAt.
- **EligibilityCheck** (VO): criterios evaluados, resultado, evaluador, fecha.

**Invariantes:**
- <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> Un estudiante no puede tener dos aplicaciones activas a la misma oportunidad. **Regla propuesta por el equipo; pendiente de validación**.
- <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> No puede enviarse al empleador sin elegibilidad validada.

### 2.3 Agreement & Document Management
- **DocumentRequirement** (VO): tipo (agreement/insurance/confidentiality/other), obligatorio (bool).
- **DocumentChecklist** (entidad, 1:1 con Placement): lista de `DocumentStatus`.
- **DocumentStatus** (VO): requirementId, estado (Pending/Submitted/UnderLegalReview/Approved/Rejected).

**Invariante crítica:** el Placement **no puede** entrar a `ReadyToActivate` mientras exista un documento obligatorio sin `Approved`.

### 2.4 Placement Lifecycle *(agregado raíz)*
- **Placement**: id, studentId, opportunityId, hostOrgId, workplaceSupervisorId, facultySupervisorId, programCoordinatorId, fechas, estado (máquina de estados — ver sección 3).
- **PlacementChange / Incident** (entidad): tipo (SupervisorChange/ScheduleChange/LocationChange/ResponsibilityChange/Incident), descripción, reportado por, estado de resolución.

**Invariantes:**
- <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> No se activa sin: aprobación académica + documentos completos + selección del empleador confirmada.
- <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> No se cierra (`Closed`) sin evaluación final **y** evidencia final del estudiante. Esta regla responde directamente al problema identificado en el RFP: "*Final completion may be recorded even when required evidence is missing*".

### 2.5 Supervision & Evaluation
- **WorkPlan** (entidad): placementId, objetivos, responsabilidades, aprobado por.
- **ProgressReport** (entidad): placementId, periodo, horas, evidencia, aprobado por.
- **Evaluation** (entidad): placementId, tipo (Midterm/Final), evaluador, rúbrica, comentarios.
- **HoursLog** (VO): fecha, horas, descripción, estado de aprobación.

**Invariante propuesta:** solo se contabilizan horas si el programa académico del estudiante las exige. <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> La necesidad de que las reglas puedan cambiar está respaldada por el RFP, pero el mecanismo concreto para configurarlas (por ejemplo, un rules engine) es una **decisión de diseño no confirmada**.

### 2.6 Notifications & Deadlines
- **Deadline** (entidad): entidad relacionada, fecha límite, tipo, estado.
- **RiskFlag** (VO): placementId, tipo de riesgo (DelayedActivation/OverdueEvaluation/MissingHours), fecha.

### 2.7 Identity & Access
- **User**: id, rol(es), identidad SSO simulada.
- **Roles**: Student, HostOrgRep, WorkplaceSupervisor, FacultySupervisor, ProgramCoordinator, ExperientialCoordinator, LegalRep, ITAdmin.
- **Policy**: <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> acceso condicionado por rol y relación con el recurso (ej. un WorkplaceSupervisor solo accede a los Placements donde es supervisor asignado).
- <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> La implementación concreta mediante una política técnica de acceso a nivel de fila (*row-level policy*) es una propuesta del equipo y debe validarse con IT.

---

## 3. Máquina de Estados — Placement (entidad core)

```mermaid
stateDiagram-v2
    [*] --> Proposed: Employer acepta candidato
    Proposed --> UnderAcademicReview: ProgramCoordinator inicia revisión
    Proposed --> Withdrawn: Student/Employer retira

    UnderAcademicReview --> Rejected: ProgramCoordinator rechaza
    UnderAcademicReview --> DocumentationPending: ProgramCoordinator aprueba

    DocumentationPending --> ReadyToActivate: ExperientialCoordinator confirma docs completos [guard: checklist=100% Approved]
    DocumentationPending --> Withdrawn: Retiro antes de activar

    ReadyToActivate --> Active: ExperientialCoordinator activa [guard: condiciones obligatorias cumplidas]

    Active --> Suspended: Coordinator suspende temporalmente
    Suspended --> Active: Coordinator reactiva
    Active --> Interrupted: Incidente reportado
    Interrupted --> Active: Coordinator resuelve y reanuda
    Interrupted --> ClosedIncomplete: Coordinator finaliza sin reanudar

    Active --> PendingFinalEvaluation: endDate alcanzada o Coordinator dispara cierre
    PendingFinalEvaluation --> PendingFinalEvidence: WorkplaceSupervisor envía evaluación final
    PendingFinalEvidence --> Closed: Student envía evidencia + FacultySupervisor/Coordinator confirma [guard: evaluación Y evidencia presentes]

    Rejected --> [*]
    Withdrawn --> [*]
    ClosedIncomplete --> [*]
    Closed --> [*]
```

**Nota de diseño:** la transición a `Closed` tiene guard doble (evaluación + evidencia) porque ese es exactamente el defecto que el RFP identifica en el proceso actual. Esta transición debe implementarse como validación explícita en el dominio, no en la UI.

**<span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> Guards adicionales propuestos — pendientes de validación:**  
Estas reglas son coherentes con el flujo descrito, pero no deben presentarse como ratificadas por el cliente mientras las aclaraciones correspondientes sigan abiertas.

- `UnderAcademicReview → DocumentationPending`: requiere `academic_approval = true`.
- `DocumentationPending → ReadyToActivate`: requiere `documents_complete = true` (calculado desde `DocumentChecklist`, no un flag manual) **y** `employer_selection_confirmed = true`.
- `PendingFinalEvaluation → PendingFinalEvidence`: requiere `final_evaluation_present = true`.

Cualquier guard adicional deberá documentarse como **propuesta del equipo** y vincularse a evidencia o a una pregunta de validación antes de considerarse una decisión definitiva.

---

## 4. Domain Events (por context)

| Context | Eventos |
|---|---|
| Opportunity | `OpportunityPublished`, `OpportunityClosed` |
| Application | `ApplicationSubmitted`, `EligibilityValidated`, `EligibilityRejected`, `ApplicationForwardedToEmployer`, `EmployerAccepted`, `EmployerRejected` |
| Documents | `DocumentSubmitted`, `DocumentApproved`, `DocumentRejected` |
| Placement | `PlacementProposed`, `AcademicReviewStarted`, `PlacementApproved`, `PlacementRejected`, `PlacementActivated`, `PlacementSuspended`, `PlacementResumed`, `PlacementInterrupted`, `PlacementClosed`, `PlacementClosedIncomplete`, `PlacementWithdrawn`, `SupervisorChanged`, `ScheduleChanged`, `LocationChanged`, `IncidentReported` |
| Supervision | `WorkPlanApproved`, `ProgressReportSubmitted`, `HoursLogged`, `MidtermEvaluationSubmitted`, `FinalEvaluationSubmitted`, `FinalEvidenceSubmitted` |
| Notifications | `DeadlineMissed`, `RiskFlagRaised` |

<span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> Los cambios, aprobaciones, evaluaciones e incidentes relevantes deben quedar registrados de forma trazable para permitir reconstruir la historia de una colocación. <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> La persistencia concreta mediante una tabla `domain_events` y su uso como fuente de Reporting es una **hipótesis de arquitectura**, no una decisión comprometida del dominio.

---

## 5. Matriz de Roles × Acciones

| Acción | Student | HostOrgRep | WorkplaceSupervisor | FacultySupervisor | ProgramCoordinator | ExperientialCoordinator | LegalRep |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Publicar oportunidad | | ✔ (propone) | | | | ✔ (aprueba) | |
| Postular | ✔ | | | | | | |
| Validar elegibilidad | | | | | ✔ | | |
| Seleccionar/rechazar candidato | | ✔ | | | | | |
| Aprobar ajuste académico | | | | | ✔ | | |
| Subir/revisar documentos | ✔ (sube) | ✔ (sube) | | | | ✔ | ✔ (revisa) |
| Activar placement | | | | | | ✔ | |
| Reportar cambio/incidente | ✔ | ✔ | ✔ | ✔ | | ✔ | |
| Enviar progreso/horas | ✔ | | ✔ (aprueba) | | | | |
| Evaluación midterm/final | | | ✔ | ✔ (revisa) | | | |
| Enviar evidencia final | ✔ | | | | | | |
| Confirmar cierre | | | | ✔ | ✔ | | |
| Ver reportes institucionales | | | | ✔ (limitado) | ✔ | ✔ | |

<span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> La autorización debe considerar **rol + relación con el recurso** para los roles con relación directa a un placement específico (Student, HostOrgRep, WorkplaceSupervisor, FacultySupervisor). <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> La implementación concreta como *policy layer* es una decisión de diseño del equipo, no una arquitectura confirmada.

**<span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> Roles institucionales globales:** el alcance preliminar contempla coordinadores de aprendizaje experiencial y representantes legales con responsabilidades institucionales amplias. La decisión de que `ExperientialCoordinator` y `LegalRep` tengan acceso global, mientras `ProgramCoordinator` tenga acceso limitado por programa, es <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> una propuesta de diseño basada en la interpretación del equipo y debe validarse con IT y los responsables institucionales.

Si en el futuro la universidad requiere coordinadores por facultad, esta decisión deberá revisarse.

---

---

## 6. Estado de confianza del modelo

| Elemento | Clasificación | Tratamiento |
|---|---|---|
| Restricciones de datos sintéticos e integraciones simuladas | 🟢 <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> | Tratar como restricciones del alcance. |
| Trazabilidad de decisiones, cambios y evaluaciones | 🟢 <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> | Necesidad del dominio; no comprometer mecanismo técnico. |
| Reglas de activación y cierre con condiciones/evidencia obligatoria | 🟢 <span style="color:#198754"><strong>KNOWN / CONSTRAINT</strong></span> | Mantener como reglas centrales, sujetas a validación del flujo exacto. |
| Publicación condicionada a revisión institucional | 🔴 <span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> | Propuesta del equipo; validar con stakeholders (CL-002). |
| Cierre automático por cupo/fecha | 🟠 <span style="color:#d97706"><strong>TEAM ASSUMPTION</strong></span> | Hipótesis; no tratar como invariante confirmada. |
| Dos aplicaciones activas a la misma oportunidad | 🟣 <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> | Regla propuesta; validar. |
| Row-level policy | 🟣 <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> | Mecanismo técnico propuesto; validar con IT. |
| Rules engine configurable | 🟣 <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> | Mecanismo técnico propuesto; el requisito de reglas modificables sí debe conservarse. |
| Event bus / CQRS-lite / `domain_events` como arquitectura concreta | 🟣 <span style="color:#6f42c1"><strong>DESIGN PROPOSAL</strong></span> | No son decisiones comprometidas del dominio; documentarlas aparte como hipótesis de arquitectura. |
| Acceso global de roles institucionales | 🔴 <span style="color:#dc3545"><strong>PENDING VALIDATION</strong></span> | Propuesta basada en la interpretación del equipo; validar. |

> **Criterio de esta fase:** el modelo distingue explícitamente entre lo respaldado por el RFP, las hipótesis del equipo y las decisiones de diseño. Las decisiones no validadas no deben presentarse como invariantes o arquitectura definitiva.
