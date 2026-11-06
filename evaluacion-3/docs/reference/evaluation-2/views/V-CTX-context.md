# V-CTX — Contexto del sistema

| Campo | Valor |
|---|---|
| **ID** | V-CTX |
| **Propósito** | Mostrar quién interactúa con DH-05 y con qué sistemas externos |
| **Requisitos** | RF-20, RNF-07, RNF-08 · RFP sec. 4, 7 y 10 |
| **ADRs** | ADR-004, ADR-006 |

```mermaid
flowchart LR
  STU["Estudiante"]
  HOST["Representante de la<br/>organización anfitriona"]
  WSUP["Supervisor en el<br/>lugar de trabajo"]
  FSUP["Supervisor docente"]
  PC["Coordinador de<br/>programa académico"]
  ELC["Coordinador de aprendizaje experiencial<br/>Oficina de Desarrollo Profesional"]
  LEG["Representante de acuerdos<br/>legales o institucionales"]
  ITS["Servicios de TI<br/>opera y da soporte"]

  SYS["DH-05<br/>Sistema de Gestión de<br/>Pasantías y Prácticas"]

  IDP["IdP institucional<br/>NO CONFIGURADO · OPEN-21"]
  SREC["Registros estudiantiles<br/>y académicos SIMULADO"]
  DOCR["Repositorio de documentos<br/>SIMULADO"]
  NTF["Canal de notificación<br/>SIMULADO, OPEN-15"]
  CAL["Calendario institucional<br/>OPCIONAL, OPEN-10"]

  STU -->|"busca, postula, entrega documentos y evidencia, ve estado"| SYS
  HOST -->|"registra y confirma oportunidades, selecciona candidatos"| SYS
  WSUP -->|"plan de trabajo, avance, evaluaciones, propone cambios"| SYS
  FSUP -->|"supervisa, evalúa, comunica"| SYS
  PC -->|"aprueba colocaciones, define política de su programa"| SYS
  ELC -->|"revisa y publica, gestiona documentos, activa y cierra"| SYS
  LEG -->|"revisa acuerdos y documentos"| SYS
  ITS -.->|"opera, configura, soporta"| SYS

  SYS -->|"consulta perfil académico"| SREC
  SYS -->|"guarda y recupera archivos"| DOCR
  SYS -->|"entrega notificaciones"| NTF
  SYS -.->|"sincroniza fechas, opcional"| CAL
```

**Lectura.** Los siete actores humanos de la izquierda interactúan con una sola aplicación; **cada uno ve solo lo que su rol y su relación con la colocación permiten** (ADR-004). C-01 autentica cuentas locales dentro de DH-05; el IdP institucional aparece como dependencia futura y no hay conexión hacia él. Los demás sistemas externos siguen simulados o pendientes.

## Relaciones principales

| Relación | Dirección | Dato | Justificación |
|---|---|---|---|
| Estudiante → DH-05 | entrada/salida | Postulaciones, documentos, horas, estado | RFP sec. 4 |
| Anfitrión → DH-05 | entrada/salida (limitada) | Oportunidades, selección, evaluación | RF-20: sin acceso innecesario |
| Usuario → C-01 local | entrada | Nombre/email y contraseña; sesión HttpOnly | RNF-07; roles se consultan en DH-05 |
| DH-05 → IdP institucional | — | Sin intercambio actual | OPEN-21: proveedor y configuración no disponibles |
| DH-05 → Registros estudiantiles | salida | Programa, nivel, créditos, cursos | Necesario para RF-05 |
| DH-05 → Repositorio de documentos | salida | Archivos; el sistema guarda metadatos y referencia | RFP sec. 7/10; OPEN-20 |
| DH-05 → Canal de notificación | salida | Avisos y recordatorios | RF-15 |
| DH-05 → Calendario | salida | Fechas | **No está en el RFP**; solo opcional |

## Fuera del contexto (a propósito)
Nómina, RR. HH. del empleador, LMS, verificación de antecedentes, seguros reales, contratos reales (RFP sec. 10).
