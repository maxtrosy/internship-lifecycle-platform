# Neon: antecedente y procedimiento pendiente

## Evidencia disponible (histórica, no revalidada en Evaluación 3)

La lectura de solo lectura reportada en la etapa T56 se hizo para el proyecto `long-truth-39527618`, rama `main` (`br-green-wind-bc6cvzzc`), con TLS. En ese momento se observaron 61 cuentas, 10 organizaciones, 16 oportunidades, 4 políticas de activación/finalización, 0 postulaciones, 0 prácticas y 41 eventos de auditoría. También se verificó que el rol separado `app_dataset_full` no existía y que no estaba su credencial de bootstrap; `app_bootstrap` carecía del ACL de escritura necesario y no podía conceder permisos.

**No es resultado de esta ejecución**, y los conteos pueden haber cambiado desde entonces. Esta entrega no se conecta a Neon, no escribe, no migra ni intenta elevar permisos. El resultado E3 procede de `pgserver` temporal; al final se limpió.

## Acción DBA que faltaría para el cargador integral

Una autoridad DBA tendría que revisar [`reference/synthetic-dataset-bootstrap.md`](reference/synthetic-dataset-bootstrap.md), crear/configurar el login de carga separado con los permisos mínimos explícitos para el modo autorizado, almacenar su secreto en un gestor seguro y confirmar el destino/snapshot. `app_runtime` no se eleva, `neondb_owner` no se usa como credencial de aplicación y esta evaluación no solicita ni ejecuta ese procedimiento. Aun con esos permisos, las aprobaciones y reglas institucionales permanecen pendientes: no se deben fabricar postulaciones, decisiones, activaciones ni cierres no respaldados.

## Afirmaciones prohibidas

- No declarar que se cargaron postulaciones o prácticas en producción.
- No presentar usuarios o contraseñas de producción como credenciales de demo.
- No presentar este ZIP como un despliegue público verificado.
- No migrar ni escribir datos para preparar la grabación; se usa exclusivamente el launcher aislado.
