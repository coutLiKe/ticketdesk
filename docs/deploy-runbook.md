# Deploy runbook: Render + Neon + Cloudflare Pages

You do the account steps (sign-ups, pasting secrets, clicking Deploy). Everything in the repo
is already prepared: `render.yaml`, the production settings, and the front-end build.

```
Browser ──> Cloudflare Pages (static React build)
   │
   └─ API calls (CORS) ──> Render web service (FastAPI Docker image) ──> Neon PostgreSQL
```

Dashboards change. If a button is not where this page says, use the linked docs and keep the
intent: **settings go in each provider's dashboard, never into git.**

> Verified here: the API image starts in production mode, honours `$PORT`, accepts a plain
> `postgresql://` URL, enforces CORS and rate-limits logins. **Not verified:** the provider
> dashboards themselves, because I can't sign in to them for you.

## 0. Put the code on GitHub

Render and Cloudflare Pages both deploy from a Git repository.

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

## 3. Front end: Cloudflare Pages

1. Sign up at [cloudflare.com](https://dash.cloudflare.com), then **Workers & Pages → Create →
   Pages → Connect to Git** and choose the repository.
2. Build settings:

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Build command | `npm run build` |
| Build output directory | `dist` |

3. Environment variables (production):

| Name | Value |
|---|---|
| `VITE_API_URL` | `https://<your-service>.onrender.com` (no trailing slash) |
| `NODE_VERSION` | `22` |

`VITE_API_URL` is baked into the JavaScript at build time. If you change it, you must redeploy.

4. Deploy and note the URL, for example `https://ticketdesk.pages.dev`.

Pages serves `index.html` for unknown paths when there is no `404.html`, so React Router links
such as `/tickets/3` work on reload. If you ever see a 404 on reload, add a `_redirects` file
containing `/* /index.html 200` to `frontend/public/`.

## 4. Connect them (CORS)

In Render, set `CORS_ORIGINS` to your exact Pages URL (scheme and host, no path, no trailing
slash), for example `https://ticketdesk.pages.dev`, and let it redeploy. Several origins can be
comma-separated (for example a custom domain later).

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
- Cloudflare Pages: 500 builds a month.
- **Do not point an uptime pinger at `/health` to keep Render awake.** It would burn instance
  hours and keep it from sleeping, which defeats the free plan. `/health` deliberately does not
  query the database, so health checks never wake Neon either.
- I could not confirm whether Render and Cloudflare require a credit card. If either asks for
  one, you decide whether to continue.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Browser console: "blocked by CORS policy" | `CORS_ORIGINS` doesn't exactly match the Pages URL (check `https`, no trailing slash), or Render hasn't redeployed yet. |
| Login page shows a network error right after a quiet period | The API is waking up. Wait a minute and retry. |
| Render deploy fails with "SECRET_KEY must be set" | `ENVIRONMENT` is `production` but `SECRET_KEY` is missing or still starts with `dev-only`. |
| Render logs: SSL or connection errors | The Neon string was truncated, or lacks `sslmode=require`. Copy it again. |
| Pages site calls `/api/...` and gets 404 | `VITE_API_URL` was not set at build time. Set it and redeploy. |
| 429 on login for a legitimate user | Too many failed attempts; they clear after 15 minutes or when the service restarts. |

## Updating and tearing down

- Updating: push to `main`. Render and Pages both redeploy automatically (`autoDeploy: true`).
  CI runs on the same push; a red CI does not by itself stop a deploy.
- Rolling back: both dashboards let you redeploy an earlier build. Database migrations don't roll
  back automatically.
- Tearing down: delete the Render service, the Pages project and the Neon project. Deleting the
  Neon project deletes the data.

## Security notes for the real deployment

- The Neon string and `SECRET_KEY` live only in provider dashboards. If either leaks, rotate it:
  reset the database password in Neon, or change `SECRET_KEY` (this logs everyone out).
- Login rate limits are kept in memory. They reset when the service restarts or wakes from sleep,
  and the limit by IP address can be sidestepped behind a proxy. The per-email limit is the
  backstop. A shared store such as Redis would make this robust.
- Tokens are kept in `localStorage`. See the README for the trade-off.
