# Análisis de impacto — contexto de versión en seguimiento

## Cambio

Los registros de horas, avances, actividades del plan, evaluaciones, incidentes y evidencia final se escribían vinculados a la práctica, pero no explicitaban qué versión aprobada de la práctica estaba vigente al momento del registro. El expediente mostraba la historia temporal, pero no permitía reconstruir completamente la relación entre un registro y una versión aprobada.

## Impactos

| Área | Impacto | Decisión |
|---|---|---|
| Datos | Seis tablas reciben una FK nullable a `placement_version` | `NULL` conserva honestamente el contexto desconocido de filas históricas |
| Dominio | Las nuevas mutaciones capturan `placement.current_version_id` | Se reutiliza el bloqueo existente de la práctica |
| Integridad | Trigger común valida que la versión pertenezca a la práctica, esté aprobada y sea la vigente | Las inserciones inválidas fallan en la transacción |
| API | Listados de seguimiento incluyen `placement_version_id` y `version_no` | La compatibilidad de clientes se mantiene; los campos son opcionales en TypeScript |
| UI | El expediente muestra “Versión vigente al registrar” cuando existe | No se presenta un dato inventado para registros históricos |
| Auditoría | Eventos de seguimiento incluyen el identificador de versión | Se conserva la reconstrucción cronológica junto con `audit_event` |
| Permisos | No cambia la matriz de autorización | Los servicios existentes siguen siendo la autoridad de lectura/escritura |
| Cierre | Las compuertas existentes continúan leyendo horas, evidencia y evaluación persistidas | No se introducen mínimos nuevos |

## Riesgos y mitigaciones

- **Regresión de clientes:** campos opcionales en los tipos frontend y pruebas HTTP actualizadas.
- **Carrera de versiones:** el servicio ya bloquea la práctica durante la aprobación; el trigger verifica el puntero vigente durante cada inserción.
- **Migración de datos:** no se backfillan identificadores desconocidos.
- **Decisión institucional pendiente:** la migración no decide quién aprueba cambios; OPEN-03 sigue explícito.
