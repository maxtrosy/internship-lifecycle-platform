# Contratos de API CR-05

Todas las rutas usan la cookie de sesión `HttpOnly`. Las mutaciones exigen el encabezado `Origin` permitido. Errores: `{"error": CODE, "detail": ...}`; 404 para actores externos sin relación, 403 para internos sin permiso, 409 para reglas de negocio. Cada ruta declara su acción con `requires(...)`.

| Método y ruta | Acción declarada | Cuerpo | Respuesta |
|---|---|---|---|
| `GET /placements/{pid}/segments` | `placement:read` | — | Lista de segmentos con `conditions`, `status_history` y `schedule_changes` (0018, solo motivo compartido). `end_reason_internal` solo aparece con `segment:read_internal`. Los externos ven solo sus segmentos. |
| `GET /placements/{pid}/segment-options` | `segment:manage` | — | `[{id, name, supervisors:[{id, display_name}]}]` |
| `POST /placements/{pid}/segments` | `segment:manage` | `{host_org_id, unit, workplace_supervisor_id, start_date, end_date, modality: ONSITE\|REMOTE\|HYBRID, responsibilities, expected_hours?}` | 201 `{segment_id, sequence_no, status:"PLANNED"}` |
| `POST /placements/{pid}/segments/{sid}/conditions/{cid}/confirm` | `segment_condition:confirm` | `{reference}` | 204 |
| `POST /placements/{pid}/segments/{sid}/activate` | `segment:manage` | — | 204 · 409 `SEGMENT_CONDITIONS_UNMET` / `SEGMENT_ALREADY_ACTIVE` |
| `POST /placements/{pid}/segments/{sid}/complete` | `segment:manage` | `{ended_on?}` | 204 · 409 `SEGMENT_FINAL_EVALUATION_MISSING` |
| `POST /placements/{pid}/segments/{sid}/terminate` | `segment:manage` | `{ended_on, reason_shared, reason_internal?, work_recognition, recognition_note?}` | 204 |
| `POST /placements/{pid}/segments/{sid}/cancel` | `segment:manage` | `{reason_shared}` | 204 |
| `POST /placements/{pid}/segments/{sid}/schedule` | `segment:manage` | `{start_date?, end_date, reason_shared}` (`start_date` solo cambia en `PLANNED`) | 200 `{segment_id, start_date, end_date, change: EXTENDED\|SHORTENED\|MOVED}`. Errores: `SEGMENT_NOT_OPEN`, `SEGMENT_START_LOCKED`, `SEGMENT_END_DATE_INVALID`, `SEGMENT_DATES_INVALID`, `SEGMENT_SCHEDULE_UNCHANGED`, `SEGMENT_SCHEDULE_CONFLICT` |
| `POST /placements/{pid}/segments/{sid}/transfer` | `segment:manage` | `{effective_date, reason_shared, reason_internal?, prior_work_treatment, destination:{...segmento}}` | 201 `{transfer_id, to_segment_id, to_sequence_no, status:"PLANNED"}` |
| `GET /placements/{pid}/transfers` | `placement:read` | — | Lista; `reason_internal` solo con `segment:read_internal` |
| `POST /placements/{pid}/hours` | `progress:create` | `{hours, work_date?, description?}` | 204 · 409 `NO_ACTIVE_SEGMENT` / `HOURS_WORK_DATE_INVALID` / `HOURS_DAILY_LIMIT` |
| `GET /placements/{pid}/hours` | `progress:read` | — | Entradas con `segment_id`, `segment_sequence_no`, `work_date`, `review_status`, `accepted_hours`, revisor |
| `GET /placements/{pid}/hours/summary` | `progress:read` | — | `{segments:[...], reported_total, accepted_total, pending_entries, scope}` |
| `POST /placements/{pid}/hours/{entry_id}/review` | `hours:review` | `{decision: ACCEPTED\|REJECTED\|DISPUTED, accepted_hours?, reason_code?, reason?}` | 201 `{review_id, decision, accepted_hours, reviewed_at}` |
| `POST /placements/{pid}/experience-review` | `experience:review` | `{decision: APPROVED\|CHANGES_REQUIRED, rationale}` | 201 |
| `GET /reports/rotations` | `reports:read` (PC en sus programas, EC institucional; otros 403) | Query opcional `program_id`, `organization_id` (organización de la oportunidad o de cualquier segmento no cancelado) | `{multi_segment_placements, single_segment_placements, active_rotations, segments_by_status:[{status,count}], transfers, transfers_by_treatment:[{treatment,count}], interruptions, interruptions_by_recognition:[{recognition,count}], hours:{reported, accepted, not_recognized, pending_entries, disputed_entries}, active_segments_without_final_evaluation, completed_segments_missing_final_evaluation, pending_consolidations, by_program:[{program_id, program_code, program_name, multi_segment_placements, pending_consolidations, transfers, interruptions}]}`. Solo agregados: sin nombres, motivos ni registros individuales (ADR-013). |
| `GET /notifications` | autenticado | — | Sin cambios de forma. Nueva categoría `SEGMENT_CHANGED` (migración 0017) para `segment.activated`, `segment.completed`, `segment.terminated_early` y `segment.transferred`. |
| `GET /placements/{pid}/dossier` | `placement:read` | — | Campos nuevos: `hours_summary`, `segments`, `transfers`, `experience_reviews`, `segment_gate`; capacidades `manage_segments`, `confirm_segment_conditions`, `review_hours`, `review_combined_experience`, `read_segment_internal` |

Cambios compatibles: las proyecciones de avances, plan de trabajo, evaluaciones e incidentes añaden `segment_id` y `segment_sequence_no`. El tipo TypeScript los declara opcionales.
