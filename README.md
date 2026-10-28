# Huduma Link

**Public Service Request System — mini eCitizen-style portal**

Huduma Link gives citizens one clear place to register, report local service problems, follow progress, and see the next action. Administrators get a protected service queue for reviewing, routing, updating, and analysing requests.

> Educational assessment project. It is not an official government website. Do not enter real personal or sensitive information.

## Assessment requirements covered

- Citizen registration and secure login
- Citizen/Admin workspace selector on the login screen
- Public service request submission
- Categories such as broken streetlights, water, garbage, roads, and public health
- Location, description, priority, phone number, and optional image upload
- Admin dashboard with queue, filters, search, status controls, and CSV export
- Status workflow: **Pending → In Progress → Resolved** (plus Rejected when necessary)
- Public tracking by reference number without signing in
- Analytics for open versus resolved cases
- Responsive mini eCitizen-style interface for desktop and mobile

## Extra features

- SLA targets and overdue case flags
- Department routing
- Citizen notifications and request timeline
- Citizen feedback and 1–5 star rating after resolution
- Search across services, FAQs, and request references
- GPS-assisted location capture
- Photo validation and preview
- Dark mode, reduced-motion support, keyboard-friendly navigation, skip links, and visible focus states
- Print-friendly request details
- Formula-safe CSV export
- Spectral Drape-inspired animated dot background in the hero
- Scroll-reactive Vortex particle tunnel between the service workflow and live request feed
- Murang'a County coat of arms identity mark used as a restrained portal context cue

## Roles and access

### Citizen

Citizens can create accounts, submit service requests, upload an optional image, view their own dashboard, follow timelines, receive updates, and rate resolved cases.

### Administrator

Administrators can review every request, filter the queue, assign departments, change priority, move requests through the controlled workflow, write public/internal notes, export CSV data, and view analytics.

The login form includes the required Citizen/Administrator dropdown. Selecting Administrator does not grant access by itself: the email must belong to an approved administrator account.

## Quick start

Requires Python 3.10+.

```bash
git clone <your-repository-url>
cd HudumaLink
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Development mode with sample accounts and sample requests (the default)
export DEMO_MODE=1
python app.py
```

Open `http://127.0.0.1:3000`.

Demo accounts when `DEMO_MODE=1`:

| Role | Email | Password |
|---|---|---|
| Citizen | `citizen@hudumalink.demo` | `Citizen@2026` |
| Administrator | `admin@hudumalink.demo` | `Admin@2026` |

To test the admin workflow, open **Sign in**, choose **Administrator — manage the service queue**, and use the Administrator credentials above. Public registration creates Citizen accounts only.

For a clean empty database, use `DEMO_MODE=0` and configure an administrator:

```bash
export DEMO_MODE=0
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD='ChangeMe123'
export SECRET_KEY='use-a-long-random-value'
python app.py
```

For Vercel production, connect the project to Neon and let Vercel provide the pooled `DATABASE_URL` environment variable. The application automatically uses PostgreSQL when that variable is present and keeps SQLite for local development and tests.

## Environment variables

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Signs session cookies; set a strong value outside local development |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Creates an approved administrator on first startup |
| `DEMO_MODE` | Loads assessment sample data and demo accounts; defaults to `1`, set to `0` for a clean database |
| `DATABASE_URL` | Neon PostgreSQL connection string for durable production data; Vercel supplies this after the Neon integration is connected |
| `DATABASE_PATH` | SQLite database file location |
| `UPLOAD_FOLDER` | Uploaded request-image location |
| `SESSION_COOKIE_SECURE` | Keep `true` for HTTPS Preview; use `false` for local HTTP |

## Run the tests

```bash
pip install pytest
python -m pytest -q
```

## Project structure

```text
HudumaLink/
├── app.py                         Flask entry point for local run and Vercel
├── hudumalink/
│   ├── __init__.py                application factory and shared context
│   ├── config.py                  environment configuration
│   ├── constants.py               categories, roles, statuses, and service rules
│   ├── db.py                      SQLite/Neon schema and initialization
│   ├── security.py                CSRF, login throttling, access control, upload checks
│   ├── services.py                business rules and analytics queries
│   ├── blueprints/                public, auth, citizen, and admin routes
│   ├── templates/                 responsive Jinja pages and reusable macros
│   └── static/                    CSS, JavaScript, logo, and route manifest
├── Dockerfile                     production container and health-check entrypoint
├── components/                    Spectral Drape and Vortex adapters for React surfaces
├── components.json                React Bits Pro registry configuration
├── tests/test_app.py               end-to-end assessment tests
├── requirements.txt
└── vercel.json                     existing Vercel routing configuration
```

## Vercel

The existing `vercel.json` routing configuration is preserved. Connect the repository to Vercel and add the production environment variables above. For a production database, replace temporary SQLite storage with a hosted database because serverless instances can be short-lived.

## Code quality and safety

Routes stay thin, SQL queries are parameterised, business rules live in one service layer, passwords are hashed, POST requests use CSRF protection, public signup creates citizens only, admin routes are protected, uploads are checked by file signature, and public tracking never exposes citizen contact details.
