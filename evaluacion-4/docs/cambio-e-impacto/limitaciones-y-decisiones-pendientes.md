# Limitaciones y decisiones institucionales pendientes

Este documento separa lo **implementado** de lo **diseñado sin implementar**, y lo **real** de lo **simulado**.

## Decisiones institucionales abiertas (no inventadas)

| Id | Pregunta | Estado actual del software |
|---|---|---|
| OPEN-CR05-01 | ¿Qué rol autoriza crear, activar, completar, terminar, cancelar y transferir segmentos? | `PLACEMENT_SEGMENT_MANAGER_ROLES` está vacío por defecto: nadie puede hacerlo. Las pruebas, el E2E y la demo usan `EXPERIENTIAL_COORDINATOR` **solo en bases temporales**. |
| OPEN-CR05-02 | ¿Qué rol acepta horas? | `PLACEMENT_HOURS_REVIEWER_ROLES` está vacío por defecto. Las pruebas y la demo usan `FACULTY_SUPERVISOR,PROGRAM_COORDINATOR`. También se admite `WORKPLACE_SUPERVISOR`, limitado al segmento que supervisa. |
| OPEN-CR05-03 | ¿Se permiten segmentos simultáneos? | Las fechas pueden solaparse, pero solo hay un segmento `ACTIVE` a la vez. |
| OPEN-CR05-04 | ¿Cómo se resuelve una disputa de horas? | Existe el estado `DISPUTED` y una nueva revisión puede reemplazarlo. No hay mediador ni plazos. |
| OPEN-CR05-05 | ¿Cuándo puede el supervisor anterior consultar sus evaluaciones? | No se concede acceso histórico. |
| OPEN-CR05-06 | ¿Qué evidencia se exige tras una interrupción? | Se exigen motivo y decisión de reconocimiento; no hay evidencia adicional. |
| OPEN-03 / OPEN-05 (E3) | Autoridades de versiones, revisión y publicación | Sin cambios. |

## Limitaciones técnicas

- No hay carga de archivos por segmento: las condiciones documentales se confirman con una referencia textual verificada por `LEGAL_REVIEWER`.
- Un segmento planificado no se puede editar: hay que cancelarlo y crear otro.
- No se emiten notificaciones nuevas para segmentos o transferencias. Las mutaciones quedan auditadas y visibles en el expediente.
- Las horas de E3 migradas quedan pendientes de revisión. En una instalación real, una autoridad debería revisarlas antes del cierre.
- La migración 0016 es irreversible (`downgrade` lanza error), porque revertirla destruiría historia. El procedimiento exige respaldo previo.
- Sin RLS en PostgreSQL: el aislamiento depende de la capa `authz` y de los filtros por segmento, verificados con pruebas.
- El E2E de Playwright existente recorre los flujos de E3 con la configuración de CR-05. No existe un spec de Playwright dedicado a una rotación completa en la interfaz; esos flujos se prueban a nivel de servicio, de HTTP y con pruebas unitarias del frontend.

## Real frente a simulado

- **Real (ejecutado):** pruebas backend contra PostgreSQL temporal (pgserver), migraciones 0001→0016 y 0010→0016 en PostgreSQL temporal, pruebas unitarias del frontend (vitest), build de producción del frontend y E2E aislado con Chromium.
- **Simulado/sintético:** todas las personas, organizaciones, políticas, horas y referencias documentales de pruebas y demo.
- **No ejecutado:** ningún despliegue en Neon, Render o Docker. Neon y Docker no se modificaron.
