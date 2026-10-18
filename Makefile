COMPOSE := docker compose
QUALITY_IMAGE := rrii-coach-quality:local
QUALITY_RUN := docker run --rm \
	--user "$$(id -u):$$(id -g)" \
	-e PRE_COMMIT_HOME=/workspace/.cache/pre-commit \
	-v "$(CURDIR):/workspace" \
	$(QUALITY_IMAGE)

.PHONY: up down build logs ps backend-shell frontend-shell db-shell migrate \
	test lint typecheck format format-check openapi clean destroy e2e check ci \
	precommit precommit-install precommit-all quality-image db-upgrade \
	db-downgrade db-current db-history db-revision db-check test-integration check-local

up:
	$(COMPOSE) up --build

down:
	$(COMPOSE) down

build:
	$(COMPOSE) build

logs:
	$(COMPOSE) logs --follow

ps:
	$(COMPOSE) ps

backend-shell:
	$(COMPOSE) exec backend sh

frontend-shell:
	$(COMPOSE) exec frontend sh

db-shell:
	$(COMPOSE) exec db sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

migrate:
	@echo "El objetivo 'migrate' es un alias de 'db-upgrade'."
	$(MAKE) db-upgrade

db-upgrade:
	$(COMPOSE) exec backend uv run alembic upgrade head

db-downgrade:
	@test "$(CONFIRM)" = "DOWNGRADE" || { \
		echo "Operación potencialmente destructiva."; \
		echo "Repetir con: make db-downgrade CONFIRM=DOWNGRADE"; \
		exit 1; \
	}
	$(COMPOSE) exec backend uv run alembic downgrade -1

db-current:
	$(COMPOSE) exec backend uv run alembic current

db-history:
	$(COMPOSE) exec backend uv run alembic history

db-revision:
	@test -n "$(MESSAGE)" || { \
		echo 'Falta MESSAGE. Ejemplo: make db-revision MESSAGE="crear tabla técnica"'; \
		exit 1; \
	}
	$(COMPOSE) exec backend uv run alembic revision --autogenerate -m "$(MESSAGE)"

db-check:
	./scripts/check_migrations.sh

test-integration:
	./scripts/test_integration.sh

test:
	$(COMPOSE) exec backend uv run pytest -m "not integration"
	$(COMPOSE) exec frontend pnpm test

lint:
	$(COMPOSE) exec backend uv run ruff check .
	$(COMPOSE) exec frontend pnpm lint

format-check:
	$(COMPOSE) exec backend uv run ruff format --check .

typecheck:
	$(COMPOSE) exec backend uv run mypy app tests
	$(COMPOSE) exec frontend pnpm typecheck

format:
	$(COMPOSE) exec backend uv run ruff format .
	$(COMPOSE) exec backend uv run ruff check --fix .

openapi:
	./scripts/export_openapi.sh

e2e:
	$(COMPOSE) exec frontend pnpm test:e2e

check: lint format-check typecheck test

ci: check-local

check-local:
	./scripts/check-local.sh

quality-image:
	docker build -t $(QUALITY_IMAGE) -f infra/quality/Dockerfile .

precommit: quality-image
	$(QUALITY_RUN) run

precommit-all: quality-image
	$(QUALITY_RUN) run --all-files
	@files="$$(git ls-files --others --exclude-standard)"; \
	if [ -n "$$files" ]; then \
		$(QUALITY_RUN) run --files $$files; \
	fi

precommit-install:
	@command -v pre-commit >/dev/null 2>&1 || { \
		echo "Falta pre-commit en el host. Instalarlo de forma aislada con:"; \
		echo "  pipx install pre-commit==4.6.0"; \
		exit 1; \
	}
	pre-commit install

clean:
	$(COMPOSE) down --remove-orphans
	@echo "Contenedores detenidos. Los volúmenes persistentes se conservaron."

destroy:
	@echo "ADVERTENCIA: este comando eliminará la base y los assets locales."
	@printf "Escriba ELIMINAR para continuar: "; read answer; \
		test "$$answer" = "ELIMINAR"
	$(COMPOSE) down --volumes --remove-orphans
