# Deployment options (research only)

**Nothing is deployed.** This page lists free-tier hosts and their limits so you can choose.
Limits were read from each provider's own pricing or docs pages on **2026-10-05**. Free tiers
change often, so re-check the linked page before you commit. Items I could not confirm are
marked **unverified**.

## What has to be hosted

| Piece | Today (Docker Compose) | Needs |
|---|---|---|
| Database | `postgres:16` container | A managed or self-run PostgreSQL |
| API | FastAPI container, runs `alembic upgrade head` on start | Anywhere that runs a Docker image or Python |
| Front end | Vite **dev server** container, proxies `/api` to the API | A production build (`npm run build` makes static files in `dist/`) |

## Database options

| Host | Free limits (verified) | Catches |
|---|---|---|
| [Neon](https://neon.com/pricing) | 1 GB per project, 100 CU-hours per project per month, compute suspends after 5 minutes idle and this can't be turned off, 5 GB egress. Free plan is "permanent (not a trial)". No credit card. | First request after idle is slower while compute wakes up (I did not measure how long). |
| [Supabase](https://supabase.com/pricing) | 500 MB database, 2 active projects, 200 pooler connections, 5 GB egress. | **Projects pause after 1 week of inactivity**, so a portfolio demo can be asleep when a recruiter visits. Card requirement unverified. |
| [Render Postgres](https://render.com/docs/free) | 1 GB, one free database per workspace. | **Expires 30 days after creation** (14-day grace to upgrade), no backups. Unsuitable for a long-lived portfolio. |
| [Koyeb Postgres](https://www.koyeb.com/pricing) | 0.25 vCPU, 1 GB RAM, 1 GB storage, scales to zero. | Listed as a dev/staging tier ("4h/day"). The exact monthly allowance was unclear on the page. |

## API (backend container) options

| Host | Free limits (verified) | Catches |
|---|---|---|
| [Render web service](https://render.com/docs/free) | 750 free instance hours per workspace per month. Spins down after 15 minutes without traffic. | **About one minute to wake up** (their words). RAM and CPU for the free instance were not stated on the page I read (**unverified**). Card requirement **unverified**. |
| [Koyeb](https://www.koyeb.com/docs/faqs/pricing) | One free web service per organization: 512 MB RAM, 0.1 vCPU, 2 GB SSD, Frankfurt or Washington D.C. "Never charged." Scale-to-zero is not available yet, so it stays running. | **Credit card required** (a $29 hold is placed and released). 0.1 vCPU is slow for bcrypt at cost 12, so expect slow logins. |
| [Railway](https://docs.railway.com/reference/pricing/plans) | Free plan: $1 of credit per month. Trial: one-time $5. When credits reach zero, workloads stop. | The pricing page says no card is needed, but the docs say a post-paid card is now required. **Conflicting sources.** $1 a month will not run an always-on API and database. |
| [Fly.io](https://docs.fly.io/about/pricing) | **No free tier for new accounts.** Trial: 2 hours of runtime or 7 days. | Cheapest always-on machine is about $2.19 per 30 days (256 MB). Fails the "zero cost" requirement. |
| Oracle Cloud Always Free | Reported (InfoQ, 2026-07, not Oracle's own page, which blocked my fetch): Ampere A1 allowance cut to **2 OCPUs and 12 GB RAM** from June 15, 2026. Idle instances can be reclaimed (CPU, network and memory under 20% for 7 days). | A real VM, so `docker compose up` works almost as-is. Needs a card to sign up, capacity can be hard to get, and you maintain the server (updates, HTTPS, backups). |

## Front-end (static site) options

| Host | Free limits (verified) | Catches |
|---|---|---|
| [Cloudflare Pages](https://developers.cloudflare.com/pages/platform/limits/) | 500 builds per month, 20,000 files per site, 25 MiB per file, 100 projects. | Bandwidth limit was not on the page (**unverified**). |
| [Vercel Hobby](https://vercel.com/docs/limits) | 100 deployments per day, 45 minute builds, 200 projects, 100 MB static upload. | Fair-use and non-commercial terms **not checked**; read them before using it for anything beyond a portfolio. |
| [Netlify](https://www.netlify.com/pricing/) | Free plan shows a 300 credit limit. | What a credit buys, and what happens when it runs out, was **not clear** from the page. |
| Render static site | Part of Render's free offering. | Limits **not verified**. |

## Suggested combinations

Ranked for your goals: zero cost, always available for a recruiter, little extra code.

1. **Render (API) + Neon (database) + Cloudflare Pages (front end).** Neon is the only database
   here that is permanent, free and card-free. Render's free API sleeps, so the first visit
   after a quiet period takes about a minute. That is the main cost of "free". It is also a
   good interview talking point: you can explain cold starts and what you'd pay for to avoid them.
2. **Everything on one Oracle Cloud VM** with Docker Compose. Most realistic ops experience and no
   sleeping, but it needs a credit card, can fail on capacity, and you own security updates and HTTPS.
3. **Koyeb (API) + Neon + Cloudflare Pages.** No sleeping API, but needs a card, and 0.1 vCPU is slow.

Not recommended: Render Postgres (expires in 30 days), Supabase (pauses after a week), Fly.io
(not free), Railway (credit too small, conflicting terms).

## Changes the code needs before any deployment

These are small, and I would do them in a new milestone once you pick a host.

1. **Production front-end build.** Serve `frontend/dist` as static files. The Vite dev server is
   for local development only.
2. **Reach the API from the browser.** Locally, `/api` is proxied. On a static host the API is on
   a different domain, so either add CORS to FastAPI and make the API base URL a build setting
   (`VITE_API_URL`), or use the static host's rewrite rules to proxy `/api`.
3. **Environment variables.** Set a real `SECRET_KEY` (`openssl rand -hex 32`) and `DATABASE_URL`.
   Hosted databases such as Neon usually require TLS (`sslmode=require`), and the URL must use the
   `postgresql+psycopg://` scheme.
4. **No demo seed in production** (it uses a published password). Instead create the first admin
   through a one-off command or a locked-down script.
5. **Migrations on start** are fine for a single instance. On a platform that sleeps, they also run
   on every wake-up, which adds to cold-start time.
6. **Login rate limiting.** A public API should not allow unlimited password guesses.
7. **Optional:** a `/health/db` endpoint, because hosts use health checks to decide when to restart.

## Decisions for you

1. Which combination (or another host)?
2. Are you comfortable putting a credit card on file? Options 2 and 3 need one, and Render's
   requirement is unconfirmed.
3. Is a one-minute cold start acceptable for the demo, or do you want an always-on host?

I won't create any accounts or deploy anything until you answer.
