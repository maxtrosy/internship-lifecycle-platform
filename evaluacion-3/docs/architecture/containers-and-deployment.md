# Contenedores y despliegue observado

## Contenedores de aplicación

```mermaid
flowchart TB
  Browser[Browser\nReact SPA]
  Vite[Vite dev / bundle estático\nfrontend/src]
  API[FastAPI\nrouters + servicios de dominio]
  DB[(PostgreSQL\nrelaciones, políticas, auditoría, blobs)]
  Alembic[Alembic\nmigraciones 0001–0014]
  Browser --> Vite
  Browser -->|HTTP API; cookie HttpOnly| API
  Vite -. proxy solo desarrollo .-> API
  API -->|psycopg 3 / SQL explícito| DB
  Alembic -->|esquema SQL versionado| DB
```

## Despliegue para la evaluación

```mermaid
flowchart LR
  CLI[run_eval3_demo.py o run_isolated_e2e.py]
  PG[pgserver en carpeta temporal OS]
  UV[Uvicorn / FastAPI en loopback]
  WEB[Vite / Chromium local]
  CLI --> PG
  CLI --> UV
  CLI --> WEB
  WEB --> UV
  UV --> PG
  Cleanup[Ctrl+C o fin del runner\nlimpieza del cluster temporal]
  CLI --> Cleanup
```

El launcher interactivo aplica Alembic a `0014`; el E2E crea el esquema temporal actual y ejecuta pruebas de navegador. Las salidas de esta evaluación verificaron ambas rutas separadamente. La ruta de despliegue objetivo Render + Neon + Vercel no se verifica mediante estas capturas; no se aportó una URL pública comprobada en este paquete. Docker Compose es un entorno local con volumen persistente y no se utiliza para esta evaluación.
