# Usage scenario: Meridyen Yazilim

The README explains the product feature by feature. This document walks through it with one
fictional company and named people instead, for anyone who would rather see the product in use
than read an endpoint list.

## The cast

| Name | Role | Reports to |
| --- | --- | --- |
| Selin Aydin | Company admin | - |
| Burak Demir | HR | - |
| Elif Kaya | Manager | Selin Aydin |
| Zeynep Arslan | Manager | Selin Aydin |
| Deniz Yilmaz | Employee | Elif Kaya |
| Kerem Sahin | Employee | Elif Kaya |
| Mert Koc | Employee | Zeynep Arslan |

All seven belong to one company, "Meridyen Yazilim". There is also a super admin,
`superadmin@platform.io`, who sits outside every company - see [Roles and
permissions](../README.md#roles-and-permissions) for what that means in practice.

Every Meridyen account logs in with the password `meridyen2026`.

## Setup

The cast above is created for real, over the running API, by
[`backend/scripts/seed_demo.py`](../backend/scripts/seed_demo.py). It does not touch the
database directly - it logs in and calls the same endpoints the frontend does, so if the seed
succeeds, the invite and account-creation flow it exercised is known to work.

1. Start the stack and apply migrations as described in [Running it
   locally](../README.md#running-it-locally), then seed the base dev users:

   ```bash
   docker compose up -d
   docker compose exec backend alembic upgrade head
   docker compose exec backend python -m app.scripts.seed_dev_user
   ```

   This is a prerequisite, not a duplicate step: `seed_demo.py` logs in as
   `superadmin@platform.io`, which only exists after this command runs.

2. Run the demo seed. `./backend` is bind-mounted to `/app` in the container, so the script's
   path is relative to that, and it needs pointing at the backend's own internal port
   (`8000`, not the `8001` it's published on for the host):

   ```bash
   docker compose exec backend python scripts/seed_demo.py --base-url http://localhost:8000
   ```

   It is idempotent - rerunning it skips any user that already exists and just re-applies the
   reporting lines, so it's safe to run again after a database reset or to fix a manager
   assignment that got changed by hand.

3. Sign in at http://localhost:5174 as any of the seven addresses above.

## Walkthrough

**Selin sets up the company.** As company admin, Selin's first moves after the seed script
would ordinarily be the invites and reporting lines it just automated - the script exists so
this document doesn't ask you to click through seven invite forms by hand. From here on, sign
in as each character to see what the seed produced and to run the parts that aren't scripted.

**Elif puts work in the pool.** Signed in as Elif Kaya (manager), open **Tasks** and create one
without an assignee - for example "Write the sprint retro notes." It appears in the shared pool,
visible to the whole company, not just Elif's reports.

**Deniz claims it.** Signed in as Deniz Yilmaz, the same task shows up under **Tasks → Pool**.
Claiming it moves it out of the pool and onto Deniz specifically; if a second person tried to
claim it at the same moment, the database - not the app - would decide who got it. Deniz marks
it **Done** once finished.

Elif could instead have assigned a task straight to Deniz or Kerem (her direct reports) without
it ever touching the pool, from the same **Tasks** page. Selin or Burak (company admin/HR) can
assign to anyone in the company; Deniz, as an employee, can only assign work to himself.

**Burak opens a review cycle.** Signed in as Burak Demir (HR), go to **Review Cycles → New
cycle**. Give it a name and a date range that includes today, so Deniz's finished task lands
inside it, add a question or two, and activate it. Activation generates a self-evaluation for
every active person in the company, and a manager evaluation for every employee with an active
manager - so Deniz and Kerem each get one evaluated by Elif, and Mert gets one evaluated by
Zeynep. Selin, Burak, Elif and Zeynep only self-evaluate; nobody reviews HR, admins, or
managers.

**Deniz and Elif fill in their evaluations.** Signed in as Deniz, open **My Evaluations** and
answer the self-evaluation. The task claimed and finished a moment ago appears on the form as
evidence, next to the questions - something concrete to answer against instead of writing from
memory. Signed in as Elif, do the same for the "Evaluate Deniz" card. Until Elif submits, Deniz
sees that review as present but unopenable.

**Someone reads the AI summary.** Once both are submitted, any of Deniz, Elif, Burak or Selin
can generate the summary from the evaluation page. It needs `GEMINI_API_KEY` set in `.env`;
without it this one step won't produce output; everything else above works regardless.

**Selin checks the dashboard.** Signed in as Selin, the **Dashboard** shows an active-cycle
progress card - the same self/manager submission counts as the cycle detail page. Signed in as
any of the seven, the same dashboard shows a personal pending-work list: evaluations still owed
and open tasks still assigned to them, merged and sorted by due date.

## What each role can and cannot do

| | Selin (company admin) | Burak (HR) | Elif / Zeynep (manager) | Deniz / Kerem / Mert (employee) |
| --- | --- | --- | --- | --- |
| Invite new users | Yes, any role | No | No | No |
| Set reporting lines | Yes | Yes | No | No |
| Deactivate a user | Yes, anyone | Yes, except a company admin | No | No |
| Create/activate/close a cycle | Yes | Yes | No | No |
| See a colleague's submitted evaluation | Yes, company-wide | Yes, company-wide | No, not even their own reports' | No |
| Assign a task to anyone active | Yes | Yes | No | No |
| Assign a task to a direct report | Also yes, like any company admin/HR | Also yes | Yes, own reports only | No |
| Claim a pool task for themselves | Yes | Yes | Yes | Yes |
| Complete their own assigned evaluations | Yes | Yes | Yes | Yes |

The manager row is worth stressing: Elif can assign work to Deniz and Kerem, but she cannot see
Deniz's submitted self-evaluation - only Deniz, Selin and Burak can, and Elif's own manager
evaluation of Deniz is a separate thing she fills in herself, not something she reads. Task
oversight and evaluation visibility are deliberately not the same permission.
