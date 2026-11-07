# Huduma Link deployment

## GitHub

Create or use a repository named `Huduma Link`, then push the project root. Do not commit `.env`, `instance/`, `node_modules/`, or generated caches.

```bash
git add .
git commit -m "Build Huduma Link public service request portal"
git branch -M main
git remote add origin https://github.com/<your-account>/<your-repository>.git
git push -u origin main
```

## Vercel

Import the GitHub repository into Vercel. The existing `vercel.json` is intentionally unchanged, so the current Vercel route remains stable.

Set these environment variables in Vercel:

- `SECRET_KEY`: a long random session-signing value
- `DEMO_MODE`: `1` for assessment/demo accounts or `0` for a clean deployment
- `ADMIN_EMAIL` and `ADMIN_PASSWORD`: an approved administrator account
- `SESSION_COOKIE_SECURE`: `true` for HTTPS

For assessment mode, `DEMO_MODE=1` exposes the documented demo accounts. Before a real public launch, set `DEMO_MODE=0`, replace the demo administrator with a private `ADMIN_EMAIL` and `ADMIN_PASSWORD`, and set a new long random `SECRET_KEY`. The application refuses to start outside tests if a production/serverless secret is missing.

The application uses Neon PostgreSQL when `DATABASE_URL` is present and SQLite for local tests. Uploaded images should use durable object storage in production.
