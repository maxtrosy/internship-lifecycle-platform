# Estado del proyecto

**Fecha de corte:** 2026-10-08. **Regla:** nada se marca como completado si solo fue diseñado.

## Completado
| Qué | Evidencia |
|---|---|
| Artefactos de la Evaluación 1 (Visión y Alcance; Requisitos/Backlog/Riesgos/Criterios; Interesados/Aclaraciones/Supuestos/AS-IS/TO-BE/Pendientes) | Entregados por el equipo (los tres archivos analizados) |
| Auditoría de coherencia de la Evaluación 1 | [`evaluation-1-audit.md`](evaluation-1-audit.md): 34 hallazgos con decisión |
| **Borrador** de la documentación de arquitectura y diseño (este paquete) | Documentos de `docs/evaluation-2/` — **diseño, no implementación** |
| PoC de la rebanada crítica ejecutado por el equipo | `prototype/evidence/results.json`: **14 PASS, 0 FAIL** (2026-10-22; incluye T-02 y T-16a..e) |
| Backend Fase 1 validado (identidad, authz, auditoría, lifecycle) | `backend/`: `pytest` **28 PASS**; `alembic upgrade head` + `app.seed` + `GET /health` OK |
| Incremento oportunidades + postulaciones (Sprint 1) | `backend/app/modules/{opportunities,applications,policies}` + `frontend/` (React+Vite, build OK); T-24/T-25 PASS |

## En progreso
| Qué | Nota |
|---|---|
| Aplicar las correcciones a los artefactos fuente de la Evaluación 1 | Ver EB-01 |
| Decidir el stack y revisar el modelo de dominio de este paquete para adoptarlo como el primero del equipo | OPEN-17; EB-03 |

## No implementado
Producto completo; API HTTP; interfaz web; worker; notificaciones; adaptadores y simuladores como puertos; flujos de oportunidad y postulación; transiciones T1, T3, T5, T6, T9; comunicación; evaluaciones e incidentes; paneles; despliegue.

## No validado
Todas las decisiones con el cliente y con Servicios de TI; los 21 elementos `OPEN`; QS-05, QS-07, QS-08; T-09..T-15; el diseño frente al código real.

## Riesgos (priorizados)

> Se conservan R-001..R-010 de la Evaluación 1 (no se reproducen los no revisados). Los marcados *(actualizado)* o *(nuevo)* cambian en esta evaluación. **Responsables:** roles genéricos como en la Evaluación 1; el equipo debe asignar nombres.

| ID | Riesgo | Prob. | Impacto | Mitigación | Responsable | Estado |
|---|---|---|---|---|---|---|
| R-013 *(nuevo)* | No hay código ni stack elegido: la implementación puede desviarse del diseño, o el modelo (primera versión) tener huecos (OPEN-17) | Media | Media | EB-03: elegir stack, revisar el modelo en equipo y portar el PoC | Líder técnico | Abierto |
| R-017 *(nuevo)* | La evidencia ejecutada no estaba reproducida por el equipo | Alta | Media | EB-04: reejecutar y registrar commit | Líder técnico | Cerrado 2026-10-22: reejecutado por el equipo, 14 PASS, commit `dcda267` |
| R-019 *(nuevo)* | Sprint 4 sobrecargado (55 pts) y habilitadores (auditoría, autorización) demasiado tarde (AUD-24) | Alta | Media | EB-17: re-secuenciar | Gestor de proyecto | Abierto |
| R-009 *(actualizado)* | Exposición de datos a externos; RF-20 sin historia | **Media** (antes Baja) | Alta | US-032, ADR-004; T-03 en el producto | Arquitecto | Abierto; mitigación probada solo en PoC |
| R-014 *(nuevo)* | El vocabulario cerrado resulta insuficiente cuando se descubren las reglas reales | Media | Alta | Validar con coordinadores; reconsiderar ADR-001 | Analista de negocio | Abierto |
| R-015 *(actualizado)* | Documento rechazado tras la activación: hay propuesta (BR-18), pero **no está validada** con el cliente (OPEN-14) | Media | Alta | EB-10: validar la propuesta y definir plazo/excepciones | Product Owner | Abierto; propuesta probada en el PoC (2026-10-22) |
| R-018 *(nuevo)* | Autenticación de usuarios externos sin definir (OPEN-21) | Media | Alta | EB-11 consultar a TI | Arquitecto | Abierto |
| R-011 *(nuevo)* | Carreras en comandos del ciclo de vida | Media | Alta | ADR-003 | Arquitecto | **Mitigación demostrada en el PoC**; falta en el producto |
| R-012 *(nuevo)* | Un endpoint nuevo olvida la autorización | Media | Alta | Prueba que exija acción declarada (no ejecutada) | Líder técnico | Abierto |
| R-016 *(nuevo)* | La lógica del trigger diverge de la política de aplicación o se rompe en migraciones | Baja | Media | Pruebas de contrato app↔BD; revisar en cada migración | Líder técnico | Abierto |
| R-001 *(sin cambio de nivel)* | Reglas por programa desconocidas o cambiantes | — | — | ADR-001 | — | Abierto |
| R-002 *(sin cambio de nivel)* | Integración simulada oculta problemas reales | — | — | ADR-006; contratos | — | Abierto |

