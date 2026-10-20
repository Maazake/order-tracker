# Order Tracker

[![CI](https://github.com/Maazake/order-tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/Maazake/order-tracker/actions/workflows/ci.yml)

REST API for tracking production orders in a machining workshop. Every order moves through a fixed sequence of manufacturing steps: cutting, turning, milling, polishing, washing, quality control and packing. Operators start and complete steps, and the API enforces the order in which that can happen.

## Tech stack

- **Python 3.14**, **FastAPI**
- **PostgreSQL**, **SQLAlchemy 2.0** (typed `Mapped[]` models), **Alembic** migrations
- **JWT** authentication (PyJWT), Argon2 password hashing (pwdlib)
- **pydantic-settings** for configuration
- **pytest** with FastAPI `TestClient`, **ruff**, **pre-commit**, **GitHub Actions**
- **uv** for dependency management, **Docker** and Docker Compose for running the app

## Features

- **Orders.** Creating an order creates all 7 process steps in a single transaction, so an order never exists without its steps.
- **Step workflow.** `pending → in_progress → done`, with rules enforced by the API:
  - a step can only be started when the previous step is `done`,
  - a step can only be completed when it is `in_progress`,
  - starting a step assigns an employee and records `started_at`; completing it records `completed_at` and an optional note.
- **Listing orders** with pagination (`limit`, `offset`), filtering by step status and sorting by any column (ascending or descending). Steps and assigned employees are eager-loaded with `selectinload` to avoid N+1 queries.
- **Roles.** `operator` and `admin`, see the permissions table below.
- **Demo data.** The seed script loads 5 employees and 7 orders at different stages: fresh, in progress, in quality control, finished, and one overdue order stuck mid-production. Completed steps have realistic timestamps and technical notes.

## Design decisions

- **The role is read from the database, not from the token.** The JWT identifies the user; permissions are checked against the current database record on every request. Demoting an admin takes effect immediately instead of when their token expires.
- **Registration cannot grant privileges.** `POST /auth/register` always creates an `operator`. A `role` field in the request body is ignored; this is covered by a test. Admin accounts come from the seed script and environment variables.
- **404 before 409.** When a request refers to something that does not exist (step, employee), the API returns 404 before checking business rules that would return 409. The client always gets the most fundamental error first.
- **Validation lives in schemas.** Input shape is validated by Pydantic (422). Endpoints only handle rules that need the database: duplicate username (409), invalid step transition (409).
- **Fail-fast configuration.** Secrets have no default values. If `SECRET_KEY` is missing or shorter than 32 characters, the application refuses to start and reports every missing variable at once, instead of failing at the first login.
- **Business logic lives in a service layer.** `app/services.py` contains the rules (create an order with its steps, start and complete a step) and knows nothing about HTTP. It raises domain exceptions (`NotFoundError`, `ConflictError`), which exception handlers in `main.py` map to 404 and 409. Endpoints only handle HTTP: authentication, request parsing, committing the transaction.
- **Services flush, callers commit.** A service never commits on its own, so several operations can run in one transaction. An endpoint commits after a single service call; the seed script commits once after building all demo data.
- **Demo data is replayed, not inserted.** The seed script creates orders and moves them through their steps by calling the same services as the API, with timestamps moved into the past. Demo data can never be in a state the API would not allow. The script is idempotent and never drops tables; the schema is managed only by Alembic.
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

### Option 1: everything in Docker

Requirements: Docker.

```bash
git clone https://github.com/Maazake/order-tracker.git
cd order-tracker

# 1. Create the config file and fill in the values (instructions inside)
cp .env.example .env

# 2. Build and start the database and the API
#    (migrations run automatically when the API container starts)
docker compose up --build

# 3. In a second terminal: load demo data
docker compose exec api python -m app.seed
```

The API container gets its `DATABASE_URL` from `docker-compose.yml`, pointing at the `db` service, so the value in `.env` only matters for option 2.

### Option 2: API on your machine, database in Docker

Better for development: code changes reload automatically. Requirements: [uv](https://docs.astral.sh/uv/) and Docker.

```bash
# 1. Start only PostgreSQL
docker compose up -d db

# 2. In .env, point the app at the database exposed on localhost:
# DATABASE_URL=postgresql+psycopg2://postgres:postgrespassword@localhost:5432/order_tracker

# 3. Install dependencies, run migrations and load demo data
uv sync
uv run alembic upgrade head
uv run python -m app.seed

# 4. Start the API with auto-reload
uv run fastapi dev
```

### Logging in

Open http://localhost:8000/docs, click **Authorize** and log in with one of the accounts:

| Account | Role | Password |
|---|---|---|
| `demo` | operator | `demo1234` |
| `ADMIN_USERNAME` from `.env` | admin | `ADMIN_PASSWORD` from `.env` |

The `demo` account is public on purpose: it can browse orders and start or complete steps, but cannot create or delete anything.

## Tests and code quality

Tests run against a real PostgreSQL database, separate from the development one. Create it once:

```bash
docker compose exec db psql -U postgres -c "CREATE DATABASE order_tracker_test;"
```

Then:

```bash
uv run pytest --cov=app --cov-report=term-missing
uv run ruff check .
uv run ruff format --check .
```

The test suite covers the happy paths and error paths: 401 (missing, expired, forged or malformed tokens), 403 (operator calling admin endpoints), 404, 409 (invalid step transitions, duplicate username) and 422 (invalid query parameters and request bodies). Configuration for tests is provided by `pytest-env`, so no `.env` file is needed. As a safety guard, the test suite refuses to run unless the database name contains `test`, because every test drops and recreates the tables.

- **pre-commit** runs ruff (lint and format) before every commit.
- **GitHub Actions** starts a PostgreSQL service container and runs ruff and the full test suite with coverage (minimum 95%) on every pull request and on every push to `master`.

## Project structure

```
app/
  main.py       # endpoints and exception handlers
  services.py   # business logic: orders and step transitions
  exceptions.py # domain exceptions (NotFoundError, ConflictError)
  models.py     # SQLAlchemy models
  schemas.py    # Pydantic request/response schemas
  security.py   # password hashing, JWT, auth dependencies
  config.py     # settings loaded from environment
  database.py   # engine and session
  seed.py       # demo data, admin and demo accounts
alembic/        # database migrations
tests/          # API tests
Dockerfile      # API image: dependencies layer first, then code
docker-compose.yml  # PostgreSQL + API
```

## Roadmap

- [ ] Deployment with a live demo and demo accounts
