> **Nota (2026-11-20):** documento histórico del incremento 0015 preparado antes de disponer de la solicitud oficial de Evaluación 4. La afirmación de que "no se encontró un documento de Evaluación 4" quedó superada: CR-05 está documentado en `../cambio-e-impacto/`. Se conserva sin otros cambios.

# Evaluación 4 — Incremento de trazabilidad versionada

Este incremento añade contexto de versión aprobado a los registros que ocurren después de la activación de una práctica. No modifica el contenido histórico existente: las filas anteriores a la migración `0015` conservan `NULL` porque el sistema no inventa qué versión estaba vigente.

## Alcance implementado

- Migración Alembic `0015_lifecycle_version_context`.
- `placement_version_id` nullable en horas, avances, plan de trabajo, evaluaciones, incidentes y evidencia final.
- Restricción transaccional: una nueva fila solo puede apuntar a la versión aprobada y vigente de su práctica.
- Proyecciones del expediente con `version_no` cuando el contexto está disponible.
- Auditoría con el identificador de la versión vigente en los eventos de seguimiento.
- Pruebas de migración desde `0001` y desde `0010`, regresión backend, frontend y E2E aislado.

## Fuentes oficiales y límites

No se encontró en el repositorio ni en `Downloads` un documento independiente denominado Evaluación 4 o una solicitud de cambio formal adicional. Por eso este paquete documenta únicamente el incremento verificable que responde a la necesidad explícita de reconstruir el seguimiento por versión. No se presentan funcionalidades no respaldadas como requisitos oficiales.

OPEN-03 (autoridad institucional para aprobar cambios versionados) permanece pendiente.

## Reproducibilidad

Desde la raíz del repositorio:

```powershell
$env:PYTHONPATH=(Resolve-Path '.').Path + ';' + (Resolve-Path 'backend').Path
python scripts/check_isolated_migrations.py
cd backend
python -m pytest -q tests
cd ../frontend
pnpm run test
pnpm run build
```

Para E2E se utiliza `python scripts/run_isolated_e2e.py --populated`, que crea PostgreSQL temporal y lo limpia al terminar. No se utiliza Neon ni una base local persistente.
