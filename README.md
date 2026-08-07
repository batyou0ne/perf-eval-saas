# Performance Eval SaaS

AI-powered employee performance evaluation platform. Company admins/HR run review cycles;
employees write self-evaluations, managers evaluate their direct reports, and Gemini
synthesizes both into an AI summary once a cycle is submitted.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **AI:** Google Gemini API (`google-genai`)
- **Auth:** JWT (access + refresh token, refresh rotation via Redis)
- **Email:** Resend (invite + password-reset emails)
- **Rate limiting:** slowapi, Redis-backed
- **Logging:** structured JSON logs to stdout
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router
- **Testing:** pytest (backend), Vitest + React Testing Library (frontend)
- **DevOps:** Docker, Docker Compose, GitHub Actions

## Roles

Super Admin, Company Admin, HR, Manager, Employee.

- **Super Admin** — creates companies, invites the first Company Admin for each.
- **Company Admin / HR** — invite teammates, manage the team (assign managers,
  deactivate/reactivate users), create and run review cycles, view AI summaries.
- **Manager** — evaluates direct reports, self-evaluates.
- **Employee** — self-evaluates, views their own evaluations and AI summary.

## Features

- **Invites** — token-based, role-scoped, expiring; company admins/HR can list, cancel,
  and resend pending invites.
- **Review cycles** — draft → active → closed. Company Admin/HR define rating and
  free-text questions, edit a cycle before activation, and track submission progress.
  Activating a cycle generates one self-evaluation for every active user and one
  manager-evaluation per **employee** who has a manager assigned (managers/admins/HR
  aren't reviewed themselves).
- **Evaluations** — fill out responses incrementally with draft-save (`PATCH`), then
  submit. Strict visibility rules: a subject can't see their manager's evaluation of
  them until it's submitted.
- **AI summaries** — once both the self- and manager-evaluation for a subject are
  submitted, an AI summary (synthesis, strengths, growth areas, self/manager alignment)
  can be generated via Gemini and is cached after first generation.
- **Team management** — assign or remove a user's manager, deactivate/reactivate users.

## Local development

```bash
cp .env.example .env   # fill in secrets
docker compose up --build
```

- Backend: http://localhost:8001 (docs at `/docs`)
- Frontend: http://localhost:5174

Ports are chosen to avoid colliding with the `rule-editor` project's stack on
this machine (which uses 5173, 8000, 8080, 8101-8103, 27017).

### Environment variables

See `.env.example` (root — this is what `docker compose up` reads) for the full list
with comments. The ones you're most likely to touch:

| Variable | Purpose |
|---|---|
| `POSTGRES_USER/PASSWORD/DB` | Compose builds `DATABASE_URL` from these for the backend service |
| `JWT_SECRET_KEY` | Signs access/refresh tokens |
| `GEMINI_API_KEY` | Enables AI summary generation (`GEMINI_MODEL` defaults to `gemini-flash-latest`) |
| `RESEND_API_KEY` | Enables real email sending — see [Email sending](#email-sending) |
| `CORS_ORIGINS`, `ENVIRONMENT` | Standard deployment config |

Running the backend directly on the host instead of via Compose? Use
`backend/.env.example` instead — it has `DATABASE_URL`/`REDIS_URL` set for
`localhost` and the same secrets otherwise.

## Email sending

Invite and password-reset emails go through [Resend](https://resend.com). Two ways to try it, neither needs a credit card:

- **Zero setup (default):** leave `RESEND_API_KEY` blank in `.env`. Emails aren't actually sent — the link is printed to the backend logs instead (`docker compose logs -f backend`), so the invite/reset flow is fully testable without any account.
- **Real emails, still free:** sign up for a free Resend account, create an API key, and set `RESEND_API_KEY` in `.env`. Keep `EMAIL_FROM=onboarding@resend.dev` (Resend's shared test sender — no domain verification required). In this mode Resend only allows sending to the email address you signed up with, so use that address when creating an invite or requesting a password reset. Sending to arbitrary recipients requires verifying your own domain with Resend, which isn't necessary for trying out this project.

## Testing

```bash
# Backend
docker compose exec backend pytest

# Frontend
docker compose exec frontend npm run test
```

(Both also work outside Docker — backend with a venv from `requirements-dev.txt`, frontend
with `npm install && npm run test` — but the frontend `node_modules` here is otherwise only
maintained inside the container, since `docker-compose.yml` bind-mounts just `frontend/src`.)

CI (`.github/workflows/ci.yml`) runs on every push/PR to `main` with three jobs:
backend tests (against real Postgres + Redis service containers, Gemini calls mocked),
an Alembic migration check (`alembic upgrade head` against an empty DB), and
frontend lint + test + build.

## API overview

All endpoints are prefixed `/api/v1`; full interactive docs at `/docs` when the backend
is running.

| Resource | Endpoints |
|---|---|
| Auth | login, refresh, logout, `me`, password-reset request/confirm |
| Companies | create, list *(Super Admin)* |
| Users | list, assign manager, deactivate/reactivate *(Company Admin/HR)* |
| Invites | create, list, cancel, resend, public preview + accept |
| Cycles | create, list, detail, edit, activate, progress *(Company Admin/HR)* |
| Evaluations | list mine (paginated), detail, draft-save, submit |
| Summaries | generate/fetch AI summary for a subject in a cycle |
