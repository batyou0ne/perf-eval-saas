# Performance Eval SaaS

AI-powered employee performance evaluation platform.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **AI:** Google Gemini API (google-genai)
- **Auth:** JWT (access + refresh token)
- **Cache:** Redis
- **Frontend:** React, TypeScript, Vite, Tailwind CSS, shadcn/ui
- **DevOps:** Docker, Docker Compose, GitHub Actions

## Roles

Super Admin, Company Admin, Manager, HR, Employee.

## Local development

```bash
cp .env.example .env   # fill in secrets
docker compose up --build
```

- Backend: http://localhost:8001 (docs at `/docs`)
- Frontend: http://localhost:5174

Ports are chosen to avoid colliding with the `rule-editor` project's stack on
this machine (which uses 5173, 8000, 8080, 8101-8103, 27017).

## Email sending

Invite and password-reset emails go through [Resend](https://resend.com). Two ways to try it, neither needs a credit card:

- **Zero setup (default):** leave `RESEND_API_KEY` blank in `.env`. Emails aren't actually sent — the link is printed to the backend logs instead (`docker compose logs -f backend`), so the invite/reset flow is fully testable without any account.
- **Real emails, still free:** sign up for a free Resend account, create an API key, and set `RESEND_API_KEY` in `.env`. Keep `EMAIL_FROM=onboarding@resend.dev` (Resend's shared test sender — no domain verification required). In this mode Resend only allows sending to the email address you signed up with, so use that address when creating an invite or requesting a password reset. Sending to arbitrary recipients requires verifying your own domain with Resend, which isn't necessary for trying out this project.
