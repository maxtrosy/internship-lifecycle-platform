# ADR-002 — Monolito modular frente a servicios distribuidos

**Status:** propuesta · **Fecha:** 2026-10-08

## Context
Escala del RFP (sec. 8, preliminar): ~12 000 estudiantes, 600–900 colocaciones/año, 200–300 organizaciones, 8–12 coordinadores, 60–100 supervisores docentes. Equipo universitario, un semestre, personal técnico limitado (RNF-09, ASM-012). El driver dominante es la integridad del ciclo de vida (AD-01): activación, cierre, versiones y auditoría deben cambiar **juntos o no cambiar**.

## Decision
- Un **monolito modular**: una API con módulos C-01..C-13 y límites explícitos (cada módulo expone una interfaz de aplicación; no se accede a tablas ajenas).
- Un **worker** que ejecuta el **mismo código** como proceso distinto (notificaciones y detección de plazos).
- **Una base de datos relacional** transaccional compartida.
- Los adaptadores externos viven dentro del monolito (ADR-006).
- Las dependencias entre módulos se **verifican automáticamente** (reglas de importación) — *propuesta, sin ejecutar*.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| Microservicios (colocaciones, documentos, evaluaciones, notificaciones…) | Obliga a sagas/consistencia eventual para activación y auditoría; costo operativo (despliegue, observabilidad, contratos) desproporcionado para el volumen y el equipo |
| Monolito en capas sin fronteras de módulo | El más rápido, pero degrada a "bola de lodo"; sin forma de proteger C-06 de accesos directos |
| Funciones serverless por caso de uso | Transacciones multi-paso y bloqueos de fila se complican; dependencia de plataforma no justificada |
| **Monolito modular + worker (elegida)** | Consistencia local, despliegue simple, fronteras explícitas para evolucionar |

## Rationale
- **Consistencia:** los guards y la auditoría se resuelven con una transacción local (ADR-003/005). Con servicios separados habría que coordinar estado y auditoría de forma distribuida.
- **Volumen:** ~900 colocaciones/año no exige escalado horizontal; lo difícil es la *concurrencia sobre un mismo agregado* (AD-07 degradado), no el caudal.
- **Equipo y semestre:** menos piezas que operar y depurar.
- **Remoto/híbrido (RNF):** una SPA y una API alcanzan; no hay requisito de operación offline.

## Consequences
Una sola unidad de despliegue y versión. El worker escala por separado en procesos, aunque comparta código. Los módulos pueden extraerse más adelante si sus fronteras se respetan.

## What gets worse / trade-offs
- Sin escalado ni despliegue independientes por módulo.
- Un defecto grave puede tumbar todo el backend.
- La BD es un único dominio de falla.
- **El acoplamiento accidental es el riesgo principal**; sin verificación automática de fronteras, el diseño modular es solo una convención.
- Extraer un módulo después tiene costo (datos compartidos, transacciones cruzadas).

## Verification
- **Ejecutado (PoC, sandbox):** solo lo que depende de esta decisión a nivel de BD — transacciones locales con bloqueo y auditoría atómica (T-01, T-02, T-05).
- **NOT EXECUTED:** verificación de fronteras de módulo, humo de despliegue, QS-05 (pico).

## Reconsider when
Aparecen varios equipos con cadencias distintas; un módulo necesita escalar o tener disponibilidad independiente; llega una integración real con carga o latencia que justifique aislamiento.

## Related requirements
RNF-01, RNF-02, RNF-09, RNF-12 · RF-09, RF-17 (consistencia)

## Related quality scenarios
QS-05, QS-01, QS-06

## Related architecture views
V-CONT, V-COMP, V-DEP
