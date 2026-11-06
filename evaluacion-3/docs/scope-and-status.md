# Alcance real del incremento

Fecha de corte: 2026-11-05. La clasificación refleja código y pruebas revisados en esta entrega. “Implementado” describe comportamiento del repositorio; no significa adopción institucional ni despliegue productivo.

## Cómo leer los estados

- **Implementado:** existe API/servicio y persistencia del flujo, validado por pruebas.
- **Parcial:** hay parte del flujo, pero falta un proceso institucional o una transición relevante.
- **Simulado:** fixture/autoridad/dato artificial usado solo en PostgreSQL efímero para ejecutar pruebas o la demo; nunca equivale a aprobación real.
- **Diseñado:** aparece en ADR o vistas, pero el código no lo ejecuta todavía.
- **Pendiente:** requiere una decisión/información institucional o trabajo que no está en el incremento.

| Área | Estado | Evidencia / límite |
|---|---|---|
| Oportunidades | Implementado con transiciones | CRUD/consulta y estados DRAFT, IN_REVIEW, APPROVED, PUBLISHED, CLOSED en API/DB. Revisor/publicador se configuran por entorno y por defecto no se autorizan. Las autoridades del E2E son solo para la base temporal. |
| Postulación y elegibilidad | Implementado | La postulación vincula la política persistida y guarda entradas/resultados. El resultado `REQUIRES_REVIEW` queda pendiente; la resolución expresa del coordinador asignado guarda fundamento y auditoría. Las políticas de fixture con créditos/nivel son supuestos sintéticos sustituibles. |
| Selección/aprobación | Implementado con autorización | Selección del anfitrión relacionado; aprobación académica del programa correspondiente. Comprobado en E2E de ciclo y permisos. |
| Documentos/versiones | Implementado en la aplicación | Entregas y revisiones quedan en DB, se pueden volver a enviar/descargar y aparecen en el expediente. Los bytes se almacenan en PostgreSQL; adaptador externo pendiente. |
| Activación/cierre | Compuertas implementadas | Reglas se instancian desde política persistida y servicios de dominio/guardas DB. En el fixture sintético se activa y cierra un recorrido; no se infiere regla institucional universal de horas. |
| Supervisión y seguimiento | Implementado | Asignaciones y su historial, plan de trabajo narrativo, actualizaciones del estudiante y evaluación narrativa; scope por rol/relación. Sin fechas límite, notas ni aprobación de horas. |
| Incidentes/cambios | Implementado parcialmente | Registro append-only con estado factual `REPORTED` e historial; no resuelve, escala ni crea una versión formal de la práctica. OPEN-03 sigue pendiente. |
| Horas | Implementado | El titular registra horas cuando el estado lo permite; el expediente permite lectura histórica tras cierre. No existe aprobación de horas ni interpretación institucional de un mínimo salvo política/configuración persistida de demo. |
| Evidencia final | Implementado | Artefacto PDF sintético almacenado con versiones; cierre valida los requisitos persistidos. No equivale a aprobación académica. |
| Notificaciones | Implementado en bandeja interna | Persistencia, destinatarios por relación y marcar leído; no hay email/worker ni recordatorios programados. |
| Mensajería | Implementado por expediente | Canales compartido y académico separados con lectura/escritura por relación; no es chat genérico ni está conectado a email. |
| Reportes | Implementado en alcance acotado | Consultas agregadas con filtros respaldados por el modelo y acceso limitado. No incluyen evaluación individual ni datos sintéticos falsamente presentados como datos reales. |
| Autenticación | Implementado localmente | Cookie de sesión y credenciales locales; no es SSO universitario. OPEN-21. |
| Decisiones institutionales | Pendientes | Autoridad final de publicación, políticas reales de elegibilidad, requisitos de documentos/horas/cierre, evaluación puntuable, tratamiento de cambios y alcance legal deben definirse por institución. |
| Integraciones, worker y RLS | Diseñado, no implementado | ADR-006 dibuja puertos/adaptadores; no hay integración real SIS/IdP/repositorio documental/calendario/email, worker ni RLS. Performance institucional y estudio de usabilidad con participantes también pendientes. |

## Incremento seleccionado

El incremento ejecutable sigue un caso desde oportunidad y postulación hasta expediente de práctica y cierre con evidencia. Incluye el caso inválido de aplicación sin política/eligibilidad y el de cierre incompleto, además de decisiones/manual review con relación autorizada. El camino de éxito completo se ejercitó en el flujo E2E de actores; los E2E con fixture poblado comprueban lectura/recarga, registros existentes, límites de escritura tras cierre y visibilidad cruzada.

El fixture de demo puede usar un valor de 100 horas y perfiles sintéticos. Eso es una entrada de prueba/requisito de política de demo, no una regla institucional. Los flujos no inventan aprobación humana en producción: los tests ejecutan la acción real bajo un usuario sintético autorizado, y la demo interactiva se identifica como temporal.

## Estado Neon separado

No se ejecutó consulta ni escritura a Neon para esta evaluación. El estado de Neon que se menciona en README es un antecedente de solo lectura y está fechado/limitado en `neon-status.md`; no es evidencia generada en esta corrida.
