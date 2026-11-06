# Demo de Evaluación 3 en macOS

Este stack permite grabar la demostración en una Mac con Docker Desktop. Levanta una SPA, FastAPI y PostgreSQL con la fixture sintética del proyecto. PostgreSQL usa un `tmpfs` de 512 MB; no hay volumen persistente ni carpetas del Mac montadas, y la base desaparece al detener el stack. No conecta con Neon ni con una base local. Solo se publica el frontend en loopback (`127.0.0.1`); PostgreSQL y FastAPI no publican puertos al host.

## Requisitos

- Mac Intel o Apple Silicon.
- Docker Desktop instalado y en ejecución; incluye Docker Compose v2.
- Aproximadamente 4 GB libres para construir imágenes y ejecutar los servicios.
- Navegador moderno.

## Inicio

1. Extrae `evaluacion-3-macos-demo.zip`.
2. Abre Terminal y entra a la carpeta `evaluacion-3` que se extrajo.
3. Inicia el stack:

   ```sh
   docker compose -p dh05-eval3-share -f compose.macos.yaml up --build -d
   ```

   La primera ejecución descarga las imágenes e instala dependencias; puede tardar varios minutos. Espera a que `docker compose ... ps` muestre `web` y `api` como activos, y que el bootstrap termine con código 0:

   ```sh
   docker compose -p dh05-eval3-share -f compose.macos.yaml ps -a
   docker compose -p dh05-eval3-share -f compose.macos.yaml logs bootstrap
   ```

4. Abre <http://localhost:8080>.

El puerto se puede cambiar antes de iniciar con `DH05_DEMO_PORT=18080`; en ese caso abre `http://localhost:18080`. Compose elige automáticamente la subred. Si Docker informa que agotó sus rangos de red, usa el override `compose.macos.subnet.yaml` y asigna una subred privada que no coincida con la VPN o red local.

## Cuentas sintéticas

Contraseña para estas cuentas temporales: `Demo-Only-2026!`.

| Usuario | Rol principal | Qué puede mostrar |
|---|---|---|
| `demo_student_07` | Estudiante | Expediente cerrado con datos persistidos de demostración y lectura tras recargar. |
| `s1` | Estudiante | Portal de postulante y ciclo sintético. |
| `pc_sys` | Coordinación de ING-SIS | Vistas académicas y estado de revisión correspondiente a sus relaciones. |
| `ec1` | Coordinación experiencial | Oportunidades y procesos de coordinación de la fixture. |
| `hm_alfa` | Miembro de anfitrión | Oportunidades y postulaciones visibles para su organización. |
| `ws_alfa` | Supervisor laboral | Seguimiento vinculado a las prácticas asignadas. |
| `f1` | Supervisor docente | Seguimiento de las prácticas efectivamente asignadas. |
| `legal1` | Revisión legal | Documentación que le corresponde revisar. |

El contenido, las organizaciones, usuarios, decisiones y reglas de la fixture son sintéticos. Las autoridades de transición y el requisito de 100 horas solo permiten ejecutar la demostración; no son políticas institucionales.

## Guion y pruebas

Sigue `video/script.md`. El expediente de `demo_student_07` es de solo lectura porque está cerrado. Para mostrar transiciones, revisión manual y permisos, puedes presentar la salida de las pruebas E2E que ya están incluidas en `evidence/test-results/2026-11-05.md`; esas pruebas usan una base temporal separada y no cambian esta demo.

La contraseña local no es de producción. No conectes este Compose a Neon, no cambies el `DATABASE_URL` y no publiques el puerto en una red. El único puerto publicado escucha en `127.0.0.1` de la Mac.

## Detener y borrar la demo

```sh
docker compose -p dh05-eval3-share -f compose.macos.yaml down
```

Si iniciaste con `compose.macos.subnet.yaml`, añade también `-f compose.macos.subnet.yaml` al comando `down`.

No se crea ningún volumen persistente. Al eliminar los contenedores se elimina el `tmpfs` con la base y sus datos sintéticos. Las imágenes construidas pueden permanecer en Docker Desktop, pero no contienen la base de datos.

## Problemas frecuentes

- Si Docker Desktop está detenido, ábrelo, espera a que indique que el motor está activo y vuelve a ejecutar `up`.
- Si el puerto 8080 está ocupado, usa `DH05_DEMO_PORT=18080` como se describe arriba.
- Si Docker no puede crear una red por falta de subredes disponibles, en macOS usa, por ejemplo, `DH05_DEMO_SUBNET=10.255.255.0/24 docker compose -p dh05-eval3-share -f compose.macos.yaml -f compose.macos.subnet.yaml up --build -d`. El bloque debe estar libre en esa Mac.
- Para revisar fallos del arranque: `docker compose -p dh05-eval3-share -f compose.macos.yaml logs --tail=100`.
- Para reiniciar la base temporal desde cero: ejecuta `down` y después `up --build -d`.
