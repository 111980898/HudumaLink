# HudumaLink

**A county-style service desk where residents report public problems and watch them get fixed.**

*Swahili: "huduma" = service. HudumaLink links citizens to the departments that serve them.*

> Educational prototype for Murang'a County's seven sub-counties. It is not an official government site; please do not enter real personal data.

Built by **Dennis Kamau**, 

---

## What a resident can do

| Step | Feature |
|---|---|
| Join | Register and sign in (hashed passwords, brute-force lock-out) |
| Report | File a request: category, sub-county, location (with GPS button), description, urgency, optional photo |
| Follow | Get a tracking number such as `HL-261020-9F3A1C`, then see a progress bar, timeline and in-app notifications |
| Check without an account | Public **Track** page: reference number in, status out, with no personal data shown |
| Rate | Give 1-5 stars and a comment once a case is resolved |

## What county staff can do

- **Case queue** sorted by urgency, with search and filters (status, service, sub-county) and pagination
- **Controlled workflow**: Pending → In Progress → Resolved (or Rejected). Illegal jumps are refused, and Resolved cases can be re-opened
- **Routing**: each service maps to a department, and staff can reassign it and change the priority
- **Two kinds of note**: a message the citizen sees and an internal staff-only note
- **Overdue flags** when an open case passes its service-level target (for example water problems: 3 days)
- **Analytics**: open vs resolved donut chart, 14-day trend, cases by service, sub-county and priority, average days to resolve, satisfaction score
- **CSV export** of the current filtered view (formula-injection safe)

## Beyond the brief (bonus features)

Public tracking page · SLA/overdue engine · priority levels · department routing · star ratings · analytics charts drawn in pure SVG · CSV export · dark mode · GPS location · photo preview · print-friendly request page · accessibility (skip link, focus rings, ARIA labels, reduced-motion support) · automated test suite.

---

## Quick start

Requires **Python 3.10+**.

```bash
git clone <your-repo-url> && cd HudumaLink
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py                    # open http://127.0.0.1:5000
```

On first run the app creates its database and, because `DEMO_MODE` is on by default, loads sample data and two demo accounts:

| Role | Email | Password |
|---|---|---|
| Citizen | `citizen@hudumalink.demo` | `Citizen@2026` |
| Admin | `admin@hudumalink.demo` | `Admin@2026` |

### Configuration (environment variables)

| Variable | Purpose | Default |
|---|---|---|
| `SECRET_KEY` | Signs session cookies. **Set it in production.** | dev value |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Creates your own administrator on start-up | none |
| `DEMO_MODE` | `false` disables demo accounts and sample data | `true` |
| `DATABASE_PATH` / `UPLOAD_FOLDER` | Where data is stored | `instance/` (or `/tmp` on Vercel) |

### Run the tests

```bash
pip install pytest
python -m pytest -q
```

---

## How the code is organised

```
HudumaLink/
├── app.py                    entry point (local run + Vercel/Gunicorn)
├── hudumalink/
│   ├── __init__.py           application factory: builds and wires the app
│   ├── config.py             settings read from environment variables
│   ├── constants.py          categories, statuses, sub-counties, allowed transitions
│   ├── db.py                 SQLite connection, schema, demo seed data
│   ├── security.py           CSRF, access control, login throttling, upload checks
│   ├── services.py           business rules and analytics queries
│   ├── filters.py            template helpers (dates, "3 days ago", stars)
│   ├── blueprints/
│   │   ├── public.py         home, track, services, FAQ, photo serving
│   │   ├── auth.py           register / login / logout
│   │   ├── citizen.py        dashboard, new request, detail, feedback, profile
│   │   └── admin.py          case queue, analytics, update, CSV export
│   ├── templates/            Jinja pages grouped by area + reusable macros
│   └── static/               css/main.css, js/app.js, img/logo.svg
├── tests/test_app.py         12 end-to-end tests
├── docs/DEPLOYMENT.md        GitHub + Vercel walkthrough
└── vercel.json, requirements.txt, .env.example
```

**Design principle:** routes stay thin (read input → call a service → render), SQL is always parameterised, and every rule (valid statuses, allowed transitions, SLA days) lives in exactly one file.

## Security notes

CSRF tokens on every POST · hashed passwords · public sign-up can only ever create *citizens* · access checks so residents see only their own cases · uploads verified by file signature, not just file name · open-redirect protection · CSV formula protection · public pages never expose names or contact details.

## Known limitations

SQLite on Vercel lives in temporary storage, so data resets on cold starts. That is fine for a demo; use a hosted database (Postgres, Turso) for real use. There is no email/SMS or password recovery, and the login limiter is in-memory.

## Licence & credits

See [NOTICE.md](NOTICE.md). Original starter: Dennis Kamau. 
