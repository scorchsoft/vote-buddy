# Unit Test Strategy

This project uses **pytest** for all automated testing. The tests live in the
`tests/` directory and can be run with:

```bash
pytest -q
```

## Fixtures

* **Application setup** – Where tests require a Flask application or database,
they should create an app using `app.create_app()` and configure it to use the
in‑memory SQLite database (`sqlite:///:memory:`). The database can be initialised
with `db.create_all()` inside the fixture.
* **Mocking** – External services and the current user should be mocked using
`unittest.mock.patch`.

## Writing tests

* Focus on individual functions and lightweight route testing.
* Avoid hitting external systems or the real database; rely on in‑memory SQLite
and mocks instead.
* Keep tests fast so they can run on every PR.

## Running in CI

Tests should pass locally and in any CI environment by just installing
`requirements.txt` and running `pytest`. No Docker services are required for unit
tests, keeping the feedback loop quick.
