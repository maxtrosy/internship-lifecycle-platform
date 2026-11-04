# Internship Lifecycle Platform

DH-05 academic project for managing professional internships from opportunity and application through activation and closure.

## Stack

- Frontend: React, TypeScript, Vite in development mode with HMR.
- Backend: FastAPI modular monolith.
- Database: PostgreSQL with Alembic migrations.
- Local run: one Docker Compose project; Vite proxies API requests to FastAPI.

## Implemented flows

- Local account authentication with Argon2id password hashes, active-account checks, revocable server-side sessions, and role/relationship authorization.
- Opportunities, eligibility policies, applications, employer selection, and academic approval.
- Versioned activation and completion policies, checklist requirements, document upload and review, re-submission, and activation gates.
- Relationship-scoped practice follow-up: student progress reports, workplace supervisor narrative evaluations, incident/change reports, and a readable lifecycle history.
- Relationship-scoped narrative work-plan activities assigned by the workplace supervisor currently attached to the placement.
- Persistent, relationship-scoped notifications and dossier conversations with separate shared and academic audiences.
- Aggregated operational reports for authorized program/experiential coordinators, with model-backed filters and no individual evaluations or student PII.
- Opportunity draft/review/approval/publication/closure transitions protected in the API and database; reviewer and publisher roles remain explicitly configurable.
- Configurable academic supervisor assignment/reassignment with an append-only assignment history.
- Student dashboard guidance derived from persisted application/practice states and configured activation requirements; supervisor and program dashboards list only the placements returned by the relationship-scoped API.
- Final report evidence stored with immutable revisions and content hashes; completion checks read persisted evidence and configured requirements, including hours where the selected policy requires them.
- Policy and document decisions retain their versions and audit history.

The document repository is currently implemented as PostgreSQL byte storage for the local demo. Uploads accept PDF, PNG, JPG, or DOCX up to 10 MB. Use synthetic files only. A production document service remains external.

Institutional transition authorities are not assumed. `OPPORTUNITY_REVIEWER_ROLES`, `OPPORTUNITY_PUBLISHER_ROLES`, and `PLACEMENT_FACULTY_ASSIGNER_ROLES` default to empty; until an institution configures them, those approval/publication and faculty assignment mutations are unavailable. The E2E harness configures these roles only for its disposable test database.

## Local authentication

The login accepts a username or email and password. The browser receives an `HttpOnly`, `SameSite=Strict` session cookie; it does not receive or store a JWT. `/auth/me` restores the current user and roles from the database after a page refresh. Roles and organizational/program relationships stay server-managed. There is no public signup.

## Local development with Docker

The root Compose project is the permanent development environment. It bind-mounts the frontend and backend source, runs Vite with HMR and FastAPI with `uvicorn --reload`, and reuses the existing PostgreSQL volume selected by the ignored root `.env` file. The database volume is external so Compose cannot silently replace it with an empty one. PostgreSQL is available only inside the Compose network; the API and Vite are published on the host loopback interface.

Start the environment from the repository root:

```powershell
docker compose up -d
```

Open the frontend at <http://localhost:5173> and the API at <http://localhost:8000> (`/health` and `/docs`). The Vite proxy sends browser API requests through the Compose network to FastAPI; the browser does not need to resolve the container service name.

```powershell
docker compose logs -f
docker compose down
docker compose exec api alembic upgrade head
```

`docker compose down` stops and removes the project containers and network but preserves both the external PostgreSQL volume and the frontend dependency volume. Do not use `down --volumes` for the development project. Source changes are live through the bind mounts; no image rebuild is needed for React/TypeScript/CSS or Python edits.

The local development database already contains provisioned accounts and domain data. Do not run the synthetic seed against this populated database. For a different machine, set `DEV_POSTGRES_VOLUME` in a local, ignored `.env` to the verified existing database volume name before starting Compose. Compose intentionally fails if that external volume is absent rather than initializing a new database. Do not put database credentials or other secrets in tracked documentation.

The synthetic seed remains available only for a deliberately fresh development database after its target has been verified:

```powershell
docker compose exec api python -m app.seed
```

It is a one-time operation and must not be run against the existing populated development database.

Operators provision accounts through the command line, using database operator credentials already configured in `DATABASE_URL`. Passwords are prompted interactively and never passed as command-line arguments. For example:

```powershell
docker compose exec api python -m app.provision_user `
  --username maria.gomez --email maria@example.edu --display-name "Maria Gomez" `
  --role STUDENT --program-code ING-SIS
```

Supported roles are validated by the provisioning command. Students and program coordinators require an existing `--program-code`; host members and workplace supervisors require an existing `--host-org-id`. Other roles cannot be assigned program or host relationships by this command. Invitation acceptance is restricted to the allowed external roles and binds the invitation's organization on the server.

Migration `0003` preserves existing user IDs, role assignments, and domain data, but disables legacy accounts until an operator assigns credentials. To activate an existing user while preserving their roles, use the operator command with `--existing-user-id <id>` plus `--username`, `--email`, and `--display-name`; do not supply a new role. This is also how a pre-authentication demo account transitions to local credentials.

Password recovery has a generic response and one-use, 30-minute random tokens stored as hashes. This repository has no mail provider. In local development only, the reset endpoint returns a token for the operator to deliver manually; in other environments delivery is disabled. Do not enable `development-token` outside a local development environment.

### SSO and production gaps

No institutional identity provider, protocol selection, discovery URL, client credentials, redirect URI, or test account was supplied in OPEN-21 or the project artifacts. The current login is real local account authentication; it is **not institutional SSO**. Enabling SSO requires those items and a validated OIDC/SAML decision. Before production, also configure a secret manager-backed `JWT_SECRET`, production HTTPS/origins, a real password-reset delivery adapter, shared rate limiting for multiple API workers, operational monitoring, and review the deployment's session/CSRF policy. The development JWT fallback is local only and production startup rejects it.

Docker Compose uses an explicitly selected external PostgreSQL volume to keep the existing local database independent of container recreation.

## Validate

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path + '\.deps;' + (Get-Location).Path
$env:DATABASE_URL = ''
python -m pytest -q  # Python 3.12; without DATABASE_URL, the suite starts a disposable pgserver database.
cd ..\frontend
pnpm run test
pnpm run build
cd ..
$env:PYTHONPATH = (Join-Path (Get-Location).Path 'backend\.deps')
python scripts\run_isolated_e2e.py
```

`scripts/run_isolated_e2e.py` starts a fresh temporary PostgreSQL instance, API, Vite, and Chromium run; it overrides any inherited `DATABASE_URL`, keeps screenshots/logs under `%TEMP%`, and cleans up the temporary database and processes. Install backend dev dependencies (including `pgserver`), frontend dependencies, and Playwright Chromium first. Validation results and known limitations are in [the validation report](docs/evaluation-2/validation/validation-results.md). Full browser E2E across every role, performance, external adapter, and usability scenarios remain open.
