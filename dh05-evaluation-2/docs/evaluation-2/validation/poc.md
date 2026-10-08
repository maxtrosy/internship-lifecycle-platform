# Prueba de concepto (PoC)

## Qué riesgo ataca
El riesgo arquitectónico más importante: **¿se puede garantizar que una colocación no se active ni se cierre con requisitos pendientes, incluso con actores concurrentes y accesos que evitan la aplicación, y que el acceso dependa de la relación y no solo del rol?** (AD-01, AD-03; QS-01, QS-02, QS-06).

## Qué se construyó
Un paquete independiente en `prototype/` (**no** es el repositorio del equipo y **no** es el producto):

| Pieza | Contenido |
|---|---|
| `poc/schema.sql` | Esquema mínimo + **triggers** (compuerta de estado, horas solo con colocación activa, inmutabilidad de versiones y auditoría) + permisos |
| `poc/lifecycle.py` | Comandos: aprobación académica, revisión de documento, activación, evidencia, horas, finalización, cierre, propuesta y aprobación de versión; cada uno = 1 transacción + bloqueo + auditoría |
| `poc/authz.py` | Autorización por rol **y** relación; listados filtrados; proyección mínima |
| `poc/policy.py` | Vocabulario cerrado de 4 condiciones; versionado; evaluación |
| `tests/run_poc.py` | T-01..T-08 contra **PostgreSQL real**, con **controles negativos** |

## Cómo ejecutarlo
```bash
cd prototype
pip install pgserver "psycopg[binary]"
python tests/run_poc.py          # escribe evidence/results.json
```

## Qué demostró (ver [resultados](validation-results.md))
1. Con bloqueo de fila, **100/100** carreras de activación doble dejaron 1 activación; sin bloqueo, **30/30** duplicaron: la prueba es capaz de fallar.
2. Rechazo de documento concurrente con activación: **0/100** resultados prohibidos con el diseño; **22/40** sin protección; **0/40** con solo el trigger.
3. El trigger **solo** no evita la doble activación; el bloqueo **solo** no protege de un acceso directo: se necesitan ambos (ADR-003).
4. 66 aserciones de autorización por relación sin fallos en una base aislada.
5. Versiones e historial inmutables incluso frente al dueño de la tabla.
6. Cambio de política sin cambiar código, con vocabulario cerrado.

## Lo que reveló del diseño (hallazgos)
- **OPEN-14:** se puede rechazar un documento **después** de activar; el diseño no dice qué hacer.
- Para que el trigger sea simple se **materializaron los requisitos**; las condiciones que dependen de cálculo (horas) se **recalculan desde el origen** (T-04 lo prueba con una bandera forzada).
- La primera corrida de T-03 falló por un fixture compartido: la **prueba de autorización exige aislamiento de datos**.

## Límites (léase antes de citar este PoC)
- **No** usa el repositorio, la tecnología ni el `domain-model.md` del equipo (OPEN-17).
- **Sin capa HTTP ni interfaz**: la autorización se probó en funciones de dominio.
- Esquema **simplificado**: un rol por usuario; sin `ApprovalDecision`, mensajes, evaluaciones ni incidentes; oportunidad y postulación son fixtures, no flujos.
- Solo **datos sintéticos**; sin adaptadores (el perfil académico sale de una tabla local).
- Las pausas inyectadas **amplían** las ventanas de carrera para que sean observables: demuestran la corrección del mecanismo, **no** la frecuencia real de las carreras en producción.
- Ejecutado por el asistente en un sandbox; **el equipo debe reejecutarlo**.
- No mide rendimiento (QS-05 sigue `NOT EXECUTED`).
- **Los conteos de orden varían entre corridas** (p. ej. 59/41 activación-primero/rechazo-primero, 22/40, 21 `GATE_VIOLATION`). Lo que debe mantenerse en cualquier corrida: **0 prohibidos en las variantes A y C, y >0 en el control B**, y 100/100 en T-01.

## Estado
`PoC: parcialmente ejecutado (sandbox del asistente)`; reproducible; **pendiente de reejecución y de portar al repositorio real**.
