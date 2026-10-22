# Prototype — PoC de compuertas y autorización (DH-05)

Paquete **independiente** (no es el repositorio del equipo ni el producto). Ejercita sobre PostgreSQL real: compuertas de activación y cierre, concurrencia, autorización por relación, versionado y auditoría append-only. Solo datos sintéticos.

```bash
pip install pgserver "psycopg[binary]"
python tests/run_poc.py      # escribe evidence/results.json; POC_TRIALS=100 por defecto
```
- `poc/schema.sql` esquema, triggers y permisos · `poc/lifecycle.py` comandos · `poc/authz.py` autorización · `poc/policy.py` políticas · `poc/seed.py` datos sintéticos
- `tests/run_poc.py` T-01..T-08 + T-16a..e
- `evidence/results.json` corrida 2026-10-22 (14 PASS) · `evidence/results-run1-T03-fixture-scope-failure.json` primera corrida (T-03 falló por fixtures compartidos)
- La corrida 2026-10-22 incluye T-02 (A 55 activación primero / 45 rechazo primero, 0 prohibidos; los conteos de orden varían entre corridas) y T-16a..e; `results.json` es la evidencia.
- Límites: ver `docs/evaluation-2/validation/poc.md`.

## Reproducir en Windows (sin `.pocdeps` versionado)

Usa **Python 3.12**: no hay wheel de `pgserver` para 3.14. Desde `prototype/`:

```powershell
python -m pip install --target .pocdeps pgserver "psycopg[binary]"
$env:PYTHONPATH=(Resolve-Path .pocdeps).Path; python tests\run_poc.py
```

`.pocdeps/` se genera localmente; no hace falta versionarlo.
