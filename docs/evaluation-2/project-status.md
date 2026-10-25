# Estado del proyecto

**Fecha de corte:** 2026-10-25. **Regla:** nada se marca como completado si solo fue diseñado. El resumen y los estados actualizados de esta fecha prevalecen sobre el plan inicial que se conserva más abajo.

La matriz requisito por requisito vigente está en [functional-completeness-matrix.md](functional-completeness-matrix.md). El RFP fuente de ocho páginas ya se contrastó completo; faltan en el repositorio los originales de Evaluación 1 y documentos institucionales que definan OPEN-xx.

## Estado actual de preparación final

### Implementado y validado
- Autenticación local y roles; matriz HTTP de rutas y relaciones con pruebas negativas: `backend/tests/test_http_authorization.py` (T-34).
- Compuerta de activación/rechazo serializada a nivel PostgreSQL mediante migración `0004`; suite backend completa del corte final: 68 pruebas aprobadas.
- Entorno de demostración separado, Alembic hasta `0004`, health check y seed de 14 cuentas sintéticas: [runbook](validation/demo-runbook.md).
- Pruebas frontend del corte final: **8 aprobadas**; `tsc -b && vite build` correcto (48 módulos).
- Flujo E2E Chromium del corte final: **3/3 pruebas**; incluye acceso rápido a cuentas sintéticas, credenciales inválidas/rutas protegidas y el recorrido de roles hasta activación, registro de 4.5 horas y persistencia tras recargar. El alcance sigue limitado a Chromium y a los flujos explícitos de `lifecycle.spec.ts`. Véase [validation-results.md](validation/validation-results.md).
- Rediseño responsive de las vistas existentes: **inspección visual** en escritorio para estudiante, empleador, coordinador, revisor legal y EC; comprobación automatizada de ancho sin desbordamiento en 13 rutas/vistas a 390 px y 320 px. Capturas de comprobación en `frontend/test-results/ui-redesign/` (directorio ignorado por Git); no equivale a E2E de todas las acciones.
- Selección valida ahora que el rango de fechas no esté invertido y que cualquier supervisor laboral indicado pertenezca a la organización anfitriona; pruebas positiva y negativas en `backend/tests/test_selection.py`.
- Estudiante titular puede registrar horas opcionales solo en prácticas `ACTIVE` y consultar su propio total e historial. El backend valida horas finitas y mayores que cero; persistencia tras recarga probada con E2E. No existe aprobación de horas; la obligatoriedad institucional queda pendiente según el RFP.

### Implementado sin E2E
- Las rutas y acciones ya implementadas fuera del recorrido de Chromium no tienen cobertura E2E exhaustiva. Las vistas/acciones de supervisión docente/laboral, actividades, aprobación de reportes, evaluaciones intermedias/finales, incidentes, comunicación y paneles agregados siguen incompletas o no implementadas; el RFP §5 declara incompleto el proceso y §9 presenta estas capacidades como posibles, no especificación definitiva.
- Evidencia final, confirmación académica y cierre permanecen solo en backend.
- El servicio interno para proponer/aprobar versiones tiene pruebas de servicio pero no endpoints HTTP ni vista; depende del alcance/actor de aprobación de OPEN-03.

### Pendiente de decisión institucional
- OPEN-05 (actor y proceso de revisión/publicación); OPEN-13 (cupos); OPEN-19 (prácticas simultáneas); OPEN-01/02/06/09/14/20 (reglas, campos y actores documentales/externos); duplicados tras retiro y selección alternativa.
- Para OPEN-19 siguen abiertas las opciones: bloquear cualquier segunda colocación activa, bloquear solo fechas solapadas o fijar máximo configurable. No se aplica límite automáticamente ni se modificaron registros sintéticos.

### Bloqueado por integración externa
- SSO institucional/IdP, envío real de recuperación por correo y repositorio de documentos externo. No existe configuración de proveedor en el repositorio; no se presentan como integraciones validadas.

