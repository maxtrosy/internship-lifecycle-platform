# Seguridad y privacidad

> **Estado:** diseño. Solo la autorización por relación (T-03), la inmutabilidad de auditoría (T-07) y las compuertas de BD (T-01/T-02/T-04/T-08) se ejercitaron en un PoC de sandbox, **sin capa HTTP**. Todo lo demás es `NOT EXECUTED`.

## 1. Autenticación y sesión

| Tema | Decisión / supuesto | Estado |
|---|---|---|
| Usuarios institucionales | Autentican por el servicio de identidad universitario o un **equivalente simulado** (RFP sec. 7) | Simulado |
| Usuarios externos | El RFP solo exige acceso "controlado y limitado". Propuesta: cuentas **creadas por invitación** de un coordinador, autenticadas en un reino externo simulado | **OPEN-21** |
| Identidad ≠ autorización | El IdP dice *quién*; roles y relaciones son datos de DH-05 (ADR-004) | Propuesta |
| Sesión | Token firmado de corta duración; cambios de rol o relación se reflejan en la siguiente solicitud (se evalúa en cada llamada, no se confía en el token para permisos) | Supuesto |
| Cierre de sesión por cambio de rol | Sin definir | OPEN |

## 2. Principios

1. **Mínimo privilegio:** cada rol ve solo lo necesario para su tarea y para las colocaciones con las que tiene relación.
2. **Denegar por defecto:** toda ruta declara su acción; una ruta sin declaración se rechaza (prueba propuesta, NOT EXECUTED).
3. **No revelar existencia** a externos (404).
4. **Proyección mínima** del estudiante para externos (BR-13).
5. **Separación de funciones:** quien propone no aprueba su propia propuesta (propuesta de diseño; no probada).
6. **Datos sintéticos únicamente** (RNF-06).

## 3. Matriz recurso × actor × acceso × condición

*Leyenda: L = leer · E = escribir/crear · A = aprobar/decidir · — = sin acceso. Toda fila exige además la **relación** indicada. `OPEN` = alcance sin definir.*

| Recurso | Actor | Acceso | Condición (relación) |
|---|---|---|---|
| Oportunidad publicada | Estudiante | L | Programa compatible (filtro informativo) |
| Oportunidad (borrador/revisión) | Anfitrión | L, E | Es de su organización |
| Oportunidad (revisión/publicación) | Coord. aprendizaje experiencial | L, E, A | Institucional (OPEN-05) |
| Postulación + resultado de elegibilidad | Estudiante | L, E | Es la titular |
| Postulación | Anfitrión | L, A (seleccionar) | Oportunidad de su organización; **proyección mínima** del estudiante |
| Postulación | Coord. de programa | L | Estudiante de su programa |
| Perfil académico (créditos, nivel, cursos) | Anfitrión / supervisor del lugar de trabajo | **—** | Nunca |
| Perfil académico | Coord. de programa | L | Estudiante de su programa |
| Colocación y versión vigente | Estudiante | L | Es la titular |
| Colocación | Anfitrión | L | Oportunidad de su organización |
| Colocación | Supervisor del lugar de trabajo | L | Su organización **y** figura en una versión |
| Colocación | Supervisor docente | L | Asignado |
| Colocación | Coord. de programa | L, A (T2, T3, T7, aprobar versión) | Estudiante de su programa |
| Colocación | Coord. aprendizaje experiencial | L, A (T4, T8, T9) | Institucional (OPEN-09) |
| Colocación | Representante legal | L (acotado a acuerdos) | Institucional (OPEN-09) |
| Versión propuesta | Supervisor del lugar de trabajo | E (proponer) | Asignado |
| Checklist y documentos | Estudiante | L, E (entregar) | Titular |
| Checklist y documentos | Representante legal | L, A (revisar) | Institucional (OPEN-09) |
| Checklist y documentos | Anfitrión | L (estado) | Su organización; sin archivos de otros ámbitos |
| Horas y progreso | Estudiante | L, E | Titular y colocación `ACTIVE` |
| Horas y progreso | Supervisor lugar de trabajo / docente | L, A (validar) | Asignado |
| **Evaluaciones** (sensibles) | Quien evalúa | L, E | Es el evaluador asignado |
| Evaluaciones | Estudiante | **OPEN-12** | Titular; ¿cuándo? |
| Evaluaciones | Anfitrión (de otra colocación) | **—** | Nunca |
| Evaluaciones | Coord. de programa / docente asignado | L | Programa / asignación |
| Incidentes | Participantes de la colocación | L, E | Relación con la colocación; visibilidad por tipo: OPEN |
| Mensajes | Participantes de esa colocación | L, E | Participante |
| Historial de auditoría | Roles que leen la colocación | L (filtrado) | Misma relación; **nadie** escribe ni borra por la aplicación |
| Políticas | Coord. de programa | L, E (crear versión) | Su programa (US-036) |
| Políticas | Resto | L (vigentes) o — | Según rol (OPEN-18) |
| Paneles y reportes | Coord. de programa | L | Su programa |
| Paneles y reportes | Coord. aprendizaje experiencial | L | Institucional |
| Paneles y reportes | Externos | **—** | Nunca |
| Notificaciones | Destinatario | L | Es el destinatario |

## 4. Amenazas relevantes (no un modelo exhaustivo)

| ID | Amenaza | Mitigación en el diseño | Evidencia |
|---|---|---|---|
| S-01 | **IDOR / enumeración**: un externo prueba identificadores ajenos | Autorización por relación + 404 | T-03 |
| S-02 | **Fuga por listados o exportaciones** | Consultas filtradas por relación; los reportes usan el mismo alcance | T-03 (listados); exportaciones: NOT EXECUTED |
| S-03 | **Exposición de datos de más** al anfitrión | Proyección mínima; el perfil académico nunca sale | T-03 (2 campos) |
| S-04 | **Escalada**: un actor aprueba algo fuera de su alcance (p. ej. coordinador de otro programa) | Acción exige rol **y** relación | T-03, T-05, T-06 |
| S-05 | **Activar/cerrar saltándose la aplicación** | Trigger de BD | T-02b, T-04 |
| S-06 | **Manipulación de la auditoría** | Permisos + trigger; el superusuario puede deshabilitar el trigger (**riesgo residual**) | T-07 |
| S-07 | **Suplantación en la identidad simulada** | La simulación es una limitación: no representa un IdP real | Limitación declarada |
| S-08 | **Descarga de documentos ajenos** | El acceso al archivo se resuelve por permiso sobre la colocación, no por URL adivinable | NOT EXECUTED |
| S-09 | **Repetición/concurrencia de comandos** | Bloqueo de fila; transiciones por estado | T-01, T-02 |
| S-10 | **Datos personales en la auditoría o en registros** | Minimizar contenido; retención sin definir | OPEN |
| S-11 | **Inyección y entradas maliciosas en políticas** | Vocabulario cerrado, sin expresiones (ADR-001) | T-06 |

## 5. Lo que este diseño **no** cubre
Cifrado en reposo y tránsito (se asume HTTPS), gestión de claves, cumplimiento normativo de datos reales, pruebas de penetración y recuperación ante desastres. No aplican a datos sintéticos de un proyecto académico, pero deben revisarse antes de cualquier uso con datos reales.
