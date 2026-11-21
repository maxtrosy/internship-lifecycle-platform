# Contratos de API CR-05

Todas las rutas usan la cookie de sesión `HttpOnly`. Las mutaciones exigen el encabezado `Origin` permitido. Errores: `{"error": CODE, "detail": ...}`; 404 para actores externos sin relación, 403 para internos sin permiso, 409 para reglas de negocio. Cada ruta declara su acción con `requires(...)`.

| Método y ruta | Acción declarada | Cuerpo | Respuesta |
|---|---|---|---|
| `GET /placements/{pid}/segments` | `placement:read` | — | Lista de segmentos con `conditions` y `status_history`. `end_reason_internal` solo aparece con `segment:read_internal`. Los externos ven solo sus segmentos. |
| `GET /placements/{pid}/segment-options` | `segment:manage` | — | `[{id, name, supervisors:[{id, display_name}]}]` |
| `POST /placements/{pid}/segments` | `segment:manage` | `{host_org_id, unit, workplace_supervisor_id, start_date, end_date, modality: ONSITE\|REMOTE\|HYBRID, responsibilities, expected_hours?}` | 201 `{segment_id, sequence_no, status:"PLANNED"}` |
| `POST /placements/{pid}/segments/{sid}/conditions/{cid}/confirm` | `segment_condition:confirm` | `{reference}` | 204 |
| `POST /placements/{pid}/segments/{sid}/activate` | `segment:manage` | — | 204 · 409 `SEGMENT_CONDITIONS_UNMET` / `SEGMENT_ALREADY_ACTIVE` |
| `POST /placements/{pid}/segments/{sid}/complete` | `segment:manage` | `{ended_on?}` | 204 · 409 `SEGMENT_FINAL_EVALUATION_MISSING` |
| `POST /placements/{pid}/segments/{sid}/terminate` | `segment:manage` | `{ended_on, reason_shared, reason_internal?, work_recognition, recognition_note?}` | 204 |
| `POST /placements/{pid}/segments/{sid}/cancel` | `segment:manage` | `{reason_shared}` | 204 |
| `POST /placements/{pid}/segments/{sid}/transfer` | `segment:manage` | `{effective_date, reason_shared, reason_internal?, prior_work_treatment, destination:{...segmento}}` | 201 `{transfer_id, to_segment_id, to_sequence_no, status:"PLANNED"}` |
| `GET /placements/{pid}/transfers` | `placement:read` | — | Lista; `reason_internal` solo con `segment:read_internal` |
| `POST /placements/{pid}/hours` | `progress:create` | `{hours, work_date?, description?}` | 204 · 409 `NO_ACTIVE_SEGMENT` / `HOURS_WORK_DATE_INVALID` / `HOURS_DAILY_LIMIT` |
| `GET /placements/{pid}/hours` | `progress:read` | — | Entradas con `segment_id`, `segment_sequence_no`, `work_date`, `review_status`, `accepted_hours`, revisor |
| `GET /placements/{pid}/hours/summary` | `progress:read` | — | `{segments:[...], reported_total, accepted_total, pending_entries, scope}` |
| `POST /placements/{pid}/hours/{entry_id}/review` | `hours:review` | `{decision: ACCEPTED\|REJECTED\|DISPUTED, accepted_hours?, reason_code?, reason?}` | 201 `{review_id, decision, accepted_hours, reviewed_at}` |
| `POST /placements/{pid}/experience-review` | `experience:review` | `{decision: APPROVED\|CHANGES_REQUIRED, rationale}` | 201 |
| `GET /placements/{pid}/dossier` | `placement:read` | — | Campos nuevos: `hours_summary`, `segments`, `transfers`, `experience_reviews`, `segment_gate`; capacidades `manage_segments`, `confirm_segment_conditions`, `review_hours`, `review_combined_experience`, `read_segment_internal` |

Cambios compatibles: las proyecciones de avances, plan de trabajo, evaluaciones e incidentes añaden `segment_id` y `segment_sequence_no`. El tipo TypeScript los declara opcionales.
