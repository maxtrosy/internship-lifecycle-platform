# Resultados de validación

## Incremento de cierre — ejecución 2026-10-23

Estos resultados corresponden al código actual del repositorio y no sustituyen los registros históricos del PoC que siguen abajo.

| Evidencia | Comando/entorno | Resultado real |
|---|---|---|
| Suite backend, incluye T-31, T-34 y ciclo de vida | `docker compose -p dh05-tests -f backend/docker-compose.test.yml run --rm tests` (PostgreSQL efímero separado, Python 3.12) | **65 passed, 1 warning, 68.75 s**. Advertencia: deprecación del TestClient de Starlette/httpx; sin fallas. El proyecto de test se desmontó después. |
| Foco HTTP y carrera T-02 | `pytest -q tests/test_http_authorization.py tests/test_lifecycle.py -k 'http_authorization_matrix or t02_reject_vs_activate'` | **2 passed, 63 deselected, 1 warning, 29.41 s**. |
| Suite frontend | `pnpm run test` en `frontend/` | **6 passed** en 2 archivos (eligibilidad y etiquetas UI). |
| Compilación frontend | `pnpm run build` | **EXIT 0**: `tsc -b && vite build`; 45 módulos. |
| E2E Chromium (T-35) | `E2E_BASE_URL=http://localhost:5174 pnpm run test:e2e` contra `dh05-demo` limpio | Resultado final asentado tras la corrida reproducible; una corrida previa detectó y permitió corregir selectores del propio test. No se reporta como validado hasta que la última corrida finalice en PASS. |
| Demo limpia (T-12) | `scripts/Start-Demo.ps1 -Reset` con confirmación explícita; `docker-compose.demo.yml` | **PASS**: Compose aislado `dh05-demo`, base `dh05_demo`, volumen `dh05-demo-postgres-data`, Alembic `0004 (head)`, `/health` OK y seed verificó 14 cuentas. Los puertos son 5433/8001/5174 en loopback. |
| Preservación de datos locales | Inspección de destino de Compose/test y script de seed | Pruebas backend usaron DB sin volumen; demo limpia solo usó `dh05-demo`. No se conectó ni se aplicó reset/seed al Compose local existente. No se borraron ni editaron registros del conjunto local. |

La suite del backend prueba autorización a nivel HTTP para cruces de titularidad, organización, supervisor, programa y actores institucionales. La matriz documenta todos los endpoints; E2E cubre un camino principal por los roles incluidos, no cada endpoint ni todos los permisos posibles.

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

> **Lectura honesta.** Los 14 PASS de esta cabecera son del PoC; no demuestran el producto, la capa HTTP ni el rendimiento. Las verificaciones del producto aparecen en su propia sección más abajo. La interfaz del PoC no existe; el frontend del producto se inspeccionó visualmente en un conjunto pequeño de pantallas, sin capturas archivadas.

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

### Backend y demo local — Fase 1 + Sprint 1 + Sprint 2 + Sprint 3 (Executed)

Ejecutado en `backend/` contra PostgreSQL real (pgserver, Python 3.12):

| Ítem | Resultado |
|---|---|
| `pytest -q` (T-01/T-02/T-02b/T-04/T-08/T-16a..e portados + T-20..T-30) | **45 PASS, 2 warnings** (clave JWT de prueba menor a la longitud recomendada) |
| `npm run build` (`tsc -b && vite build`) | EXIT 0; 43 módulos compilados |
| `docker compose up --build -d` | EXIT 0; imágenes de API y frontend reconstruidas |
| Alembic en contenedor | `0002 (head)` |
| `GET /health` | `{"status":"ok"}` |
| Flujo Sprint 3 vía HTTP, datos sintéticos | Política versionada → oportunidad/postulación/selección/aprobación → entrega PDF → revisión con motivo → listo para activar → `ACTIVE`; descarga autorizada validada como `%PDF-1.4` |
| Revisión visual en navegador embebido | Login, panel de políticas y cola del revisor legal inspeccionados a viewport estrecho; no cubre todos los roles/rutas ni el flujo UI completo |

El flujo HTTP añadió registros sintéticos de demo en la base local que ya estaba en ejecución. El comando de seed no se volvió a lanzar sobre esa base.

### Hallazgo local — varias colocaciones activas para un estudiante

Consulta de solo lectura del 2026-10-23: `student1@demo.local` (cuenta sintética `Student One`) tiene dos postulaciones `SELECTED` y dos colocaciones `ACTIVE`: `Pasantia Demo` (postulación 1 / colocación 1) y `HTTP smoke — Synthetic Internship` (postulación 3 / colocación 2). La bitácora registra selección, aprobación académica y activación para ambas. La segunda está identificada explícitamente como flujo HTTP de smoke; ambas pertenecen al conjunto de datos sintéticos de desarrollo. No se borró ni modificó ningún registro.

El esquema solo hace único `placement.application_id`; no impone unicidad por estudiante. `select_application` bloquea la postulación seleccionada, sin consultar ni bloquear otras postulaciones/colocaciones de ese estudiante, y cada activación evalúa una colocación individual. Por tanto, el backend actualmente permite que más de una colocación del mismo estudiante llegue a `ACTIVE`, incluso mediante selecciones concurrentes sobre postulaciones diferentes.

No hay una regla aprobada que limite a una las colocaciones activas por estudiante. BR-10 deja abierto el tope de cupos y OPEN-19 indica que no hay respaldo para bloquear conflictos entre colocaciones. La política de simultaneidad —incluido si se bloquean todas las prácticas activas o solo periodos de fechas solapados— requiere definición de producto antes de añadir una restricción. Este hallazgo no cambia la base de datos.

## C. Not executed

| Ítem | Qué falta |
|---|---|
| T-09 Pico (QS-05) | API HTTP, generador de carga, conjunto de datos de 12 000 estudiantes, entorno de demo |
| T-10 Indisponibilidad de adaptadores (QS-07) | Puertos y simuladores con fallo a pedido |
| T-11 Notificaciones y recordatorios | Worker y bandeja de salida |
| T-12 Humo de despliegue | **Parcial:** Compose inicia con éxito, Alembic está en `0002` y `/health` responde. Falta repetir sobre una base limpia y comprobar el recorrido completo desde cero. |
| T-13 Comprensión de estado (QS-08) | Prototipo de UI y 5 participantes |
| T-14 RLS como defensa en profundidad | Esquema con políticas de fila y evaluación con TI |
| T-15 Fronteras de módulo | Herramienta de reglas de importación en el repositorio del producto, cuando exista |
| T-04 variante concurrente | Un caso análogo a T-02 para `ConfirmCompletion` |
| Integración frontend↔backend en navegador | La revisión visual fue parcial; falta recorrer el flujo completo desde login hasta cierre en UI y todos los roles. |
| Medición de latencias (QS-03, QS-04) | Instrumentación |
| Flujo completo SEQ-01 | Implementación de T1, T3, T5, T6, T9 y de las vistas de oportunidad/postulación |
| Integración institucional | Proveedor de documentos, IdP y políticas reales aún sin conectar/validar |
