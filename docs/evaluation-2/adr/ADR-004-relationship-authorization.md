# ADR-004 — Autorización por rol y relación con la colocación

**Status:** propuesta, **parcialmente verificada** en PoC (sin capa HTTP) · **Fecha:** 2026-10-08

## Context
El RFP: acceso "dependiente del rol y de la relación con la oportunidad o colocación", acceso externo "controlado y limitado" y preocupación explícita porque "host organizations may access more student information than necessary" (sec. 2 y 7). RF-20, RNF-04. Hay muchos usuarios con el **mismo rol pero distinta relación**: dos organizaciones anfitrionas, supervisores docentes asignados a ciertas colocaciones, coordinadores de un programa. ASM-003B propone política a nivel de fila (cita un `domain-model.md` que no existe, AUD-34). La autenticación de usuarios externos no está definida por el RFP (OPEN-21).

## Decision
1. **Identidad ≠ autorización.** El servicio de identidad (simulado) entrega *quién es* el sujeto; los roles y relaciones son datos de DH-05.
2. Un **componente central de autorización (C-02)** decide con predicados **rol + relación** sobre el recurso:

| Rol | Relación requerida para leer una colocación |
|---|---|
| Estudiante | Es el titular de la postulación/colocación |
| Miembro de la organización anfitriona | La oportunidad pertenece a su organización |
| Supervisor del lugar de trabajo | Su organización **y** figura como supervisor en alguna versión de esa colocación |
| Supervisor docente | Está asignado a la colocación |
| Coordinador de programa | El programa del estudiante es el suyo |
| Coordinador de aprendizaje experiencial / Representante legal | Alcance institucional (¿todo o por programa? **OPEN-09**) |

3. Las **acciones** requieren además el rol adecuado (p. ej. activar: coordinador de aprendizaje experiencial; aprobar académicamente: coordinador **del programa del estudiante**).
4. Los **listados** usan **consultas ya filtradas por relación** (no "traer todo y filtrar"), y la lectura directa y el listado deben coincidir.
5. **Usuarios externos:** si no hay relación, la respuesta es **"no encontrado"** (no revela existencia); para internos, "prohibido".
6. **Proyección mínima** del estudiante para externos (BR-13): nombre y programa; sin créditos, nivel, cursos aprobados ni otras postulaciones (el detalle final es OPEN-06).
7. **Defensa en profundidad opcional:** política a nivel de fila de la BD (ASM-003B) a evaluar con Servicios de TI; **no es la base** del diseño.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| RBAC puro | Insuficiente: dos anfitriones con el mismo rol verían los mismos datos |
| Motor de políticas externo (ABAC/ReBAC como servicio) | Potente, pero una pieza más que operar para ~6 tipos de relación |
| Solo seguridad a nivel de fila en BD | Buena última línea, pero la lógica de rol/acción y mensajes queda fuera, y complica pools de conexión y pruebas |
| **Aplicación con predicados de relación + consultas filtradas + proyección (elegida)** | Testeable, portable y proporcional |

## Rationale
Es la forma mínima que satisface "rol y relación" y es verificable con una matriz de pruebas. Mantener la identidad separada permite sustituir el IdP simulado sin tocar permisos.

## Consequences
Cada caso de uso pasa por C-02. Se necesitan índices para los predicados de relación. La matriz de seguridad (`design/security.md`) es la especificación de pruebas.

## What gets worse / trade-offs
- Más lógica de autorización y más *joins* por consulta.
- Matriz de pruebas más grande (sujeto × recurso × acción).
- Riesgo de olvidar C-02 en un endpoint nuevo (mitigación propuesta: prueba que falle si una ruta no declara su acción — *NOT EXECUTED*).
- RLS adicional agregaría complejidad con pools de conexión y depuración.
- Ocultar existencia con 404 dificulta un poco el soporte.

## Verification
- **Ejecutado (PoC, equipo):** T-03 — 66 aserciones sobre 13 sujetos × 3 colocaciones en una base aislada: listados exactos, coincidencia lectura/listado, 9 denegaciones externas como "no encontrado", 11 denegaciones internas como "prohibido", 8/8 acciones negativas denegadas, 5/5 positivas permitidas, proyección con solo 2 campos.
- **Hallazgo de proceso:** la primera corrida de T-03 falló por fixtures compartidos entre pruebas (defecto del harness, no del diseño); se aisló la base y se conservó la evidencia del fallo.
- **NOT EXECUTED:** capa HTTP, usuarios externos reales, RLS, escaneo de rutas sin autorización, exportaciones/reportes.

## Reconsider when
TI exige RLS; el número de tipos de relación crece o las políticas deben cambiarlas no desarrolladores (entonces evaluar un motor externo); se define la autenticación externa (OPEN-21).

## Related requirements
RF-20, RNF-04, RNF-07 · RFP sec. 2 y 7 · CL-008, PT-003

## Related quality scenarios
QS-02

## Related architecture views
V-COMP (C-02), V-CTX (identidad), SEQ-04, [security](../design/security.md)
