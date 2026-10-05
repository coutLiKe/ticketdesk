# Deploy runbook: Render + Neon + GitHub Pages

You do the account steps (sign-ups, pasting secrets). Everything in the repo is already
prepared: `render.yaml`, the production settings, and the GitHub Pages workflow.

> Change of plan: the front end is hosted on **GitHub Pages**, not Cloudflare Pages. It needs no
> extra account or card and deploys from code (`.github/workflows/pages.yml`).

```
Browser ──> GitHub Pages (static React build)
   │
   └─ API calls (CORS) ──> Render web service (FastAPI Docker image) ──> Neon PostgreSQL
```

Dashboards change. If a button is not where this page says, use the linked docs and keep the
intent: **settings go in each provider's dashboard, never into git.**

> Verified here: the API image starts in production mode, honours `$PORT`, accepts a plain
> `postgresql://` URL, enforces CORS and rate-limits logins. **Not verified:** the provider
> dashboards themselves, because I can't sign in to them for you.

## 0. Put the code on GitHub

Render and GitHub Pages both deploy from this repository.

1. Create an empty repository on GitHub (private is fine). Do not add a README or licence.
2. From the project folder:

```bash
git remote add origin https://github.com/<you>/<repo>.git
git push -u origin main
```

3. Check that CI goes green on the Actions tab, and then add the badge line from the README.
4. Confirm `git ls-files | grep -i '\.env$'` prints nothing. Only `.env.example` is tracked.

## 1. Database: Neon

