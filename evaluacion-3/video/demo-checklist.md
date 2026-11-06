# Checklist de grabación

## Antes de grabar

- [ ] En la carpeta `evaluacion-3/src`, instalar dependencias según README y confirmar Chromium.
- [ ] Ejecutar `python scripts/run_eval3_demo.py --smoke`; verificar 0014, health, ready, login y limpieza.
- [ ] Ejecutar `python scripts/run_isolated_e2e.py` y `python scripts/run_isolated_e2e.py --populated`; conservar la salida real.
- [ ] Iniciar el entorno interactivo con `python scripts/run_eval3_demo.py --open-browser`; usar solo el URL dinámico que imprima.
- [ ] No conectar Neon ni el servicio público. La demo usa una base aleatoria temporal que se borra con Ctrl+C.
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
- [ ] Detener demo con Ctrl+C; verificar `TEMPORARY_DATABASE_CLEANED=true`.

## Después

- [ ] Reproducir el video y comprobar audio legible, ausencia de secretos y duración de 5–6 min.
- [ ] Verificar que cada aserción narrada tenga evidencia en `evidence/test-results/2026-11-05.md` o capturas.
- [ ] Añadir el video únicamente por decisión del estudiante; esta entrega no lo contiene.
