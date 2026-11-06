# Guion de video (6:00 máximo estimado; no grabado)

**Objetivo del video:** mostrar un incremento real y su arquitectura como construida, sin hacer pasar fixtures por datos reales ni decisiones pendientes por política oficial. Mantener visible que el entorno es temporal. Referencia de formato/timing: `docs/reference/Evaluacion_3.pdf`; el video no forma parte de este ZIP.

**Preparación para grabar en Mac:** sigue `README-macos-demo.md`, levanta Docker Compose antes de empezar la captura y abre `http://localhost:8080`. El bootstrap debe mostrar la fixture y Alembic 0014. Usa `demo_student_07` para el expediente persistido. La cuenta tiene un expediente cerrado de solo lectura. Para mostrar transiciones, permisos y revisión manual, usa las capturas y resultados E2E citados; no inventes una acción dentro de un caso cerrado.

## 0:00–0:45 — Contexto y alcance

**Pantalla:** portada del README E3 y luego diagrama de contexto.

**Decir:** “Este proyecto convierte una necesidad de trazabilidad del ciclo de prácticas en un incremento comprobable. Me concentro en una práctica desde oportunidad y elegibilidad hasta documentación, activación, seguimiento y cierre. La evaluación no afirma terminar el RFP completo. Las políticas de elegibilidad y el ejemplo de 100 horas son sintéticos y no son reglas aprobadas por la universidad. Voy a demostrar cómo el driver de trazabilidad y control se refleja en decisiones de política, autorización relacional y auditoría, y cómo eso aparece en el software y en las pruebas.”

**Resultado que debe verse:** carpeta `evaluacion-3/`, alcance honesto; no mencionar Neon como entorno de la demo.

## 0:45–2:00 — Arquitectura y ADR

**Pantalla:** `docs/architecture/containers-and-deployment.md`, luego `sequence.md` y `docs/adrs/review.md`.

**Decir:** “La aplicación es una SPA React/TypeScript que habla con una API FastAPI; servicios modulares usan SQL explícito sobre PostgreSQL. Alembic mantiene el esquema. ADR-004 plantea rol más relación; el código vuelve a comprobar titular, programa, organización o asignación docente al consultar. ADR-003 corresponde a gates de activación y cierre; los requisitos se leen de políticas persistidas. ADR-005 separa versiones de auditoría append-only. ADR-006 sigue siendo parcialmente diseño: hoy no hay proveedor externo de documentos, correo, SSO ni worker. Los ADR continúan siendo propuestas del equipo, no políticas institucionales adoptadas.”

**Resultado que debe verse:** diagrama as-built y tabla de ADR; señalar una consecuencia real y un límite (no RLS, no adaptador externo).

## 2:00–4:45 — Demostración funcional

### 2:00–2:35 — Revisión manual

**Pantalla:** `evidence/screenshots/01-revision-manual-escritorio.png` (y, brevemente, la versión móvil). Es una captura del caso pendiente guardada antes de la decisión. Si se abre la demo interactiva, `pc_sys` puede tener la cola vacía; no se inventa un caso para la grabación ni se pulsa un botón de decisión.

**Decir:** “Una política persistida puede dejar una postulación en revisión manual; el coordinador del programa ve su cola y los datos necesarios, y debe guardar fundamento para resolver. Esta captura muestra el caso todavía pendiente. La prueba E2E hace una decisión real en la base efímera, verifica el estado, la notificación y la persistencia. No presento una decisión de fixture como aprobación de una institución.”

### 2:35–3:10 — Aplicación, actores y permisos

**Pantalla:** ejecutar/mostrar log de E2E lifecycle o mostrar listado sintético con `s1`, luego `hm_alfa`, `pc_sys`, `ec1`.

**Decir:** “La prueba Chromium recorre oportunidad en borrador, revisión/publicación bajo autoridades de prueba explícitas, postulación, selección del anfitrión y aprobación académica del programa. La relación limita cada vista. El E2E comprueba también accesos cruzados; no se deja que una organización vea postulaciones de otra.”

### 3:10–4:15 — Expediente e historial

**Pantalla:** iniciar como `demo_student_07`; abrir “Expedientes”; mostrar el expediente cerrado; mostrar responsable docente/laboral, documentos/versiones, plan, avances, evaluación narrativa, evidencia y timeline; recargar.

**Decir:** “El expediente reúne datos persistidos y los proyecta según permisos. Se ven supervisores, una versión de documento, horas registradas, asignación narrativa, avance, evaluación sin nota, el informe de cierre y las acciones auditadas. Recargo y la consulta permanece. El fixture usa nombres y archivos sintéticos. Después del cierre, el historial se puede leer, mientras las escrituras de seguimiento se rechazan.”

### 4:15–4:45 — Viewport móvil

**Pantalla:** cambiar viewport a 390 px o mostrar `05-expediente-persistido-movil-390.png`; alternar tema oscuro.

**Decir:** “La pantalla se probó en 390 píxeles y modo oscuro. Las pruebas verifican que no haya overflow horizontal y la imagen fue revisada, no generada artificialmente.”

## 4:45–6:00 — Pruebas, divergencias y límites

**Pantalla:** `evidence/test-results/2026-11-05.md`; comandos reproducibles; `scope-and-status.md`; `neon-status.md`.

**Decir:** “La corrida de hoy obtuvo 105 pruebas backend aprobadas con una advertencia de deprecación, 40 frontend, build TypeScript/Vite correcto, 18 E2E generales con cuatro escenarios poblados omitidos intencionalmente y ejecutados aparte como cuatro aprobados, más migraciones frescas e incrementales hasta 0014. El launcher migró y arrancó una base temporal, pasó salud/listo/login y la eliminó. Quedan pendientes decisiones institucionales sobre autoridad, reglas reales, evaluación puntuable y cambios formales; también integraciones y validación de carga. Neon no se modificó y este paquete no pretende ser un despliegue público validado.”

**Resultado que debe verse:** resultados con fecha/entorno y límites. Finalizar sin afirmar que el producto completo está terminado.

## Driver → ADR → componente → evidencia (línea narrativa)

| Driver | ADR | Componente/archivo | Demostración o prueba |
|---|---|---|---|
| AD-02 / QS-03: elegibilidad configurable y trazable | ADR-001 | `applications/service.py`, `policies/service.py` | revisión manual E2E; tests de política; capturas 01–03 |
| AD-01: proteger transiciones del ciclo | ADR-003 | `lifecycle/service.py` y guards de DB | E2E de ciclo, cierre incompleto y populated close/reload |
| AD-03 / QS-02: datos visibles por rol/relación | ADR-004 | `authz/service.py`, proyección dossier | matriz HTTP + populated relationship scope |
| AD-04 / QS-04: reconstruir decisiones/cambios | ADR-005 | `audit/service.py`, dossier history | append-only test + timeline del expediente |

## Segmentos de tiempo

| Reloj | Duración |
|---|---:|
| 0:00–0:45 | 0:45 |
| 0:45–2:00 | 1:15 |
| 2:00–4:45 | 2:45 |
| 4:45–6:00 | 1:15 |
| Total máximo | 6:00 |
