# Diagramas de estados y secuencia (CR-05)

## Estados de un segmento

```mermaid
stateDiagram-v2
  [*] --> PLANNED: create_segment / transfer (destino)
  [*] --> ACTIVE: activación de la práctica (segmento 1) / migración 0016
  PLANNED --> ACTIVE: activate_segment (condiciones SATISFIED, sin otro ACTIVE)
  PLANNED --> CANCELLED: cancel_segment (motivo)
  ACTIVE --> COMPLETED: complete_segment (evaluación final del segmento)
  ACTIVE --> TERMINATED_EARLY: terminate_segment (motivo + reconocimiento)
  ACTIVE --> TRANSFERRED: transfer (registro placement_transfer)
  COMPLETED --> [*]
  TERMINATED_EARLY --> [*]
  TRANSFERRED --> [*]
  CANCELLED --> [*]
```

Completar un segmento **no** activa el siguiente (BR-02). Los estados finales son inmutables.

## Estados de una entrada de horas

```mermaid
stateDiagram-v2
  [*] --> SUBMITTED: record_hours (segmento activo)
  SUBMITTED --> ACCEPTED: review ACCEPTED (total o parcial)
  SUBMITTED --> REJECTED: review REJECTED (motivo)
  SUBMITTED --> DISPUTED: review DISPUTED (motivo)
  DISPUTED --> ACCEPTED: nueva revisión
  DISPUTED --> REJECTED: nueva revisión
  REJECTED --> ACCEPTED: nueva revisión
```

Cada flecha es una fila nueva en `progress_entry_review`; la última fila define el estado.

## Secuencia: transferencia a mitad de práctica

```mermaid
sequenceDiagram
  actor EC as Gestor de segmentos (configurado)
  participant UI as PlacementSegments.tsx
  participant API as POST /placements/{pid}/segments/{sid}/transfer
  participant SG as segments.transfer
  participant DB as PostgreSQL
  EC->>UI: fecha de efecto, motivos, tratamiento, destino
  UI->>API: JSON
  API->>SG: db.command(actor)
  SG->>DB: authorize(segment:manage) + SELECT placement FOR UPDATE
  SG->>DB: valida origen ACTIVE, fechas, supervisor de la organización destino
  SG->>DB: UPDATE origen → TRANSFERRED (trigger: historial, inmutabilidad)
  SG->>DB: INSERT segmento destino PLANNED + condiciones de la política
  SG->>DB: INSERT placement_transfer (aprobador = actor)
  SG->>DB: INSERT audit_event segment.transferred (sin motivo interno)
  DB-->>API: COMMIT (todo o nada)
  API-->>UI: 201 {transfer_id, to_segment_id}
  Note over UI,DB: El destino necesita confirmar sus condiciones y una activación explícita.
```

## Secuencia: cierre de una práctica con varios segmentos

```mermaid
sequenceDiagram
  actor PC as Coordinación del programa
  participant SV as confirm_completion
  participant DB as PostgreSQL
  PC->>SV: confirmar finalización
  SV->>DB: requisitos de política (MIN_HOURS con horas aceptadas, informe final, evaluación final)
  SV->>DB: segment_blockers: segmentos abiertos, horas pendientes, evaluación final por segmento, revisión combinada
  alt bloqueadores
    SV-->>PC: 409 SEGMENT_REQUIREMENTS_PENDING / COMPLETION_EVIDENCE_MISSING
  else listo
    SV->>DB: UPDATE placement state=COMPLETED (trg_placement_gate vuelve a verificar)
    SV-->>PC: 204
  end
```
