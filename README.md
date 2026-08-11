# Performance Eval SaaS

A multi-tenant performance review platform. Companies run review cycles; employees write
self-evaluations, managers review their direct reports, and Google Gemini synthesizes both
sides into a single summary once they are in.

Built as a portfolio project: FastAPI with async SQLAlchemy on the backend, React with
TypeScript on the frontend, deployed on Vercel, Render and Neon.

---

## Contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Running it locally](#running-it-locally)
- [Walkthrough: running a full review cycle](#walkthrough-running-a-full-review-cycle)
- [Roles and permissions](#roles-and-permissions)
- [How the review cycle works](#how-the-review-cycle-works)
- [AI summaries](#ai-summaries)
- [Email sending](#email-sending)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [Testing](#testing)
- [Continuous integration](#continuous-integration)
- [Project layout](#project-layout)

---

## Features

**Accounts and access**

- JWT authentication with short-lived access tokens and rotating refresh tokens, kept in an
  httpOnly cookie and revocable through Redis.
- Self-service password reset that is safe against account enumeration: the same response is
  returned whether or not the address exists.
- Five roles (super admin, company admin, HR, manager, employee) with permissions enforced at
  the API layer, not just hidden in the UI.
- Multi-tenancy: every query is scoped to the caller's company. Cross-tenant reads return 404
  rather than 403, so an outsider cannot even confirm that a record exists.

**Onboarding**

- Token-based invitations with configurable expiry, single use, and role restrictions on who
  may invite whom.
- Invites can be listed, cancelled, and resent with a fresh token.
- Real invite and password-reset emails through Resend, with a zero-setup local fallback that
  prints the link to the console instead.

**Team management**

- Assign or clear a user's manager.
- Deactivate and reactivate users. Deactivation hands the departing manager's direct reports
  and their unfinished reviews up to the skip-level manager in a single transaction, and is
  refused outright when there is nobody to hand them to.

**Review cycles**

- Build a cycle from rating (1-5) and free-text questions, edit it freely while it is a draft,
  then activate it to generate evaluations for the whole company.
- Close a cycle when the review period ends; closed cycles become read-only.
- A progress dashboard showing, per person, whether the self-evaluation and the manager
  evaluation have been submitted.

**Evaluations**

- Save partial answers as a draft and come back later, or submit when complete.
- Answer validation on both paths: ratings must be 1-5, text answers must be non-empty, and
  every question must be answered before submitting.
- Strict visibility rules. A manager's review of you is invisible until they submit it, even
  to company admins.

**AI summaries**

- Once both the self-evaluation and the manager evaluation are submitted, Gemini produces a
  structured summary: an overall synthesis, strengths, growth areas, and notes on where the
  two sides agreed or diverged.
- Generated once and cached, so re-opening the page does not spend tokens again.

**Production concerns**

- Pagination on every list endpoint, with a deliberate exception for the two endpoints that
  feed pickers (see [API reference](#api-reference)).
- Rate limiting on login and password-reset requests, backed by Redis.
- Structured JSON logs to stdout, including unhandled exceptions and rate-limit trips.
- A health endpoint that actually checks database and Redis connectivity.

---

## Tech stack

| Layer | Choice |
| --- | --- |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Pydantic v2, Alembic |
| Database | PostgreSQL |
| Cache and rate limiting | Redis, slowapi |
| AI | Google Gemini via `google-genai` |
| Email | Resend |
| Frontend | React, TypeScript, Vite, Tailwind CSS, shadcn/ui, React Router |
| Testing | pytest (backend), Vitest and React Testing Library (frontend) |
| Tooling | Docker Compose, GitHub Actions, oxlint |

---

## Running it locally

You need Docker and Docker Compose. Nothing else is installed on your machine.

**1. Configure the environment**

```bash
cp .env.example .env
```

The defaults work as-is for local development. `GEMINI_API_KEY` is the only thing worth
filling in right away, and only if you want to try the AI summaries.

**2. Start the stack**

```bash
docker compose up --build
```

**3. Apply migrations**

In a second terminal:

```bash
docker compose exec backend alembic upgrade head
```

**4. Create the first users**

```bash
docker compose exec backend python -m app.scripts.seed_dev_user
```

This creates a company called Acme Inc. and two accounts, both with the password
`devpassword123`:

| Email | Role |
| --- | --- |
| `admin@acmecorp.io` | Company admin |
| `superadmin@platform.io` | Super admin |

**Where things run**

| Service | URL |
| --- | --- |
| Frontend | http://localhost:5174 |
| Backend | http://localhost:8001 |
| Interactive API docs | http://localhost:8001/docs |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6379 |

These ports avoid colliding with another project on the author's machine, which uses 5173,
8000, 8080, 8101-8103 and 27017.

---

## Walkthrough: running a full review cycle

This is the whole product end to end. It takes about ten minutes and needs no email account
and no API keys, because invite links are printed to the backend console by default.

### 1. Sign in as the company admin

Open http://localhost:5174 and sign in as `admin@acmecorp.io` with `devpassword123`.

### 2. Invite an employee and a manager

On the dashboard, use the invite form to send an invite to any address, for example
`manager@example.com` with the role **manager**. Repeat with `employee@example.com` as an
**employee**.

No mail is actually sent unless you configure Resend, so grab the links from the console:

```bash
docker compose logs -f backend
```

Look for lines beginning `[dev-stub email]`. The invite link is also shown on screen right
after you send it, and listed under **Invites** where you can resend or cancel it.

### 3. Accept the invites

Open each link in a private window, set a password, and the account is created and signed in
immediately. Sign back out.

### 4. Set the reporting line

As the company admin, go to **Team** and set the employee's manager to the manager account.
Only active users are offered, because a deactivated manager could never complete a review.

### 5. Create a review cycle

Go to **Review Cycles**, then **New cycle**. Give it a name and dates, and add questions -
a mix of rating and free-text works best for the summary later. Save it.

While the cycle is a draft you can still edit it. Once you activate it, the questions are
frozen.

### 6. Activate it

Open the cycle and choose **Activate cycle**. This generates:

- one self-evaluation for every active person in the company, and
- one manager evaluation for every **employee** who has an active manager.

Managers, HR and admins are not reviewed by anyone; they only self-evaluate.

### 7. Fill the evaluations in

Sign in as the employee and open **My Evaluations**. Answer part of the self-evaluation and
choose **Save Draft** - the status moves to "in progress" and you can leave and come back.
Answer everything and choose **Submit evaluation**.

Sign in as the manager. There are two cards: their own self-evaluation, and "Evaluate
{employee}". Complete and submit both.

Note what the employee sees while this is happening: the manager's review of them appears as
"Manager review / Awaiting manager" and cannot be opened. It only becomes readable once the
manager submits it.

### 8. Read the AI summary

With both evaluations submitted, open the evaluation as any of the participants and choose
**Generate AI Summary**. Gemini returns a synthesis, strengths, growth areas, and a note on
how closely the self-assessment and the manager's assessment lined up. It is stored, so
opening the page again does not regenerate it.

This step needs `GEMINI_API_KEY` set in `.env`. Everything else in the walkthrough works
without it.

### 9. Track progress and close the cycle

Back as the company admin, the cycle page shows a per-person progress table. When the review
period is over, choose **Close cycle**. Closed cycles are read-only: draft saves and
submissions are rejected, and the existing answers stay readable.

---

## Roles and permissions

| Capability | Super admin | Company admin | HR | Manager | Employee |
| --- | :---: | :---: | :---: | :---: | :---: |
| Create and list companies | Yes | - | - | - | - |
| Invite a company admin | Yes | Yes | - | - | - |
| Invite HR, managers, employees | - | Yes | - | - | - |
| List, cancel, resend invites | - | Yes | - | - | - |
| List users, assign managers | - | Yes | Yes | - | - |
| Deactivate and reactivate users | - | Yes | Yes* | - | - |
| Create, edit, activate, close cycles | - | Yes | Yes | - | - |
| View cycle progress | - | Yes | Yes | - | - |
| Complete assigned evaluations | - | Yes | Yes | Yes | Yes |
| View a submitted evaluation in their company | - | Yes | Yes | - | - |

\* HR may not deactivate or reactivate a company admin.

A super admin belongs to no company. They onboard customer companies and invite each
company's first admin, and cannot see any company's evaluation data.

Every user, whatever their role, can be assigned evaluations and sees them under
**My Evaluations**.

---

## How the review cycle works

```
draft ──activate──> active ──close──> closed
  │                    │                 │
  edit freely          evaluations       read-only
                       can be filled
```

**Draft.** Name, dates and questions can be changed as often as you like. A cycle must have
at least one question.

**Activation** creates the evaluations in one pass:

- Every active user in the company gets a self-evaluation, where they are both subject and
  evaluator.
- Every active user whose role is **employee** and whose manager is also active gets a manager
  evaluation, with their manager as the evaluator.

The manager must be active because an inactive account cannot sign in, which would leave a
review nobody could ever submit.

**Active.** Evaluators can save drafts and submit. An evaluation moves from `not_started` to
`in_progress` on the first draft save, and to `submitted` on submission. Submissions are
final.

**Closed.** No further writes. Existing answers and summaries remain visible.

**Who can read an evaluation**

| Viewer | Access |
| --- | --- |
| The assigned evaluator | Always, including before submission |
| The subject | Only after it has been submitted |
| Company admin or HR in the same company | Only after it has been submitted |
| Anyone else | Never |

---

## AI summaries

A summary covers one person in one cycle and requires both their self-evaluation and their
manager evaluation to be submitted. The model receives the questions and both sets of answers
and returns a structured object:

| Field | Meaning |
| --- | --- |
| `synthesis` | An overall narrative combining both perspectives |
| `strengths` | What both sides pointed to as going well |
| `growth_areas` | Where development is needed |
| `alignment_notes` | Where the self-assessment and the manager's assessment agreed or diverged |

The result is written to the database on first generation and served from there afterwards.
The model defaults to `gemini-flash-latest` and can be changed with `GEMINI_MODEL`. Upstream
failures, including an invalid API key, surface as a 502 with a readable message rather than a
stack trace.

---

## Email sending

Invite and password-reset emails go through [Resend](https://resend.com). There are two ways
to run it, and neither needs a credit card.

**Zero setup, the default.** Leave `RESEND_API_KEY` blank. No mail is sent; the link is
printed to the backend log instead:

```bash
docker compose logs -f backend
```

The full invite and reset flows are testable this way.

**Real email, still free.** Create a Resend account, generate an API key, and set
`RESEND_API_KEY` in `.env`. Keep `EMAIL_FROM=onboarding@resend.dev`, which is Resend's shared
test sender and needs no domain verification. In this mode Resend only delivers to the address
you signed up with, so use that address when testing. Sending to arbitrary recipients requires
verifying your own domain, which is not necessary to try the project out.

---

## Configuration

Docker Compose reads `.env` in the repository root. To run the backend directly on your host
instead, use `backend/.env.example`, which points `DATABASE_URL` and `REDIS_URL` at localhost.

| Variable | Default | Purpose |
| --- | --- | --- |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | `performance_eval` | Compose builds the backend's `DATABASE_URL` from these |
| `JWT_SECRET_KEY` | - | Signs access and refresh tokens. Change it for anything real |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token lifetime |
| `GEMINI_API_KEY` | empty | Enables AI summaries |
| `GEMINI_MODEL` | `gemini-flash-latest` | Model used for summaries |
| `RESEND_API_KEY` | empty | Enables real email. Blank falls back to console output |
| `EMAIL_FROM` | `onboarding@resend.dev` | Sender address |
| `INVITE_EXPIRE_DAYS` | `7` | Invite link lifetime |
| `PASSWORD_RESET_EXPIRE_MINUTES` | `60` | Reset link lifetime |
| `FRONTEND_URL` | `http://localhost:5174` | Used to build invite and reset links. Startup fails if this is left at the default while `ENVIRONMENT=production` |
| `CORS_ORIGINS` | `http://localhost:5174` | Comma-separated allowed origins |
| `ENVIRONMENT` | `development` | `development` or `production` |

---

## API reference

Everything is under `/api/v1`. Full interactive documentation is at `/docs` while the backend
is running.

**Authentication**

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/auth/login` | Rate limited to 5 per minute |
| POST | `/auth/refresh` | Rotates the refresh token |
| POST | `/auth/logout` | Revokes the refresh token |
| GET | `/auth/me` | Current user |
| POST | `/auth/password-reset/request` | Rate limited to 3 per minute. Enumeration-safe |
| POST | `/auth/password-reset/confirm` | Signs the user in on success |

**Companies** (super admin)

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/companies` | |
| GET | `/companies` | Paginated |
| GET | `/companies/options` | Unpaginated `id` and `name`, for the invite picker |

**Invites**

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/invites` | Super admin or company admin. Sends the email |
| GET | `/invites` | Company admin. Paginated |
| DELETE | `/invites/{invite_id}` | Company admin. Cancels a pending invite |
| POST | `/invites/{invite_id}/resend` | Company admin. Issues a fresh token |
| GET | `/invites/{token}` | Public preview, no authentication |
| POST | `/invites/{token}/accept` | Public. Creates the account and signs in |

**Users** (company admin, HR)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/users` | Paginated |
| GET | `/users/options` | Unpaginated `id` and `full_name`, for the manager picker |
| POST | `/users/{user_id}/manager` | Assign or clear a manager |
| POST | `/users/{user_id}/deactivate` | Hands over reports and unfinished reviews |
| POST | `/users/{user_id}/reactivate` | |

**Review cycles** (company admin, HR)

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/cycles` | At least one question required |
| GET | `/cycles` | Paginated |
| GET | `/cycles/{cycle_id}` | Includes questions |
| PATCH | `/cycles/{cycle_id}` | Drafts only |
| POST | `/cycles/{cycle_id}/activate` | Drafts only. Generates evaluations |
| POST | `/cycles/{cycle_id}/close` | Active cycles only |
| GET | `/cycles/{cycle_id}/progress` | Per-person submission status |

**Evaluations** (any signed-in user; ownership enforced per record)

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/evaluations/me` | Paginated |
| GET | `/evaluations/{evaluation_id}` | Subject to the visibility rules above |
| PATCH | `/evaluations/{evaluation_id}` | Draft save. Partial answers allowed |
| POST | `/evaluations/{evaluation_id}/submit` | Requires every question answered |

**Summaries**

| Method | Path | Notes |
| --- | --- | --- |
| POST | `/cycles/{cycle_id}/subjects/{subject_id}/summary` | Generates, or returns the cached one |
| GET | `/cycles/{cycle_id}/subjects/{subject_id}/summary` | 404 if none has been generated |

**Health**

| Method | Path | Notes |
| --- | --- | --- |
| GET | `/health` | Checks database and Redis connectivity |

### Pagination

Paginated endpoints accept `page` (default 1) and `page_size` (default 20, maximum 100), and
respond with:

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

The two `/options` endpoints are deliberately **not** paginated. They feed pickers, and a
manager or company that happened to fall on page two would be impossible to select. They
return only an id and a display name to keep the payload small.

---

## Testing

```bash
docker compose exec backend pytest
docker compose exec frontend npm run test
```

The backend suite runs against a real PostgreSQL and Redis rather than mocks, with each test
isolated in its own transaction. Gemini calls are mocked. Coverage is heaviest where the risk
is: the permission matrix, tenant isolation, cycle state transitions, and the evaluation
visibility rules.

Both suites also run outside Docker, with a virtualenv from `requirements-dev.txt` and
`npm install` respectively. The frontend's `node_modules` is otherwise maintained only inside
its container, since Compose bind-mounts just `frontend/src`.

---

## Continuous integration

`.github/workflows/ci.yml` runs on every push and pull request against `main`:

| Job | What it does |
| --- | --- |
| Backend tests | Starts PostgreSQL and Redis service containers and runs `pytest` |
| Migrations apply cleanly | Runs `alembic upgrade head` against an empty database, catching migration-chain problems the test suite would miss |
| Frontend | `npm ci`, then lint, tests, and a production build (which type-checks) |

---

## Project layout

```
backend/
  app/
    api/v1/endpoints/   HTTP routing, dependencies, status codes
    services/           Business rules and state transitions
    crud/               Database queries, no business logic
    schemas/            Pydantic request and response models
    models/             SQLAlchemy tables
    ai/                 Gemini prompt and client
    core/               Config, database, Redis, security, logging
    scripts/            Seed scripts for development and production
  tests/
  alembic/
frontend/
  src/
    pages/              One component per route, colocated tests
    components/         Shared UI, including the shadcn/ui primitives
    lib/                API client, auth context, pagination helpers
```

Requests flow in one direction: endpoint to service to crud. Endpoints stay thin and handle
routing and authorization dependencies, services own the rules and raise HTTP errors, and crud
functions only talk to the database.
