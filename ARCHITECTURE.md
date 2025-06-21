# Architecture Overview

This document describes the overall structure of the VoteBuddy code base. VoteBuddy is a Flask 3 application using SQLAlchemy ORM and Alembic migrations. Functionality is organised into blueprints so each feature area is isolated and easy to maintain.

## System Architecture

VoteBuddy normally runs behind **Nginx** with **Gunicorn** serving the Flask
application from `wsgi.py`.  The application factory `create_app` in
`app/__init__.py` initialises SQLAlchemy, Mail and other extensions.  Database
access goes through PostgreSQL and SQLAlchemy.  A built‑in **APScheduler**
instance handles routine jobs such as reminder emails and token cleanup.  For
larger deployments, **Celery** with Redis can be added for asynchronous tasks.
Outbound email uses SMTP or AWS SES and static files are served from local
storage or optionally S3.

The stack can be visualised as:

```text
Nginx
  ↳ Gunicorn (Flask)
       ↳ Blueprints
            auth/
            meetings/
            voting/
            admin/
Postgres  ─── SQLAlchemy ORM
Redis (optional) ─── Celery worker (optional)
Local storage ─── Static files & document exports
SES/SMTP  ─── Outbound mail
```

## Directory Tree

```
.
├── AGENTS.md
├── Dockerfile
├── LICENCE.md
├── README.md
├── app
│   ├── __init__.py
│   ├── admin
│   ├── api
│   ├── auth
│   ├── cli.py
│   ├── comments
│   ├── extensions.py
│   ├── help
│   ├── meetings
│   ├── models.py
│   ├── notifications
│   ├── permissions.py
│   ├── ro
│   ├── routes.py
│   ├── services
│   ├── static
│   ├── submissions
│   ├── tasks.py
│   ├── templates
│   ├── utils.py
│   └── voting
├── assets
│   ├── icons
│   ├── logo.png
│   └── screenshots
├── config.py
├── docker-compose.yml
├── docker-entrypoint.sh
├── docs
│   ├── api.yaml
│   ├── app-settings-guidance.md
│   ├── full-database-structure.md
│   ├── help-voting.md
│   ├── member-import.md
│   ├── original-british-powerlifting-voting-process-motion.md
│   ├── prd.md
│   ├── template-motion.md
│   ├── ui-ux-design-guidance.md
│   └── unit-test-strategy.md
├── migrations
│   ├── README
│   ├── alembic.ini
│   ├── env.py
│   ├── script.py.mako
│   └── versions
├── package-lock.json
├── package.json
├── requirements.txt
├── scripts
│   └── zap_baseline.py
├── tailwind.config.cjs
├── tests
│   ├── test_admin_audit.py
│   ├── test_admin_dashboard.py
│   ├── test_admin_permissions.py
│   ├── test_admin_user.py
│   ├── test_api.py
│   ├── test_auth.py
│   ├── test_comments.py
│   ├── test_email_service.py
│   ├── test_errors.py
│   ├── test_extension_reason.py
│   ├── test_footer_template.py
│   ├── test_form_templates.py
│   ├── test_help.py
│   ├── test_meetings_routes.py
│   ├── test_models.py
│   ├── test_navigation.py
│   ├── test_notifications.py
│   ├── test_objections.py
│   ├── test_password_reset.py
│   ├── test_pdf_export.py
│   ├── test_permissions.py
│   ├── test_prod_secret.py
│   ├── test_public_meetings.py
│   ├── test_public_results.py
│   ├── test_resend_rate_limit.py
│   ├── test_results_index.py
│   ├── test_ro_dashboard.py
│   ├── test_runoff.py
│   ├── test_scheduler.py
│   ├── test_security_headers.py
│   ├── test_settings.py
│   ├── test_submissions.py
│   ├── test_utils.py
│   └── test_voting.py
└── wsgi.py

23 directories, 72 files
```

## Root Files

- **AGENTS.md** – Contributor guidance and development rules.
- **Dockerfile** – Defines the production container image.
- **docker-compose.yml** – Local development stack for PostgreSQL etc.
- **docker-entrypoint.sh** – Entrypoint script used in the container.
- **LICENCE.md** – Project licence terms.
- **README.md** – Project overview and setup instructions.
- **config.py** – Application configuration classes loaded via environment variables.
- **requirements.txt** – Python package requirements.
- **package.json** / **package-lock.json** – Node dependencies for Tailwind build.
- **tailwind.config.cjs** – Tailwind build configuration.
- **wsgi.py** – WSGI entrypoint creating the Flask app.

