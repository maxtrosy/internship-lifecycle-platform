# ADR-012: Autorización por segmento y fin del acceso de supervisores anteriores

**Estado:** aceptada como decisión técnica. Refina ADR-004 (rol + relación) sin reemplazarla. El acceso histórico de supervisores anteriores sigue siendo una decisión institucional abierta (OPEN-CR05-05).
**Reglas:** CR-05-BR-06, BR-09.
**Fecha:** 2026-11-20.

## Contexto

En E3, la relación del supervisor laboral se derivaba de la versión vigente de la práctica. Con segmentos, un supervisor anterior no debe operar sobre el segmento nuevo (BR-06). Además, las evaluaciones previas deben seguir siendo consultables según los permisos históricos que correspondan.

## Decisión

- `_ctx` calcula, para cada práctica: si tiene segmentos, las organizaciones de los segmentos abiertos supervisados por el usuario (`open_sup_orgs`), el segmento activo supervisado (`active_sup_orgs`) y las organizaciones de todos los segmentos (`segment_orgs`).
- `WORKPLACE_SUPERVISOR`: puede leer la práctica si supervisa un segmento `PLANNED` o `ACTIVE`, y puede operar (evaluar, asignar plan, revisar horas si está configurado) solo si supervisa el segmento `ACTIVE`. Cuando su segmento termina, se transfiere o se completa, pierde toda relación: recibe `NotFound`, igual que cualquier externo sin relación.
- `HOST_ORG_MEMBER`: ve la práctica si su organización tiene algún segmento no cancelado, y solo los registros de los segmentos de su organización.
- Los actores externos ven solo los registros de sus segmentos (`visible_segment_ids` + `filter_by_segment`). Los actores internos (coordinación, supervisión docente, estudiante titular) ven todos los segmentos según las reglas de E3.
- **Acceso histórico:** no se concede ninguno automáticamente. Las evaluaciones del segmento anterior quedan disponibles para el estudiante y los roles internos autorizados (`test_s02`, escenario 8). Que el supervisor anterior pueda consultar sus propias evaluaciones después del cierre requiere una decisión institucional; no se implementó para no ampliar el acceso sin autorización.
- Las nuevas acciones (`segment:manage`, `segment_condition:confirm`, `segment:read_internal`, `hours:review`, `experience:review`) están declaradas en cada endpoint con `requires(...)` y se verifican en el servicio.

## Consecuencias

- **Cambio de comportamiento respecto a E3:** después de completar una práctica, el supervisor anterior recibe `NotFound` en lugar de `PLACEMENT_NOT_ACTIVE`. Las pruebas de E3 afectadas se actualizaron y documentan BR-06.
- Las notificaciones usan `placement_operational_supervisor(pid)` para dirigirse al supervisor del segmento activo.
- **Riesgo:** sin RLS, la protección depende de que cada consulta pase por `authz` y por `filter_by_segment`. Lo cubren las pruebas de dominio y HTTP de acceso cruzado (`test_s16`, `test_s16b`, `test_http_segment_endpoints_enforce_permissions_and_privacy`).
