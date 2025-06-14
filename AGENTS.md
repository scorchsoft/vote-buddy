# AGENTS.md – Repo-wide Agent Guide
## Purpose & Scope
This guide directs AI and human contributors for all folders in this repository.

## Project Map
- `app/` – Flask blueprints, models and templates
- `migrations/` – Alembic migration scripts
- `docs/` – product requirements and design notes
- `docker-compose.yml` and `Dockerfile` – local dev environment

## Coding Conventions
- Language: Python 3.12 with Flask 3
- Style: PEP 8, 4-space indents
- Class names use `PascalCase`; functions and variables use `snake_case`
- HTML templates follow the naming examples from `docs/ui-ux-design-guidance.md`
- Custom CSS classes should be prefixed `bp-`; avoid heavy JavaScript
- htmx: ensure htmx is used where appropriate (if not overkill), such as for CRUDS.

## Toolchain Commands
| Task | Command |
|------|--------|
| Start containers | `docker-compose up --build` |
| Run dev server | `flask --app app run` |
| Apply migrations | `flask db upgrade` |

## Documentation Rules
- When merging a feature PR, append a date + summary to `docs/prd.md` under **Changelog**.
- Minor tweaks to `docs/ui-ux-design-guidance.md` may be committed with `[ci skip]` in the message.
- If headings change in `docs/ui-ux-design-guidance.md`, update internal links in `README.md` or the PR will fail.

## Pull-Request Checklist
1. Include migrations or documentation updates when relevant.
2. Ensure the app starts with `docker-compose up --build`.
3. Keep commits focused; follow Conventional Commits style if possible.

## Agent Rules
- Prompt instructions override AGENTS.md if they conflict.
- Do not write secrets to the repo. Use environment variables as per `.env.example`.
- Run toolchain commands above before committing changes.

## Environment Variables
- `DATABASE_URL` – PostgreSQL connection string
- `SECRET_KEY` – Flask session secret

## Troubleshooting
If the repo becomes unstable, reset with:
```
git clean -fd && git reset --hard HEAD
```

Docker-compose commands dont work in OpenAI Codex, you'll get this error so dont bither trying:
```
docker-compose up --build -d (failed to run: docker-compose: command not found
```

When running flask for testing try a non standard port as sometimes we get this error:
```
flask --app app run (failed: port already in use in second attempt)
```

## Change Log
| Date | Author | Reason |
|------|--------|-------|
| 2025-06-13 | Initial draft | Repository documentation for agents |

