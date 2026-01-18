auth-service/
├─ app/
│  ├─ main.py
│  ├─ core/
│  ├─ api/
│  ├─ db/
│  ├─ models/
│  ├─ schemas/
│  ├─ crud/
│  └─ services/
├─ alembic/
├─ docker/
├─ tests/
├─ docker-compose.yml
├─ requirements.txt
├─ .env.example
└─ README.md


### Build Docker
docker compose up -d --build

### Alembic init
docker compose exec auth-service python -m alembic init alembic
docker compose exec auth-service python -m alembic revision --autogenerate -m "add profile fields sessions and password reset"
docker compose exec auth-service python -m alembic upgrade head

### Check Alembic in Container
docker compose exec auth-service python -m alembic --version

## View Error from Containter
docker compose logs --tail=120 auth-service

### Unit Test from Pytest 
docker compose exec auth-service bash -lc "PYTHONPATH=/app python -m pytest -q"

