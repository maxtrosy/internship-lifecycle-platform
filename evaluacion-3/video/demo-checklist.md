# Checklist de grabación

## Antes de grabar

- [ ] En Mac, iniciar Docker Desktop y seguir `README-macos-demo.md`; el primer build necesita Internet y tarda más que los siguientes.
- [ ] Confirmar el log de bootstrap con Alembic 0014, runtime `app_runtime`/`app_user` y conteos sintéticos; abrir `http://localhost:8080`.
- [ ] Si se usa un entorno nativo sin Docker, instalar dependencias en `evaluacion-3/src`, ejecutar `python scripts/run_eval3_demo.py --smoke` y luego `--open-browser`.
- [ ] Las pruebas `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated` son opcionales para mostrar resultados; son bases temporales separadas.
- [ ] No conectar Neon ni el servicio público. Docker usa PostgreSQL en tmpfs; el launcher nativo usa un clúster temporal que borra con Ctrl+C.
- [ ] Cuentas sintéticas: `pc_sys`, `s1`, `demo_student_07`, `hm_alfa`, `ws_alfa`, `f1`, `ec1`, `legal1`; contraseña común solo de prueba `Demo-Only-2026!`.
- [ ] No mostrar secretos de ambiente, `.env`, `.neon`, credenciales reales ni consola con URI de base.
- [ ] Tener lista la captura del expediente móvil, pero declarar si se muestra captura o ventana responsiva en vivo.

## Grabación

- [ ] Seguir los tiempos y texto de `script.md`; total entre 5:00 y 6:00.
- [ ] Mostrar primero alcance y arquitectura as-built.
- [ ] Mostrar la cola pendiente de `pc_sys`; no pulsar los botones de decisión durante la grabación.
- [ ] Describir que las pruebas sí ejecutan una resolución autorizada en base aislada; evitar decir que se aprobó una práctica real.
- [ ] Mostrar expediente de `demo_student_07`, documentos/versiones, plan, avance, horas, evaluación narrativa, evidencia, timeline y reload.
- [ ] Mostrar responsive 390 px y tema oscuro.
- [ ] Mostrar pruebas de esta corrida y una lista concreta de pendientes.
- [ ] Detener la demo Docker con `docker compose -p dh05-eval3-share -f compose.macos.yaml down`; para la opción nativa, Ctrl+C y verificar `TEMPORARY_DATABASE_CLEANED=true`.

## Después

- [ ] Reproducir el video y comprobar audio legible, ausencia de secretos y duración de 5–6 min.
- [ ] Verificar que cada aserción narrada tenga evidencia en `evidence/test-results/2026-11-05.md` o capturas.
- [ ] Añadir el video únicamente por decisión del estudiante; esta entrega no lo contiene.
