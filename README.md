**THIS IS CURRENTLY AN IN-DEVELOPMENT REPOSITORY**
Functionality and information IS incompete and WILL contain errors

# VoteBuddy (Free and Open source AGM and EGM software for membership organisations)

VoteBuddy by [Scorchsoft](https://www.scorchsoft.com) is an Open Source web application that membership organisations can run online voting for two stage electronic ballots at AGMs and EGMs.

It supports two stage voting on amendments and final motions, sends unique voting links by email and produces auditable results.

VoteBuddy aims to apply principles from UK Parliamentary Proceedure as well as "Roberts Rules" around governance and effective meetings, to make an online ballot format that is robust and but simple enough to understand as to be inclusive.

VoteBuddy also includes a [special resolution motion template](docs/template-motion.md) to guide you through implementing the governance changes necessary for your organisation to follow this tool's recommended process.

![Admin dashboard screenshot](assets/screenshots_v0_4/admin-dashboard.png)

## Features

- Flask 3 with SQLAlchemy ORM
- PostgreSQL database managed via Alembic migrations
- Dockerised development stack with Gunicorn
- Modular blueprints for auth, meetings, voting, admin and RO dashboards
- Models for meetings, members, motions, amendments, vote tokens, votes and
  run-offs with role/permission support
- Hashed vote tokens and ballot receipts for verifiable results
- Automated run-off ballots with Stage 1 extensions on ties
- Email reminders and token resends scheduled via APScheduler
- iCalendar downloads for Stage 1 and Stage 2 voting windows
- Results exports to CSV and DOCX plus audit logs
- Clone meetings to duplicate motions and amendments
- Token-based forms for submitting motions and amendments with coordinator review
- Optional unsubscribe tokens for members
- Resubscribe links allow members to opt back in to emails
- Manual tally entry for in-person meetings with PDF results export
- Live countdown timers and progress bars on public pages
- Early Stage 1 results page and token-based public API with rate limits
- Password reset flow via emailed tokens
- File uploads per meeting with optional public links
- Built in Python (Flask)

## Screenshots

The following images show key features and interfaces of VoteBuddy. For a comprehensive gallery of all screenshots, see our [detailed screenshots page](screenshots.md).

### Admin Dashboard & Management

The admin dashboard provides a central hub for managing meetings and monitoring voting progress
![Admin dashboard screenshot](assets/screenshots_v0_4/admin-dashboard.png)

Control user access and permissions with the enhanced user management interface
![Admin users screenshot](assets/screenshots_v0_4/admin-user-management.png)

Manage all meetings from a central admin interface with improved overview
![Admin meeting list screenshot](assets/screenshots_v0_4/admin-view-meetings.png)

### Meeting Management

See the status of meetings and motions with a comprehensive overview and timeline
![Meeting overview screenshot](assets/screenshots_v0_4/admin-meeting-overview.png)

Create new meetings with an intuitive form interface
![Admin create meeting screenshot](assets/screenshots_v0_4/admin-create-meeting.png)

### Public Interface

The main home page welcomes members and provides access to meetings
![Home page screenshot](assets/screenshots_v0_4/home-page.png)

Public meetings list shows all available meetings that members can access
![Public meetings screenshot](assets/screenshots_v0_4/meetings-public.png)

### Voting & Results

Members can easily cast their votes using the comprehensive voting interface
![Voting interface screenshot](assets/screenshots_v0_4/voting-motion-amend-review.png)

View detailed charts and visualizations of voting results
![View results charts screenshot](assets/screenshots_v0_4/results-public-charts.png)

Detailed tabular view of voting results with comprehensive breakdown
![View results table screenshot](assets/screenshots_v0_4/results-public-table.png)

### Settings & Configuration

Customize system-wide settings and branding
![Application settings screenshot](assets/screenshots_v0_4/app-settings.png)

Returning officers can monitor voting progress and manage the process
![Returning officer dashboard screenshot](assets/screenshots_v0_4/returning-officer-dash.png)

### Help & Documentation

Comprehensive help documentation guides users through the voting process
![Help section screenshot](assets/screenshots_v0_4/help-example.png)

### Additional Features

The application also includes advanced features like:
- Interactive commenting system for motions and amendments  
- Professional email templates for member communication
- Comprehensive audit trails and reporting
- Motion and amendment submission workflows

**[View all screenshots →](screenshots.md)**

## Development setup

1. Copy `.env.example` to `.env`.
   
   **On Linux/macOS:**
   
   ```bash
   cp .env.example .env
   ```
   
   **On Windows (in Command Prompt or PowerShell):**
   
   ```powershell
   copy .env.example .env
   ```
   
   Then, review the values in the new `.env` file. The defaults include options for email reminders and run-off timing such as
   `RUNOFF_EXTENSION_MINUTES`, `REMINDER_HOURS_BEFORE_CLOSE`,
   `REMINDER_COOLDOWN_HOURS`, `REMINDER_TEMPLATE`,
   `STAGE2_REMINDER_HOURS_BEFORE_CLOSE`, `STAGE2_REMINDER_COOLDOWN_HOURS`,
   `STAGE2_REMINDER_TEMPLATE`, `TIE_BREAK_DECISIONS` and `MAIL_USE_TLS`. These can later be changed in the Settings UI.
   `SECRET_KEY`, `TOKEN_SALT`, `API_TOKEN_SALT` and `UPLOAD_FOLDER` are also defined here. `SECRET_KEY`, `TOKEN_SALT` and `API_TOKEN_SALT` must be set to unique values in production. `UPLOAD_FOLDER` determines where uploaded files are stored. The optional `TIMEZONE` variable sets the timezone for calendar downloads and defaults to `Europe/London`.

2. Install the Python packages:

```bash
pip install -r requirements.txt
```

If the `flask` command isn't found after installation, run commands using
`python -m flask --app app` instead of `flask`.

3. Build and start the containers:

```bash
docker-compose up --build
```

Note that you don't have to run this with Docker. The app will also run locally if you have Python, Node and PostgreSQL installed.

### Running without Docker

1. Install PostgreSQL and create a database and user.
   
   **On Linux/macOS:**
   
   ```bash
   sudo -u postgres createuser -P vote_buddy
   sudo -u postgres createdb -O vote_buddy vote_buddy
   ```
   
   **On Windows:**
   
   If you get an error that `createuser` cannot be found, your `PATH` environment variable may not include the PostgreSQL `bin` directory. A PowerShell script is included to help with this. Open a PowerShell terminal and run:
   
   ```powershell
   .\scripts\setup-pg-path.ps1
   ```
   
   You may need to restart your terminal for the change to take effect. if this fails you can also just copy and paste its contents into powershell. This script finds where PostgresSQL is installed, then auto assigns that to path for you.
   
   Once your `PATH` is configured, run these commands:
   
   ```powershell
   createuser -P -U postgres vote_buddy
   createdb -O vote_buddy -U postgres vote_buddy
   ```
   
   You will be prompted for the `postgres` user's password, and then to set a password for the new `vote_buddy` user.

2. Edit your copied `.env` and point `DATABASE_URL` at the new user:

```env
DATABASE_URL=postgresql+psycopg://vote_buddy:<password>@localhost:5432/vote_buddy
```

3. Apply the migrations locally:

```bash
python -m flask --app app db upgrade
```

From here you can continue with the remaining steps such as building the CSS and creating an admin account.

4. Install Node dependencies and compile the Tailwind CSS:

```bash
npm install
npm run build:css
```

Running the build now uses a local copy of htmx rather than fetching it from the
internet.

5. Create an initial admin user:

```bash
flask --app app create-admin
```

or if you want to run via the python module
```bash
python -m flask --app app create-admin
```

set email and pass to whatever you like, then the role to root_admin

The `web` service runs migrations on start and exposes the app at `http://localhost:8000`.

To run the development server directly on your machine, first install the requirements and then execute:

```bash
FLASK_APP=app flask run --port 5555
```

If the `flask` command is unavailable, use:

```bash
python -m flask --app app run --port 5555
```

or to run in debug mode (recommended for testing)
```bash
python -m flask --app app --debug run --port 5555
```

Or more simply if running locally where there may not be port conflicts:

```bash
python -m flask --app app run
```

### Generating demo data

You can seed a fresh development database with example meetings and members using the
`generate-fake-data` CLI command:

```bash
python -m flask --app app generate-fake-data
```

This creates demo coordinator and returning officer accounts and inserts several sample meetings with
random members, motions, amendments and recorded votes. **Run it only on a local database** as it may
conflict with real data and could trigger emails if your mail settings are active.

### Running tests

Install the dependencies and execute:

```bash
pytest -q
```

### Local email testing

To prevent real emails being sent during local testing, set `MAIL_SUPPRESS_SEND=1` in your environment:

```bash
export MAIL_SUPPRESS_SEND=1
```

You can also run a local SMTP capture tool like [MailHog](https://github.com/mailhog/MailHog) and point
`MAIL_SERVER` and `MAIL_PORT` to it, e.g. `MAIL_SERVER=localhost` and `MAIL_PORT=1025`.

### Security testing

Run the automated OWASP ZAP baseline scan against the local server:

```bash
scripts/zap_baseline.py
```

## Repository layout

```
app/            Flask application modules and templates
assets/         Branding assets and uploaded files
migrations/     Alembic migration scripts
tests/          Pytest unit tests
Dockerfile      Container image definition
docker-entrypoint.sh  Entrypoint used in the container
config.py       Application configuration classes
docs/           Project documentation
package.json, tailwind.config.cjs  Front-end build configuration
requirements.txt    Python dependencies
wsgi.py         App entry for Gunicorn
```

### Public API

Token-authenticated endpoints provide read-only access to meeting results.
Generate a token in the admin dashboard then query using the `Authorization`
header:

```bash
curl -H "Authorization: Bearer <token>" https://example.com/api/meetings
```

See the [API Docs](/api/docs) page for full details. Endpoints include
`/meetings/{id}/stage1-results` once Stage 1 tallies are published.

### Documentation

The `docs` directory contains background and design material:

- **prd.md** – Product Requirements Document describing the MVP goals, system architecture and work plan.
- **ui-ux-design-guidance.md** – Guidance on branding, layout and component conventions for building a consistent user experience.
- **original-british-powerlifting-voting-process-motion.md** – The full text of the motion modernising British Powerlifting's voting procedure which this app implements.
- **template-motion.md** - A more readily adoptable motion template that membership organisations can revise and adopt to make their Articles support the VoteBuddy process.
- **full-database-structure.md** – Quick reference describing all database tables and columns.
- **app-settings-guidance.md** – When to store global values in the `app_settings` table.
- **member-import.md** – Steps and CSV format for uploading members and issuing tokens.
- **unit-test-strategy.md** – Fixtures and patterns for the tests under `tests/`.
- **ARCHITECTURE.md** – Overview of the code layout and responsibilities.

Refer to these files for detail on features, design and governance context.


## Handling Alembic "multiple heads" errors (On Windows Locally)

If you see an error like this during `db upgrade`:

```
ERROR [flask_migrate] Error: Multiple head revisions are present for given argument 'head'
```

Run the following command to identify the conflicting heads:

```bash
python -m flask --app app db heads
```

Then merge the revisions (replacing the IDs below with the ones shown on your system):

```bash
python -m flask --app app db merge -m "Merge branches" <head1> <head2>
```

This will generate a merge revision file in `migrations/versions/`. Then rerun the upgrade:

```bash
python -m flask --app app db upgrade
```

This fixes the migration history and prevents the error from blocking deployment.

## Contributing

Pull requests are welcome. Please include updates to migrations or documentation where relevant.

## License

This project is released under the [Apache 2.0](LICENCE.md) license.