## Backlog de la evaluación

| ID | Tarea | Prioridad | Responsable | Dependencia | Estado |
|---|---|---|---|---|---|
| EB-01 | Aplicar correcciones a la Evaluación 1 (ASM-005, CL-004, ASM-009..011, SC-06, división de US-019, enmienda de US-020, prioridades de US-003/US-017, fuente de ASM-003B) | Alta | Analista de negocio | — | Pendiente |
| EB-02 | Agregar US-032..US-036 y SC-13 al backlog y validarlas | Alta | Product Owner | EB-01 | Pendiente |
| EB-03 | Elegir el stack y revisar en equipo `views/domain-model.md` para adoptarlo (o corregirlo) como el modelo oficial | Alta | Líder técnico | — | Propuesta de stack en ADR-007, pendiente de adopción |
| EB-04 | Reejecutar `run_poc.py` y registrar commit y fecha | Alta | Líder técnico | — | Hecho (2026-10-22, commit `dcda267`) |
| EB-05 | Portar las compuertas (ADR-003) con pruebas T-01/T-02 en la tecnología real | Alta | Desarrollo | EB-03 | EXECUTED en `backend/` (28 PASS) |
| EB-06 | Autorización C-02 con matriz de pruebas (ADR-004), **antes** de exponer postulantes a externos | Alta | Desarrollo | EB-03 | EXECUTED en `backend/` (T-03, 28 PASS) |
| EB-07 | Escritor de auditoría atómico (ADR-005), **antes** de la primera aprobación | Alta | Desarrollo | EB-03 | EXECUTED en `backend/` (T-07, 28 PASS) |
| EB-08 | Políticas C-05: 4 condiciones de elegibilidad + activación + finalización | Alta | Desarrollo | EB-03 | Pendiente |
| EB-10 | Validar con el cliente la propuesta para OPEN-14 (BR-18: sigue `Active`, indicador derivado y compuerta de cierre) y definir plazo de corrección y aprobador de excepciones | Alta | Product Owner | — | Propuesta probada en el PoC (2026-10-22) |
| EB-11 | Cerrar OPEN-01, 02, 03, 21 con interesados y TI | Alta | Analista de negocio | — | Pendiente |
| EB-17 | Re-secuenciar sprints con habilitadores primero y reestimar | Alta | Gestor de proyecto | EB-02 | Pendiente |
| EB-09 | Puertos y simuladores con pruebas de contrato (ADR-006) | Media | Desarrollo | EB-03 | Pendiente |
| EB-12 | Variante concurrente de T-04 | Media | Desarrollo | EB-05 | Pendiente |
| EB-13 | Verificación de fronteras de módulo (T-15) | Media | Líder técnico | EB-03 | Pendiente |
| EB-15 | Despliegue de demo y prueba de humo (T-12) | Media | Desarrollo | EB-05 | Pendiente |
| EB-14 | Generador de carga y T-09 | Baja | Desarrollo | EB-05 | Pendiente |
| EB-16 | Prueba de usabilidad (T-13) | Baja | Analista de negocio | UI | Pendiente |

*Fechas: sin asignar; las define el equipo.*

## Propuesta de re-secuenciación (a validar y reestimar)
Sprint 1: identidad simulada (US-031), **autorización (US-032)**, **escritor de auditoría**, registro/publicación y búsqueda, postulación con elegibilidad y políticas mínimas. Sprint 2: selección, aprobación académica, checklist y entrega de documentos, compuerta de activación. Sprint 3: activación, supervisión, horas, cambios. Sprint 4: evaluaciones, finalización/cierre, notificaciones, paneles. **El flujo extremo a extremo debería cerrarse antes del último sprint** y el calendario (US-030) queda opcional.

## Próximos pasos (por prioridad)
1. EB-03: elegir el stack y revisar el modelo en equipo. (EB-04 ya está hecho.)
2. EB-01 y EB-02: corregir y ampliar la Evaluación 1.
3. EB-11 y EB-10: resolver con el cliente OPEN-01/02/03/14/21.
4. EB-06 y EB-07: autorización y auditoría antes de que haya flujos con externos o aprobaciones.
5. EB-05 y EB-08: compuertas y políticas en la tecnología real.
6. Resto del backlog según prioridad.
