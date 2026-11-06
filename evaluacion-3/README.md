# Evaluación 3 — Internship Lifecycle Platform

Entrega de Software Design II basada en el documento de evaluación incluido en [`docs/reference/Evaluacion_3.pdf`](docs/reference/Evaluacion_3.pdf). El paquete presenta un incremento ejecutable y rastreable del ciclo de prácticas; no afirma cubrir el RFP completo. El video no se incluye: el guion y la lista de grabación están en [`video/script.md`](video/script.md) y [`video/demo-checklist.md`](video/demo-checklist.md).

## Fuente y alcance

- `Evaluacion_3.pdf` aporta la rúbrica académica: justificar una arquitectura como construida, demostrar un incremento, enlazar requisito/diseño/código/prueba/evidencia, entregar instrucciones reproducibles y preparar una grabación de 5–6 minutos. La petición del estudiante excluye expresamente grabar o generar ese video; se entrega únicamente el guion y su checklist.
- `Project_5_RFP.pdf` aporta el contexto y los requisitos del producto. No se interpreta como obligación de terminar el RFP completo para esta evaluación: la petición selecciona un incremento significativo, exige distinguir implementado/simulado/diseñado/pendiente y prohíbe inventar reglas institucionales.
- Las restricciones de ejecución de esta entrega (PostgreSQL temporal, sin Neon ni escritura local persistente, sin Docker y sin commit/push) proceden de la petición del estudiante. El paquete documenta su cumplimiento y no las atribuye a los PDF.

## Alcance demostrable

El incremento integra oportunidades, postulación con elegibilidad configurable, revisión manual documentada, selección, aprobación académica, documentos versionados y revisión, activación, responsables, seguimiento narrativo, horas, evaluación narrativa, incidentes/cambios reportados, evidencia final y cierre con requisitos persistidos. Las pruebas recorren el ciclo mediante servicios/API y Chromium; un launcher separa la demo interactiva en PostgreSQL efímero. La elegibilidad, los umbrales y el ciclo de datos sintéticos están identificados como demostración reemplazable, no como política institucional.

La tabla de alcance distingue **implementado**, **datos sintéticos de demostración**, **diseñado sin flujo completo** y **pendiente** en [`docs/scope-and-status.md`](docs/scope-and-status.md). La arquitectura actual, las interfaces, las transiciones y la trazabilidad están bajo [`docs/architecture/`](docs/architecture/) y [`docs/traceability/matrix.md`](docs/traceability/matrix.md). Los ADR originales conservan su carácter de propuestas del equipo; su estado observado se resume en [`docs/adrs/review.md`](docs/adrs/review.md).

## Requisitos

- Windows, macOS o Linux; Python **3.12**, Node.js compatible con pnpm, Corepack/pnpm.
- PostgreSQL temporal provisto por `pgserver` (incluido en dependencias de desarrollo); no requiere Docker, Neon ni base persistente.
- Chromium de Playwright para E2E.
- En Windows, PostgreSQL temporal puede requerir las herramientas/runtime de Visual C++ que requiere `pgserver`.

## Instalar dependencias

