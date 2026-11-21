# Trazabilidad del incremento

| Requisito del cambio | Componente | Implementación | Prueba | Evidencia |
|---|---|---|---|---|
| Reconstruir seguimiento por versión | Lifecycle service + schema | `UPGRADE_0015_SQL`; inserciones capturan `current_version_id`; proyecciones exponen `version_no` | `test_follow_up_records_capture_the_approved_version_in_force` | `test-results-2026-11-17.md` |
| Evitar referencias inválidas | Trigger SQL | `trg_lifecycle_version_context` | Suite backend + migración aislada | Resultado `0015` |
| Mantener permisos actuales | Authz/lifecycle routers | No se agregan permisos; se reutiliza autorización existente | `tests/test_http_authorization.py` | 110 pruebas backend |
| Mostrar contexto en expediente | React dossier/follow-up/work-plan | Tipos y etiquetas opcionales de versión | Frontend Vitest + E2E poblado | Capturas desktop/móvil |
| No inventar historia previa | Migración nullable | Sin backfill de filas anteriores | Pruebas de migración incremental | Análisis de impacto |
