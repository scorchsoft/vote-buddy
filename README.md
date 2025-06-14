# VoteBuddy (Open source AGM and EGM software for membership organisations)

VoteBuddy by [Scorchsoft](https://www.scorchsoft.com) is a Python Flask application for running electronic ballots at AGMs and EGMs, and was originally programmed for use by British Powerlifting.

It supports two stage voting on amendments and final motions, sends unique voting links by email and produces auditable results.

## Features

- Flask 3 with SQLAlchemy ORM
- PostgreSQL database managed via Alembic migrations
- Dockerised development stack with Gunicorn
- Modular blueprints for auth, meetings, voting and admin
- Models for meetings, members, amendments and votes

## Development setup

1. Copy `.env.example` to `.env` and review the values.
2. Build and start the containers:

```bash
docker-compose up --build
```

3. Install Node dependencies and compile the Tailwind CSS:

```bash
npm install
npm run build:css
```

The `web` service runs migrations on start and exposes the app at `http://localhost:8000`.

To run the development server directly on your machine, install the requirements and execute:

```bash
flask --app app run
```

## Repository layout

```
app/            Flask application with blueprints, templates and static files
migrations/     Alembic migration scripts
Dockerfile      Container image definition
config.py       Application configuration classes
docs/           Project documentation
```

### Documentation

The `docs` directory contains background and design material:

- **prd.md** – Product Requirements Document describing the MVP goals, system architecture and work plan.
- **ui-ux-design-guidance.md** – Guidance on branding, layout and component conventions for building a consistent user experience.
- **voting-process-motion.md** – The full text of the motion modernising British Powerlifting's voting procedure which this app implements.

Refer to these files for detail on features, design and governance context.

## Contributing

Pull requests are welcome. Please include updates to migrations or documentation where relevant.
