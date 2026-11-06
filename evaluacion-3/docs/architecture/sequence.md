# Secuencia del incremento ejecutable

```mermaid
sequenceDiagram
  actor Student as Estudiante
  participant UI as SPA
  participant API as FastAPI
  participant Policy as Aplicación/Políticas
  participant DB as PostgreSQL
  actor Host as Anfitrión
  actor PC as Coordinador de programa
  actor EC as Coordinador experiencial
  actor WS as Supervisor laboral

  Student->>UI: elegir oportunidad publicada y postular
  UI->>API: POST /opportunities/{id}/apply
  API->>Policy: resolver relación, política y elegibilidad
  Policy->>DB: guardar postulación + policy_version + audit_event
  alt Requiere revisión manual
    PC->>UI: consultar cola de su programa
    PC->>API: POST /applications/{id}/eligibility-review + motivo
    API->>DB: decisión explícita + auditoría + notificaciones
  end
  Host->>API: seleccionar postulación permitida
  API->>DB: selección y colocación pendiente
  PC->>API: aprobar académicamente en su programa
  API->>DB: versión 1 + colocación en documentación pendiente
  Student->>API: entregar documento/versiones
  API->>DB: bytes + metadata + auditoría
  EC->>API: revisar documento y activar si pasan los requisitos persistidos
  API->>DB: revisar y activar
  WS->>API: asignar plan narrativo y registrar evaluación narrativa
  Student->>API: registrar avances/horas y evidencia final
  API->>DB: persistir cada evento en transacción y agregar historial
  EC->>API: confirmar finalización y cerrar
  API->>DB: recalcular requisitos persistidos + transición + auditoría
  Student->>UI: recargar expediente
  UI->>API: GET /placements/{id}/dossier
  API->>DB: filtrar por usuario/relación y proyectar historial
```

La revisión y las transiciones son acciones de un actor autorizado, no efectos automáticos. El E2E ejecuta actores sintéticos en un PostgreSQL temporal; no son aprobaciones ni datos institucionales.