## Completado
| Qué | Evidencia |
|---|---|
| Artefactos de la Evaluación 1 (Visión y Alcance; Requisitos/Backlog/Riesgos/Criterios; Interesados/Aclaraciones/Supuestos/AS-IS/TO-BE/Pendientes) | Tres archivos entregados en contexto fueron analizados; sus originales no están incluidos en este repositorio. |
| Auditoría de coherencia de la Evaluación 1 | [`evaluation-1-audit.md`](evaluation-1-audit.md): 34 hallazgos con decisión |
| Documentación de arquitectura y diseño | `docs/evaluation-2/` distingue el diseño acordado, el estado real del demo y los pendientes institucionales |
| PoC de la rebanada crítica ejecutado por el equipo | `prototype/evidence/results.json`: **14 PASS, 0 FAIL** (2026-10-22; incluye T-02 y T-16a..e) |
| Backend Fase 1 (identidad, authz, auditoría, lifecycle) | `backend/`: T-20..T-31; autenticación local con Argon2id, cookie de sesión y recuperación |
| Incremento oportunidades + postulaciones (Sprint 1) | `backend/app/modules/{opportunities,applications,policies}` + frontend React; T-24/T-25 |
| Sprint 2: selección del empleador + aprobación académica | Selección, aprobación/rechazo, relación por programa y auditoría; pruebas T-26/T-27 |
| Frontend UX/UI (shell, dashboard, formularios y vistas por rol) | `frontend/src/{index.css,components,pages}`; build TypeScript/Vite aprobado, 8 pruebas unitarias y E2E Chromium 3/3 en el corte final; rediseño inspeccionado visualmente en roles con vista y viewport sin desbordamiento en 13 vistas a 390/320 px. Acciones exhaustivas, supervisión y browsers adicionales siguen sin E2E |
| Sprint 3: documentos + activación | Archivos PDF/PNG/JPG/DOCX en PostgreSQL (≤10 MB), revisiones con motivo, historial y reentrega; permisos de descarga; activación/cierre por políticas versionadas; vistas de estudiante, revisor legal y EC; T-28..T-30 |
| Políticas EB-08 | UI de coordinación para versiones de elegibilidad, activación y cierre; validadores de vocabulario cerrado; las colocaciones fijan las versiones al aprobarse académicamente |

## En progreso
| Qué | Nota |
|---|---|
| Aplicar las correcciones a los artefactos fuente de la Evaluación 1 | Ver EB-01 |
| Decidir el stack y revisar el modelo de dominio de este paquete para adoptarlo como el primero del equipo | OPEN-17; EB-03 |

## No implementado
Revisión/publicación de oportunidades (OPEN-05); IdP/SSO institucional (OPEN-21); proveedor real de correo para recuperación; reglas institucionales exactas de documentos/evidencia y actores (OPEN-01/02); workers y notificaciones; adaptadores con fallos a pedido; supervisión, evaluaciones, incidentes, mensajes y paneles.

## No validado
Las decisiones institucionales marcadas `OPEN`; QS-05, QS-07, QS-08; T-09..T-11 y T-13..T-15; revisión visual completa y cobertura responsive/E2E de todas las vistas, roles y browsers. T-12 sí pasó según su runbook. Los flujos E2E explícitos están validados en Chromium (T-35/T-37, 3/3 pruebas en la ejecución final). El repositorio de documentos externo y el SSO real no están integrados.

## Riesgos (priorizados)

> Se conservan R-001..R-010 de la Evaluación 1 (no se reproducen los no revisados). Los marcados *(actualizado)* o *(nuevo)* cambian en esta evaluación. **Responsables:** roles genéricos como en la Evaluación 1; el equipo debe asignar nombres.

