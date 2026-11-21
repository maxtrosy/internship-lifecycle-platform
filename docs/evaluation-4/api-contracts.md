# Contratos afectados

Los endpoints existentes conservan sus rutas y permisos. Sus respuestas de lectura agregan contexto cuando está disponible:

- `GET /placements/{id}/hours`
- `GET /placements/{id}/progress-reports`
- `GET /placements/{id}/work-plan`
- `GET /placements/{id}/evaluations`
- `GET /placements/{id}/incidents`
- `GET /placements/{id}/completion-evidence`
- `GET /placements/{id}/dossier`

Cada registro puede incluir:

```json
{
  "placement_version_id": 12,
  "version_no": 2
}
```

Cuando el registro precede a la migración `0015` o se creó fuera del flujo que conoce la versión, ambos valores pueden ser `null`. Esto es intencional y evita reconstrucciones ficticias.

Las operaciones de escritura no reciben `placement_version_id` desde el cliente. El backend lo toma de la versión aprobada vigente dentro de la transacción:

- `POST /placements/{id}/hours`
- `POST /placements/{id}/progress-reports`
- `POST /placements/{id}/work-plan`
- `POST /placements/{id}/evaluations`
- `POST /placements/{id}/incidents`
- `POST /placements/{id}/completion-evidence/FINAL_REPORT`
