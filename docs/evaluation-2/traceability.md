# Trazabilidad

Permite responder **"¿dónde se satisface este requisito?"** y **"¿por qué existe este componente?"**. Solo se incluyen los requisitos arquitectónicamente significativos (ver `architecture-and-design.md` §3).

## D.0 Matriz principal

| Requisito | Escenario de calidad | Driver | ADR | Componente | Vista | Regla | Validación |
|---|---|---|---|---|---|---|---|
| RF-05 | QS-03 | AD-02 | ADR-001 | C-04, C-05 | V-COMP, SEQ-01 | BR-08, BR-12 | **T-06, T-25, T-30** (EXECUTED) |
| RF-06 / RF-07 | QS-01 (precondición) | AD-01 | ADR-003 | C-06 | V-STATE-PLC T1–T3, SEQ-01 | BR-10, BR-11 | **T-26/T-27** (selección y aprobación); T-03 autorización (EXECUTED) |
| RF-08 | QS-01, QS-03 | AD-01, AD-02 | ADR-001, ADR-003 | C-05, C-07 | V-DOM | BR-14 | T-02/T-16e (PoC); T-28 (entrega, revisión y activación), T-29 (revisiones, motivos y descarga) |
| RF-09 | QS-01 | AD-01 | ADR-003 | C-06, C-07 | V-STATE-PLC T4, SEQ-02 | BR-01, BR-02, BR-18 | **T-01, T-02, T-02b, T-08** (EXECUTED); T-16a/b/d (PoC); T-28/T-30 (política y compuerta) |
| RF-13 | QS-04 | AD-04 | ADR-005 | C-06, C-11 | V-DOM, SEQ-03 | BR-04 | **T-05** (EXECUTED) |
| RF-15 | QS-07 | AD-05 | ADR-006 | C-10, C-13 | V-CONT | — | T-11 NOT EXECUTED |
| RF-17 | QS-06 | AD-01 | ADR-003 | C-06, C-08 | V-STATE-PLC T7, T8 | BR-05, BR-17, BR-18 | **T-04** (EXECUTED; variante concurrente NOT EXECUTED); T-16b/c/d (EXECUTED 2026-10-22) |
| RF-18 | (QS-05) | AD-07 | ADR-002 | C-12 | V-COMP | BR-03 | NOT EXECUTED |
| RF-19 | QS-04 | AD-04 | ADR-005 | C-11 | V-DOM | BR-06, BR-07 | **T-05, T-07** (EXECUTED) |
| RF-20 | QS-02 | AD-03 | ADR-004 | C-02 | SEQ-04, [security](design/security.md) | BR-03, BR-13 | **T-03** (EXECUTED, sin HTTP) |
| RNF-01 / RNF-02 | QS-05 | AD-07 | ADR-002 | CT-2, CT-4 | V-CONT, V-DEP | — | T-09 NOT EXECUTED |
| RNF-03 | QS-03 | AD-02 | ADR-001 | C-05 | V-COMP | BR-12 | **T-06** |
| RNF-04 | QS-02 | AD-03 | ADR-004 | C-02 | security | BR-03, BR-13 | **T-03** |
| RNF-05 | QS-04 | AD-04 | ADR-005 | C-11 | V-DOM | BR-06, BR-07 | **T-07** |
| RNF-07 | — | AD-05 | ADR-007 | C-01 | V-CTX | — | **T-31** (autenticación local); SSO institucional OPEN-21 |
| RNF-08 | QS-07 | AD-05 | ADR-006 | C-13 | V-COMP | — | T-10 NOT EXECUTED |
| RNF-09 | — (filtro) | AD-06 | ADR-001, ADR-002 | todos | V-CONT | — | T-15 NOT EXECUTED |
| RNF-11 | QS-08 | — | ADR-003 (estado derivado) | CT-1, C-06 | V-STATE-PLC | — | T-13 NOT EXECUTED |
| RNF-12 | QS-05 | AD-07 | ADR-002 | CT-4 | V-DEP | — | T-09 NOT EXECUTED |

## D.1 Cruce RF ↔ US (propuesto; verificar contra la hoja FR)

> Mapeo **propuesto por esta auditoría** a partir de los títulos y criterios disponibles. Confirmarlo contra el xlsx antes de adoptarlo como oficial. US-010 está retirado.

