# Prototype — PoC de compuertas y autorización (DH-05)

Paquete **independiente** (no es el repositorio del equipo ni el producto). Ejercita sobre PostgreSQL real: compuertas de activación y cierre, concurrencia, autorización por relación, versionado y auditoría append-only. Solo datos sintéticos.

```bash
pip install pgserver "psycopg[binary]"
python tests/run_poc.py      # escribe evidence/results.json; POC_TRIALS=100 por defecto
```
- `poc/schema.sql` esquema, triggers y permisos · `poc/lifecycle.py` comandos · `poc/authz.py` autorización · `poc/policy.py` políticas · `poc/seed.py` datos sintéticos
- `evidence/results.json` corrida final · `evidence/results-run1-T03-fixture-scope-failure.json` primera corrida (T-03 falló por fixtures compartidos)
- Límites: ver `docs/evaluation-2/validation/poc.md`.
