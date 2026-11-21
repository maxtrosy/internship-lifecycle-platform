# CR-05: Prácticas rotativas y transferencias a mitad de práctica

**Proyecto:** DH-05 Internship and Practicum Management. Solo se implementa CR-05; las solicitudes de DH-01 a DH-04 no se abordan.

## Fuentes oficiales consultadas

| Fuente | Uso |
|---|---|
| `Evaluacion_4_Solicitudes_de_Cambio_DH01_DH05.md` (sección DH-05) | Texto de la solicitud, reglas BR-01 a BR-10, escenarios mínimos y preguntas abiertas. |
| Presentación PDF de Evaluación 4 (20 diapositivas) | Evolución E3→E4, análisis de impacto, vistas de arquitectura, ADR, datos, historial y permisos, cadena regla→decisión→componente→implementación→prueba, registro de evidencia, estructura sugerida del ZIP y guion de video. |
| Presentación PPTX con notas del docente | Notas sobre condiciones de entrega (ver `condiciones-de-entrega.md`). |

Los valores numéricos del documento (por ejemplo, 480 h, o 120 h reportadas → 100 h aceptadas + 140 h = 240 h) son **ejemplos**. No se convirtieron en reglas: los umbrales siguen saliendo de la política de finalización configurada por programa.

## Reglas y cómo se interpretan en el software

| Regla | Enunciado resumido | Interpretación implementada |
|---|---|---|
| BR-01 | Una práctica puede tener varios segmentos sin crear prácticas académicas separadas. | `placement_segment` hija de `placement` (ADR-009). |
| BR-02 | Cada segmento necesita sus condiciones de habilitación antes de activarse; completar uno no activa el siguiente. | Condiciones por segmento desde la política de activación. Activación explícita con gate en el servicio y en un trigger. |
| BR-03 | Cada segmento conserva sus condiciones (organización, unidad, supervisor, fechas, modalidad, responsabilidades, horas esperadas) y sus registros. | Columnas del segmento y `segment_id` en horas, avances, plan, evaluaciones e incidentes. |
| BR-04 | Distinguir horas reportadas y aceptadas, consolidar entre segmentos y no duplicar. | Revisión append-only y total consolidado con la última revisión (ADR-011). |
| BR-05 | Una transferencia registra fecha, motivo, origen, destino, tratamiento del trabajo previo y aprobador sin reescribir historia. | Operación atómica `transfer` + `placement_transfer` inmutable (ADR-010). |
| BR-06 | Un supervisor anterior no opera sobre el segmento nuevo; las evaluaciones previas siguen disponibles según los permisos que correspondan. | Relación derivada del segmento activo. Sin acceso histórico automático (ADR-012). |
| BR-07 | El cierre exige que segmentos, evaluaciones y requisitos estén resueltos, además de las horas. | Gate en servicio y trigger: segmentos cerrados, horas revisadas, evaluación final por segmento y revisión combinada. |
| BR-08 | Una terminación anticipada conserva el historial, el motivo y la decisión sobre el trabajo realizado. | `TERMINATED_EARLY` con reconocimiento explícito. |
| BR-09 | Los motivos sensibles solo los ven los roles autorizados. | Motivo compartido y motivo interno separados. El interno se oculta y no se audita. |
| BR-10 | Las prácticas de un solo segmento siguen funcionando. | Segmento 1 automático. La confirmación de cierre completa el único segmento. |

## Escenarios mínimos del documento y dónde se prueban

Ver `../diagramas-y-trazabilidad/matriz-de-trazabilidad.md`. Los 18 escenarios obligatorios de la misión están cubiertos por `backend/tests/test_cr05_segments.py` y por las suites de regresión de E3.

## Preguntas abiertas del documento (sección 6.8) y tratamiento

| Pregunta | Tratamiento | Identificador |
|---|---|---|
| ¿Quién autoriza una transferencia? | Configurable (`PLACEMENT_SEGMENT_MANAGER_ROLES`), vacío por defecto. | OPEN-CR05-01 |
| ¿Quién acepta las horas? | Configurable (`PLACEMENT_HOURS_REVIEWER_ROLES`), vacío por defecto. | OPEN-CR05-02 |
| ¿Se permiten solapamientos o simultaneidad? | No se prohíbe solapar fechas al planificar. Solo un segmento activo a la vez (decisión técnica conservadora). | OPEN-CR05-03 |
| ¿Cómo se resuelven las disputas de horas? | Existe el estado `DISPUTED`; no hay un flujo de resolución. | OPEN-CR05-04 |
| ¿Cuándo se permite acceso histórico al supervisor anterior? | No se concede ninguno automáticamente. | OPEN-CR05-05 |
| ¿Qué evidencia se exige tras una interrupción? | La terminación exige un motivo y una decisión de reconocimiento; no se exige evidencia adicional. | OPEN-CR05-06 |
