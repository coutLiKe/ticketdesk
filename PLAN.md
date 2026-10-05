# TicketDesk: Milestone Plan

An IT ticketing and asset tracker, built as an interview-ready portfolio project.

**Status:** M0 to M9 complete. M10 (deployment options research) not started; nothing is deployed.

| Milestone | State |
|---|---|
| M0 Scaffold, M1 Database, M2 Auth, M3 Tickets | done |
| M4 Comments | done (implemented by Claude at the owner's request; the original spec and tests are in `docs/M4-comments-spec.md`) |
| M5 Assets, M6 Seed, M7/M8 Front end, M9 Docs | done |
| M10 Deployment options | waiting on you |

## Decisions so far

| Topic | Decision |
|---|---|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.x (sync; 2.1 was installed), Alembic, Pydantic v2 |
| Database | PostgreSQL 16 (official multi-arch image, runs natively on Apple Silicon) |
| Auth | Email + password, bcrypt hashes, short-lived JWT access tokens, signup always creates a `requester`, only admins change roles |
| Front end | Vite + React + TypeScript, React Router, plain CSS, `fetch`, no UI framework |
| Tests | pytest + FastAPI `TestClient`, run against a real Postgres (no SQLite substitute) |
| Lint / format | ruff (backend), ESLint + `tsc` (front end) |
| CI | GitHub Actions: lint + tests on every push |
| Local run | `docker compose up` starts db, api (with migrations) and web |
| Cost | All free and open source. No API keys. |

**Why sync SQLAlchemy:** simpler to reason about and explain, and plenty fast for this scale. Async adds concepts (event loops, async sessions) that don't help this project.

**Why a real Postgres in tests:** tests exercise the same SQL, constraints and enums as production. SQLite hides real bugs.

## Prerequisite: Docker is not installed on this Mac

I checked and `docker` is not on this machine. Before Milestone 0 can be verified, you need to install one of these (all free):

- **Docker Desktop** (free for personal use / education, native Apple Silicon)
- **OrbStack** (free for personal use, lighter and faster)
- **Colima** (fully open source, needs Homebrew, which is also not installed)

I recommend Docker Desktop because it is what most job postings and tutorials assume. I won't install it for you. It needs an admin password and a licence acceptance.

## Roles and permissions (the spec every endpoint is tested against)

| Action | Requester | Technician | Admin |
|---|---|---|---|
| Register / log in / view own profile | yes | yes | yes |
| Create ticket | yes | yes | yes |
| View tickets | own only | all | all |
| Comment on a ticket | own tickets | all | all |
| Set priority | no | yes | yes |
| Assign ticket | no | yes (to technicians) | yes |
| Change status | close own ticket only | any valid transition | any valid transition |
| List / view assets | own assigned only | all | all |
| Create / edit assets, assign to users, link to tickets | no | yes | yes |
| List users, change roles, deactivate users | no | no | yes |

**Status flow:** `open -> in_progress -> resolved -> closed`. A resolved ticket can be reopened to `in_progress`. Invalid jumps return 409. This rule is a small state machine you can explain.

I'll confirm any ambiguous cell with you in the relevant milestone before coding it.

## Data model (first draft)

- `users`: id, email (unique), full_name, hashed_password, role, is_active, created_at
- `tickets`: id, title, description, status, priority, requester_id, assignee_id, created_at, updated_at
- `comments`: id, ticket_id, author_id, body, created_at
- `assets`: id, asset_tag (unique), name, type, serial_number, status, assigned_user_id, created_at
- `ticket_assets`: ticket_id, asset_id (many-to-many link table)

## Milestones

Each milestone ends with a summary (what I built, why, what you should be able to explain), then I stop and wait for you. Each is a series of small commits.

### M0: Scaffold and tooling
- `git init`, `.gitignore`, folder layout (`backend/`, `frontend/`, `docs/`)
- Backend skeleton with a `/health` endpoint and the first passing test
- `docker-compose.yml` with `db` and `api`, healthcheck, env file example
- ruff config and a GitHub Actions workflow that runs lint + tests
- **You should be able to explain:** what Docker Compose does, why the API waits for the DB, what CI does on a push.

### M1: Database layer and migrations
- SQLAlchemy models for all tables, enums for role / status / priority
- Alembic set up, first migration generated and reviewed by hand
- Test fixtures: a fresh database per test run, a rollback per test
- **Explain:** ORM vs raw SQL, what a migration is and why we don't use `create_all`, foreign keys, the many-to-many link table, sessions and transactions.

### M2: Authentication and roles
- `POST /auth/register`, `POST /auth/login` (returns JWT), `GET /users/me`
- Password hashing, token creation and verification
- Reusable dependencies: `get_current_user`, `require_role(...)`
- Admin endpoints: list users, change role, deactivate
- Tests for each endpoint, including 401 (no token), 403 (wrong role), and bad credentials
- **Explain:** hashing vs encryption, what a JWT contains and why it isn't secret, 401 vs 403, FastAPI dependency injection.

### M3: Tickets
- Create, list (filter by status / priority / assignee, text search, pagination), get, update
- Assign, set priority, status transitions with the state machine
- Permission rules from the table above, enforced in one place
- Tests for every endpoint and every permission cell
- **Explain:** query building with filters, pagination, why permission checks live on the server, the state machine, 404 vs 403 for tickets you can't see.

### M4: Comments (YOU implement this one)
I write:
- The route stubs and Pydantic schemas (empty bodies)
- A full set of **failing tests** that act as your spec, covering happy paths and permissions
- A short spec doc listing exactly what each endpoint must do

You write:
- The implementation, using M2 and M3 as your reference

Then I review your code for correctness, security, style and testability, and we iterate until green.
- **Explain:** everything. This is your milestone, and the best interview story in the project.

*Note:* I'm reading "leave ticket comments for me" as "the ticket comments feature". If you meant something else, tell me.

### M5: Assets
- Asset CRUD, assign to a user, link and unlink to tickets
- Requesters see only assets assigned to them
- Tests for every endpoint and permission
- **Explain:** many-to-many relationships, nullable foreign keys, unique constraints.

### M6: Seed script and demo data
- `python -m app.seed` creates demo users in all three roles, tickets in every status, comments, and assets
- Idempotent (safe to run twice), with demo credentials documented in the README
- Hooked into `docker compose` as an optional profile
- **Explain:** why idempotent, why demo data lives outside migrations.

### M7: React front end, part 1
- Vite + TS scaffold, login / register, token storage, protected routes
- Ticket list with filters and search, ticket detail with comments, create ticket form
- Role-aware UI (hide actions the role can't do; the server still enforces them)
- Added to `docker compose`
- **Explain:** why hiding buttons isn't security, where the token is stored and the tradeoffs (localStorage vs httpOnly cookie), CORS.

### M8: React front end, part 2
- Assign and prioritize tickets, status controls, asset pages, admin user management
- ESLint + `tsc` in CI
- **Explain:** component structure, state handling, how the UI maps to API errors.

### M9: Docs, CI polish, screenshots
- README: what it is, setup steps, architecture diagram (Mermaid, renders on GitHub), API overview, design decisions, how to run tests
- Screenshots of the running app (taken by me from the real UI)
- CI badge, coverage report
- Final check that a clean clone runs with `docker compose up`
- **Explain:** the whole architecture end to end.

### M10: Deployment options (research only)
- A written comparison of free-tier hosts with their limits (compute, database, sleep behaviour, expiry), verified against current docs at the time
- Candidates I'll check: Render, Fly.io, Railway, Koyeb, Neon (Postgres), Supabase (Postgres), Vercel / Netlify / Cloudflare Pages (front end)
- **I will not deploy anything until you pick one.** Free tiers change often, so I'll check current terms before listing them.

## How I'll work

- Commits are small and use clear messages (e.g. `Add Ticket model and status enum`). I commit locally only. I won't push anywhere. You add the GitHub remote when you're ready.
- I verify each milestone by actually running the tests and (once Docker is installed) `docker compose up` before I report it done. If something fails or I couldn't run it, I'll say so.
- I'll keep each summary short and aimed at interview prep, with a few "could you answer this?" questions at the end.

## Open items for you

1. Approve this plan, or tell me what to change.
2. Install Docker Desktop (or OrbStack) before M0 verification.
3. Confirm the permissions table above, especially: requesters can close their own resolved tickets, and requesters can see assets assigned to them.
