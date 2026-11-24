# Guion de demostración (video no grabado)

Preparado según los tiempos sugeridos en el PDF de Evaluación 4. **No se grabó ningún video**: el formato final debe confirmarse con el docente (ver `../cambio-e-impacto/condiciones-de-entrega.md`).

| Tiempo | Contenido | Acción en pantalla |
|---|---|---|
| 0:00–0:40 | **Problema:** una práctica puede rotar entre organizaciones o transferirse a mitad de periodo sin fragmentar la práctica académica ni perder historia (CR-05, BR-01 a BR-10). | Mostrar `docs/cambio-e-impacto/solicitud-cr05-y-reglas.md`. |
| 0:40–1:50 | **Arquitectura:** práctica = identidad académica; segmento = tramo operativo. Un solo segmento activo, transferencia atómica, horas aceptadas append-only y autorización por segmento. Mostrar ADR-009 a ADR-013 y el diagrama de estados. | `docs/arquitectura-y-adrs/arquitectura-final.md`, `docs/diagramas-y-trazabilidad/diagramas.md`. |
| 1:50–4:20 | **Software:** lanzar `python scripts/run_eval3_demo.py --open-browser`. Con `s1`, registrar horas con fecha. Con `pc_sys`, aceptar parcialmente y rechazar un duplicado; mostrar reportadas frente a aceptadas. Con `ec1`, transferir el segmento 1 a Org Beta con motivo interno. Con `legal1`, confirmar la condición del destino. Con `ec1`, activarlo y extender su fecha de fin con «Cambiar fecha de fin» (queda en «Cambios de periodo»). Con `ws_alfa`, mostrar que ya no ve la práctica. Con `s1`, mostrar que no ve el motivo interno y que recibió el aviso «Cambió un segmento de la práctica». Con `pc_sys`, abrir Reportes operativos → «Rotaciones y transferencias» y mostrar la transferencia contada. | Navegador. |
| 4:20–5:30 | **Evidencia:** ejecutar `pytest tests/test_cr05_segments.py`, `check_isolated_migrations.py` y `run_isolated_e2e.py --populated` (incluye `rotation.spec.ts`), y mostrar la matriz de trazabilidad y los resultados con fecha y versión. | Terminal + `evidence/test-results-2026-11-23.md`. |

Si la demo poblada no tiene una práctica activa con el usuario esperado, el recorrido de software puede mostrarse con las pruebas automatizadas, que crean exactamente esos estados.