| ID | Riesgo | Prob. | Impacto | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|
| R-013 *(nuevo)* | No hay código ni stack elegido: la implementación puede desviarse del diseño, o el modelo (primera versión) tener huecos (OPEN-17) | Media | Media | EB-03: elegir stack, revisar el modelo en equipo y portar el PoC | Líder técnico | Abierto |
| R-017 *(nuevo)* | La evidencia ejecutada no estaba reproducida por el equipo | Alta | Media | EB-04: reejecutar y registrar commit | Líder técnico | Cerrado 2026-10-22: reejecutado por el equipo, 14 PASS, commit `dcda267` |
| R-019 *(nuevo)* | Sprint 4 sobrecargado (55 pts) y habilitadores (auditoría, autorización) demasiado tarde (AUD-24) | Alta | Media | EB-17: re-secuenciar | Gestor de proyecto | Abierto |
| R-009 *(actualizado)* | Exposición de datos a externos; RF-20 sin historia | **Media** (antes Baja) | Alta | US-032, ADR-004; matriz HTTP T-34 y negativas cruzadas | Arquitecto | Mitigación implementada y validada en endpoints cubiertos; revisar al agregar rutas y resolver OPEN-06 |
| R-014 *(nuevo)* | El vocabulario cerrado resulta insuficiente cuando se descubren las reglas reales | Media | Alta | Validar con coordinadores; reconsiderar ADR-001 | Analista de negocio | Abierto |
| R-015 *(actualizado)* | Documento rechazado tras la activación: hay propuesta (BR-18), pero **no está validada** con el cliente (OPEN-14) | Media | Alta | EB-10: validar la propuesta y definir plazo/excepciones | Product Owner | Abierto; propuesta probada en el PoC (2026-10-22) |
| R-018 *(nuevo)* | SSO institucional sin proveedor ni configuración (OPEN-21); cuentas locales implementadas como alternativa | Media | Alta | EB-11 consultar a TI | Arquitecto | Abierto: datos de TI pendientes |
| R-011 *(nuevo)* | Carreras en comandos del ciclo de vida | Media | Alta | ADR-003 | Arquitecto | T-01/T-02 y serialización de activación/rechazo verificadas con PostgreSQL; T-04 concurrente pendiente |
| R-012 *(nuevo)* | Un endpoint nuevo olvida la autorización | Media | Alta | Prueba de rutas con acción declarada | Líder técnico | Matriz HTTP T-34 ejecutada; mantener la cobertura en CI |
| R-016 *(nuevo)* | La lógica del trigger diverge de la política de aplicación o se rompe en migraciones | Baja | Media | Pruebas de contrato app↔BD; revisar cada migración | Líder técnico | Migraciones hasta `0004 (head)` aplicadas en demo limpia; suite backend aprobada |
| R-001 *(sin cambio de nivel)* | Reglas por programa desconocidas o cambiantes | — | — | ADR-001 | — | Abierto |
| R-002 *(sin cambio de nivel)* | Integración simulada oculta problemas reales | — | — | ADR-006; contratos | — | Abierto |

## Backlog de la evaluación