1. Sign up at [neon.com](https://neon.com) and create a project. Choose a region close to where
   you will put Render (same continent at least).
2. Open the connection details and copy the **direct** (not pooled) connection string. It looks
   like `postgresql://user:password@ep-xxxx.region.aws.neon.tech/dbname?sslmode=require`.
   - Direct is simpler: one small API doesn't need a pooler, and migrations behave better.
   - Treat this string like a password.
3. Nothing else to configure. The API creates the tables itself on first start.

## 2. API: Render

1. Sign up at [render.com](https://render.com) and connect your GitHub account.
2. **New → Blueprint**, pick the repository. Render reads `render.yaml` and proposes a free web
   service named `ticketdesk-api`.
3. When prompted for the environment variables it can't generate:
   - `DATABASE_URL`: paste the Neon string from step 1.
   - `CORS_ORIGINS`: type `https://placeholder.invalid` for now. You set the real value in step 4.
   - `SECRET_KEY` and `ENVIRONMENT` are filled in for you.
4. Deploy. Watch the logs for `alembic` running migrations, then `Uvicorn running`.
5. Open `https://<your-service>.onrender.com/health`. Expect `{"status":"ok"}`. Also open `/docs`.

If the service is asleep the first request takes about a minute. That is normal on the free plan.

## 3. Front end: GitHub Pages (automatic)

Nothing to click once Pages is enabled. `.github/workflows/pages.yml` builds the React app on
every push that touches `frontend/` and publishes it at
`https://<owner>.github.io/ticketdesk/`.

- One-time setting: repository **Settings → Pages → Source: GitHub Actions** (already done if you
  used the setup in this repo's history).
- `VITE_API_URL` (the Render address) and `VITE_BASE` (`/ticketdesk/`) are set in the workflow.
  They are baked into the JavaScript at build time, so changing them means another run.
- GitHub Pages serves `404.html` for unknown paths. The workflow copies `index.html` there so
  links like `/ticketdesk/tickets/3` still work when reloaded.

## 4. Connect them (CORS)

`render.yaml` sets `CORS_ORIGINS` to `https://coutlike.github.io` (scheme and host only, never a
path). Render applies the file whenever you push. To add another origin later (a custom domain),
list them comma-separated.

## 5. Create the first admin

Do **not** run the demo seed against production unless you decide on purpose to make a public
demo (see step 6).

1. Register an account in the live app.
2. Promote it from your Mac, with the Neon string kept out of your shell history:

```bash
cd backend
read -rs DATABASE_URL && export DATABASE_URL   # paste the Neon string, press Enter
.venv/bin/python -m app.make_admin you@example.com
unset DATABASE_URL
```

3. Log out and back in. You now see the Users page.

## 6. Optional: demo data

Recruiters open an empty app and see nothing. You can load the demo data:

```bash
cd backend
read -rs DATABASE_URL && export DATABASE_URL
.venv/bin/python -m app.seed
unset DATABASE_URL
```

Be aware of the trade-off: the seed creates admin and technician accounts with the **published**
password `demo1234`, so anyone who reads your README can log in as an admin. That is acceptable
for a throwaway public demo with no real data, and it should be a conscious choice. If you do
it, never use a real person's data, and change the admin from step 5 to a private account.

## 7. Verify

- [ ] `/health` returns ok and `/docs` loads on the Render URL.
- [ ] The Pages site loads, and you can register and log in (browser dev tools show no CORS errors).
- [ ] As a requester you cannot see the Users page, and `GET /users` returns 403 with your token.
- [ ] Six wrong passwords in a row return 429.
- [ ] After 20 minutes of inactivity the first request is slow, then fast. You know why.

## Costs and limits to watch (checked 2026-10-05, see `deployment.md`)

- Render: 750 free instance hours per workspace per month. One always-awake service is at most
  744 hours in a 31-day month, so a single service fits. A second service would not.
- Render sleeps after 15 minutes idle; wake-up is about a minute.
- Neon: 1 GB storage, 100 compute-hours per project per month, suspends after 5 minutes idle.
- GitHub Pages: free for public repositories (soft limits: 1 GB site, 100 GB bandwidth a month,
  10 builds an hour; check GitHub's current docs).
- **Do not point an uptime pinger at `/health` to keep Render awake.** It would burn instance
  hours and keep it from sleeping, which defeats the free plan. `/health` deliberately does not
  query the database, so health checks never wake Neon either.
- Render did not ask for a credit card when this was deployed.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Browser console: "blocked by CORS policy" | `CORS_ORIGINS` doesn't exactly match the Pages URL (check `https`, no trailing slash), or Render hasn't redeployed yet. |
| Login page shows a network error right after a quiet period | The API is waking up. Wait a minute and retry. |
| Render deploy fails with "SECRET_KEY must be set" | `ENVIRONMENT` is `production` but `SECRET_KEY` is missing or still starts with `dev-only`. |
| Render logs: SSL or connection errors | The Neon string was truncated, or lacks `sslmode=require`. Copy it again. |
| The site calls `/api/...` and gets 404 | `VITE_API_URL` was not set at build time. Fix `pages.yml` and push. |
| 429 on login for a legitimate user | Too many failed attempts; they clear after 15 minutes or when the service restarts. |

## Updating and tearing down

- Updating: push to `main`. Render redeploys (`autoDeploy: true`) and the Pages workflow republishes the front end.
  CI runs on the same push; a red CI does not by itself stop a deploy.
- Rolling back: both dashboards let you redeploy an earlier build. Database migrations don't roll
  back automatically.
- Tearing down: delete the Render service and the Neon project, and disable Pages in repository settings. Deleting the
  Neon project deletes the data.

## Security notes for the real deployment

- The Neon string and `SECRET_KEY` live only in provider dashboards. If either leaks, rotate it:
  reset the database password in Neon, or change `SECRET_KEY` (this logs everyone out).
- Login rate limits are kept in memory. They reset when the service restarts or wakes from sleep,
  and the limit by IP address can be sidestepped behind a proxy. The per-email limit is the
  backstop. A shared store such as Redis would make this robust.
- Tokens are kept in `localStorage`, which belongs to the whole origin `<owner>.github.io`, so any
  other site you host under that name could read it. A custom domain would isolate it. See the
  README for the wider trade-off.
