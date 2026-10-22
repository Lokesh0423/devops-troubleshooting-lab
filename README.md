# Orders Service

A hands-on DevOps learning project: a Flask orders API running with Gunicorn and PostgreSQL, managed through Docker Compose.

The project explores container builds, deployment verification, persistent storage, and incident troubleshooting in a local environment.

## Stack

- Python 3.12, Flask, Gunicorn
- PostgreSQL 17
- Psycopg PostgreSQL driver
- Docker and Docker Compose
- Git and GitHub

## How it works

Requests to `http://localhost:8000` reach the app container. The app connects to PostgreSQL through the Compose service name `db` on port 5432. PostgreSQL stores its files in the named volume `orders_data` (normally prefixed with the Compose project name).

Only the app port is published, bound to localhost. The database port is available inside the Compose network.

## Project files

| File | Purpose |
| --- | --- |
| `app/app.py` | API routes, validation, database connections, table initialization |
| `app/requirements.txt` | Python dependencies |
| `Dockerfile` | Application image build and startup instructions |
| `compose.yaml` | App, database, network, health check, and volume settings |
| `.gitignore` | Excludes local secrets and Python cache files |

## Run locally

Prerequisites: Git, Docker Engine/Desktop running with Linux containers, and Docker Compose. Commands below use Bash or Git Bash.

### 1. Clone

```bash
git clone https://github.com/Lokesh0423/orders-service.git
cd orders-service
```

### 2. Configure the database password

Create a file named `.env` in the project root:

```dotenv
POSTGRES_PASSWORD=replace_with_a_local_password
```

Use a non-empty password containing letters, numbers, and underscores for this example. The current Compose configuration embeds it directly in a connection URL; other special characters require URL encoding.

Keep `.env` out of Git. Verify the ignore rule:

```bash
git check-ignore .env
```

PostgreSQL initialization settings apply when the data directory is first created. Changing this variable later does not change the password stored in an existing database.

### 3. Build and start

```bash
docker compose up -d --build
docker compose ps
```

Compose waits for the database health check before starting the app. Container startup alone does not prove the application is ready.

### 4. Initialize the orders table

```bash
docker compose exec app python -c "from app import init_db; init_db()"
```

Run this once for a new database. It uses `CREATE TABLE IF NOT EXISTS`, so repeating it does not delete existing orders. This is a simple learning setup, not a schema migration system.

### 5. Verify

```bash
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Both should return HTTP 200. The readiness check verifies database connectivity with `SELECT 1`; it does not verify that the orders table exists.

## API examples

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Service information |
| GET | `/health` | App responds to HTTP requests |
| GET | `/ready` | Database connectivity |
| POST | `/orders` | Create an order |
| GET | `/orders` | List orders by ID |

### Create an order

```bash
curl -i -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item":"Biryani","quantity":2}'
```

Expected status: `201 CREATED`. Example response for a fresh database:

```json
{"id":1,"item":"Biryani","quantity":2}
```

The item must be a non-empty string and quantity must be a positive integer. Invalid input returns HTTP 400.

### List orders

```bash
curl -i http://localhost:8000/orders
```

Expected status: `200 OK`.

```json
[{"id":1,"item":"Biryani","quantity":2}]
```

Database errors are logged and return HTTP 503.

## Operations and troubleshooting

```bash
# Include stopped containers
docker compose ps -a

# Last 30 app or database log lines
docker compose logs --tail 30 app
docker compose logs --tail 30 db

# Follow application logs (Ctrl+C exits the viewer)
docker compose logs -f app
```

### Incident 1: Image builds, but application fails to start

**Observed:** Gunicorn reported `Failed to find attribute 'app' in 'app'`.

**Cause:** An empty `app.py` was copied into the image.

**Resolution:** Save the application code, rebuild the image, and replace the container. Verify startup logs and an HTTP response.

**Lesson:** A successful image build does not prove that the application starts.

### Incident 2: Orders disappear after an app restart

**Observed:** The initial implementation returned an empty list after restart.

**Cause:** Orders were stored in a Python list in process memory.

**Resolution:** Store orders in PostgreSQL. Verify that orders remain after an app restart:

```bash
docker compose restart app
# After the app is ready:
curl -i http://localhost:8000/orders
```

A named volume retains PostgreSQL data when containers are replaced. To test this locally after creating an order:

```bash
docker compose down
docker compose up -d
# Once ready, verify the existing order:
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/orders
```

Do not add `-v` to `docker compose down` when retaining the database: it removes the Compose-managed named volume. A volume provides persistence, not a backup.

### Incident 3: App running, database unavailable

Stop the database in the local lab:

```bash
docker compose stop db
curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/orders
```

Observed responses:

| Endpoint | Status |
| --- | --- |
| `/health` | 200 |
| `/ready` | 503 |
| `/orders` | 503 |

The app stayed running while database-dependent operations failed. Logs showed a failure to resolve the stopped `db` service.

Recover the database:

```bash
docker compose start db
docker compose ps
# Once the database is healthy:
curl -i http://localhost:8000/ready
curl -i http://localhost:8000/orders
```

**Verified recovery:** Both endpoints returned HTTP 200 and the saved order remained, without restarting the app.
