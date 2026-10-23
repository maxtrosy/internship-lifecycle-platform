# Seguridad y privacidad

> **Estado:** autenticación local y autorización por rol/relación están implementadas en el producto. T-31 cubre credenciales, estado de cuenta, cookie y recuperación; T-20..T-30 cubren rutas y flujos de negocio. No se ha configurado SSO, proveedor de correo, pruebas de penetración ni controles operacionales de producción.

## 1. Autenticación y sesión

| Tema | Decisión / supuesto | Estado |
|---|---|---|
| Cuenta | Inicio de sesión por nombre de usuario o correo y contraseña local | Implementado |
| Credenciales | Argon2id con salt aleatorio; mínimo 12 caracteres; se verifica contra el hash guardado | Implementado |
| Sesión | JWT HS256 de 15 minutos en cookie `HttpOnly`, `SameSite=Strict`; `jti` debe corresponder a una sesión activa en la BD | Implementado |
| Logout / estado | Logout revoca `jti`; cuenta inactiva o sesión expirada/revocada se rechaza en cada solicitud | Implementado |
| CSRF | `Origin` debe estar en `APP_ALLOWED_ORIGINS` para operaciones con cookie; frontend servido por el proxy same-origin | Implementado |
| Roles y relaciones | Nunca viajan en cookie/JWT; se resuelven desde `role_assignment` por solicitud | Implementado |
| Cuentas y roles | Sin registro público; operador con acceso privilegiado aprovisiona. Invitación externa asigna el rol y organización desde el servidor | Implementado |
| Recuperación | Respuesta genérica; token aleatorio de un uso, hash en BD, 30 minutos; todas las sesiones se revocan al cambiar contraseña | Implementado |
| Entrega de recuperación | No hay proveedor de correo; el token solo se devuelve en `APP_ENV=development` con `PASSWORD_RESET_DELIVERY=development-token` | Limitación local |
| Límite de intentos | 10 fallos por identificador/15 min y 60 por IP/15 min; recuperación limitada por solicitud. El contador es por proceso | Demo de un trabajador |
| SSO institucional | No hay IdP, protocolo ni configuración en el RFP/artefactos disponibles | OPEN-21 |

## 2. Principios

1. **Mínimo privilegio:** cada rol ve solo lo necesario para su tarea y para las colocaciones con las que tiene relación.
2. **Denegar por defecto:** toda ruta autenticada declara su acción; T-20 verifica las excepciones explícitas.
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
| S-07 | **Robo de credenciales o abuso de login** | Argon2id, errores genéricos, cookie `HttpOnly`, expiración/revocación de sesión, bloqueo por ventana y validación de `Origin` | T-31; rate limit distribuido pendiente |
| S-12 | **Afirmar que una cuenta local es identidad institucional** | La pantalla y documentación identifican el acceso como local; no hay integración SSO declarada | Revisión documental; OPEN-21 |
| S-08 | **Descarga de documentos ajenos** | La descarga se resuelve por rol y relación con la colocación, no por URL adivinable | T-29 (estudiante y revisor legal permitidos; anfitrión denegado) |
| S-09 | **Repetición/concurrencia de comandos** | Bloqueo de fila; transiciones por estado | T-01, T-02 |
| S-10 | **Datos personales en la auditoría o en registros** | Minimizar contenido; retención sin definir | OPEN |
| S-11 | **Inyección y entradas maliciosas en políticas** | Vocabulario cerrado, sin expresiones (ADR-001) | T-06 |

## 5. Lo que este diseño **no** cubre
Cifrado en reposo y tránsito (se asume HTTPS), gestión de claves, cumplimiento normativo de datos reales, pruebas de penetración y recuperación ante desastres. No aplican a datos sintéticos de un proyecto académico, pero deben revisarse antes de cualquier uso con datos reales.