Desde la carpeta `src/` del paquete:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".\backend[dev]"
corepack pnpm --dir .\frontend install --frozen-lockfile
corepack pnpm --dir .\frontend exec playwright install chromium
```

En macOS/Linux, sustituir el ejecutable del entorno por `.venv/bin/python` y activar el entorno equivalente. El archivo `src/frontend/pnpm-lock.yaml` fija las dependencias del frontend; `src/backend/pyproject.toml` fija sus rangos compatibles. No se distribuyen `node_modules`, paquetes instalados, secretos ni credenciales.

## Variables y datos de demostración

`run_eval3_demo.py` crea su propia base temporal, establece `DATABASE_URL` solo a esa instancia, genera un secreto de sesión efímero, aplica Alembic hasta `0014`, carga fixtures sintéticas y borra el clúster temporal al salir. Ignora una `DATABASE_URL` heredada. No necesita `.env`.

Para las pruebas, deja `DATABASE_URL` vacía; la suite backend crea un `pgserver` temporal. El E2E y el comprobador de migraciones también crean sus propias bases. Ningún comando de esta guía escribe en Neon, en la base de desarrollo o en Docker.

La contraseña común de demo, `Demo-Only-2026!`, se usa únicamente en cuentas sintéticas de la base temporal. No corresponde a producción ni debe reutilizarse. Las credenciales del paquete no incluyen ningún usuario real.

## Iniciar demo interactiva

Desde `src/`:

```powershell
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'backend')
.\.venv\Scripts\python .\scripts\run_eval3_demo.py --open-browser
```

El comando imprime las URL locales asignadas y los usuarios sintéticos disponibles. Cuentas útiles: `s1` (estudiante), `pc_sys` (coordinación de ING-SIS), `ec1` (coordinación experiencial), `hm_alfa` (organización anfitriona), `ws_alfa` (supervisor laboral), `f1` (supervisor docente) y `legal1` (revisión legal). La demo ofrece login sintético habilitado en esa instancia aislada. Detener con Ctrl+C; al final debe aparecer `TEMPORARY_DATABASE_CLEANED=true`.

## Puertos y salud

Los puertos API y web se asignan dinámicamente para evitar colisiones. La salida informa la dirección del frontend, `/health` y `/ready`. La demo verifica login sintético antes de quedar interactiva. No se requiere un puerto PostgreSQL fijo.

## Ejecutar validaciones

Desde `src/`:

```powershell
$env:DATABASE_URL = ''
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'backend')
.\.venv\Scripts\python -m pytest -q .\backend\tests
corepack pnpm --dir .\frontend run test
corepack pnpm --dir .\frontend run build
.\.venv\Scripts\python .\scripts\check_isolated_migrations.py
.\.venv\Scripts\python .\scripts\run_isolated_e2e.py
.\.venv\Scripts\python .\scripts\run_isolated_e2e.py --populated
```

Resultados exactos de la ejecución del 5 de noviembre de 2026: [`evidence/test-results/2026-11-05.md`](evidence/test-results/2026-11-05.md). El reporte separa pytest (esquema SQL actual), migraciones Alembic (0001→0014 y 0010→head), E2E general y E2E con prácticas relacionadas. Capturas recién generadas y revisadas: [`evidence/screenshots/`](evidence/screenshots/).

## Recorrido recomendado

1. Abrir la demo y revisar roles, navegación y políticas con `pc_sys`. La captura del caso pendiente de revisión manual procede de su E2E específico; la demo base puede tener la cola vacía.
2. Iniciar sesión como `demo_student_07` para ver el expediente sintético cerrado y persistido; recargar para comprobar la lectura.
3. Revisar, como titular, el plan narrativo, avances, horas, documentos/versiones, evidencia final e historial. El formulario de mensaje y la conversación son reales en la demo, pero el expediente cerrado no admite mutaciones de seguimiento.
4. Iniciar sesión como `ws_alfa`, `f1`, `hm_alfa`, `ec1` o `legal1` y observar la proyección según relación. No afirmar que un rol ve información fuera de su alcance.
5. Para ver el estado pendiente de revisión manual, mostrar `evidence/screenshots/01-revision-manual-escritorio.png` y explicar que corresponde al E2E aislado. Para ver transiciones reales y denegaciones, consultar los E2E descritos arriba; no presentar capturas del fixture como si todas las acciones hubieran ocurrido durante la grabación.

## Neon, producción y datos

Neon no se modifica en esta entrega. En el último estado documentado, el proyecto `long-truth-39527618`, rama `main`, tenía 61 cuentas, 10 organizaciones, 16 oportunidades, 0 postulaciones y 0 prácticas; el login `app_dataset_full` no estaba disponible y `app_bootstrap` no contaba con ACL de escritura requerido. Ese estado proviene de la comprobación de solo lectura documentada en [`docs/neon-status.md`](docs/neon-status.md), no de una consulta ejecutada en esta evaluación. El paquete no contiene URI ni contraseñas. El incremento se demuestra con PostgreSQL temporal.

## Límites y riesgos

- Las credenciales institucionales/SSO, autoridad de revisión/publicación, políticas reales de elegibilidad y requisitos de horas/cierre requieren confirmación institucional.
- Evaluaciones son narrativas, sin escala/puntaje institucional. Los incidentes se registran; no se resuelven ni escalan automáticamente. La notificación es una bandeja persistida, sin entrega externa ni worker.
- La evidencia documental del demo se almacena en PostgreSQL; no hay repositorio documental externo.
- El reporte de cambio no implementa un proceso formal de nueva versión y aprobación (OPEN-03). El calendario, sistemas externos, RLS, carga/performance y pruebas con usuarios reales no están completados.
- La aprobación del evaluador y las decisiones institucionales quedan fuera del software de demostración.

Véase [`docs/scope-and-status.md`](docs/scope-and-status.md), [`docs/neon-status.md`](docs/neon-status.md) y el guion para declarar estas divergencias correctamente.
