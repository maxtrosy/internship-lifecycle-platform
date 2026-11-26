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
- Las fechas de un segmento abierto pueden cambiar con historial (0018, ADR-014). Desde 0019 (ADR-015) la unidad y el supervisor de un segmento planificado, y la modalidad, las responsabilidades y las horas esperadas de uno planificado o activo, se ajustan con historial. La organización nunca se edita. La unidad o el supervisor de un segmento activo solo cambian con una transferencia.
- Los avisos de segmento (`SEGMENT_CHANGED`, ADR-013) cubren activación, cierre, terminación, transferencia y cambio de periodo. No hay aviso al planificar un segmento, ni al supervisor anterior tras una transferencia (no tiene acceso, BR-06). Tampoco hay envío por correo: los avisos viven en la bandeja de la aplicación, como en E3.
- Los reportes de CR-05 (`GET /reports/rotations`) son agregados por alcance y se calculan en cada petición, lo que es suficiente para el volumen de un semestre (ADR-013). El filtro de organización incluye la organización de cada segmento. No listan prácticas individuales ni permiten exportar. Un listado nominal para actuar sobre consolidaciones pendientes requeriría decidir qué datos personales puede ver cada rol en un reporte.
- Las horas de E3 migradas quedan pendientes de revisión. En una instalación real, una autoridad debería revisarlas antes del cierre.
- La migración 0016 es irreversible (`downgrade` lanza error), porque revertirla destruiría historia. El procedimiento exige respaldo previo.
- Sin RLS en PostgreSQL: el aislamiento depende de la capa `authz` y de los filtros por segmento, verificados con pruebas.
- El E2E de Playwright recorre los flujos de E3 con la configuración de CR-05. `frontend/e2e/rotation.spec.ts` (modo `--populated`) recorre en el navegador una transferencia completa: revisión de horas, transferencia, condición jurídica, activación, acceso del supervisor anterior y del nuevo, privacidad del motivo, avisos y reporte. La planificación de una rotación sin transferencia y la terminación anticipada se prueban a nivel de servicio y HTTP, no en el navegador.
- La fixture poblada calcula sus periodos a partir del día en que se genera (pasado, actual y futuro), así que el escenario del navegador no caduca (corregido el 2026-11-24).

## Real frente a simulado

- **Real (ejecutado):** pruebas backend contra PostgreSQL temporal (pgserver), migraciones 0001→0019 y 0010→0019 en PostgreSQL temporal, pruebas unitarias del frontend (vitest), build de producción del frontend y E2E aislado con Chromium.
- **Simulado/sintético:** todas las personas, organizaciones, políticas, horas y referencias documentales de pruebas y demo.
- **No ejecutado:** ningún despliegue en Neon, Render o Docker. Neon y Docker no se modificaron.
