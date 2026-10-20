# Deploying HudumaLink

## 1. Put the code on GitHub
1. Create an empty repository on <https://github.com/new> (name it `HudumaLink`, no README).
2. In the project folder:
```bash
git init
git add .
git commit -m "HudumaLink: extended build of the Murang'a service request starter"
git branch -M main
git remote add origin https://github.com/<your-username>/HudumaLink.git
git push -u origin main
```

## 2. Deploy on Vercel
1. Sign in at <https://vercel.com> with GitHub, then **Add New → Project** and import `HudumaLink`.
2. Framework preset: **Flask** (auto-detected from `app.py`). Leave build settings as they are.
3. Under **Environment Variables** add:
   - `SECRET_KEY` = a long random string (generate one: `python -c "import secrets; print(secrets.token_hex(32))"`)
   - `DEMO_MODE` = `true` (keeps the demo accounts for markers)
4. Click **Deploy**. Your live link looks like `https://hudumalink.vercel.app`.

## 3. Things to know
- Vercel's disk is temporary: data and uploaded photos reset when the function restarts. Demo data is re-seeded automatically, so the site is never empty.
- To use your own admin, set `ADMIN_EMAIL` and `ADMIN_PASSWORD` and redeploy.
- If the deploy fails, open the build log in Vercel and check that `requirements.txt` lists Flask.
