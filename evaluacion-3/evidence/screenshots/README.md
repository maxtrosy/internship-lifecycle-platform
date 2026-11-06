# Capturas verificadas

Todas las imágenes de esta carpeta se generaron en las ejecuciones Chromium del 2026-11-05 y se inspeccionaron visualmente en esta continuación. No se arrastraron capturas históricas.

| Archivo | Escena / viewport | Qué verifica |
|---|---|---|
| `01-revision-manual-escritorio.png` | Cola de revisión de coordinación, 1280×900 | Estado pendiente, inputs de política, fundamento; captura previa a la decisión. |
| `02-revision-manual-movil-390.png` | Misma cola, 390×844 | Columnas refluídas; sin overflow horizontal; acciones/fundamento legibles. |
| `03-politica-y-auditoria-escritorio.png` | Políticas | Versión, origen y rastro de política demo. |
| `04-expediente-persistido-escritorio.png` | Dossier cerrado, 1280×720, página completa | Relaciones, documentos, versiones, horas, plan, avance, evaluación narrativa, evidencia e historial de ciclo. |
| `05-expediente-persistido-movil-390.png` | Dossier cerrado, 390×844, página completa | Apilado responsive, persistencia visible y controles legibles. |
| `06-expediente-tema-oscuro-escritorio.png` | Dossier cerrado, tema oscuro | Tokens/estados en dark mode. |
| `07-expediente-tema-oscuro-movil-390.png` | Dossier cerrado, tema oscuro, 390×844 | Dark mode responsivo. |

La vista de política y el expediente cerrado muestran **datos de fixture** (incluida una condición de 100 h en la política de cierre sintética), no una regla institucional. Parte de la configuración visible en la tarjeta corresponde a versiones históricas sembradas por el seed y algunas aparecen con autor/motivo histórico no disponible. La prueba E2E hace reload y compara estado/documentos/historial. Para el dashboard por cada rol y rutas adicionales, el runner produjo capturas de escritorio/móvil que se inspeccionaron durante E2E; no se incorporaron todas para mantener el ZIP compacto.
