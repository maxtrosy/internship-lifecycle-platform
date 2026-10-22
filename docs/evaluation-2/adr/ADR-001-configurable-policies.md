# ADR-001 — Políticas de elegibilidad, activación y finalización configurables

**Status:** propuesta (pendiente de validación con el cliente) · **Fecha:** 2026-10-08

## Context
El RFP exige que las reglas de elegibilidad y finalización por programa "puedan cambiar" (sec. 7). La Evaluación 1 lo recoge en RNF-03, RF-05, RF-08 y RF-17, y registra que las reglas son desconocidas (CL-001, CL-003..CL-005, PT-002..PT-004, R-001). Hecho importante: **el RFP no exige que el cambio ocurra sin redeploy ni que lo haga un no desarrollador**; eso aparece en ASM-006B/RNF-03 como propuesta del equipo (AUD-21). El equipo técnico es pequeño y el semestre es corto (RNF-09).

## Decision
1. Una **política** se identifica por (tipo, programa, tipo de colocación) y tiene **versiones inmutables**.
2. Cada versión es una **lista de condiciones de un vocabulario cerrado**, combinadas con AND:

| Familia | Condiciones soportadas en v1 |
|---|---|
| Elegibilidad | `PROGRAM_IN`, `ACADEMIC_LEVEL_MIN`, `CREDITS_MIN`, `PREREQUISITE_COMPLETED` |
| Activación | `REQUIRED_DOCUMENT(tipo)`, `SUPERVISORS_ASSIGNED` *(propuesta, OPEN-01)* |
| Finalización/cierre | `FINAL_REPORT`, `FINAL_EVALUATION`, `MIN_HOURS(n)` *(solo si el programa lo exige, OPEN-11)* |

3. Cada tipo de condición tiene **un evaluador en código** (tabla de estrategias). **No hay expresiones, scripts ni DSL.**
4. Al guardar, se **valida** forma y vocabulario; lo no soportado se rechaza.
5. **Vinculación:** la postulación guarda la versión de elegibilidad usada y los datos de entrada; la colocación vincula sus políticas de activación y finalización al aprobarse académicamente. Las versiones posteriores **no alteran** colocaciones en curso salvo migración explícita (OPEN-04).
6. La activación y el cierre no leen la política cada vez: se **materializan** como instancias (`checklist_item`, `completion_requirement`) al vincular la política (base de ADR-003).
7. Agregar un **tipo de condición nuevo** requiere cambio de código y release. Cambiar **parámetros** de condiciones existentes no.

## Alternatives considered
| Alternativa | Por qué se descartó |
|---|---|
| A. Reglas fijas en código por programa | Más simple hoy, pero cada cambio exige ingeniería; contradice R-001 |
| B. Motor de reglas genérico con scripts o DSL | Máxima flexibilidad, pero superficie de seguridad, pruebas combinatorias y mantenimiento incompatibles con personal técnico limitado (RNF-09) |
| C. Archivos de configuración versionados y redesplegados | Aceptable como plan B; no permite cambio operativo ni trazabilidad por decisión |
| **D. Vocabulario cerrado + política versionada (elegida)** | Cubre el cambio de parámetros con control y bajo costo |

## Rationale
Atiende el requisito real del RFP (reglas cambiables) sin pagar el costo de un motor general. Las versiones inmutables dan reproducibilidad: se puede explicar por qué una postulación fue (in)elegible meses después.

## Consequences
Postulaciones y colocaciones guardan referencias a versiones. Se necesita una pantalla/endpoint de gestión de políticas (US-036, propuesta). La auditoría registra cada versión creada.

## What gets worse / trade-offs
- Expresividad limitada: OR, excepciones por estudiante o reglas dependientes del tiempo requieren rediseño.
- Más complejidad que reglas fijas: validación, versionado, vinculación, migración.
- **Costo de mantenimiento:** cada tipo de condición nuevo = código + pruebas + release; el equipo debe resistir la tentación de "una condición genérica".
- Cualquier cambio de política mal configurado puede bloquear activaciones: requiere vista previa/validación (pendiente).

## Verification
- **Ejecutado (PoC, equipo):** T-06 — versión v1 → v2 aplicada a evaluaciones posteriores sin cambiar código; la postulación previa conserva v1 y su resultado; 4 formas inválidas rechazadas (script, clave extra, valor inválido, vacía); coordinador de otro programa rechazado; 2 eventos de auditoría de política.
- **NOT EXECUTED:** latencia de vigencia (QS-03), evaluadores de activación/finalización en el producto, pruebas de regresión por evaluador, comportamiento ante políticas con fecha de vigencia futura.

## Reconsider when
Más de ~5 reglas reales exigen OR o anidamiento; el cliente exige que usuarios no técnicos definan lógica arbitraria; la frecuencia de nuevos tipos de condición hace inviable el release por condición.

## Related requirements
RF-05, RF-08, RF-17, RNF-03, RNF-09 · CL-001/003/004/005 · ASM-006/006B (reinterpretado) · R-001

## Related quality scenarios
QS-03 (principal), QS-01, QS-06

## Related architecture views
V-COMP (C-05, C-04, C-07), V-DOM (Policy, PolicyVersion, ChecklistItem, CompletionRequirement), SEQ-01
