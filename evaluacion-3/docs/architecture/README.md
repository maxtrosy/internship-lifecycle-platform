# Arquitectura como construida

Estas vistas describen el código inspeccionado en la revisión del 2026-11-05. El diseño propuesto E2 se conserva en `docs/reference/evaluation-2/` como antecedente y no se presenta como si todas sus decisiones se hubieran implementado. Los ADR de este paquete son copias intactas; su estado como construido se documenta en `docs/adrs/review.md`.

- [Contexto](context.md)
- [Contenedores y despliegue](containers-and-deployment.md)
- [Componentes e interfaces](components-and-interfaces.md)
- [Modelo de datos](data-model.md)
- [Secuencia de extremo a extremo](sequence.md)
- [Estados y transiciones](states.md)

## Resumen técnico

SPA React/TypeScript/Vite → API FastAPI en un proceso modular → PostgreSQL. El backend usa SQL explícito con psycopg 3; Alembic aplica migraciones SQL. Las decisiones de dominio se concentran en servicios y se invocan desde routers. Autenticación local y autorización rol+relación se consultan en la base. No existe un worker, cola externa, proveedor de identidad, almacén documental externo ni sistema institucional conectado.

La demo y Playwright levantan un PostgreSQL efímero. La configuración de despliegue en nube no forma parte de la evidencia E3 de ejecución pública.
