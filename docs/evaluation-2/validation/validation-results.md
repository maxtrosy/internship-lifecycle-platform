# Resultados de validación

## Cabecera de evidencia

| Campo | Valor |
|---|---|
| Fecha de ejecución | 2026-10-22 (23:27 UTC, corrida registrada en `results.json`) |
| Ejecutado por | **El equipo**, en Windows 10 (corrida registrada en `results.json`) |
| Commit evaluado | `dcda267` (el PoC es un paquete independiente en `prototype/`) |
| Entorno | Windows 10 · Python 3.12.14 · PostgreSQL 16.2 (`pgserver` 0.1.4) · psycopg 3.3.6 |
| Evidencia cruda | `prototype/evidence/results.json` (corrida 2026-10-22) y `prototype/evidence/results-run1-T03-fixture-scope-failure.json` (primera corrida) |
| Comando | `cd prototype && pip install pgserver "psycopg[binary]" && python tests/run_poc.py` |
| Resumen | **14 PASS, 0 FAIL** (T-01, T-02, T-02b, T-03, T-04, T-05, T-06, T-07, T-08, T-16a..T-16e) |

> **Corrida 2026-10-22.** 14 PASS. T-02 variante A: **55 activación primero / 45 rechazo primero**, 0 prohibidos; control B: **25/40**; variante C: **0/40** con 21 `GATE_VIOLATION`. T-16a..e: PASS. **Los conteos de orden varían entre corridas.**

> **Lectura honesta.** "PASS" significa que *este PoC* se comportó como se diseñó en *esta* base de datos. No demuestra el producto, ni la capa HTTP, ni el rendimiento. No se capturaron pantallas porque no existe interfaz.

## B. Executed

### Corrida 1 y su fallo (se conserva)
La primera ejecución dio **8 PASS y 1 FAIL (T-03)**. **Causa:** T-03 compartía base de datos con otras pruebas, que ya habían creado colocaciones de las mismas organizaciones; los conjuntos esperados (solo 3 colocaciones) no podían coincidir. Fue un **defecto del harness**, no del sistema. **Corrección:** T-03 ahora corre en una base aislada. Se conserva la evidencia del fallo y se informa.

### T-01 — Activación simultánea (corrida 2026-10-22)
| Métrica | Resultado |
|---|---|
| Ensayos (diseño propuesto, con bloqueo) | 100 |
| Con exactamente 1 éxito **y** 1 evento de auditoría | **100/100** (el otro actor recibió `INVALID_TRANSITION`; estado final `ACTIVE`) |
| **Control negativo** (sin bloqueo, pausa inyectada entre verificar y escribir) | **30/30 con activación doble** |

*Hallazgo:* el control demuestra que la prueba **puede** detectar el defecto. También muestra que **el trigger por sí solo no evita ACTIVE→ACTIVE**: lo evita el bloqueo de fila. Por eso ADR-003 exige ambos.

### T-02 — Documento rechazado mientras se activa
| Variante | Ensayos | Resultados prohibidos | Detalle |
|---|---|---|---|
| **A.** Diseño propuesto (bloqueo + trigger) | 100 | **0** | **55 activación primero · 45 rechazo primero** |
| **B.** Control: sin bloqueo y **sin** trigger | 40 | **25** | La prueba detecta la violación |
| **C.** Sin bloqueo, **con** trigger | 40 | **0** | 21 `GATE_VIOLATION` + 19 `ACTIVATION_CONDITIONS_UNMET` |

*Resultado prohibido:* activación confirmada habiendo un rechazo de documento ya registrado antes.
*Hallazgo:* con el bloqueo, la variante A observó **ambos órdenes** y no produjo resultados prohibidos. **Los conteos de orden varían entre corridas**; no deben tratarse como un reparto fijo (en esta corrida, 55/45).

### T-02b — Evitar la aplicación y atomicidad
Dos `UPDATE` directos a `ACTIVE` (uno con 3 requisitos sin aprobar; otro sin aprobación académica) fueron rechazados por la BD (`GATE: 3 mandatory activation requirement(s) not approved`; `GATE: illegal transition PENDING_ACADEMIC_APPROVAL -> ACTIVE`). Un comando denegado por la aplicación agregó **0 filas** de auditoría.

### T-03 — Autorización por rol y relación (base aislada)
66 aserciones sobre 13 sujetos × 3 colocaciones: listados exactos; coincidencia entre lectura directa y listado; **9** denegaciones de externos como "no encontrado" y **11** de internos como "prohibido"; acciones negativas **8/8** denegadas; positivas **5/5** permitidas; la proyección para externos expone **solo** `display_name` y `program_code`.
*Alcance:* funciones de dominio, **sin HTTP**; el rol se guarda como un único valor por usuario.

### T-04 — Cierre con evidencia faltante
| Caso | Resultado |
|---|---|
| Confirmar sin nada | `COMPLETION_EVIDENCE_MISSING` |
| Solo informe | `COMPLETION_EVIDENCE_MISSING` |
| 40 de 100 horas | `COMPLETION_EVIDENCE_MISSING` |
| `UPDATE` directo a `COMPLETED` | `GATE: 1 mandatory completion requirement(s) unsatisfied` |
| Cerrar sin estar completada | `INVALID_TRANSITION` |
| Con toda la evidencia (110 h) | confirmación y cierre `OK` |
| Bandera "satisfecho" forzada con horas insuficientes | `COMPLETION_EVIDENCE_MISSING` (recalculado desde filas) |