| RF | US existentes | US propuestas / enmiendas |
|---|---|---|
| RF-01 | US-001, US-002 | — |
| RF-02 | US-002, US-003 | prioridad de US-003 en conflicto (AUD-14) |
| RF-03 | US-004 | — |
| RF-04 | US-005 | — |
| RF-05 | US-006 | **US-036** (gestión de políticas) |
| RF-06 | US-008 | — |
| RF-07 | US-009 | — |
| RF-08 | US-011, US-012 | **US-033** (entrega de documentos) |
| RF-09 | US-013, US-014 | — |
| RF-10 | US-015, US-016 | — |
| RF-11 | US-017 | prioridad a *Must condicional* (AUD-09) |
| RF-12 | US-020 | **enmienda:** incluir al supervisor docente (AUD-04) |
| RF-13 | US-019 | **US-019A** (cambios/versiones) |
| RF-14 | US-019 | **US-019B** (incidentes + resolución) |
| RF-15 | US-024, US-025, US-026 | — |
| RF-16 | US-018 (parcial) | **US-034** |
| RF-17 | US-021, US-022, US-023 | — |
| RF-18 | US-028, US-029 | quitar "conflictos" (AUD-23) |
| RF-19 | US-027 | mover el habilitador de auditoría a antes de la 1ª aprobación (AUD-24) |
| RF-20 | **ninguna** | **US-032** |
| RNF-07 | US-031 | **T-31** (cuentas locales, sesión segura; SSO sigue OPEN-21) |
| RNF-11 | US-007 | — |
| — | US-030 (calendario) | sin RF; OPEN-10 |
| — | — | **US-035** (interrupción/cancelación, OPEN-08) |

## D.2 ADR → Requisitos

| ADR | Requisitos | Escenarios | Drivers |
|---|---|---|---|
| ADR-001 | RF-05, RF-08, RF-17, RNF-03, RNF-09 | QS-03 | AD-02, AD-06 |
| ADR-002 | RNF-01, RNF-02, RNF-09, RNF-12 | QS-05 | AD-01, AD-06, AD-07 |
| ADR-003 | RF-09, RF-17 | QS-01, QS-06 | AD-01 |
| ADR-004 | RF-20, RNF-04, RNF-07 | QS-02 | AD-03 |
| ADR-005 | RF-13, RF-14, RF-19, RNF-05 | QS-04 | AD-04 |
| ADR-006 | RNF-08, RF-15 | QS-07 | AD-05 |

## D.3 Escenario de calidad → Validación

| QS | Pruebas | Estado |
|---|---|---|
| QS-01 | T-01, T-02, T-02b, T-08, T-26..T-28, T-30 | EXECUTED; T-16a/e PoC (2026-10-22) |
| QS-02 | T-03, T-29 | EXECUTED at domain/service level; T-14 NOT EXECUTED |
| QS-03 | T-06, T-25, T-30 | EXECUTED partial (no latency measurement) |
| QS-04 | T-05, T-07 | EXECUTED; latencia de historial NOT EXECUTED |
| QS-05 | T-09 | **NOT EXECUTED** |
| QS-06 | T-04 | EXECUTED; variante concurrente NOT EXECUTED; T-16b/c/d EXECUTED (2026-10-22) |
| QS-07 | T-10 | **NOT EXECUTED** |
| QS-08 | T-13 | **NOT EXECUTED** |

**Backend (ADR-007):** T-31 cubre autenticación, sesión y recuperación local; T-20..T-30 cubren rutas y flujos de negocio. El conteo actualizado, la migración 0003 y la verificación Docker de base limpia se registran en [validation-results.md](validation/validation-results.md).

## D.4 Componente → Responsabilidad y razón de existir

| Componente | Responsabilidad | **¿Por qué existe?** (requisito / driver / ADR) |
|---|---|---|
| C-01 Identidad y sesión | Autenticar cuenta local, emitir y revocar sesión | RNF-07 · AD-05 · ADR-007 |
| C-02 Autorización | Rol + relación, filtrado, proyección | RF-20, RNF-04 · AD-03 · ADR-004 |
| C-03 Oportunidades | Registro, revisión, publicación, búsqueda | RF-01..RF-04 (CRUD/flujo estándar) |
| C-04 Postulaciones y elegibilidad | Postular y evaluar con política | RF-05 · AD-02 · ADR-001 |
| C-05 Configuración de políticas | Versiones validadas con vocabulario cerrado | RNF-03 · AD-02 · ADR-001 |
| C-06 Ciclo de vida | Agregado `Placement`, compuertas, versiones | RF-06..RF-09, RF-13, RF-17 · AD-01, AD-04 · ADR-003, ADR-005 |
| C-07 Checklist y documentos | Instancias de requisitos de activación | RF-08, RF-09 · AD-01 · ADR-003 |
| C-08 Supervisión y evaluación | Plan, avance, horas, evaluaciones, incidentes | RF-10..RF-12, RF-14; evidencia de cierre (RF-17) |
| C-09 Comunicación | Mensajes registrados | RF-16 (alcance mínimo; US-034 propuesta) |
| C-10 Notificaciones | Bandeja de salida y plazos | RF-15 · AD-05 · ADR-006 |
| C-11 Auditoría | Eventos append-only | RF-19, RNF-05 · AD-04 · ADR-005 |
| C-12 Reportes y paneles | Modelos de lectura | RF-18 |
| C-13 Adaptadores | Puertos y simuladores | RNF-08 · AD-05 · ADR-006 |

**Prueba de la cadena inversa (ejemplo).** *¿Por qué existe el trigger de la compuerta?* → RF-09 exige bloquear la activación → AD-01 lo vuelve dominante → ADR-003 pide una red de seguridad además de la guarda → SEQ-02 muestra dónde actúa → BR-01 la formula → **T-02b** la ejercitó (2/2 `UPDATE` directos rechazados).
