# Usuarios y datos sintéticos

Todos los datos son ficticios. Las cuentas existen solo en las bases temporales creadas por las pruebas, el E2E o la demo. La contraseña de la demo la imprime el lanzador (`Demo-Only-2026!` por defecto, solo para la base temporal); las pruebas usan su propia contraseña de prueba.

| Usuario | Rol sintético | Papel en CR-05 |
|---|---|---|
| `s1` | Estudiante (ING-SIS) | Reporta horas en el segmento activo; ve sus segmentos sin motivos internos. |
| `ws_alfa` | Supervisor laboral, Org Alfa | Supervisa el segmento 1. Pierde el acceso cuando su segmento termina o se transfiere. |
| `ws_alfa2` | Supervisor laboral, Org Alfa | Supervisor sin relación (acceso cruzado) o supervisor de otra rotación. |
| `ws_beta` | Supervisor laboral, Org Beta | Supervisor del segmento destino. |
| `hm_alfa`, `hm_beta` | Miembros de organización | Ven solo los segmentos de su organización. |
| `pc_sys` | Coordinación del programa ING-SIS | Revisora de horas (configurada), revisión combinada y confirmación de cierre. |
| `pc_adm` | Coordinación de otro programa | Acceso cruzado: se rechaza. |
| `ec1` | Coordinación experiencial | Gestora de segmentos (configurada solo en bases temporales) y cierre. |
| `legal1` | Revisor legal | Confirma las condiciones documentales del segmento. |
| `f1` | Supervisión docente | Revisora de horas (configurada) cuando está asignada. |

## Configuración usada en bases temporales (no es política institucional)

```text
PLACEMENT_SEGMENT_MANAGER_ROLES=EXPERIENTIAL_COORDINATOR
PLACEMENT_HOURS_REVIEWER_ROLES=FACULTY_SUPERVISOR,PROGRAM_COORDINATOR
```

Las políticas sintéticas (por ejemplo, `MIN_HOURS = 100` o `DOC_INSURANCE`) son fixtures de prueba, no requisitos institucionales.
