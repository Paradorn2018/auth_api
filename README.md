### Build Docker Developer Environment
docker compose --profile dev --env-file .env.dev up -d --build

### Unit Test from Pytest (dev environment only)
docker compose --env-file .env.dev exec auth-service bash -lc "PYTHONPATH=/app python -m pytest -q"

### Build Docker Production Environment
docker compose --profile prod --env-file .env.prod up -d --build