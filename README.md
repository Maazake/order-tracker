# Order Tracker

[![CI](https://github.com/Maazake/order-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Maazake/order-tracker/actions/workflows/ci.yml)

REST API for tracking production orders in a machining workshop. Every order moves through a fixed sequence of manufacturing steps: cutting, turning, milling, polishing, washing, quality control and packing. Operators start and complete steps, and the API enforces the order in which that can happen.

## Tech stack

- **Python 3.14**, **FastAPI**
- **PostgreSQL**, **SQLAlchemy 2.0** (typed `Mapped[]` models), **Alembic** migrations
- **JWT** authentication (PyJWT), Argon2 password hashing (pwdlib)
- **pydantic-settings** for configuration
- **pytest** with FastAPI `TestClient`, **ruff**, **pre-commit**, **GitHub Actions**
- **uv** for dependency management

## Features

- **Orders.** Creating an order creates all 7 process steps in a single transaction, so an order never exists without its steps.
- **Step workflow.** `pending → in_progress → done`, with rules enforced by the API:
  - a step can only be started when the previous step is `done`,
  - a step can only be completed when it is `in_progress`,
  - starting a step assigns an employee and records `started_at`; completing it records `completed_at` and an optional note.
- **Listing orders** with pagination (`limit`, `offset`), filtering by step status and sorting by any column (ascending or descending). Steps and assigned employees are eager-loaded with `selectinload` to avoid N+1 queries.
- **Roles.** `operator` and `admin`, see the permissions table below.

## Design decisions

- **The role is read from the database, not from the token.** The JWT identifies the user; permissions are checked against the current database record on every request. Demoting an admin takes effect immediately instead of when their token expires.
- **Registration cannot grant privileges.** `POST /auth/register` always creates an `operator`. A `role` field in the request body is ignored; this is covered by a test. Admin accounts come from the seed script and environment variables.
- **404 before 409.** When a request refers to something that does not exist (step, employee), the API returns 404 before checking business rules that would return 409. The client always gets the most fundamental error first.
- **Validation lives in schemas.** Input shape is validated by Pydantic (422). Endpoints only handle rules that need the database: duplicate username (409), invalid step transition (409).
- **Fail-fast configuration.** Secrets have no default values. If `SECRET_KEY` is missing or shorter than 32 characters, the application refuses to start and reports every missing variable at once, instead of failing at the first login.
- **Responses are filtered by `response_model`.** Fields like `hashed_password` can never leak into a response by accident.

## API overview

| Method | Endpoint | Access |
|---|---|---|
| `POST` | `/auth/register` | public |
| `POST` | `/auth/login` | public |
| `GET` | `/users/me` | logged in |
| `GET` | `/users` | admin |
| `GET` | `/orders` | logged in |
| `GET` | `/orders/{id}` | logged in |
| `POST` | `/orders` | admin |
| `DELETE` | `/orders/{id}` | admin |
| `POST` | `/steps/{id}/start` | logged in |
| `POST` | `/steps/{id}/complete` | logged in |
| `GET` | `/employees` | admin |
| `POST` | `/employees` | admin |

Interactive documentation is available at `/docs` once the app is running.

Example query: `GET /orders?status=in_progress&sort=planned_completion_date&desc=true&limit=20`

## Running locally

Requirements: [uv](https://docs.astral.sh/uv/) and Docker.

```bash
git clone https://github.com/Maazake/order-tracker.git
cd order-tracker

# 1. Start PostgreSQL
docker compose up -d

# 2. Create the config file and fill in the values (instructions inside)
cp .env.example .env
# For the database from docker-compose:
# DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/order_tracker

# 3. Install dependencies, run migrations and load sample data
uv sync
uv run alembic upgrade head
uv run python -m app.seed

# 4. Start the API
uv run fastapi dev
```

Open http://localhost:8000/docs and log in with `ADMIN_USERNAME` / `ADMIN_PASSWORD` from your `.env`.

## Tests and code quality

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The test suite covers the happy paths and error paths: 401 (missing, expired, forged or malformed tokens), 403 (operator calling admin endpoints), 404, 409 (invalid step transitions, duplicate username) and 422 (invalid query parameters and request bodies). Configuration for tests is provided by `pytest-env`, so no `.env` file is needed.

- **pre-commit** runs ruff (lint and format) before every commit.
- **GitHub Actions** runs ruff and the full test suite on every pull request and on every push to `master`.

## Project structure

```
app/
  main.py       # endpoints
  models.py     # SQLAlchemy models
  schemas.py    # Pydantic request/response schemas
  security.py   # password hashing, JWT, auth dependencies
  config.py     # settings loaded from environment
  database.py   # engine and session
  seed.py       # sample data and admin account
alembic/        # database migrations
tests/          # API tests
```

## Roadmap

- [ ] Move business logic into a service layer; seed realistic data through it
- [ ] Dockerfile for the application
- [ ] Deployment with a live demo and demo accounts
