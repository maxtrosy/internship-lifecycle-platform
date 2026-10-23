# Interfaces

Solo las relevantes. Los puertos externos no tienen integraciones institucionales o de terceros conectadas. C-01 implementa autenticación local en FastAPI; el SSO institucional sigue pendiente. Los endpoints y el almacenamiento de archivos descritos aquí corresponden al código actual; los módulos no listados siguen siendo propuestas.

## 1. Interfaces externas (puertos) — todas **simuladas**

| ID | Consumidor | Proveedor | Propósito | Operaciones | Entrada | Salida | Autorización | Comportamiento ante fallo | Dependencia | Simulada/Real |
|---|---|---|---|---|---|---|---|---|---|---|
| IF-ID | C-01 | Cuentas locales de DH-05 | Autenticar y resolver sujeto | `POST /auth/login`, `GET /auth/me`, `POST /auth/logout`, recuperación e invitación | Nombre/email + contraseña; cookie de sesión | Identidad y roles resueltos en DH-05 | El sujeto no implica permisos; roles y relaciones se consultan en BD | Sesión de 15 min; logout revoca; contraseña recuperada revoca todas las sesiones | RNF-07 | **Real local; SSO OPEN-21** |
| IF-STU | C-04 | Registros estudiantiles | Perfil académico para elegibilidad | `getAcademicProfile(studentId)` | Id del estudiante | Programa, nivel, créditos, cursos aprobados | Solo C-04; solo el estudiante que postula | Elegibilidad **no evaluada** (nunca se asume elegible); reintento | RF-05 | **Simulada** |
| IF-DOC | C-07 | Repositorio de documentos | Guardar y recuperar archivos | `store`, `getReference`, `exists` | Archivo + metadatos | Referencia opaca | Descarga solo con permiso sobre la colocación | Demo actual almacena bytes en PostgreSQL (PDF, PNG, JPG o DOCX; máximo 10 MB); reintentar entrega crea revisión. El adaptador institucional sigue pendiente | RFP sec. 7/10; OPEN-20 | **Local demo; proveedor externo pendiente** |
| IF-NTF | C-10 | Canal de notificación | Entregar avisos | `deliver(notification)` | Destinatario, mensaje | Acuse o error | Interno | Reintentos con límite; **no revierte** el comando de negocio | RF-15; OPEN-15 | **Simulada / interna** |
| IF-CAL | C-10 | Calendario | Sincronizar fechas | `publish(event)` | Fechas de colocación | Acuse | Interno | Se ignora | US-030; OPEN-10 | **Opcional**, no necesaria |

**Pruebas de contrato del adaptador externo (NOT EXECUTED):** un mismo conjunto deberá pasar el simulador y cualquier implementación futura; los simuladores deben poder **fallar a pedido** (QS-07). Las pruebas T-28/T-29 cubren el almacenamiento local de demo, no el proveedor institucional.

## 2. Interfaces internas (API de aplicación)

| ID | Consumidor | Proveedor | Propósito | Operaciones (implementadas donde se indica; resto propuesto) | Autorización (C-02) | Fallos principales |
|---|---|---|---|---|---|---|
| IF-API-01 | UI | C-03 | Oportunidades | `POST /opportunities`, `POST …/submit-review`, `POST …/publish`, `GET /opportunities?filtros` | Staff por rol; estudiantes por programa/elegibilidad; anfitrión solo las suyas | 404 externo sin relación; 422 sin revisión |
| IF-API-02 | UI | C-04 | Postulaciones y elegibilidad | `POST /opportunities/{id}/applications`, `GET /applications/{id}` | Titular; anfitrión de esa oportunidad; coordinador del programa | `ELIGIBILITY_UNAVAILABLE`, resultado `NOT_ELIGIBLE` con motivos |
| IF-API-03 | UI | C-06 | Comandos del ciclo de vida | `POST /applications/{id}/select`, `POST /placements/{id}/approve-academic`, `…/reject-academic`, **`…/activate`**, `…/confirm-completion`, `…/close`, `…/cancel` | Rol **y** relación (ver §3) | 404/403, 409 `INVALID_TRANSITION`, 422 `ACTIVATION_CONDITIONS_UNMET`, 422 `COMPLETION_EVIDENCE_MISSING`, 409 `GATE_VIOLATION` |
| IF-API-04 | UI | C-07 | Checklist y documentos | Implementado: `GET /placements/{pid}/checklist`, `POST /placements/{pid}/items/{item_id}/submit?filename=…` (bytes; `Content-Type`), `GET …/submissions`, `GET …/submissions/{submission_id}/download`, `POST …/review` (decisión + motivo) | Estudiante titular entrega/descarga; **revisor legal** revisa/descarga | 403; `DOCUMENT_TYPE_UNSUPPORTED`; `DOCUMENT_REVIEW_REASON_REQUIRED`; 409 estado inválido |
| IF-API-05 | UI | C-08 | Supervisión | `POST …/progress`, `POST …/evaluations`, `POST …/incidents` | Estudiante titular (horas); supervisores asignados; docente asignado | `PLACEMENT_NOT_ACTIVE` (422) |
| IF-API-06 | UI | C-06 | Cambios | `POST /placements/{id}/versions`, `POST /versions/{id}/approve` | Supervisor asignado o coordinador propone; coordinador **del programa** aprueba | 403/404; 409 |
| IF-API-07 | UI | C-05 | Políticas | Implementado: `GET /policies`, `POST /policies` (programa, familia y condiciones; crea versión) | Coordinador **del programa** (US-036, pendiente de validación institucional) | 422 vocabulario inválido |
| IF-API-08 | UI | C-11 | Historial | `GET /placements/{id}/history` | Quienes leen la colocación; evaluaciones y datos sensibles filtrados | 404/403 |
| IF-API-09 | UI | C-12 | Paneles y reportes | `GET /dashboards/…`, `GET /reports/…` | Filtrado por alcance (programa/organización) | 403 |
| IF-API-10 | UI | C-10 | Notificaciones | `GET /notifications`, `POST …/{id}/read` | Destinatario | — |

**Convenciones de error:** 404 en lugar de 403 para externos sin relación (no revelar existencia); 409 = conflicto de estado (otro actor se adelantó); 422 = precondición de negocio no cumplida; los errores de negocio devuelven un código estable y la lista de lo pendiente.

## 3. Ejemplo trabajado — `activate`

```http
POST /placements/42/activate
Authorization: Bearer <sesión del coordinador de aprendizaje experiencial>
```

**204** (éxito; respuesta sin cuerpo)
```

**422** (requisitos pendientes)
```json
{ "error": "ACTIVATION_CONDITIONS_UNMET",
  "unmet": ["DOC_INSURANCE=REJECTED", "COND_SUPERVISOR_ASSIGNED=REQUIRED"] }
```

**409** (otro actor se adelantó)
```json
{ "error": "INVALID_TRANSITION", "current_state": "ACTIVE" }
```

**404** si el sujeto es externo y no tiene relación con la colocación; **403** si es interno sin permiso para activar.

## 4. Qué no se define aquí
Formato de tokens, paginación, versionado de la API, límites de tasa y reportes exportables: **no necesarios para justificar la estructura** en esta evaluación.
