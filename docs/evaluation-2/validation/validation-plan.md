# Plan de validación

Objetivo: demostrar que las decisiones arquitectónicas son razonables, **sin inventar resultados**. Tres estados, siempre separados:

| Estado | Significado |
|---|---|
| **A. Planned** | Lo que queremos probar |
| **B. Executed** | Lo que realmente se corrió, con evidencia reproducible |
| **C. Not executed** | `NOT EXECUTED` + qué falta |

**Cómo se ejecutó B:** `prototype/tests/run_poc.py` contra una instancia real de PostgreSQL. Corridas registradas: **2026-10-08** (9 PASS, asistente, sandbox Linux; en el historial de git) y **2026-10-22** (14 PASS, equipo, Windows 10, PostgreSQL 16.2, Python 3.12). Resultados crudos: `prototype/evidence/results.json`. Detalle en [validation-results.md](validation-results.md); alcance y límites en [poc.md](poc.md). Los conteos de orden de T-02 **varían entre corridas**.

## 1. Catálogo de pruebas

| ID | Objetivo | Setup | Estímulo | Resultado esperado | Resultado real | Estado |
|---|---|---|---|---|---|---|
| **T-01** | Dos actores activan a la vez (QS-01c) | 100 colocaciones en `DocumentationPending` con requisitos aprobados; dos conexiones independientes sincronizadas por barrera | Ambos ejecutan `Activate` | Exactamente 1 éxito, 1 `INVALID_TRANSITION`, 1 evento de auditoría, estado `ACTIVE` | 100/100 cumplen. **Control** sin bloqueo: doble activación en 30/30 | **EXECUTED — PASS** |
| **T-02** | Documento rechazado mientras se activa (QS-01b) | Colocación con un ítem `APPROVED`; activación con pausa inyectada; orden de llegada aleatorio | `Activate` y `Reject` concurrentes | Ningún resultado prohibido: activar habiendo un rechazo ya confirmado | A: 0/100 prohibidos (**55 activación primero, 45 rechazo primero**); B: **25/40**; C: 0/40 (21 `GATE_VIOLATION`). *Los conteos de orden varían entre corridas.* | **EXECUTED — PASS** |
| **T-02b** | Evitar la aplicación (QS-01d) y atomicidad al denegar | Colocación con ítems sin aprobar; y otra sin aprobación académica | `UPDATE … SET state='ACTIVE'` directo; luego comando denegado | La BD rechaza ambos; el comando denegado no escribe auditoría | 2/2 rechazos de BD; 0 filas de auditoría agregadas | **EXECUTED — PASS** |
| **T-03** | Autorización por rol y relación (QS-02) | Base **aislada**: 2 organizaciones, 3 colocaciones, 13 sujetos | Lectura directa, listado y acciones por cada sujeto | Visibilidad exacta; externos reciben "no encontrado"; acciones negativas denegadas; proyección mínima | 66 aserciones sin fallos (ver results) | **EXECUTED — PASS** (1ª corrida: FAIL por fixture compartido, corregido) |
| **T-04** | Cierre con evidencia faltante (QS-06) | Colocación `ACTIVE` con informe final, evaluación final y 100 h requeridas | Confirmar/cerrar con evidencia incompleta; `UPDATE` directo; bandera de horas forzada | Todo denegado hasta cumplir; horas recalculadas desde filas | 8/8 resultados esperados | **EXECUTED — PASS**; **variante concurrente: NOT EXECUTED** |
| **T-05** | Cambio tras la aprobación (QS-04) | Colocación activa con v1 aprobada | Proponer v2, aprobar con actor correcto/incorrecto; intentar modificar v1 | v1 vigente hasta aprobar; actor incorrecto rechazado; v1 intacta; 2 eventos con antes/después | Cumple | **EXECUTED — PASS**; estado de la colocación con versión pendiente: **OPEN-03** |
| **T-06** | Cambio de regla de elegibilidad (QS-03) | Política v1 (100 créditos) y estudiante con 105 | Crear v2 (110); nueva postulación; políticas inválidas; coordinador de otro programa | v1 mantiene su resultado; v2 rechaza con motivo; 4 inválidas rechazadas; ajeno rechazado | Cumple | **EXECUTED — PASS**; latencia de vigencia: **NOT MEASURED** |
| **T-07** | Auditoría append-only (QS-04) | Un evento de activación existente | `UPDATE`/`DELETE` como rol de aplicación y como dueño | Permiso denegado a la aplicación; trigger rechaza al dueño; evento intacto | Cumple | **EXECUTED — PASS**; superusuario deshabilitando trigger: no probado (riesgo residual) |
| **T-08** | Sin horas antes de activar (BR-02) | Colocación `DocumentationPending` | El estudiante registra horas | `PLACEMENT_NOT_ACTIVE`; 0 filas | Cumple | **EXECUTED — PASS** |
| **T-16a** | Rechazo de documento con la colocación `ACTIVE` (BR-18) | Colocación `ACTIVE` con el ítem `APPROVED`; revocación directa | `review_document(REJECTED)` | Indicador derivado `true`; evento `checklist_item.rejected_after_activation`; la colocación sigue `ACTIVE` | PASS (2026-10-22) | **EXECUTED — PASS** |
| **T-16b** | `confirm_completion` con activación no conforme (BR-18) | Colocación no conforme y toda la evidencia de cierre completa | `confirm_completion` | `ACTIVATION_NONCOMPLIANT`; estado sigue `ACTIVE`; control negativo conforme → `OK` | PASS (2026-10-22) | **EXECUTED — PASS** |
| **T-16c** | `UPDATE` directo a `COMPLETED` con activación no conforme (BR-18) | Colocación no conforme con requisitos de cierre instanciados | `UPDATE placement SET state='COMPLETED'` | Rechazo de BD con mensaje `GATE`; control negativo conforme → permitido | PASS (2026-10-22) | **EXECUTED — PASS** |
| **T-16d** | Reentrega y aprobación posteriores (BR-18) | Colocación no conforme con evidencia completa | Reentrega (fixture) + `review_document(APPROVED)` + `confirm_completion` + `close_placement` | Indicador pasa a `false`; finalización y cierre `OK`; estado `CLOSED` | PASS (2026-10-22) | **EXECUTED — PASS** |
| **T-16e** | Revisión de un ítem en `REQUIRED` (BR-14) | Ítem sin entrega (`REQUIRED`) | `review_document(APPROVED)` | `INVALID_TRANSITION`; estado y auditoría intactos; control positivo desde `SUBMITTED` → `OK` | PASS (2026-10-22) | **EXECUTED — PASS** |
| T-09 | Pico de inicio de período (QS-05) | API, worker, BD, 12 000 estudiantes sintéticos, generador de carga | Carga propuesta de QS-05 | p95 lecturas < 800 ms, escrituras < 1 500 ms, errores < 1 %, 0 violaciones | — | **NOT EXECUTED** (sin API ni generador de carga) |
| T-10 | Adaptador caído y contratos (QS-07) | Simuladores con fallo a pedido | Registros estudiantiles caído; notificación caída | Elegibilidad "no evaluada"; notificación en cola y reintentada | — | **NOT EXECUTED** (puertos sin implementar) |
| T-11 | Notificaciones y recordatorios (RF-15) | Worker + bandeja de salida | Plazo próximo/vencido | Notificación creada una vez y entregada | — | **NOT EXECUTED** |
| T-12 | Humo de despliegue (V-DEP) | Contenedores de demo | Levantar, migrar, flujo mínimo | Sistema operativo desde cero | — | **NOT EXECUTED** |
| T-13 | Comprensión de estado (QS-08) | 5 participantes, prototipo de UI | Tareas "¿en qué estado estoy y qué sigue?" | ≥ 4 de 5 aciertos | — | **NOT EXECUTED** |
| T-14 | RLS como defensa en profundidad (ADR-004) | Esquema con políticas de fila | Repetir T-03 por SQL directo | Mismos resultados | — | **NOT EXECUTED** |
| T-15 | Fronteras de módulo (ADR-002) | Herramienta de reglas de importación | Introducir dependencia prohibida | La verificación falla | — | **NOT EXECUTED** |
| **T-20** | Rutas sin acción declarada (R-012) | `backend/app/main.py` + `app.routes` | Enumerar rutas y exigir `requires(action)` en cada una (excepto exentas) | Ninguna ruta sin acción | PASS | **EXECUTED — PASS** |
| **T-21** | Token sin roles / cambio de rol efectivo en la siguiente solicitud (C-01) | `backend/tests/test_identity.py` | Emitir JWT, mutar `role_assignment`, releer sujeto | El token solo lleva `sub`; los roles se leen en BD | PASS | **EXECUTED — PASS** |
| **T-22** | Invitación expirada / reutilizada / de otra organización (OPEN-21) | `backend/tests/test_invitations.py` | Crear/aceptar invitaciones | `INVITATION_EXPIRED`, `INVITATION_USED`; 404 sin relación | PASS | **EXECUTED — PASS** |
| **T-23** | Fronteras de módulo (ADR-002/ADR-007) | chequeo AST en `backend/tests/test_module_boundaries.py` | Importar adaptadores o archivos no públicos entre módulos | El chequeo falla | PASS | **EXECUTED — PASS** |
| **T-24** | Oportunidades: creación y listado por rol/relación (C-03) | `backend/tests/test_opportunities.py` | Crear/listar con `HOST_ORG_MEMBER`, `PROGRAM_COORDINATOR` | Creación permitida/denegada; listado filtrado por relación | PASS | **EXECUTED — PASS** |
| **T-25** | Postulaciones con elegibilidad (C-04/C-05) | `backend/tests/test_applications.py` | Crear política, postular | `ELIGIBLE`/`INELIGIBLE`; `OPPORTUNITY_NOT_PUBLISHED`; `NO_POLICY_IN_EFFECT`; no-estudiante denegado | PASS | **EXECUTED — PASS** |

