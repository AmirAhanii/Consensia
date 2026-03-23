.PHONY: up up-build down rebuild logs

# Runs backend + frontend using Docker Compose.
# `up-build` forces image rebuild (useful if you changed Dockerfiles / deps).
up:
	docker compose up

up-build:
	docker compose up --build

down:
	docker compose down

# Convenience alias
rebuild: down up-build

logs:
	docker compose logs -f

