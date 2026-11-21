# ADR-009: Segmentos de práctica dentro de una misma práctica académica

**Estado:** aceptada como decisión técnica del equipo para CR-05 (Evaluación 4). No es una decisión institucional.
**Reglas:** CR-05-BR-01, BR-02, BR-03, BR-10.
**Fecha:** 2026-11-20.

## Contexto

En Evaluación 3, `placement` representaba al mismo tiempo la identidad académica de la práctica y sus condiciones operativas: una organización, un supervisor laboral, unas fechas y unas responsabilidades, guardadas en `placement_version`. CR-05 exige que una práctica tenga varias rotaciones o asignaciones sucesivas sin crear prácticas académicas separadas (BR-01). También exige que cada rotación conserve sus condiciones y sus registros (BR-03), y que las prácticas de un único tramo sigan funcionando (BR-10).

## Alternativas consideradas

| Alternativa | Ventaja | Por qué se descartó |
|---|---|---|
| A. Crear una práctica (`placement`) por rotación | Reutiliza todo el código de E3 | Rompe BR-01: fragmenta la práctica académica, duplica requisitos y evaluaciones y obliga a sumar horas entre prácticas. |
| B. Reutilizar `placement_version` como rotación | Sin tabla nueva | Una versión es una *corrección* de las condiciones vigentes, no un tramo nuevo. Mezclar ambos conceptos impediría saber si un cambio corrige un error o inicia una rotación, y la versión no tiene un ciclo de vida propio (planificado, activo, terminado). |
| **C. Tabla `placement_segment` hija de `placement`** | Separa la identidad académica de la operación de cada tramo. Cada segmento tiene su propio estado y su propio historial | Exige migrar los registros existentes y adaptar autorización y gates. **Elegida.** |

## Decisión

- `placement` conserva la identidad académica: estudiante, programa, políticas fijadas, requisitos de cierre y estado global.
- `placement_segment` guarda cada tramo operativo: organización, unidad, supervisor laboral, fechas, modalidad, responsabilidades, horas esperadas, origen (`PLACEMENT_ACTIVATION`, `MIGRATED_SINGLE`, `ROTATION`, `TRANSFER`) y estado (`PLANNED` → `ACTIVE` → `COMPLETED` / `TERMINATED_EARLY` / `TRANSFERRED`, o `PLANNED` → `CANCELLED`).
- **Un único segmento activo por práctica**, garantizado por un índice único parcial (`placement_one_active_segment`) y por el bloqueo `FOR UPDATE` de la práctica en el servicio. Las fechas pueden solaparse en la planificación. La operación simultánea de dos segmentos queda como decisión institucional abierta (OPEN-CR05-03).
- El segmento 1 se crea automáticamente cuando la práctica pasa a `ACTIVE`, con las condiciones de la versión aprobada vigente (trigger `trg_placement_initial_segment`). Una práctica de un solo tramo no exige ninguna acción adicional (BR-10).
- Cada segmento nuevo nace `PLANNED` con condiciones de habilitación tomadas de la política de activación del programa: los documentos `REQUIRE_DOCUMENTS` quedan `REQUIRED` y el supervisor validado queda `SATISFIED`. La activación es explícita (BR-02). Completar un segmento nunca activa el siguiente.
- Horas, avances, plan de trabajo, evaluaciones e incidentes guardan `segment_id`. Un trigger (`zz_<tabla>_segment_context`) exige que un registro nuevo pertenezca al segmento activo y respete sus fechas.
- La migración `0016` crea un segmento `MIGRATED_SINGLE` por cada práctica activa, completada o cerrada y asocia allí los registros existentes. No inventa unidad ni modalidad: quedan `NULL`.

## Consecuencias

- **Positivas:** se puede reconstruir qué organización y qué supervisor respaldaban cada registro. Las transferencias y terminaciones no reescriben historia. El flujo de E3 de un solo tramo se conserva y está probado (`test_s01_single_segment_practice_keeps_e3_flow` y toda la suite de E3).
- **Negativas / coste:** todas las consultas de seguimiento filtran por segmento para los actores externos. La autorización ahora depende del segmento (ver ADR-012). La migración es irreversible (`downgrade` lanza error), porque deshacerla implicaría borrar historia.
- **Pendiente:** la carga de archivos por segmento no existe; las condiciones documentales se confirman con una referencia verificada por `LEGAL_REVIEWER`. Tampoco existe edición de un segmento planificado: hay que cancelarlo y crear otro.
