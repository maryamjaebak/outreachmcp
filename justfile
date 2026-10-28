# install dependencies and git hooks
setup:
    uv sync
    uv run pre-commit install
    test -f searxng/settings.yml || sed "s/ultrasecretkey/$(openssl rand -hex 32)/" searxng/settings.yml.template > searxng/settings.yml

# check code style and types, no changes written
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy

test:
    uv run pytest
