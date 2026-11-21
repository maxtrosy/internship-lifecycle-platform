# Dirección visual — "Institucional sobrio"

> **Institutional Corporate University SaaS.** Este documento justifica la dirección visual. Los valores concretos están en `design-system.md`.

## 1. El problema, en una frase

DH-05 se ve hoy como un panel genérico: tarjetas "bento" de esquinas redondeadas, rótulos en mayúsculas sobre cada título, tipografía de 9–11 px y acentos de color por rol. Pero el producto real es otro: **un sistema de expedientes académico-administrativos**, donde cada pantalla responde a tres preguntas:

1. ¿En qué estado está este caso?
2. ¿Qué falta?
3. ¿Quién debe actuar?

La dirección visual parte de ahí: **el expediente y su estado son los protagonistas**, no las tarjetas.

## 2. Sujeto, audiencia y tarea principal

| | |
|---|---|
| **Sujeto** | El ciclo de vida de una práctica profesional: postulación, selección, aprobación académica, documentación, activación, seguimiento por segmentos y cierre. |
| **Audiencia** | Personal universitario que usa el sistema a diario y por periodos largos (coordinaciones, revisión jurídica, supervisión docente). También estudiantes y supervisores externos que entran de forma ocasional y necesitan orientación inmediata. |
| **Tarea principal** | Revisar casos y tomar decisiones auditables con el menor número de errores. |
| **Contexto** | Escritorio en oficina como uso principal. Móvil para consultas y registros puntuales (horas, avances, mensajes). |

## 3. Principios

1. **Estado primero.**
   - Toda vista de registro abre con su estado, lo pendiente y la persona responsable de actuar.
   - El color de estado siempre va acompañado de icono y texto.
2. **Estructura antes que decoración.**
   - La jerarquía se construye con tipografía, alineación, filetes y espacio, no con tarjetas, sombras ni degradados.
   - Una página es un documento con secciones, no un mosaico.
3. **Un solo color institucional.**
   - El color de marca se reserva para la acción principal, la selección y el foco.
   - Los estados usan una paleta semántica separada que no compite con la marca.
4. **Densidad legible.**
   - Las tablas y listas muestran mucha información sin bajar de 12 px.
   - Las cifras usan dígitos tabulares.
   - Los textos largos se limitan a unos 72 caracteres por línea.
5. **Identidad intercambiable.**
   - Nada de la identidad de Horizon University se inventa.
   - La marca vive en un pequeño grupo de tokens (`--brand-*`, logotipo y nombre) que se sustituye cuando haya recursos oficiales.
6. **Honestidad del dominio.**
   - Se conservan los textos actuales, que son precisos ("no representa aprobación académica").
   - El rediseño cambia la presentación, no el significado.

## 4. Proceso aplicado (skill `frontend-design`: planificar, revisar, construir, criticar)

### 4.1 Primer plan (borrador)

- **Color:** azul marino institucional `#1E3A5F`, fondo `#F8FAFC` y acento ocre `#A16207`. Es la propuesta literal de UI/UX Pro Max para "Research Lab / University Department".
- **Tipo:** EB Garamond en títulos y Crimson Text en el cuerpo, la pareja académica que sugiere UI/UX Pro Max.
- **Layout:** sidebar claro, rejilla de tarjetas métricas en el inicio y expediente en mosaico.

### 4.2 Revisión contra el brief y contra los valores por defecto

| Elemento del borrador | Diagnóstico | Revisión |
|---|---|---|
| Azul marino `#1E3A5F` | Es el valor por defecto de "universidad" en cualquier generador, y se confunde con el azul de "información". | Pasa a **petróleo** `#1E4D5C`, un azul verdoso profundo. Sigue siendo institucional y no es el marino genérico. Se separa del verde de "éxito" y del azul de "información". Además, conserva parentesco con el verde actual del producto, lo que facilita la transición. |
| Serif en el cuerpo (Crimson Text) | Pensada para sitios editoriales y de archivo. En tablas densas, formularios y etiquetas de 12–13 px pierde legibilidad. | El cuerpo pasa a **sans humanista con dígitos tabulares** (Source Sans 3). La serif queda **solo en los títulos de página** (Source Serif 4) como única señal académica. |
| Rejilla de métricas en el inicio | "Número grande con etiqueta pequeña" es el tratamiento por defecto que señala `frontend-design`. | El inicio pasa a ser una **bandeja de trabajo**: lista priorizada de casos que esperan la acción del rol. Las cifras quedan en una línea de resumen. |
| Mosaico de tarjetas en el expediente | Es el "kit de tarjetas SaaS": mismo radio, misma sombra y misma importancia para todo. | **Documento con secciones**: cabecera de expediente con secuencia de estados, índice de secciones fijo al hacer scroll y paneles separados por filetes. |
| Rótulos superiores en mayúsculas | Es la "plantilla genérica" más reconocible. | Se eliminan. El contexto lo aportan los **breadcrumbs**. |
| Acento por rol (8 colores) | Fragmenta la identidad. | Se elimina. El rol se indica con un chip de texto en la cabecera. |

