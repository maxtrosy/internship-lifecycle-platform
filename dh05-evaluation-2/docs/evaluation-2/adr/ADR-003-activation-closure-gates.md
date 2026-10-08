# ADR-003 — Compuertas de activación, finalización y cierre

**Status:** propuesta, **parcialmente verificada** en un PoC ejecutado en sandbox · **Fecha:** 2026-10-08

## Context
RFP: "Students must not begin a placement before mandatory activation conditions are satisfied" y la universidad no puede registrar una finalización con evidencia faltante (sec. 2 y 7). RF-09 y RF-17 los convierten en bloqueos. Riesgos concretos: dos actores activan a la vez; un documento se rechaza mientras se activa; alguien evita la aplicación (migración, consola, defecto). Las listas exactas de condiciones están abiertas (OPEN-01, OPEN-02).

## Decision
Una **defensa en capas** con una regla común: *las condiciones obligatorias son filas materializadas (instancias) y la compuerta es "no existe ninguna instancia obligatoria sin cumplir"*.

1. **Comando = una transacción** que: autoriza → **bloquea la fila de la colocación (`SELECT … FOR UPDATE`)** → evalúa la guarda **desde las filas de origen** → cambia estado → escribe auditoría.
2. **Orden de bloqueo fijo:** primero la colocación, luego sus dependientes (ítems, requisitos). Rechazar/aprobar un documento también toma primero el bloqueo de la colocación.
3. **Instancias materializadas** desde la política vinculada (ADR-001): `checklist_item` (activación) y `completion_requirement` (cierre).
4. **Recalcular desde el origen** lo que depende de otros datos: p. ej. `MIN_HOURS` se recalcula sumando horas antes de decidir; la bandera guardada no es fuente de verdad.
5. **Red de seguridad en BD (triggers)** sobre transiciones a `ACTIVE`, `COMPLETED` y `CLOSED` (origen válido + sin instancias obligatorias sin cumplir) y sobre la inserción de horas/progreso (BR-02).
6. **Errores de negocio tipados** (`ACTIVATION_CONDITIONS_UNMET`, `COMPLETION_EVIDENCE_MISSING`, `INVALID_TRANSITION`, `GATE_VIOLATION`). Un comando denegado no escribe auditoría de negocio; se registra como evento operativo.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| Solo guarda en aplicación | Sin red si se evita la aplicación; cualquier defecto la anula |
| Solo restricciones/triggers en BD | Mensajes pobres, la lógica de política no cabe bien, no evita duplicados por sí sola (ver hallazgo) |
| Motor de flujo de trabajo externo | Más piezas que operar; no justificado para un solo agregado |
| Aislamiento `SERIALIZABLE` en todo | Reintentos complejos para un volumen bajo; el bloqueo de fila es más simple y explicable |
| **Aplicación + bloqueo + instancias + trigger (elegida)** | Cubre concurrencia y bypass con costo moderado |

## Rationale
El bloqueo evita carreras; el trigger atrapa lo que escape; las instancias hacen que el trigger sea simple y no duplique la política completa. El volumen bajo hace despreciable la contención del bloqueo.

## Consequences
La política se evalúa al vincular y se materializa; la UI puede mostrar "listo para activar" como **estado derivado** (no almacenado) calculado de las instancias.

## What gets worse / trade-offs
- Lógica en dos sitios (aplicación y SQL) que debe mantenerse sincronizada.
- Triggers: más difíciles de probar, versionar y migrar.
- La red en BD solo cubre lo materializado; las condiciones que dependen de cálculo (horas) dependen del recálculo de la aplicación.
- Un superusuario de BD puede deshabilitar el trigger.
- Quedó **abierta una laguna** (OPEN-14): rechazar un documento *después* de activar es legal en esta versión y deja una colocación activa con un documento rechazado.

## Verification (ejecutado en sandbox; PostgreSQL 16.2; 2026-10-08)
- **T-01:** 100/100 carreras de activación doble → exactamente 1 éxito, 1 `INVALID_TRANSITION`, 1 evento. **Control negativo** (sin bloqueo): doble activación en 30/30. *Hallazgo:* el trigger solo **no** impide ACTIVE→ACTIVE; lo evita el bloqueo.
- **T-02:** rechazo de documento concurrente con activación. Variante A (diseño propuesto): 100 ensayos, **0** resultados prohibidos; ambos órdenes ocurrieron (59 activación primero, 41 rechazo primero). Control B (sin bloqueo ni trigger): **22/40** prohibidos. Variante C (sin bloqueo, con trigger): **0/40**; el trigger respondió con `GATE_VIOLATION` en 21.
- **T-02b:** `UPDATE` directo rechazado por la BD; un comando denegado no agrega filas de auditoría.
- **T-04, T-08:** ver resultados.
- **NOT EXECUTED:** concurrencia de cierre; migración de datos que deje instancias inconsistentes; comportamiento con otra BD.

## Reconsider when
Las condiciones dejan de ser "instancias obligatorias" (p. ej. reglas con dependencias complejas entre requisitos); el volumen genera contención medible; se cambia de motor de BD.

## Related requirements
RF-09, RF-17 · RNF-05 · ASM-007 · RFP sec. 7

## Related quality scenarios
QS-01, QS-06

## Related architecture views
V-COMP (C-06, C-07), V-STATE-PLC (T4, T7, T8), SEQ-02, V-DOM (ChecklistItem, CompletionRequirement)