> **Backend (Fase 1 + incremento):** los tests del PoC T-01, T-02, T-02b, T-04, T-08 y T-16a..e se portaron a `backend/tests/` y se ejecutaron contra el código de `backend/app`; junto con T-20..T-25 dan **28 PASS**. Migración `alembic upgrade head`, `app.seed` y `GET /health` verificados.

## 2. Trazabilidad requisito → prueba

| Prueba | Requisitos | Reglas | QS | ADR |
|---|---|---|---|---|
| T-01, T-02, T-02b | RF-09 | BR-01, BR-07 | QS-01 | ADR-003 |
| T-03 | RF-20, RNF-04 | BR-03, BR-13 | QS-02 | ADR-004 |
| T-04 | RF-17 | BR-05, BR-17 | QS-06 | ADR-003 |
| T-05 | RF-13, RF-19 | BR-04, BR-07 | QS-04 | ADR-005 |
| T-06 | RF-05, RNF-03 | BR-08, BR-12 | QS-03 | ADR-001 |
| T-07 | RF-19, RNF-05 | BR-06 | QS-04 | ADR-005 |
| T-08 | RF-09, RF-11 | BR-02 | QS-01 | ADR-003 |
| T-16a..T-16e | RF-09, RF-17 | BR-14, BR-18 | QS-01, QS-06 | ADR-003 |
| T-20 | RNF-09 | — | — | ADR-007 |
| T-21 | RNF-07, RF-20 | BR-03 | — | ADR-007 |
| T-22 | RF-20 | BR-03, BR-13 | QS-02 | ADR-007 |
| T-23 | RNF-09 | — | — | ADR-002, ADR-007 |
| T-24 | RF-01..RF-04 | BR-03 | QS-02 | ADR-007 |
| T-25 | RF-05, RF-06 | BR-08, BR-12 | QS-03 | ADR-001, ADR-007 |
| T-09 | RNF-02, RNF-12 | — | QS-05 | ADR-002 |
| T-10 | RNF-08 | — | QS-07 | ADR-006 |

## 3. Criterio de "hecho" para pasar un ítem de NOT EXECUTED a EXECUTED
Prueba automatizada reproducible en el repositorio del equipo, registro del commit evaluado, fecha, entorno y resultado crudo, ejecutada por un integrante del equipo.
