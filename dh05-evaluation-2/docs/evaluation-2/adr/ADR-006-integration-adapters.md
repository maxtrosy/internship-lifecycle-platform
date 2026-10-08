# ADR-006 — Adaptadores para integraciones externas (simuladas)

**Status:** propuesta · **Fecha:** 2026-10-08

## Context
El RFP permite simular las integraciones con sistemas estudiantiles, de identidad, documentales y académicos (sec. 7 y 10) y exige operar de forma independiente de otros proyectos. RNF-07, RNF-08, R-002. La auditoría detectó listas de integraciones inconsistentes (AUD-18) y un calendario no respaldado por el RFP (AUD-19).

## Decision
Se definen **puertos** (interfaces del dominio/aplicación) con un **adaptador simulado** por cada uno. Ningún módulo de dominio importa código de adaptador.

| Puerto | Propósito | En el RFP | Estado |
|---|---|---|---|
| `IdentityPort` (IF-ID) | Autenticar y resolver el sujeto | Sí (sec. 7) | Simulado |
| `StudentRecordsPort` (IF-STU) | Programa, nivel, créditos, cursos aprobados para elegibilidad | Sí (estudiantes/académicos) | Simulado |
| `DocumentRepositoryPort` (IF-DOC) | Guardar/recuperar archivos; el sistema conserva solo metadatos, estado y referencia | Sí (documentos) | Simulado |
| `NotificationChannelPort` (IF-NTF) | Entregar notificaciones | No lo nombra; es necesario para RF-15 (**OPEN-15**) | Simulado / interno |
| `CalendarPort` (IF-CAL) | Sincronizar fechas | **No** | **Opcional** (OPEN-10) |

Reglas de fallo:
- **Registros estudiantiles caídos:** la elegibilidad no se puede evaluar → estado explícito de "no evaluada"; **nunca** se asume elegible. Los datos de entrada usados se **guardan** con el resultado.
- **Notificación fallida:** no revierte el comando de negocio; la notificación se persiste (bandeja de salida) y el worker reintenta.
- **Identidad caída:** impide nuevos ingresos; las sesiones vigentes siguen hasta expirar.
- **Repositorio de documentos caído:** se puede registrar el estado, pero no adjuntar archivos; no se aprueba un documento sin referencia válida.
Cada adaptador tiene **pruebas de contrato** compartidas entre el simulado y cualquier implementación futura.

## Alternatives considered
| Alternativa | Evaluación |
|---|---|
| Llamar directamente a los servicios simulados | Acopla el dominio a los simuladores; sustituirlos cuesta |
| Bus/ESB de integración | Desproporcionado: no hay integraciones reales |
| Simular solo en pruebas | No cumple "integraciones simuladas" para la demo y esconde el contrato |
| **Puertos y adaptadores con simuladores (elegida)** | Aislamiento barato y verificable |

## Rationale
Aisla el dominio de lo que el RFP dice que puede simularse, hace explícito el contrato y permite fallar de forma controlada (QS-07).

## Consequences
Más archivos y una capa de traducción. Los simuladores usan datos **sintéticos** (RNF-06) y deben poder fallar a pedido para probar QS-07.

## What gets worse / trade-offs
- Capa adicional que mantener.
- Un simulador demasiado benévolo oculta riesgos reales (R-002): la integración real queda sin probar.
- Guardar entradas de elegibilidad aumenta el volumen de datos personales sintéticos que proteger.

## Verification
- **NOT EXECUTED:** pruebas de contrato, QS-07, verificación de que ningún módulo importa adaptadores.
- **Nota honesta:** el PoC obtuvo el perfil académico desde una tabla local que *representa* los registros estudiantiles; **no** pasó por un puerto.

## Reconsider when
Se confirma una integración real; el calendario pasa a requisito; aparecen más de ~5 integraciones o la necesidad de un bus.

## Related requirements
RNF-07, RNF-08, RF-15 · RFP sec. 7 y 10 · R-002, ASM-005

## Related quality scenarios
QS-07 (apoyo)

## Related architecture views
V-CTX, V-CONT, V-COMP (C-13), V-DEP, [interfaces](../design/interfaces.md)