### 4.3 El elemento memorable (la única audacia)

Según la skill: *"spend your boldness in one place"*. En DH-05 esa audacia se concentra en dos piezas que comparten un mismo gesto:

1. **Sidebar institucional oscuro.**
   - Fondo tinta-petróleo `#14212A`, marca arriba y navegación por áreas.
   - Enmarca el sistema como herramienta oficial, frente al contenido claro y silencioso.
2. **La secuencia de estados del expediente.**
   - Es una banda horizontal en la cabecera de cada práctica: Postulación → Selección → Aprobación académica → Documentación → Activa → Completada → Cerrada.
   - Marca el paso actual y los cerrados, y muestra las salidas alternativas (Rechazada, Cancelada) como desvío.
   - Usar marcadores numerados se justifica porque el contenido es una secuencia real.
   - Se calcula con `placement.state` y `application.state`, que ya están en el payload del expediente. No se inventa ningún estado.

Todo lo demás se mantiene silencioso: superficies blancas, filetes de 1 px, sin sombras salvo en capas flotantes y sin animaciones decorativas.

## 5. Resultados de UI/UX Pro Max: qué se adopta y qué no

Consultas ejecutadas en local con `search.py` (sin red y sin escribir archivos):

| Consulta | Resultado | Decisión |
|---|---|---|
| `--design-system "university administration platform institutional academic management"` (variance 2, motion 2, density 7) | Estilo **Minimalism & Swiss Style** ("enterprise apps, dashboards, professional tools"), paleta marino y ocre, tipografía EB Garamond y Crimson Text, patrón "Portfolio Grid" y movimiento GSAP | **Se adopta el estilo suizo** (rejilla, filetes, contraste y tipografía como jerarquía). **Se rechazan** el patrón "Portfolio Grid", pensado para portafolios; el movimiento GSAP, que es una dependencia nueva y movimiento decorativo; y la serif en el cuerpo. |
| `--domain product "educational platform"` (repetición tras 0 resultados con "education administration enterprise dashboard") | "Educational App" con **claymorphism**, microinteracciones y "playful colors" | **Se rechaza.** Corresponde a apps de aprendizaje para consumidores, no a un sistema administrativo institucional. No hubo coincidencia en la base para "administración educativa". |
| `--domain color "government institutional trust navy"` | Government/Public Service (marino con azul `#0369A1`) y University Department (marino con ocre) | Se toma la **estructura** de ambas (primario oscuro, fondo frío casi blanco y bordes `#CBD5E1`/`#E2E8F0`), pero no los valores literales. |
| `--domain typography "professional enterprise dashboard legible"` | Plus Jakarta Sans, Fira Sans + Fira Code y **Lexend + Source Sans 3 ("Corporate Trust")** | Se adopta **Source Sans 3** para la UI ("corporate, trustworthy, accessible, readable"). Lexend se descarta por ser geométrica y muy ancha para tablas densas. |
| `--domain ux` (tablas, estado y color) | "Table Handling: horizontal scroll or card layout", "Bulk Actions" y "Color Only: use icons/text in addition to color" | Se adoptan las tablas con alternativa en tarjetas para móvil y el estado con icono y texto. Las acciones masivas quedan como mejora opcional, ya que **la API actual no expone operaciones por lote**. |
| `--stack react "form validation accessible labels"` | `label htmlFor` y consultas por rol en las pruebas | Se adopta. Coincide con el hallazgo A1 de la auditoría. |

## 6. Referencias conceptuales (sin copiar interfaces)

- **Sistemas de gestión académica institucionales:** expediente por estudiante, colas de revisión y trazabilidad de decisiones. Se toma la *organización por casos y responsabilidades*.
- **Sistemas de diseño de administración pública:** formularios de una columna, errores junto al campo y resumen de errores enlazado. Se toma el *rigor de formularios y accesibilidad*. La familia Source Sans procede de ese ámbito de interfaces de uso prolongado.
- **SaaS empresarial de alta calidad:** tablas densas con barra de herramientas, paneles laterales para detalle y breadcrumbs. Se toma la *eficiencia en tareas repetitivas*.

Ninguna interfaz concreta se reproduce, y no se usan marcas, escudos ni nombres de terceros.

## 7. Identidad de Horizon University

