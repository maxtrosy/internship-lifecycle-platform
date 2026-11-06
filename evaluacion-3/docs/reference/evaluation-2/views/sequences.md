# Secuencias críticas

Cuatro interacciones. Cada una relaciona requisitos, reglas, componentes, ADR y prueba.

| Secuencia | Requisitos | Reglas | Componentes | ADR | Validación |
|---|---|---|---|---|---|
| SEQ-01 flujo extremo a extremo | RF-05..RF-09 | BR-08..BR-11, BR-14 | C-02..C-07, C-10, C-11 | ADR-001, 003, 004 | Diseño; **NOT EXECUTED** como flujo completo (el PoC cubre T2/T4) |
| SEQ-02 activación denegada | RF-09 | BR-01, BR-02 | C-06, C-07, DB | ADR-003 | T-01, T-02, T-02b |
| SEQ-03 cambio → versión → re-aprobación | RF-13, RF-19 | BR-04, BR-06, BR-07 | C-06, C-11, C-10 | ADR-005 | T-05 |
| SEQ-04 acceso externo no autorizado | RF-20 | BR-03, BR-13 | C-02, C-12 | ADR-004 | T-03 |

---

## SEQ-01 — De la postulación a la activación

*Propósito: mostrar el camino feliz y **dónde está cada decisión y cada guarda**. Requisitos: RF-05..RF-09. ADR: 001, 003, 004.*

```mermaid
sequenceDiagram
  autonumber
  participant S as Estudiante
  participant API as API
  participant AZ as C-02 Autorización
  participant EL as C-04 Elegibilidad
  participant SR as StudentRecordsPort
  participant LC as C-06 Ciclo de vida
  participant DB as Base de datos
  participant H as Anfitrión
  participant PC as Coord. programa
  participant LG as Revisor legal
  participant EC as Coord. aprendizaje

  S->>API: postular a oportunidad publicada
  API->>AZ: puede postular
  AZ-->>API: sí, es el titular
  API->>EL: evaluar elegibilidad
  EL->>SR: perfil académico
  SR-->>EL: créditos, nivel, cursos
  EL->>DB: guardar postulación con versión de política y entradas
  EL-->>S: ELEGIBLE o NO ELEGIBLE con motivos

  H->>API: seleccionar postulación
  API->>AZ: puede seleccionar, relación con la oportunidad
  API->>LC: T1 EmployerSelects
  LC->>DB: crear colocación y versión 1 con auditoría, una transacción

  PC->>API: aprobar académicamente
  API->>AZ: coordinador del programa del estudiante
  API->>LC: T2 AcademicApprove
  LC->>DB: materializar checklist desde la política, auditoría

  S->>API: entregar documentos requeridos
  LG->>API: aprobar o rechazar cada documento
  API->>DB: actualizar ítem bajo bloqueo de la colocación

  EC->>API: activar
  API->>AZ: puede activar
  API->>LC: T4 Activate
  LC->>DB: bloquear fila, evaluar requisitos, activar, auditar
  LC-->>EC: ACTIVE
```

*Nota: el estado "listo para activar" no existe como estado; la UI lo deriva de los ítems.*

---

## SEQ-02 — Intento de activación con un requisito pendiente

*Propósito: mostrar **exactamente dónde se rechaza**. Requisitos: RF-09. ADR-003. Prueba: T-01, T-02, T-02b.*

```mermaid
sequenceDiagram
  autonumber
  participant EC as Coord. aprendizaje
  participant API as API
  participant AZ as C-02 Autorización
  participant LC as C-06 Ciclo de vida
  participant DB as Base de datos
  participant X as Cliente directo a BD

  EC->>API: POST activar colocación
  API->>AZ: puede activar
  AZ-->>API: permitido
  API->>LC: Activate
  LC->>DB: BEGIN
  LC->>DB: SELECT colocación FOR UPDATE
  Note over LC,DB: Si otro actor activa o rechaza un documento a la vez,<br/>espera aquí. Gana quien bloquea primero
  LC->>DB: leer requisitos obligatorios no aprobados
  DB-->>LC: DOC_INSURANCE en REJECTED
  LC->>DB: ROLLBACK
  LC-->>API: ACTIVATION_CONDITIONS_UNMET con lista
  API-->>EC: 422 y pendientes, sin cambio de estado ni auditoría de negocio

  Note over X,DB: Camino que evita la aplicación
  X->>DB: UPDATE placement SET state ACTIVE
  DB-->>X: error de compuerta, trigger rechaza
```

**Dónde se rechaza:** primera línea = guarda del comando bajo bloqueo (paso 7–9); última línea de defensa = trigger de BD (paso 12). Ambas fueron ejercitadas en el PoC.

---

## SEQ-03 — Cambio relevante → nueva versión → re-aprobación

*Propósito: mostrar la diferencia entre estado vigente, versión y auditoría. Requisitos: RF-13, RF-19. ADR-005. Prueba: T-05. **OPEN-03:** qué cambios requieren esto y quién aprueba.*

```mermaid
sequenceDiagram
  autonumber
  participant WS as Supervisor lugar de trabajo
  participant API as API
  participant AZ as C-02 Autorización
  participant LC as C-06 Ciclo de vida
  participant DB as Base de datos
  participant PC as Coord. programa
  participant WK as Worker

  WS->>API: proponer cambio de ubicación
  API->>AZ: supervisor asignado a esta colocación
  API->>LC: ProposeChange
  LC->>DB: bloquear colocación
  LC->>DB: insertar versión 2 PROPOSED
  LC->>DB: auditoría change_proposed, misma transacción
  Note over LC,DB: La versión 1 sigue vigente. El puntero current_version no cambia

  PC->>API: aprobar versión 2
  API->>AZ: coordinador del programa del estudiante
  API->>LC: ApproveVersion
  LC->>DB: bloquear colocación
  LC->>DB: versión 2 APPROVED y mover current_version
  LC->>DB: auditoría version_approved con antes y después
  LC->>DB: crear notificaciones pendientes
  WK->>DB: leer notificaciones pendientes
  WK-->>WS: entregar por el puerto de notificación
```

---

## SEQ-04 — Acceso externo no autorizado

*Propósito: mostrar que la denegación ocurre por **relación**, no por rol. Requisitos: RF-20. ADR-004. Prueba: T-03.*

```mermaid
sequenceDiagram
  autonumber
  participant HB as Miembro de organización Beta
  participant API as API
  participant AZ as C-02 Autorización
  participant DB as Base de datos
  participant LOG as Registro operativo

  HB->>API: GET colocación de la organización Alfa
  API->>AZ: leer colocación
  AZ->>DB: contexto de relación, organización de la oportunidad
  DB-->>AZ: organización Alfa distinta de Beta
  AZ-->>API: sin relación
  API->>LOG: evento de seguridad, acceso denegado
  API-->>HB: 404 no encontrado, sin revelar existencia

  HB->>API: GET lista de colocaciones
  API->>AZ: alcance para el rol y la organización
  AZ->>DB: consulta ya filtrada por relación
  DB-->>API: solo colocaciones de Beta
  API-->>HB: lista y proyección mínima del estudiante
```

**Observación:** la denegación se registra en el **registro operativo** (seguridad), no en la auditoría de negocio, que solo contiene mutaciones aceptadas.
