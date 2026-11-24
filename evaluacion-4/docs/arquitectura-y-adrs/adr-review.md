# Revisión de ADR para Evaluación 4 (CR-05)

Ningún ADR se eliminó. Los ADR-001 a ADR-007 se conservan en el paquete de Evaluación 3 (`evaluacion-3/docs/adrs/review.md` y `docs/reference/evaluation-2/adr/`). ADR-008 (Codex, incremento 0015) se conserva en esta carpeta. Para cada ADR se indica si se **mantiene**, se **refina** o se **reemplaza** frente a CR-05.

| ADR | Decisión frente a CR-05 | Motivo y evidencia |
|---|---|---|
| ADR-001: políticas configurables | **Mantiene** | Las condiciones de habilitación de cada segmento se toman de la política de activación vigente del programa (`_instantiate_conditions`). No se añadió ninguna regla institucional. |
| ADR-002: monolito modular | **Mantiene** | CR-05 se implementa como submódulo `lifecycle/segments.py` dentro del mismo proceso FastAPI y la misma base de datos. No hay servicios nuevos. |
| ADR-003: gates de activación/cierre | **Refina** | Se añaden un gate de activación por segmento (condiciones `SATISFIED`, supervisor de la organización y segmento único activo) y nuevas condiciones de cierre: sin segmentos abiertos, sin horas pendientes, `MIN_HOURS` con horas aceptadas, evaluación final por segmento completado y revisión combinada aprobada si hay más de un segmento. El trigger `trg_placement_gate` se reescribió en la migración 0016. |
| ADR-004: autorización por rol + relación | **Refina** con ADR-012 | La relación del supervisor y de la organización se deriva del segmento, no de la versión. Las acciones nuevas tienen capacidad declarada. |
| ADR-005: versiones y auditoría | **Refina** con ADR-010/011 | Segmentos, condiciones, transferencias, revisiones de horas y revisiones de experiencia son inmutables o append-only. Cada mutación escribe `audit_event` en la misma transacción. El motivo interno no se audita. |
| ADR-006: adaptadores externos | **Mantiene** (no realizado) | CR-05 no añade proveedores externos. Las condiciones documentales se confirman con referencia, sin carga de archivos nueva. |
| ADR-007: stack y migraciones | **Refina** | Revisión de esquema vigente: **0018** (0016 crea segmentos; 0017 solo amplía las categorías de aviso; 0018 añade el historial de cambios de periodo). La migración es irreversible y está documentada en `../diagramas-y-trazabilidad/migraciones-y-actualizacion.md`. |
| ADR-008: contexto de versión aprobado (0015) | **Mantiene** | Los registros guardan `placement_version_id` y además `segment_id`. Ambos contextos son complementarios: la versión indica las condiciones aprobadas y el segmento indica el tramo operativo. |
| **ADR-009: segmentos de práctica** | **Nuevo** | Ver `ADR-009-segmentos-de-practica.md`. |
| **ADR-010: transferencia y terminación** | **Nuevo** | Ver `ADR-010-transferencia-y-terminacion.md`. |
| **ADR-011: horas reportadas/aceptadas** | **Nuevo** | Ver `ADR-011-horas-reportadas-y-aceptadas.md`. |
| **ADR-012: acceso por segmento** | **Nuevo** (refina ADR-004) | Ver `ADR-012-acceso-por-segmento.md`. |
| **ADR-013: reportes y avisos de CR-05** | **Nuevo** (amplía ADR-005 y el reporte operativo de E3) | Ver `ADR-013-reportes-y-avisos-cr05.md`. Indicadores calculados desde las tablas de 0016; avisos generados desde la auditoría, sin estado nuevo. |
| **ADR-014: cambios de periodo de segmento** | **Nuevo** (refina ADR-009) | Ver `ADR-014-cambios-de-periodo-de-segmento.md`. Las fechas de un segmento abierto cambian solo con un registro append-only en la misma transacción; el resto del segmento sigue inmutable. |

Ningún ADR se marcó como reemplazado: CR-05 amplía el modelo sin invalidar las decisiones previas.