| ID | Tarea | Prioridad | Responsable | Dependencia | Estado |
|---|---|---|---|---|---|
| EB-01 | Aplicar correcciones a la Evaluación 1 (ASM-005, CL-004, ASM-009..011, SC-06, división de US-019, enmienda de US-020, prioridades de US-003/US-017, fuente de ASM-003B) | Alta | Analista de negocio | — | Pendiente |
| EB-02 | Agregar US-032..US-036 y SC-13 al backlog y validarlas | Alta | Product Owner | EB-01 | Pendiente |
| EB-03 | Elegir el stack y revisar en equipo `views/domain-model.md` para adoptarlo (o corregirlo) como el modelo oficial | Alta | Líder técnico | — | Propuesta de stack en ADR-007, pendiente de adopción |
| EB-04 | Reejecutar `run_poc.py` y registrar commit y fecha | Alta | Líder técnico | — | Hecho (2026-10-22, commit `dcda267`) |
| EB-05 | Portar las compuertas (ADR-003) con pruebas T-01/T-02 en la tecnología real | Alta | Desarrollo | EB-03 | Ejecutado y cubierto por suite del backend |
| EB-06 | Autorización C-02 con matriz de pruebas (ADR-004), **antes** de exponer postulantes a externos | Alta | Desarrollo | EB-03 | Matriz HTTP T-34 y negativas cruzadas ejecutadas; RLS y cobertura de penetración no incluidas |
| EB-07 | Escritor de auditoría atómico (ADR-005), **antes** de la primera aprobación | Alta | Desarrollo | EB-03 | Ejecutado; eventos de entrega y revisión registran metadatos/motivos, nunca bytes |
| EB-08 | Políticas C-05: 4 condiciones de elegibilidad + activación + finalización | Alta | Desarrollo | EB-03 | Implementado en API/UI con versiones inmutables y binding al aprobar; probar reglas reales y validar listas institucionales sigue OPEN-01/02/04/11 |
| EB-10 | Validar con el cliente la propuesta para OPEN-14 (BR-18: sigue `Active`, indicador derivado y compuerta de cierre) y definir plazo de corrección y aprobador de excepciones | Alta | Product Owner | — | Propuesta probada en el PoC (2026-10-22) |
| EB-11 | Cerrar OPEN-01, 02, 03, 21 con interesados y TI | Alta | Analista de negocio | — | Pendiente |
| EB-17 | Re-secuenciar sprints con habilitadores primero y reestimar | Alta | Gestor de proyecto | EB-02 | Pendiente |
| EB-09 | Puertos y simuladores con pruebas de contrato (ADR-006) | Media | Desarrollo | EB-03 | Pendiente |
| EB-12 | Variante concurrente de T-04 | Media | Desarrollo | EB-05 | Pendiente |
| EB-13 | Verificación de fronteras de módulo (T-15) | Media | Líder técnico | EB-03 | Pendiente |
| EB-15 | Despliegue de demo y prueba de humo (T-12) | Media | Desarrollo | EB-05 | Ejecutado en Compose aislado: migración `0004`, `/health` OK, 14 cuentas seed; runbook reproducible |
| EB-14 | Generador de carga y T-09 | Baja | Desarrollo | EB-05 | Pendiente |
| EB-16 | Prueba de usabilidad (T-13) | Baja | Analista de negocio | UI | Pendiente |

*Fechas: sin asignar; las define el equipo.*

## Propuesta de re-secuenciación (a validar y reestimar)
Plan inicial por sprint (referencia histórica): Sprint 1 proponía identidad, **autorización (US-032)**, auditoría, oportunidades, postulaciones y políticas; DH-05 ahora usa cuentas locales para identidad. Sprint 2 cubría selección, aprobación académica, checklist y documentos; Sprint 3, activación, supervisión, horas y cambios; Sprint 4, evaluaciones, cierre, notificaciones y paneles. **El flujo extremo a extremo debería cerrarse antes del último sprint** y el calendario (US-030) queda opcional.

## Próximos pasos (por prioridad al corte 2026-10-24)
1. Resolver con producto OPEN-05 (revisión/publicación), OPEN-13 (cupos), retiro/repostulación/alternos y OPEN-19 (colocaciones activas simultáneas); no se implementarán reglas hasta su decisión.
2. Resolver con producto/TI OPEN-01/02/06/14/20/21: reglas y actores documentales, campos externos, comportamiento tras activación, proveedor de correo e IdP/SSO.
3. Ampliar la validación de frontend a las demás vistas/roles y tamaños responsive; el E2E actual cubre solo el camino principal Chromium descrito en T-35.
4. Ejecutar T-04 concurrente, QS-05/QS-07/QS-08, T-09..T-15 y validaciones de carga, usabilidad e integración cuando exista el entorno y alcance correspondiente.
5. Mantener EB-01/02/03/09/13/14 como tareas de evaluación/arquitectura aún abiertas; la adopción oficial del stack sigue siendo decisión del equipo.
