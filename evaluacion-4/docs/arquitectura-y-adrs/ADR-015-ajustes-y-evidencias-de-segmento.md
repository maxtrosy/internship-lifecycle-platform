# ADR-015: Ajustes administrativos de segmento y evidencia documental de sus condiciones

**Estado:** aceptada como decisión técnica. Refina ADR-009 (segmentos) y ADR-014 (cambios de periodo). No decide quién gestiona segmentos (OPEN-CR05-01) ni la superposición (OPEN-CR05-03).
**Reglas:** CR-05-BR-02 (condiciones de habilitación), BR-03 (historial propio), BR-05 (transferencia como operación única), BR-06 (el supervisor anterior pierde el acceso).
**Fecha:** 2026-11-24.

## Contexto

Hasta 0018 solo las fechas de un segmento abierto podían cambiar (ADR-014). Corregir la unidad, la modalidad, las responsabilidades o las horas esperadas obligaba a cancelar y volver a planificar, incluso en un segmento ya activo. Además, las condiciones documentales de un segmento se confirmaban escribiendo una referencia: no había un archivo real, ni revisión, ni corrección.

## Alternativas

**Ajustes de datos**

- **A1. `UPDATE` libre.** Simple, pero borra el valor anterior y permite cambiar el supervisor de un segmento activo sin transferencia. Eso dejaría al supervisor anterior con registros que ya no le corresponden.
- **A2. Tabla append-only `placement_segment_revision`, con un trigger que solo acepta el cambio junto con su revisión en la misma transacción y reglas por estado.**

**Evidencia**

- **B1. Tabla y almacenamiento propios para evidencias de segmento.** Duplica subida, versiones, revisión, descarga privada y avisos.
- **B2. Reutilizar el módulo documental de E3** (`checklist_item` → `document_submission` → `document_review`), con un ítem enlazado a la condición (`segment_condition_id`).

## Decisión

Se eligen **A2** y **B2** (migración `0019`).

### Ajustes de datos

`PATCH /placements/{pid}/segments/{sid}` (`segments.update_segment`) requiere `segment:manage` (configurable y vacío por defecto). Sus reglas son explícitas:

| Cambio | Segmento planificado | Segmento activo |
|---|---|---|
| Organización | No: cancelar y planificar (`SEGMENT_ORGANIZATION_LOCKED`) | No: transferencia (`SEGMENT_ORGANIZATION_LOCKED`) |
| Unidad, supervisor | Sí; el supervisor debe pertenecer a la misma organización | No: es una transferencia (`SEGMENT_CHANGE_REQUIRES_TRANSFER`) |
| Modalidad, responsabilidades, horas esperadas | Sí | Sí |
| Fechas | Solo por `/schedule` (ADR-014) | Solo por `/schedule` (ADR-014) |

- **Revisión:** cada ajuste guarda los campos cambiados, los valores anterior y nuevo, el motivo compartido, el autor y la hora. La tabla no admite `UPDATE` ni `DELETE`.
- **Trigger:** `trg_placement_segment_guard` rechaza cualquier cambio de esos campos sin una revisión de la misma transacción (`txid_current()`) con los mismos valores. También repite las reglas por estado, así que ni el SQL directo puede convertir un ajuste en una transferencia encubierta.
- **Registros asociados:** las horas, evaluaciones, incidentes y documentos ya asociados al segmento no se modifican.
- **Auditoría y avisos:** la auditoría (`segment.updated`) solo nombra los campos cambiados; el texto libre no se copia en ella. Genera el aviso `SEGMENT_CHANGED`.

### Evidencia documental

- **Ítem de evidencia:** al crear una condición documental de un segmento (de la política de activación del programa), se crea un ítem `DOC_SEG{n}_{TIPO}` con `mandatory = false`.
  - Una restricción impide marcarlo obligatorio, así que las compuertas E3 de activación y cierre de la práctica y el reporte operacional no cambian.
  - La migración crea los ítems de las condiciones pendientes de segmentos planificados existentes.
- **Entrega:** el estudiante titular sube el archivo desde «Mis documentos», con las mismas reglas del módulo:
  - tipos PDF, PNG, JPG o DOCX; firma del contenido; hasta 10 MB;
  - versión y `sha256`;
  - descarga autenticada sin URL pública.

  Solo se acepta mientras el segmento está planificado (`SEGMENT_EVIDENCE_CLOSED`).
- **Revisión:** la hace la revisión legal (`document:review`) en «Revisión documental».
  - **Aprobar** satisface la condición: `confirmed_by` es el revisor y la referencia es `Documento aprobado: <archivo> (revisión N)`. Se audita como `segment.condition_satisfied`. Solo ocurre si el revisor también tiene `segment_condition:confirm`; no se amplía ningún privilegio.
  - **Rechazar** una evidencia ya aprobada, con el segmento aún planificado, devuelve la condición a pendiente (`segment.condition_reopened`). El trigger de condiciones solo permite ese retroceso cuando el ítem enlazado está `REJECTED`. Una condición confirmada manualmente con referencia no se reabre.
- **Confirmación manual:** sigue disponible como alternativa para condiciones no documentales.
- **Almacenamiento:** el contenido se guarda en PostgreSQL (`bytea`), como en E3. Cambiar a un proveedor externo afecta solo a `submit_document` y `get_submission`, no a este flujo.

## Consecuencias

- **Expediente:**
  - muestra «Ajustar datos» con los campos permitidos por estado;
  - en un segmento activo, organización, unidad y supervisor aparecen como texto fijo con la indicación de usar una transferencia;
  - muestra el historial «Ajustes de datos» y, junto a cada condición, el estado de su documento.
- **Visibilidad:** la lista de requisitos (`/checklist` y `/activation-status`) nombra el segmento y la condición, y oculta los ítems de segmentos que la persona no puede ver (BR-07).
- **Downgrade:** `downgrade()` se niega si existen revisiones o evidencias entregadas, para no borrar historia.

## Comprobación

- `backend/tests/test_cr05_segments.py::test_segment_attribute_changes_are_adjustments_not_transfers`: autoridad; reglas por estado; transferencia exigida; organización y fechas bloqueadas; historial; `UPDATE` directo rechazado; auditoría sin texto libre; aviso; HTTP 200, 403/404, 409 y 422.
- `backend/tests/test_cr05_segments.py::test_segment_condition_evidence_reuses_the_document_module`:
  - ítem opcional enlazado; titularidad; ítem de otra práctica; revisor sin permiso;
  - rechazo, corrección y aprobación que satisface la condición; revocación que la reabre;
  - restricción de obligatoriedad; cierre de la evidencia al activar; descargas privadas.
- `scripts/check_isolated_migrations.py`: rechazo de un `UPDATE` directo de atributos y ciclo 0019→0018→0017→0019.
- `frontend/e2e/rotation.spec.ts`:
  - el estudiante sube la evidencia del segmento destino;
  - `legal1` la aprueba;
  - la condición queda cumplida;
  - se activa el segmento y se ajustan su modalidad y sus horas esperadas.
