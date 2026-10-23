# Internship Lifecycle Platform

DH-05 academic project for managing professional internships from opportunity and application through activation and closure.

## Stack

- Frontend: React, TypeScript, Vite, served by Nginx.
- Backend: FastAPI modular monolith.
- Database: PostgreSQL with Alembic migrations.
- Local run: Docker Compose; Nginx proxies API requests to FastAPI.

## Implemented flows

- Local account authentication with Argon2id password hashes, active-account checks, revocable server-side sessions, and role/relationship authorization.
- Opportunities, eligibility policies, applications, employer selection, and academic approval.
- Versioned activation and completion policies, checklist requirements, document upload and review, re-submission, and activation gates.
- Completion evidence and hour checks before a placement can close.
- Policy and document decisions retain their versions and audit history.

The document repository is currently implemented as PostgreSQL byte storage for the local demo. Uploads accept PDF, PNG, JPG, or DOCX up to 10 MB. Use synthetic files only. A production document service remains external.

## Local authentication

The login accepts a username or email and password. The browser receives an `HttpOnly`, `SameSite=Strict` session cookie; it does not receive or store a JWT. `/auth/me` restores the current user and roles from the database after a page refresh. Roles and organizational/program relationships stay server-managed. There is no public signup.

For a fresh local database:

```powershell
docker compose up --build -d
docker compose exec api python -m app.seed
```

Open <http://localhost:5173>. Seeded demo accounts share the local-only password `Demo-Only-2026!` (override it with `DEMO_PASSWORD` before seeding). Example: username `s1` or email `s1@demo.local`. Other seeded usernames include `s2`, `s3`, `pc_sys`, `pc_adm`, `ec1`, `legal1`, `hm_alfa`, `hm_beta`, `ws_alfa`, `ws_alfa2`, `ws_beta`, `f1`, and `dual1`. The seed is synthetic, only allowed with `APP_ENV=development`, and is intended to run once on a fresh database.

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

Docker Compose currently has no named database volume, so removing the database container removes its data.

## Validate

```powershell
cd backend
$env:PYTHONPATH = (Get-Location).Path + '\.deps;' + (Get-Location).Path
python -m pytest -q
cd ..\frontend
npm run build
```

Validation results, commands, and known limitations are in [the validation report](docs/evaluation-2/validation/validation-results.md). Full browser E2E across every role, performance, external adapter, and usability scenarios remain open.
