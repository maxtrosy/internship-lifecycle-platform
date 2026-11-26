# Verificaciones externas pendientes: guiones y listas de control

Estas comprobaciones necesitan personas, herramientas o autorizaciones que el equipo no puede simular. **No se han ejecutado.** Este documento deja preparado cómo hacerlas y qué registrar. Ningún resultado de esta página debe presentarse como obtenido mientras su fila de registro esté vacía.

## 1. Lector de pantalla real

**Herramientas sugeridas:**

- NVDA con Firefox o Chrome en Windows.
- VoiceOver con Safari en macOS o iOS.

**Datos:** usar exclusivamente la demo aislada (`python scripts/run_eval3_demo.py --open-browser`) con sus usuarios sintéticos.

| # | Recorrido | Qué comprobar | Resultado | Persona y fecha |
|---|---|---|---|---|
| 1 | Inicio de sesión con `s1` | Las etiquetas de campo se anuncian, el error de credenciales se anuncia sin mover el foco a otra parte y el enlace de salto al contenido funciona. | | |
| 2 | «Mis documentos» con `s1` | La tabla de requisitos se lee por filas. El requisito «Seguro · segmento 2» y su nota «Habilita el segmento 2» se anuncian. El selector de archivo tiene nombre accesible y el aviso «Documento enviado» se anuncia. | | |
| 3 | «Revisión documental» con `legal1` | El botón «Ver documentos» anuncia si está expandido. El motivo es obligatorio y su error se anuncia. El diálogo de confirmación atrapa el foco y lo devuelve al cerrarse. | | |
| 4 | Expediente con `ec1` | «Ajustar datos», «Cambiar fecha de fin» y «Transferir» abren paneles con título. El foco entra al panel, `Esc` lo cierra y el foco vuelve al botón. Los historiales «Ajustes de datos» y «Cambios de periodo» se leen como listas. | | |
| 5 | Reportes operativos con `pc_sys` | Los filtros tienen etiqueta y las tablas de rotaciones tienen encabezados. El cambio de filtro anuncia la carga o el error. | | |
| 6 | Navegación general | El orden de tabulación es lógico en escritorio y a 390 px, el menú móvil se puede abrir y cerrar con teclado, y ningún control queda sin nombre. | | |

**Registro:** para cada fila, escribir *Cumple*, *Cumple con observaciones* o *No cumple*, con el texto anunciado cuando no coincida. Un defecto se registra como incidencia con el recorrido y el navegador.

## 2. Pruebas con usuarios reales

**Participantes:** al menos una persona por rol: estudiante, coordinación de programa, coordinación de experiencia, revisión legal, supervisión laboral y supervisión docente. Las personas deben aceptar participar según las normas de la institución; el equipo no puede decidir ese procedimiento.

**Tareas sugeridas (5 a 10 minutos cada una, con datos sintéticos):**

1. **Estudiante:** entregar el documento que falta para un segmento y saber si fue aprobado.
2. **Revisión legal:** aprobar una evidencia y luego revocarla con motivo.
3. **Coordinación de experiencia:**
   - ajustar la modalidad de un segmento activo;
   - intentar cambiar su supervisor y entender que se requiere una transferencia;
   - registrar la transferencia.
4. **Coordinación de programa:** aceptar horas y leer en el reporte de rotaciones las horas aceptadas frente a las reportadas, filtrando por organización y estado.
5. **Supervisión laboral:** registrar una evaluación final del segmento propio y comprobar que no ve segmentos ajenos.

**Medir:**

- éxito o fracaso de cada tarea;
- tiempo;
- errores;
- puntos de duda expresados en voz alta;
- satisfacción en una escala de 1 a 5.

**No medir:** datos personales que no hagan falta.

## 3. Aprobación institucional

- **Decisiones abiertas:** OPEN-CR05-01 a 06 siguen abiertas (ver `docs/cambio-e-impacto/limitaciones-y-decisiones-pendientes.md`).
- **Configuración:** la plataforma deja vacías por defecto las autoridades sensibles (`PLACEMENT_SEGMENT_MANAGER_ROLES`, `PLACEMENT_HOURS_REVIEWER_ROLES` y las de oportunidades y asignación docente). Sus valores deben venir de una decisión de Horizon University.
- **Valores de prueba:** los valores usados en pruebas y en la demo están en los scripts aislados y no son una política institucional.

## 4. Identidad visual oficial

- No hay logotipos, escudos, colores ni tipografías oficiales de Horizon University en el producto.
- Para incorporarlos hacen falta los archivos oficiales y su manual de uso. Deben reemplazar los tokens de `frontend/src/theme.css` sin crear una paleta paralela.

## 5. Integraciones institucionales reales

- **Correo:** la entrega del restablecimiento de contraseña tiene dos adaptadores, `development-token` y `disabled`. El correo real necesita un proveedor y credenciales de la institución.
- **Documentos:** se guardan en PostgreSQL (`bytea`). Un proveedor externo de almacenamiento solo cambiaría `submit_document` y `get_submission` (ADR-015). Necesita su contrato, su política de retención y sus credenciales.
- **Directorio de usuarios e inicio de sesión institucional:** no integrados. Las cuentas se crean con `backend/app/provision_user.py`.
