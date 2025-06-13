# vote-buddy
Votebuddy is for running AGMs/EGMs for membership organisations.

## Development setup

1. Copy `.env.example` to `.env` and adjust if needed.
2. Build and start the stack:

   ```bash
   docker-compose up --build
   ```

The web container runs database migrations on startup and exposes the
application on `http://localhost:8000`.
