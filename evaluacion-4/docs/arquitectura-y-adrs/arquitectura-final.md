# Arquitectura final (as-built, Evaluación 4)

Los diagramas describen el código de este repositorio en la revisión de esquema **0018** (0016: segmentos; 0017: categoría de aviso `SEGMENT_CHANGED`; 0018: historial de cambios de periodo de segmento). Reemplazan a los de E3 solo en lo que CR-05 cambia; los de E3 siguen en `evaluacion-3/docs/architecture/`.

## Contexto

```mermaid
flowchart LR
  E[Estudiante] -->|reporta horas, avances, incidentes| S((DH-05 Plataforma de prácticas))
  WS[Supervisor laboral del segmento activo] -->|evalúa, asigna plan, revisa horas si está configurado| S
  HM[Miembro de organización anfitriona] -->|consulta segmentos de su organización| S
  FS[Supervisión docente] -->|revisa horas, lee motivos internos| S
  PC[Coordinación del programa] -->|revisa horas, revisión combinada, confirma cierre| S
  EC[Coordinación experiencial] -->|gestiona segmentos si está configurada, cierra| S
  LR[Revisor legal] -->|confirma condiciones documentales del segmento| S
  S --> DB[(PostgreSQL)]
```

No hay sistemas externos nuevos: IdP, correo y almacenamiento externo siguen pendientes (ADR-006).

## Contenedores

```mermaid
flowchart LR
  B[Navegador: React 18 + TypeScript + Vite] -->|HTTP JSON, cookie HttpOnly| A[API FastAPI: monolito modular]
  A -->|psycopg 3, SQL explícito, rol app_user| P[(PostgreSQL: esquema 0018, triggers de seguridad)]
  M[Alembic 0001→0018] -->|migraciones| P
```

## Componentes afectados por CR-05

```mermaid
flowchart TB
  subgraph API[FastAPI]
    R[lifecycle/router.py: endpoints de segmentos, horas y revisiones]
    SV[lifecycle/service.py: horas, registros, gates de cierre, expediente]
    SG[lifecycle/segments.py: segmentos, condiciones, transferencias, revisiones]
    AZ[authz/service.py: rol + relación + segmento]
    AU[audit/service.py]
    NO[notifications/service.py: avisos SEGMENT_CHANGED desde la auditoría]
    RP[reports/service.py: rotations, agregados CR-05]
    CF[config.py: PLACEMENT_SEGMENT_MANAGER_ROLES, PLACEMENT_HOURS_REVIEWER_ROLES]
  end
  subgraph DB[PostgreSQL 0018]
    T1[placement_segment / _condition / _status_history]
    T2[placement_transfer]
    T3[progress_entry_review]
    T4[placement_experience_review]
    TG[triggers: segment_guard, segment_context, placement_gate, initial_segment]
  end
  subgraph UI[Frontend]
    PD[PracticeDossier.tsx]
    PS[PlacementSegments.tsx]
    HR[HoursReviewList.tsx]
    DOC[Documents.tsx: horas con fecha y descripción]
    HL[segments.ts: helpers puros]
    RR[RotationReportSection.tsx: reporte CR-05]
    NI[NotificationInbox.tsx]
  end
  R --> SV & SG
  SV --> SG
  SG --> AZ & AU
  SV --> AZ & AU
  AZ --> CF
  SG --> DB
  SV --> DB
  NO --> DB
  AU --> NO
  RP --> DB
  RR --> RP
  NI --> NO
  PD --> PS & HR
  PS --> HL
  HR --> HL
```

## Patrón de comando (sin cambios, aplicado a CR-05)

Cada mutación de segmento sigue el mismo orden que en E3: `db.command(actor)` → autorizar → `SELECT ... FOR UPDATE` sobre la práctica → evaluar guardas desde filas persistidas → mutar → `audit.write`, todo en una transacción. Los triggers repiten las guardas críticas como red de seguridad, incluso contra SQL directo.

Las vistas de estados y de secuencia están en `../diagramas-y-trazabilidad/diagramas.md`. El modelo de datos está en `modelo-de-datos.md`.