- En el repositorio **no hay recursos de identidad**: ni logotipo, ni escudo, ni colores oficiales, ni tipografías licenciadas. La marca actual es una letra "D" en un cuadrado verde (`Layout.tsx:127`).
- **Propuesta neutral:**
  - Un wordmark tipográfico con el nombre del producto ("Prácticas y Pasantías"), en Source Serif 4, y debajo "DH-05".
  - Un espacio reservado de 32×32 px para el escudo oficial, vacío hasta que la universidad lo entregue (sin dibujar un escudo provisional).
  - Los tokens `--brand-50 … --brand-900` en un único bloque.
- **Para personalizar más adelante** basta con sustituir ese bloque de tokens, el wordmark y el `theme-color` de `index.html`. Ningún componente usa un hexadecimal de marca directamente.

## 8. Composición de referencia (wireframes)

**Escritorio, bandeja de trabajo de coordinación experiencial (≥1024 px):**

```
┌────────────┬───────────────────────────────────────────────────────────────┐
│ ▣ Prácticas│ Inicio                                [Avisos 3] [EC1 ▾]       │ ← header 56 px
│   y Pasan- ├───────────────────────────────────────────────────────────────┤
│   tías     │ Bandeja de trabajo                        Coord. de prácticas │ ← h1 serif
│   DH-05    │ 3 prácticas esperan activación · 1 segmento por confirmar     │ ← resumen
│            │                                                               │
│ Trabajo    │ ┌ Requieren tu acción ─────────────────────────────────────┐  │
│  ● Inicio  │ │ Estudiante      Práctica           Pendiente      Acción  │  │ ← tabla
│  Notific.  │ │ Est. Demo 07    Práct. sint. 07    Seguro         Revisar │  │
│ Prácticas  │ │ Est. Demo 08    Práct. sint. 08    Listo ✓        Activar │  │
│  Expedien. │ └──────────────────────────────────────────────────────────┘  │
│  Oportun.  │ ┌ Actividad reciente ───────────┐ ┌ Accesos ─────────────┐  │
│ Operación  │ │ …                              │ │ Reportes operativos  │  │
│  Activación│ └────────────────────────────────┘ └──────────────────────┘  │
│  Reportes  │                                                               │
└────────────┴───────────────────────────────────────────────────────────────┘
  sidebar 264 px oscuro          contenido máx. 1360 px, alineado a la izquierda
```

**Escritorio, expediente:**

```
Inicio / Expedientes / Práctica sintética 04
┌──────────────────────────────────────────────────────────────────────────┐
│ Práctica sintética 04 · activa-con-incidente-y-cambio      [● Activa]    │
│ Estudiante Demo 20 · Centro Horizonte (synthetic) · ADM                  │
│ ①Postulación ─ ②Selección ─ ③Aprob. académica ─ ④Documentación ─ ⑤Activa │ ← secuencia
│ Falta para finalizar: 2 registros de horas sin revisar · evaluación final│ ← bloqueos
│                                         [Registrar horas] [Más acciones▾]│
└──────────────────────────────────────────────────────────────────────────┘
┌ Secciones ──────┐ ┌──────────────────────────────────────────────────────┐
│ Resumen         │ │ Segmentos y rotaciones                               │
│ Segmentos  (2)  │ │ ...                                                  │
│ Horas  (2 pend.)│ │──────────────────────────────────────────────────────│
│ Documentos      │ │ Registro de horas                                    │
│ Seguimiento     │ │ ...                                                  │
│ Conversación    │ └──────────────────────────────────────────────────────┘
│ Actividad       │
└─────────────────┘  ← índice fijo al hacer scroll; en móvil pasa a un selector
```

**Alineación:** todo el contenido alineado a la izquierda sobre una rejilla de 12 columnas. Solo los estados vacíos van centrados.

## 9. Lo que esta dirección evita

| Rechazado | Por qué en DH-05 |
|---|---|
| Degradados morados o de cualquier color | No aportan información. El producto no es una landing. |
| Glassmorphism (por ejemplo, el `backdrop-filter: blur` actual del header) | Reduce el contraste y añade coste de render. |
| Sombras bajo cada panel | La jerarquía la dan los filetes. Las sombras solo marcan capas (menús y diálogos). |
| Hover que eleva los botones | Movimiento sin significado. |
| Emojis o glifos como iconos | Sustituidos por un set SVG coherente (§ componentes). |
| Rótulos en mayúsculas sobre cada título | Los sustituyen los breadcrumbs y los títulos claros. |
| Colores saturados sin función | La saturación queda reservada a los estados críticos. |
| Fuentes por defecto sin criterio (Inter declarada y no cargada) | Familia elegida por legibilidad tabular y tono institucional. |
| Animaciones de entrada | Solo movimiento que responde a una acción: abrir, expandir, confirmar. |
