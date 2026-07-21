# Performance Eval SaaS

AI-powered employee performance evaluation platform.

## Stack

- **Backend:** FastAPI, SQLAlchemy 2.0 (async), PostgreSQL, Alembic
- **AI:** OpenAI API (GPT-4o)
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
