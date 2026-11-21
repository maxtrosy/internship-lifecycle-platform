# DH-05 Internship and Practicum Management: Evaluación 4

**Solicitud implementada:** CR-05, prácticas rotativas y transferencias a mitad de práctica (reglas CR-05-BR-01 a BR-10). Este paquete corresponde solo a DH-05; no implementa solicitudes de DH-01 a DH-04.

**Versión de esquema:** Alembic `0016`. **Fecha del paquete:** 2026-11-20. **Datos:** 100 % sintéticos.

## Qué cambió respecto a Evaluación 3

- Una práctica académica puede tener varios **segmentos** (rotaciones o asignaciones). Cada uno tiene organización, unidad, supervisor, fechas, modalidad, responsabilidades, horas esperadas y registros propios.
- Cada segmento necesita sus propias condiciones de habilitación y una activación explícita. Completar un segmento no activa el siguiente.
- **Transferencia atómica:** el segmento de origen queda `TRANSFERRED` sin reescribir sus registros, y el destino nace planificado. Se registran la fecha de efecto, los motivos compartido e interno, el tratamiento del trabajo previo y el aprobador.
- **Terminación anticipada** con motivo y decisión de reconocimiento.
- **Horas reportadas frente a aceptadas:** las revisiones son append-only, la aceptación puede ser parcial, los rechazos se justifican, los duplicados no cuentan dos veces y el total consolidado se calcula entre segmentos. `MIN_HOURS` usa horas aceptadas.
- **Cierre:** además de los requisitos de E3, exige segmentos cerrados, horas revisadas, evaluación final por segmento y, si hubo varios segmentos, una revisión académica de la experiencia combinada.
- **Autorización por segmento:** el supervisor anterior pierde el acceso al terminar su segmento. Los externos ven solo sus segmentos y los motivos internos se ocultan.
- Una práctica de un solo segmento sigue el flujo de E3: el segmento 1 se crea al activar la práctica y se completa al confirmar el cierre.

**Cambios de comportamiento deliberados** (documentados y probados): el cierre exige horas aceptadas, y después del cierre el supervisor anterior recibe `NotFound`.

## Estructura

| Ruta | Contenido |
|---|---|
| `docs/cambio-e-impacto/` | Solicitud y reglas, matriz de impacto, limitaciones y decisiones pendientes, condiciones de entrega |
| `docs/arquitectura-y-adrs/` | Arquitectura final (contexto, contenedores, componentes), modelo de datos, revisión de ADR, ADR-008 a ADR-012 |
| `docs/diagramas-y-trazabilidad/` | Diagramas de estados y secuencia, matriz de trazabilidad (incluye los 18 escenarios), contratos de API, migraciones |
| `docs/operacion/` | Instalación y ejecución, usuarios y datos sintéticos, guion de demostración (sin video) |
| `docs/historial-incremento-0015/` | Documentos del incremento previo (contexto de versión, ADR-008), conservados |
| `src/` | Código fuente completo: `backend/`, `frontend/`, `scripts/` |
| `tests/` | Índice de pruebas y copias de las pruebas CR-05 y de migración |
| `evidence/` | Resultados ejecutados con fecha, versión, entorno y comandos |
| `config/.env.example` | Configuración de ejemplo sin secretos |

## Reproducir en cinco pasos

1. **Identificar:** leer este README y `docs/cambio-e-impacto/solicitud-cr05-y-reglas.md`.
2. **Preparar:** instalar las dependencias de `src/backend` (entorno virtual) y de `src/frontend`.
3. **Adaptar datos:** no hace falta; todo usa PostgreSQL temporal con usuarios sintéticos.
4. **Ejecutar:** `python -m pytest -q tests` (backend), `python scripts/check_isolated_migrations.py`, `npx vitest run --exclude "e2e/**"`, `python scripts/run_isolated_e2e.py`.
5. **Verificar:** comparar con `evidence/test-results-2026-11-20.md`.

Los detalles están en `docs/operacion/instalacion-y-ejecucion.md`.

## Decisiones institucionales pendientes

Quién gestiona segmentos y aprueba transferencias (OPEN-CR05-01), quién acepta horas (OPEN-CR05-02), la simultaneidad de segmentos (03), la resolución de disputas (04), el acceso histórico del supervisor anterior (05) y la evidencia tras una interrupción (06). Las dos autoridades son variables de entorno **vacías por defecto**. Ver `docs/cambio-e-impacto/limitaciones-y-decisiones-pendientes.md`.

## Entrega

El PDF sugiere un ZIP y un video de 5 a 6 minutos; las notas del docente indican que las condiciones de E3 no se presuponen. Se preparó el ZIP y un guion; **no se grabó video** ni se asumieron fechas (ver `docs/cambio-e-impacto/condiciones-de-entrega.md`).
