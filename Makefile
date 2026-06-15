.PHONY: up down logs migrate test integration-test demo lint format mypy

up:
	docker compose up --build -d
	./scripts/wait-for-services.sh

down:
	docker compose down

logs:
	docker compose logs -f

migrate:
	docker compose run --rm migration

test:
	uv run pytest tests/unit

integration-test:
	RUN_COMPOSE_INTEGRATION=1 uv run pytest tests/integration

demo:
	./scripts/demo.sh

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src

format:
	uv run ruff format .
	uv run ruff check --fix .

mypy:
	uv run mypy src