## Application Package `app/`

### Core modules
- **\_\_init\_\_.py** – Factory `create_app` sets up extensions, registers blueprints and CLI commands, and defines template helpers.
- **cli.py** – Custom Flask CLI commands (create-admin, generate-fake-data).
- **extensions.py** – Initialises SQLAlchemy, Migrate, LoginManager, CSRF, Bcrypt, Mail, APScheduler and Limiter.
- **models.py** – SQLAlchemy models for users, roles, meetings, motions, amendments, votes, tokens and settings.
- **permissions.py** – Permission constants and decorator for role-based access control.
- **routes.py** – Public landing pages, results views and resend link handler.
- **tasks.py** – APScheduler jobs for email reminders and token cleanup.
- **utils.py** – Helpers for Markdown rendering, caching and config lookup.

### Blueprints
Each subfolder implements a blueprint with its own templates and forms.
- **admin/** – Admin dashboard and management UI.
  - `routes.py` – All admin views and actions.
  - `forms.py` – User, role, permission and settings forms.
  - `\_\_init\_\_.py` – Blueprint setup.
- **api/** – Token-based JSON API.
  - `routes.py` – Read-only endpoints for meeting data.
  - `\_\_init\_\_.py` – Blueprint setup.
- **auth/** – Login and password reset flows.
  - `routes.py` – Authentication pages.
  - `utils.py` – Send password reset emails.
  - `\_\_init\_\_.py` – Blueprint setup.
- **comments/** – Member comments on motions.
  - `routes.py` – CRUD handlers.
  - `\_\_init\_\_.py` – Blueprint setup.
- **help/** – Static help section.
  - `routes.py` – Serve help pages.
  - `\_\_init\_\_.py` – Blueprint setup.
- **meetings/** – Meeting management.
  - `routes.py` – Coordinator views to create and edit meetings, manage members and files.
  - `forms.py` – Meeting form and CSV member import form.
  - `\_\_init\_\_.py` – Blueprint setup.
- **notifications/** – Unsubscribe/resubscribe endpoints.
  - `routes.py` – Manage email preferences.
  - `\_\_init\_\_.py` – Blueprint setup.
- **ro/** – Returning Officer tools.
  - `routes.py` – Quorum tracking, stage locking and results downloads.
  - `\_\_init\_\_.py` – Blueprint setup.
- **submissions/** – Public motion/amendment submissions.
  - `routes.py` – Submission forms and chair/board review screens.
  - `forms.py` – Submission and amendment forms.
  - `\_\_init\_\_.py` – Blueprint setup.
- **voting/** – Ballot handling by token.
  - `routes.py` – Stage 1 and Stage 2 ballots and run‑off flows.
  - `\_\_init\_\_.py` – Blueprint setup.

### Services
- **services/audit.py** – Record administrative actions for the audit log.
- **services/email.py** – Build and send all emails (invites, reminders, receipts, board notices).
- **services/runoff.py** – Detect ties and create run‑off ballots.

### Scheduler Jobs
The APScheduler instance registers several periodic tasks when the app starts:
- `stage1_reminders` – email members when Stage 1 voting is almost closed.
- `stage2_reminders` – send reminders for Stage 2 closing soon.
- `token_cleanup` – remove used or expired vote tokens each day.
- `objection_check` – process amendment objection deadlines hourly.
- `submission_invites` – dispatch submission invites when the window opens.

### Static files and templates
- **static/** – Compiled CSS/JS assets and a sample member CSV.
- **templates/** – Jinja templates grouped by blueprint name.

## Other Directories
- **assets/** – Logos and screenshots for documentation.
- **docs/** – Background documentation including product requirements, database reference and design guidance.
- **migrations/** – Alembic environment and revision scripts under `versions/`.
- **scripts/** – Helper scripts such as `zap_baseline.py` for security scanning.
- **tests/** – Pytest suite covering all modules. Files like `test_admin_dashboard.py`, `test_voting.py` and `test_scheduler.py` verify the corresponding blueprints and services.

