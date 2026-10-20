# install dependencies and git hooks
setup:
    uv sync
    uv run pre-commit install

# check code style and types, no changes written
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy

test:
    uv run pytest
