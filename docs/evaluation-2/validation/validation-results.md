# Resultados de validación

## Cabecera de evidencia

| Campo | Valor |
|---|---|
| Fecha de ejecución | 2026-10-08 (07:32 UTC, corrida final) |
| Ejecutado por | **El asistente, en un sandbox aislado, a pedido del equipo.** *No* lo ha vuelto a ejecutar el equipo |
| Commit evaluado | **Ninguno** (el equipo aún no tiene código del producto; el PoC es un paquete independiente en `prototype/`) |
| Entorno | Linux · Python 3.12.3 · PostgreSQL 16.2 (`pgserver` 0.1.4) · psycopg 3.3.6 |
| Evidencia cruda | `prototype/evidence/results.json` (corrida final) y `prototype/evidence/results-run1-T03-fixture-scope-failure.json` (primera corrida) |
| Comando | `cd prototype && pip install pgserver "psycopg[binary]" && python tests/run_poc.py` |
| Resumen | **9 PASS, 0 FAIL** en la corrida final (T-01, T-02, T-02b, T-03, T-04, T-05, T-06, T-07, T-08) |

> **Revisión posterior (2026-10-22).** Se implementaron T-16a..e (BR-18/OPEN-14) y se ajustó el fixture de T-02 (ahora el ítem se marca `SUBMITTED` antes de rechazarlo, porque revisar desde `APPROVED` es `INVALID_TRANSITION`). La ejecución **no se pudo completar** en el entorno del asistente: `initdb` de PostgreSQL falla al crear su token restringido dentro del sandbox y la escalada fue rechazada. Por eso el resumen anterior (**9 PASS**) corresponde a la revisión previa; la revisión actual está **NOT EXECUTED**, `evidence/results.json` no se regeneró y **no se reportan cifras nuevas**.

> **Lectura honesta.** "PASS" significa que *este PoC* se comportó como se diseñó en *esta* base de datos. No demuestra el producto, ni la capa HTTP, ni el rendimiento. No se capturaron pantallas porque no existe interfaz.

## B. Executed

### Corrida 1 y su fallo (se conserva)
La primera ejecución dio **8 PASS y 1 FAIL (T-03)**. **Causa:** T-03 compartía base de datos con otras pruebas, que ya habían creado colocaciones de las mismas organizaciones; los conjuntos esperados (solo 3 colocaciones) no podían coincidir. Fue un **defecto del harness**, no del sistema. **Corrección:** T-03 ahora corre en una base aislada. Se conserva la evidencia del fallo y se informa.

### T-01 — Activación simultánea
| Métrica | Resultado |
|---|---|
| Ensayos (diseño propuesto, con bloqueo) | 100 |
| Con exactamente 1 éxito **y** 1 evento de auditoría | **100/100** (el otro actor recibió `INVALID_TRANSITION`; estado final `ACTIVE`) |
| **Control negativo** (sin bloqueo, pausa inyectada entre verificar y escribir) | **30/30 con activación doble** |

*Hallazgo:* el control demuestra que la prueba **puede** detectar el defecto. También muestra que **el trigger por sí solo no evita ACTIVE→ACTIVE**: lo evita el bloqueo de fila. Por eso ADR-003 exige ambos.

### T-02 — Documento rechazado mientras se activa
| Variante | Ensayos | Resultados prohibidos | Detalle |
|---|---|---|---|
| **A.** Diseño propuesto (bloqueo + trigger) | 100 | **0** | 59 activación primero · 41 rechazo primero (activación denegada) |
| **B.** Control: sin bloqueo y **sin** trigger | 40 | **22** | La prueba detecta la violación |
| **C.** Sin bloqueo, **con** trigger | 40 | **0** | 21 `GATE_VIOLATION` + 19 `ACTIVATION_CONDITIONS_UNMET` |

*Resultado prohibido:* activación confirmada habiendo un rechazo de documento ya registrado antes.
*Hallazgo de diseño (→ OPEN-14):* en las 59 activaciones que ganaron, el documento se rechazó **después**, dejando una colocación `ACTIVE` con un requisito `REJECTED`. El diseño de esa corrida lo permitía y **no definía qué debía pasar**; la revisión 2026-10-22 propone BR-18 (ver nota siguiente).

> **Revisión 2026-10-22 (NOT EXECUTED).** La decisión propuesta está en BR-18/ADR-003. El fixture de T-02 cambió: el ítem se marca `SUBMITTED` antes de la revisión (no hay comando de entrega en el PoC), porque rechazar desde `APPROVED` ahora produce `INVALID_TRANSITION`. Las cifras de la tabla son de la corrida anterior y **no** deben citarse como resultado de esta revisión.

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
| **T-16a..T-16e** (BR-18, revisión 2026-10-22) | Ejecución real del PoC: `initdb`/PostgreSQL no arranca bajo el token restringido del sandbox y la escalada fue rechazada. Las pruebas están implementadas en `run_poc.py` pero **no se ejecutaron**; no hay resultados que reportar |
| Medición de latencias (QS-03, QS-04) | Instrumentación |
| Flujo completo SEQ-01 | Implementación de T1, T3, T5, T6, T9 y de las vistas de oportunidad/postulación |
| Reejecución por el equipo | Correr `run_poc.py` en su entorno y registrar commit |

### T-16a..T-16e — NOT EXECUTED (detalle)

Se implementaron en `prototype/tests/run_poc.py` con el mismo patrón que las pruebas existentes. Qué habría que observar en una corrida real:

| ID | Escenario | Resultado esperado |
|---|---|---|
| T-16a | Rechazar un documento con la colocación `ACTIVE` | Indicador derivado `true`; evento `checklist_item.rejected_after_activation`; estado `ACTIVE` |
| T-16b | `confirm_completion` con indicador `true` y evidencia de cierre completa | `ACTIVATION_NONCOMPLIANT`; control negativo conforme → `OK` |
| T-16c | `UPDATE` directo a `COMPLETED` con indicador `true` | Rechazo de BD con mensaje `GATE`; control negativo conforme → permitido |
| T-16d | Reentrega (fixture) + aprobación + cierre | Indicador `false`; finalización y cierre `OK`; estado `CLOSED` |
| T-16e | Revisar un ítem en `REQUIRED` | `INVALID_TRANSITION`; sin cambios de estado ni auditoría; control positivo desde `SUBMITTED` |

**Motivo exacto del bloqueo:** `initdb` responde `could not create restricted token: error code 87` / `could not re-execute with restricted token` y no inicializa el clúster; la solicitud de ejecución con acceso completo fue rechazada. No se sustituyó PostgreSQL por otra base porque el PoC depende de triggers, `SELECT … FOR UPDATE` y permisos reales.
