# Matriz de trazabilidad: regla → decisión → componente → implementación → prueba → evidencia

Las rutas de prueba son relativas a `src/backend/tests/` (backend) y `src/frontend/` (frontend). La evidencia ejecutada vigente está en `../../evidence/test-results-2026-11-24.md` (la de 2026-11-20 se conserva como historial).

## Reglas CR-05

| Regla | Decisión | Componente | Implementación | Prueba |
|---|---|---|---|---|
| BR-01 | ADR-009 | `lifecycle/segments.py` | `create_segment`, tabla `placement_segment` | `test_cr05_segments.py::test_s02_multi_segment_rotation_end_to_end` |
| BR-02 | ADR-009, ADR-003 refinado | `segments.py`, trigger `trg_placement_segment_guard` | `confirm_condition`, `activate_segment` | `test_s02` (activación sin condiciones; completar no activa) |
| BR-03 | ADR-009 | `service.py`, triggers `zz_*_segment_context` | `segment_id` en registros | `test_s02`, `test_s05` |
| BR-04 | ADR-011 | `segments.review_hours`, `placement_accepted_hours` | revisión append-only | `test_s10`, `test_s11`, `test_s17b`, `src/segments.test.ts`, E2E `lifecycle.spec.ts` (revisión de horas) |
| BR-05 | ADR-010 | `segments.transfer` | `placement_transfer` | `test_s05`, `test_s17` |
| BR-06 | ADR-012 | `authz/service.py` | `_ctx`, `_ws_relation`, `_ws_operational`, `visible_segment_ids` | `test_s02` (escenarios 7 y 8), `test_s16b`, `test_lifecycle.py` (supervisor anterior → NotFound) |
| BR-07 | ADR-003 refinado | `confirm_completion`, `close_placement`, `trg_placement_gate` | `segment_blockers` | `test_s02` (escenario 14), `test_s13` |
| BR-08 | ADR-010 | `segments.terminate_segment` | `TERMINATED_EARLY` + reconocimiento | `test_s12` |
| BR-09 | ADR-010 | `list_segments`, `list_transfers` | ocultamiento y auditoría sin motivo interno | `test_s05` (escenario 15), `test_http_segment_endpoints_enforce_permissions_and_privacy` |
| BR-10 | ADR-009 | `trg_placement_initial_segment`, `auto_complete_single_segment` | segmento 1 automático | `test_s01`, suites E3 completas, E2E `lifecycle.spec.ts` |

## Los 18 escenarios obligatorios de la misión

| # | Escenario | Prueba | Resultado |
|---|---|---|---|
| 1 | Una práctica con un solo segmento funciona | `test_s01_single_segment_practice_keeps_e3_flow` | Pasa |
| 2 | Una práctica con varios segmentos | `test_s02_multi_segment_rotation_end_to_end` | Pasa |
| 3 | Un segmento no se activa sin condiciones (servicio y BD) | `test_s02` | Pasa |
| 4 | Completar un segmento no activa el siguiente | `test_s02` | Pasa |
| 5 | La transferencia conserva el segmento anterior y sus registros | `test_s05_transfer_preserves_origin_records_and_registers_decision` | Pasa |
| 6 | La transferencia registra fecha, motivo, origen, destino, tratamiento y aprobador | `test_s05` | Pasa |
| 7 | El supervisor anterior no opera sobre el segmento nuevo | `test_s02`, `test_s16b` | Pasa |
| 8 | Las evaluaciones previas siguen disponibles según los permisos | `test_s02` | Pasa |
| 9 | Las horas aceptadas se consolidan entre segmentos | `test_s02` | Pasa |
| 10 | Los duplicados no se cuentan dos veces | `test_s10_duplicate_entries_are_not_double_counted`, `test_s17b` | Pasa |
| 11 | Horas reportadas ≠ horas aceptadas | `test_s11_reported_hours_are_not_accepted_hours` | Pasa |
| 12 | Un segmento terminado anticipadamente conserva su historial | `test_s12_early_termination_keeps_history_and_recognition_decision` | Pasa |
| 13 | No se cierra con evaluaciones pendientes | `test_s13_closure_blocked_by_pending_segment_evaluation` | Pasa |
| 14 | No se cierra con requisitos de segmento pendientes | `test_s02` (segmento abierto, revisión combinada; también en BD) | Pasa |
| 15 | Los motivos sensibles se ocultan | `test_s05`, prueba HTTP | Pasa |
| 16 | Se rechaza el acceso cruzado | `test_s16_cross_access_is_rejected`, `test_s16b`, prueba HTTP | Pasa |
| 17 | Consistencia bajo concurrencia | `test_s17_concurrent_activation_and_transfer_stay_consistent`, `test_s17b` | Pasa |
| 18 | Los flujos de E3 siguen funcionando | suites `test_lifecycle.py`, `test_http_authorization.py`, `test_documents.py`, etc.; E2E aislado; migración 0001→0019 | Pasa (ver evidencia) |
| 19 | Una transferencia conserva las horas aceptadas y el supervisor anterior queda sin acceso, recorrido en el navegador | `frontend/e2e/rotation.spec.ts` (`--populated`) | Ver evidencia 2026-11-24 |
| 20 | Reportes de CR-05 agregados y limitados por alcance | `test_rotation_reports_aggregate_cr05_state_within_scope`, `src/api.segments.test.ts` | Ver evidencia 2026-11-24 |
| 21 | Avisos de segmento sin alcanzar al supervisor anterior ni al actor | `test_segment_events_notify_related_people_but_not_the_previous_supervisor` | Ver evidencia 2026-11-24 |
| 22 | Excepciones temporales: acortar o extender un segmento abierto y mover uno planificado, con reglas explícitas e historial | `test_segment_schedule_changes_follow_explicit_rules_and_keep_history`, `check_isolated_migrations.py`, `rotation.spec.ts` | Ver evidencia 2026-11-24 |
| 23 | Reporte de rotaciones filtrado por la organización del segmento | `test_rotation_reports_aggregate_cr05_state_within_scope` | Ver evidencia 2026-11-24 |
| 24 | Ajustes de datos de segmento sin convertirlos en transferencias, con historial | `test_segment_attribute_changes_are_adjustments_not_transfers`, `check_isolated_migrations.py`, `rotation.spec.ts` | Ver evidencia 2026-11-24 |
| 25 | Evidencia documental real de condiciones de segmento con revisión, corrección y trazabilidad | `test_segment_condition_evidence_reuses_the_document_module`, `rotation.spec.ts` | Ver evidencia 2026-11-24 |
| 26 | Reporte de rotaciones: cada filtro, sus combinaciones y el alcance de cada rol | `test_rotation_report_filters_and_scope_regression` | Ver evidencia 2026-11-24 |
| 27 | Secretos de desarrollo publicados rechazados fuera de desarrollo y demo | `test_published_development_secrets_are_refused_outside_development` | Ver evidencia 2026-11-24 |
