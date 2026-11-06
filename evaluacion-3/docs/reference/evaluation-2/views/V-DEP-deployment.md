# V-DEP — Supuestos de despliegue

> **Estado T-51, 2026-11-04:** El preflight read-only de `long-truth-39527618/main` confirmó `app_runtime`+TLS+`SET ROLE app_user`, 14 cuentas base, 2 programas, 2 organizaciones y 4 políticas de activación/finalización, sin ciclos ni políticas de elegibilidad. El cargador SYN-01 quedó implementado, pero la ejecución `--apply` no se realizó: faltan reglas de elegibilidad, autoridades OPEN-05, snapshot y credencial puntual de escritura. El HTTP 200 de Render `/health` y `/ready` procede del T-50 anterior; Vercel no se verificó. Véase [`validation-results.md`](../validation/validation-results.md); no hay dataset poblado en Neon.

> El diagrama siguiente conserva el supuesto original de arquitectura; no representa recursos ya aprovisionados.

| Campo | Valor |
|---|---|
| **ID** | V-DEP |
| **Propósito** | Explicitar dónde correrían los contenedores y qué se asume de cada entorno |
| **Requisitos** | RNF-02, RNF-06, RNF-07, RNF-09, RNF-12 · RFP sec. 7 (remoto/híbrido, datos sintéticos) |
| **ADRs** | ADR-002, ADR-006 |

```mermaid
flowchart TB
  subgraph UD["Dispositivo del usuario - fuera del control del equipo"]
    BR["Navegador"]
  end

  subgraph HOST["Host de demostración - SUPUESTO"]
    PX["Servidor web<br/>estáticos de la SPA y proxy"]
    API["API"]
    WRK["Worker"]
    DB[("PostgreSQL")]
    MOCK["Simuladores<br/>registros, documentos,<br/>notificación"]
  end

  BR -->|"HTTPS"| PX
  PX --> API
  API --> DB
  WRK --> DB
  API -.-> MOCK
  WRK -.-> MOCK
```

**Fronteras de despliegue:** (1) el navegador del usuario, no controlado; (2) el host de la aplicación, controlado por el equipo; (3) los servicios simulados, que **en esta entrega viven dentro del mismo host** para no depender de nadie (RFP: operar de forma independiente).

## Entornos

| Entorno | Supuesto | Datos | Estado |
|---|---|---|---|
| Desarrollo | Contenedores locales (API, worker, BD, simuladores) | Sintéticos | **Supuesto** |
| Pruebas / CI | BD efímera por ejecución; simuladores con fallo a pedido (QS-07) | Sintéticos | **Supuesto**; el PoC usó una BD efímera local |
| Demostración | Un host, 1 proceso API, 1 worker, 1 BD | Sintéticos | **Supuesto** |
| Producción real | Fuera del alcance de este semestre | — | **No considerado** |

## Supuestos operativos

| Tema | Supuesto | Estado |
|---|---|---|
| Configuración y secretos | Variables de entorno o gestor de secretos del host; **nada embebido en el código** | Supuesto |
| Datos | Solo sintéticos (RNF-06); sin datos reales de estudiantes ni empleadores | Restricción del RFP |
| Respaldo | Volcado periódico de la BD en demo; frecuencia y retención sin definir | **OPEN-16** |
| Disponibilidad | Una sola instancia, sin alta disponibilidad; umbral sin definir (RNF-12) | **OPEN-16** |
| Escalabilidad | Vertical; el worker puede ejecutarse en varios procesos; no hay escalado automático | Supuesto |
| Observabilidad | Registro operativo estructurado, con eventos de seguridad (denegaciones) separados de la auditoría de negocio | Supuesto |
| Autenticación | Cuentas locales: Argon2id y sesión corta en cookie `HttpOnly`; SSO institucional: **OPEN-21** | Implementado local; IdP no configurado |
| Red | Acceso remoto por HTTPS; sin VPN | Supuesto |

## Qué no se debe afirmar
Que el sistema "está desplegado", que "soporta N usuarios" o que "se respalda": nada de eso se implementó ni se midió (QS-05: NOT EXECUTED).