**NOT EXECUTED:** retiro concurrente de evidencia durante la confirmación (mismo patrón que T-02).

### T-05 — Cambio posterior a la aprobación
La versión vigente no cambió al proponer; un coordinador de otro programa fue **rechazado** (prohibido); un supervisor de otra organización recibió **no encontrado**; al aprobar, el puntero pasó a v2; v1 permaneció `APPROVED`; la modificación directa del contenido de v1 fue rechazada por el trigger (`IMMUTABLE: placement_version content cannot change`); se registraron `placement.change_proposed` y `placement.version_approved` con ubicación antes/después.
*No cubierto:* estado de la colocación con una versión pendiente y cambios urgentes (OPEN-03).

### T-06 — Cambio de política de elegibilidad
v1 (100 créditos, nivel 6) → estudiante con 105 créditos **ELEGIBLE**; v2 (110) → misma persona **NO ELEGIBLE** con el motivo "credits 105 < 110"; la primera postulación **conserva v1 y su resultado**; 4 condiciones inválidas (script, clave extra, valor inválido, lista vacía) rechazadas; el coordinador de otro programa recibió prohibido; **2** eventos de auditoría de política.
*No cubierto:* latencia de vigencia, reevaluación de postulaciones en curso, vigencias futuras.

### T-07 — Auditoría append-only
Rol de aplicación: `UPDATE` y `DELETE` → *permission denied*. Dueño de la tabla: ambos → `IMMUTABLE: audit_event is append-only`. El evento de activación quedó intacto.
*Límite:* un superusuario puede deshabilitar el trigger (no probado).

### T-08 — Sin horas antes de la activación
`record_hours` en una colocación no activa → `PLACEMENT_NOT_ACTIVE`; 0 filas insertadas.

### T-16a..T-16e — Activación no conforme y cierre (BR-18)
Resultados de la corrida 2026-10-22:

| Prueba | Resultado |
|---|---|
| **T-16a** | PASS. Revocación directa `APPROVED → REJECTED` con la colocación `ACTIVE`: indicador `false` antes · `true` después; la vista SQL también `true`; estado `ACTIVE`; evento `checklist_item.rejected_after_activation`. |
| **T-16b** | PASS. Evidencia de cierre completa (`completion_unmet = []`), indicador `true`, `ACTIVATION_NONCOMPLIANT`, estado `ACTIVE`; control negativo conforme → `OK`. |
| **T-16c** | PASS. `UPDATE` directo a `COMPLETED` rechazado con `GATE: 1 mandatory activation requirement(s) not approved`; control negativo conforme → permitido. |
| **T-16d** | PASS. Indicador `true` tras el rechazo, finalización denegada con `ACTIVATION_NONCOMPLIANT`; tras reentrega y aprobación, indicador `false`, confirmación y cierre `OK`, estado `CLOSED`. |
| **T-16e** | PASS. Revisión desde `REQUIRED` → `INVALID_TRANSITION`, estado y auditoría intactos; control positivo desde `SUBMITTED` → `OK`. |

### Backend — Fase 1 + incremento oportunidades/postulaciones (Executed)

Ejecutado en `backend/` contra PostgreSQL real (pgserver, Python 3.12):

| Ítem | Resultado |
|---|---|
| `pytest` (T-01/T-02/T-02b/T-04/T-08/T-16a..e portados + T-20..T-25) | **28 PASS** |
| `alembic upgrade head` | OK |
| `python -m app.seed` | OK |
| `GET /health` | `{"status":"ok"}` |
| Frontend `tsc -b && vite build` | bundler OK; genera `frontend/dist/` (pnpm advierte build-script de esbuild ignorado). Integración navegador↔API: NOT EXECUTED |

## C. Not executed

| Ítem | Qué falta |
|---|---|
| T-09 Pico (QS-05) | API HTTP, generador de carga, conjunto de datos de 12 000 estudiantes, entorno de demo |
| T-10 Indisponibilidad de adaptadores (QS-07) | Puertos y simuladores con fallo a pedido |
| T-11 Notificaciones y recordatorios | Worker y bandeja de salida |
| T-12 Humo de despliegue | Contenedores y scripts de despliegue |
| T-13 Comprensión de estado (QS-08) | Prototipo de UI y 5 participantes |
| T-14 RLS como defensa en profundidad | Esquema con políticas de fila y evaluación con TI |
| T-15 Fronteras de módulo | Herramienta de reglas de importación en el repositorio del producto, cuando exista |
| T-04 variante concurrente | Un caso análogo a T-02 para `ConfirmCompletion` |
| Integración frontend↔backend en navegador | Levantar `uvicorn` + `vite dev` y recorrer el flujo login→oportunidades→postulación manualmente |
| `docker compose up` | Levantar db + api y comprobar `/health` desde el contenedor |
| Medición de latencias (QS-03, QS-04) | Instrumentación |
| Flujo completo SEQ-01 | Implementación de T1, T3, T5, T6, T9 y de las vistas de oportunidad/postulación |
| Reejecución por el equipo | Correr `run_poc.py` en su entorno y registrar commit |
