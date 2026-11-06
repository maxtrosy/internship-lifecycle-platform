# Vista de contexto

```mermaid
flowchart LR
  Student[Estudiante]
  PC[Coordinación de programa]
  EC[Coordinación experiencial]
  Legal[Revisión Legal]
  Host[Organización anfitriona]
  WS[Supervisor laboral]
  Faculty[Supervisor docente]
  System[Internship Lifecycle Platform\nSPA React + API FastAPI + PostgreSQL]
  Student -->|postula, entrega, consulta, reporta horas| System
  PC -->|revisa elegibilidad y aprueba ámbito académico| System
  EC -->|opera gates y reportes según rol configurado| System
  Legal -->|consulta tareas autorizadas del expediente| System
  Host -->|gestiona oportunidad y selección de su ámbito| System
  WS -->|asigna plan y registra evaluación narrativa| System
  Faculty -->|consulta solo práctica asignada| System
```

Las relaciones del sujeto con programa, organización y colocación condicionan la lectura/escritura. La app ofrece identidad local; no se identificó un IdP institucional. No hay SIS real, correo, calendario ni repositorio documental externo conectados. Las notificaciones se persisten en una bandeja interna y el contenido de documentos se guarda en PostgreSQL.
